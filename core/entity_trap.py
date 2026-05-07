"""
entity_trap.py
--------------
Classe Trap.
"""
import math
import random
import os
import pygame
from core.config import (
    GRID_SIZE, COLS, ROWS, SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, START, END, PLAYER_HP, TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT, TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import ui.sprites as spr
from core.entity_helpers import (
    _crop_alpha_surface, _direction_from_delta, _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)


class Trap:
    """
    Piège sur la grille (invisible pour le pathfinding).

    Sprites dans assets/sprites/traps/ :
        <type>_idle.png    spritesheet idle en boucle (1 frame par niveau si multi-niveaux)
        <type>_attack.png  spritesheet attaque jouée une fois au déclenchement

    Structure mine_idle.png : 3 frames côte à côte (une par niveau)
    Structure spikes_idle.png : N frames en boucle
    """

    # Caches
    _idle_cache   = {}   # {trap_type: SpritesheetAnimator}
    _attack_cache = {}   # {trap_type: SpritesheetAnimator}
    # legacy
    _anim_cache   = {}

    @classmethod
    def load_sprites(cls):
        """
        Charge assets/sprites/traps/<type>_idle.png et <type>_attack.png.
        Fallback sur <type>.png (ancien système).
        """
        traps_dir = os.path.join(_ASSETS_BASE, "traps")
        for trap_type in ("spikes", "mine"):
            idle_path   = os.path.join(traps_dir, f"{trap_type}_idle.png")
            attack_path = os.path.join(traps_dir, f"{trap_type}_attack.png")

            if os.path.isfile(idle_path):
                try:
                    cls._idle_cache[trap_type] = spr.SpritesheetAnimator(
                        idle_path, fps=8, target_size=(GRID_SIZE, GRID_SIZE), loop=True
                    )
                    print(f"[Trap] {trap_type}_idle : {cls._idle_cache[trap_type].n_frames} frames")
                except Exception as e:
                    print(f"[Trap] Erreur {trap_type}_idle : {e}")

            if os.path.isfile(attack_path):
                try:
                    cls._attack_cache[trap_type] = spr.SpritesheetAnimator(
                        attack_path, fps=12, target_size=(GRID_SIZE, GRID_SIZE), loop=False
                    )
                    print(f"[Trap] {trap_type}_attack : {cls._attack_cache[trap_type].n_frames} frames")
                except Exception as e:
                    print(f"[Trap] Erreur {trap_type}_attack : {e}")

            # Fallback legacy
            if trap_type not in cls._idle_cache:
                path = os.path.join(traps_dir, f"{trap_type}.png")
                if os.path.isfile(path):
                    try:
                        cls._anim_cache[trap_type] = spr.SpritesheetAnimator(
                            path, fps=6, target_size=(GRID_SIZE, GRID_SIZE), loop=True
                        )
                    except Exception as e:
                        print(f"[Trap] Erreur {trap_type}.png : {e}")

    _level_font = None

    @classmethod
    def _get_level_font(cls):
        if cls._level_font is None:
            cls._level_font = pygame.font.SysFont(None, 16)
        return cls._level_font

    def __init__(self, cells, trap_type="spikes", gacha_level=1, fusion_level=1):
        self.cells     = cells
        self.trap_type = trap_type
        self.gacha_level = gacha_level
        self.fusion_level = fusion_level
        self.level = fusion_level  # Pour l'affichage visuel
        self.timer     = 0
        self._attacking = False
        self.x = sum(c[0] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.y = sum(c[1] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2

        # Cloner les animateurs
        master_idle = Trap._idle_cache.get(trap_type)
        self._idle_anim = spr._clone_animator(master_idle) if master_idle else None

        master_attack = Trap._attack_cache.get(trap_type)
        self._attack_anim = spr._clone_animator(master_attack) if master_attack else None

        # Fallback legacy
        master_legacy = Trap._anim_cache.get(trap_type)
        self._animator = spr._clone_animator(master_legacy) if master_legacy else None

        self.set_stats()

    def set_stats(self, damage_bonus=0, cooldown_bonus=0):
        # Multiplicateur basé sur le niveau fusion (1.0 pour niveau 1, +10% par niveau fusion)
        fusion_mult = 1.0 + (self.fusion_level - 1) * 0.1
        
        if self.trap_type == "spikes":
            base_damage = 5 + (self.gacha_level - 1) * 10
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.cooldown = max(60 - (self.gacha_level - 1) * 15 - cooldown_bonus, 20)
        elif self.trap_type == "mine":
            base_damage = 30 + (self.gacha_level - 1) * 20
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.cooldown = max(200 - (self.gacha_level - 1) * 40 - cooldown_bonus, 60)
        else:
            base_damage = 10 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.cooldown = max(50 - (self.gacha_level - 1) * 10 - cooldown_bonus, 15)

        self.damage   = max(1, int(raw_damage * TRAP_DAMAGE_MULT))
        self._base_damage = self.damage
        self._eren_boosted = False
        self._armin_boosted = False
        self.cooldown = max(1, int(self.cooldown * TRAP_COOLDOWN_MULT))

        # Appliquer les buffs persistants
        if hasattr(self, '_armin_buff_mult') and self._armin_boosted:
            self.damage = int(self._base_damage * self._armin_buff_mult)

    def update(self, enemies, projectiles):
        # Avancer les animations UNE SEULE FOIS par frame (pas dans draw)
        if self._attacking and self._attack_anim:
            self._attack_anim.update()
            if self._attack_anim.finished:
                self._attacking = False
                self._attack_anim.reset()
        elif self._idle_anim and self.trap_type != "mine":
            self._idle_anim.update()
        elif self._animator:
            self._animator.update()

        if self.timer > 0:
            self.timer -= 1
            return

        trap_cells = set(self.cells)
        triggered  = False
        for e in enemies:
            if e.is_dead or e._dying:
                continue
            ex, ey = e.get_cell()
            if (ex, ey) in trap_cells:
                e.receive_damage(self.damage)
                if e.hp <= 0:
                    e.mark_dead()
                triggered = True

        if triggered:
            self.timer = self.cooldown
            if self._attack_anim:
                self._attacking = True
                self._attack_anim.reset()

    def draw(self, screen, offset_x, offset_y):
        if self.trap_type == "mine":
            # Mine : un seul sprite centré sur toute la hitbox
            min_cx = min(c[0] for c in self.cells)
            min_cy = min(c[1] for c in self.cells)
            max_cx = max(c[0] for c in self.cells)
            max_cy = max(c[1] for c in self.cells)
            total_w = (max_cx - min_cx + 1) * GRID_SIZE
            total_h = (max_cy - min_cy + 1) * GRID_SIZE
            px = offset_x + min_cx * GRID_SIZE + (total_w - GRID_SIZE) // 2
            py = offset_y + min_cy * GRID_SIZE + (total_h - GRID_SIZE) // 2

            if self._attacking and self._attack_anim:
                frame = self._attack_anim.get_frame()
                if frame:
                    # Impact centré et plus grand
                    scaled = pygame.transform.scale(frame, (total_w, total_h))
                    screen.blit(scaled, (offset_x + min_cx * GRID_SIZE,
                                         offset_y + min_cy * GRID_SIZE))
            elif self._idle_anim:
                idx = min(self.level - 1, self._idle_anim.n_frames - 1)
                self._idle_anim._frame_idx = idx
                frame = self._idle_anim.get_frame()
                if frame:
                    screen.blit(frame, (px, py))

        else:
            # Spikes : sprite sur chaque case
            for cx, cy in self.cells:
                px = offset_x + cx * GRID_SIZE
                py = offset_y + cy * GRID_SIZE

                if self._attacking and self._attack_anim:
                    frame = self._attack_anim.get_frame()
                    if frame:
                        screen.blit(frame, (px, py))
                elif self._idle_anim:
                    frame = self._idle_anim.get_frame()
                    if frame:
                        screen.blit(frame, (px, py))
                elif self._animator:
                    frame = self._animator.get_frame()
                    if frame:
                        screen.blit(frame, (px, py))

        # Jauge de cooldown bleue en bas du piège
        if self.cooldown > 0:
            min_cx = min(c[0] for c in self.cells)
            max_cx = max(c[0] for c in self.cells)
            max_cy = max(c[1] for c in self.cells)
            gauge_x = offset_x + min_cx * GRID_SIZE
            gauge_y = offset_y + max_cy * GRID_SIZE + GRID_SIZE - 5
            gauge_w = (max_cx - min_cx + 1) * GRID_SIZE
            gauge_h = 4
            # Fond gris
            pygame.draw.rect(screen, (50, 50, 70),
                             (gauge_x, gauge_y, gauge_w, gauge_h), border_radius=2)
            # Remplissage bleu : 1.0 = prêt, 0.0 = vient de tirer
            ratio = 1.0 - (self.timer / self.cooldown) if self.timer > 0 else 1.0
            fill_w = int(gauge_w * ratio)
            if fill_w > 0:
                pygame.draw.rect(screen, (60, 160, 255),
                                 (gauge_x, gauge_y, fill_w, gauge_h), border_radius=2)

        if self.level > 1:
            lvl_font = Trap._get_level_font()
            lbl = lvl_font.render(f"L{self.level}", True, (255, 255, 255))
            sx = offset_x + self.cells[0][0] * GRID_SIZE
            sy = offset_y + self.cells[0][1] * GRID_SIZE
            screen.blit(lbl, (sx + 4, sy + 2))


# ============================================================
# CLASSE PROJECTILE
# ============================================================
