"""
entity_tower.py
---------------
Classe Tower.
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
from core.entity_projectile import Projectile

class Tower:
    """Tour placée sur la grille, tir automatique."""

    TYPE_COLORS = {
        "small":        (0, 150, 200),
        "big":          (0, 100, 180),
        "sniper":       (230, 180, 60),
        "mortar":       (180, 90,  50),
        "frost":        (120, 200, 255),
        "tesla":        (120, 180, 250),
        "cannon":       (140, 90, 30),
        "laser":        (180, 60, 180),
    }

    # Cache des animateurs maîtres (un par type, partagé entre instances)
    _anim_cache = {}
    _scaled_frame_cache = {}

    # Système base + arme par niveau :
    #   assets/sprites/towers/<type>_base.png       → spritesheet statique, 1 frame par niveau
    #   assets/sprites/towers/<type>_weapon_1.png   → arme animée niveau 1
    #   assets/sprites/towers/<type>_weapon_2.png   → arme animée niveau 2
    #   assets/sprites/towers/<type>_weapon_3.png   → arme animée niveau 3
    # Si ces fichiers sont absents, fallback sur <type>.png (ancien système).
    _base_cache   = {}   # {tower_type: [surf_lvl1, surf_lvl2, surf_lvl3]}
    _weapon_cache = {}   # {tower_type: {1: animator, 2: animator, 3: animator}}
    @classmethod
    def _build_tower_asset_map(cls):
        towers_dir = os.path.join(_ASSETS_BASE, "towers")
        mapping = {}
        if not os.path.isdir(towers_dir):
            return mapping
        for tower_type in cls.TYPE_COLORS:
            path = os.path.join(towers_dir, f"{tower_type}.png")
            if os.path.isfile(path):
                mapping[tower_type] = path
        return mapping

    @classmethod
    def load_sprites(cls):
        """
        Charge les sprites de tours selon deux systèmes (priorité au système base+arme) :

        Système base+arme (nouveau) :
            assets/sprites/towers/<type>_base.png      spritesheet 1 frame/niveau
            assets/sprites/towers/<type>_weapon_1.png  arme animée niveau 1
            assets/sprites/towers/<type>_weapon_2.png  arme animée niveau 2
            assets/sprites/towers/<type>_weapon_3.png  arme animée niveau 3

        Système classique (fallback) :
            assets/sprites/towers/<type>.png           spritesheet animée unique
        """
        towers_dir = os.path.join(_ASSETS_BASE, "towers")
        for tower_type in cls.TYPE_COLORS:
            base_path = os.path.join(towers_dir, f"{tower_type}_base.png")

            if os.path.isfile(base_path):
                print(f"[Tower] Chargement base+weapon pour : {tower_type}")
                # ── Système base + arme par niveau ──
                try:
                    base_sheet = pygame.image.load(base_path).convert_alpha()
                    bw = base_sheet.get_width()
                    bh = base_sheet.get_height()
                    # Largeur d'une frame = largeur totale / 3 niveaux
                    fw = bw // 3
                    levels = []
                    for i in range(3):
                        frame = base_sheet.subsurface(pygame.Rect(i * fw, 0, fw, bh)).copy()
                        levels.append(frame)
                    cls._base_cache[tower_type] = levels
                except Exception as e:
                    print(f"[entities] Impossible de charger {tower_type}_base.png : {e}")

                weapons = {}
                for lvl in range(1, 4):
                    wp = os.path.join(towers_dir, f"{tower_type}_weapon_{lvl}.png")
                    if os.path.isfile(wp):
                        try:
                            anim = spr.SpritesheetAnimator(
                                wp, fps=8, target_size=(GRID_SIZE * 2, GRID_SIZE * 2), loop=True
                            )
                            weapons[lvl] = anim
                            print(f"[Tower] {tower_type}_weapon_{lvl} : {anim.n_frames} frames OK")
                        except Exception as e:
                            print(f"[Tower] ERREUR {tower_type}_weapon_{lvl} : {e}")
                    else:
                        print(f"[Tower] {tower_type}_weapon_{lvl}.png INTROUVABLE")
                if weapons:
                    cls._weapon_cache[tower_type] = weapons
                    print(f"[Tower] {tower_type} : {len(weapons)} weapon(s) chargée(s)")
                else:
                    print(f"[Tower] {tower_type}_base OK mais aucune weapon trouvée")

            else:
                # ── Fallback : système classique ──
                path = os.path.join(towers_dir, f"{tower_type}.png")
                if os.path.isfile(path):
                    try:
                        cls._anim_cache[tower_type] = spr.SpritesheetAnimator(
                            path, fps=6, target_size=(GRID_SIZE, GRID_SIZE), loop=True
                        )
                    except Exception as e:
                        print(f"[entities] Impossible de charger {tower_type}.png : {e}")

    # OPTIM-E1 : cache de font de classe (évite pygame.font.SysFont à chaque draw)
    _level_font = None

    @classmethod
    def _get_level_font(cls):
        if cls._level_font is None:
            cls._level_font = pygame.font.SysFont(None, 18)
        return cls._level_font

    # Frames d'anticipation : l'animation de l'arme démarre avant le tir
    WINDUP_FRAMES = 30

    def __init__(self, cells, tower_type, gacha_level=1, fusion_level=1):
        self.cells      = cells
        self.tower_type = tower_type
        self.gacha_level = gacha_level
        self.fusion_level = fusion_level
        self.level = fusion_level  # Pour l'affichage visuel
        self.timer      = 0
        self.x = sum(c[0] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.y = sum(c[1] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        # Système classique (fallback)
        master = Tower._anim_cache.get(tower_type)
        self._animator = spr._clone_animator(master) if master else None

        # Système base + arme par niveau
        self._weapon_anim    = None
        self._attacking      = False   # True uniquement pendant l'animation de tir
        self._target_in_range = False  # True si un ennemi est dans la portée
        self._refresh_weapon_anim()

        # Emprise en pixels (pour scaler le sprite sur toutes les cellules)
        min_cx = min(c[0] for c in cells)
        min_cy = min(c[1] for c in cells)
        max_cx = max(c[0] for c in cells)
        max_cy = max(c[1] for c in cells)
        self._fp_x  = min_cx
        self._fp_y  = min_cy
        self._fp_w  = (max_cx - min_cx + 1) * GRID_SIZE
        self._fp_h  = (max_cy - min_cy + 1) * GRID_SIZE
        self._render_w = max(1, int(self._fp_w * 0.94))
        self._render_h = max(1, int(self._fp_h * 0.94))
        self._render_dx = (self._fp_w - self._render_w) // 2
        self._render_dy = (self._fp_h - self._render_h) // 2
        self.set_stats()

    def _refresh_weapon_anim(self):
        """Instancie (ou met à jour) l'animateur de l'arme selon self.level (niveau fusion/visuel)."""
        weapons = Tower._weapon_cache.get(self.tower_type)
        if not weapons:
            self._weapon_anim = None
            return
        # Cherche l'arme du niveau exact, sinon prend la plus haute disponible
        lvl = self.level
        while lvl >= 1:
            master = weapons.get(lvl)
            if master:
                self._weapon_anim = spr._clone_animator(master)
                return
            lvl -= 1
        self._weapon_anim = None

    def set_stats(self, damage_bonus=0, cooldown_bonus=0):
        # Multiplicateur basé sur le niveau fusion (1.0 pour niveau 1, +10% par niveau fusion)
        fusion_mult = 1.0 + (self.fusion_level - 1) * 0.1
        
        if self.tower_type == "small":
            base_damage = 5 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (3 * GRID_SIZE + (self.gacha_level - 1) * 8) * fusion_mult
            self.cooldown = max(38 - (self.gacha_level - 1) * 4 - cooldown_bonus, 8)
        elif self.tower_type == "big":
            base_damage = 8 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (5 * GRID_SIZE + (self.gacha_level - 1) * 12) * fusion_mult
            self.cooldown = max(72 - (self.gacha_level - 1) * 9 - cooldown_bonus, 14)
        elif self.tower_type == "sniper":
            base_damage = 10 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (7 * GRID_SIZE + (self.gacha_level - 1) * 10) * fusion_mult
            self.cooldown = max(110 - (self.gacha_level - 1) * 12 - cooldown_bonus, 15)
        elif self.tower_type == "mortar":
            base_damage = 9 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (6 * GRID_SIZE + (self.gacha_level - 1) * 10) * fusion_mult
            self.cooldown = max(90 - (self.gacha_level - 1) * 11 - cooldown_bonus, 14)
        elif self.tower_type == "frost":
            base_damage = 4 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (4 * GRID_SIZE + (self.gacha_level - 1) * 7) * fusion_mult
            self.cooldown = max(78 - (self.gacha_level - 1) * 9 - cooldown_bonus, 12)
        elif self.tower_type == "tesla":
            base_damage = 7 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (5 * GRID_SIZE + (self.gacha_level - 1) * 7) * fusion_mult
            self.cooldown = max(58 - (self.gacha_level - 1) * 8 - cooldown_bonus, 12)
        elif self.tower_type == "cannon":
            base_damage = 9 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (5 * GRID_SIZE + (self.gacha_level - 1) * 8) * fusion_mult
            self.cooldown = max(82 - (self.gacha_level - 1) * 10 - cooldown_bonus, 14)
        elif self.tower_type == "laser":
            base_damage = 12 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (6 * GRID_SIZE + (self.gacha_level - 1) * 9) * fusion_mult
            self.cooldown = max(102 - (self.gacha_level - 1) * 13 - cooldown_bonus, 14)
        else:
            base_damage = 4 * self.gacha_level
            raw_damage   = base_damage * fusion_mult + damage_bonus
            self.range    = (4 * GRID_SIZE + (self.gacha_level - 1) * 7) * fusion_mult
            self.cooldown = max(44 - (self.gacha_level - 1) * 7 - cooldown_bonus, 10)

        self.damage   = max(1, int(raw_damage * TOWER_DAMAGE_MULT))
        self._base_damage = self.damage
        self._eren_boosted = False
        self._armin_boosted = False
        self.range    = max(1, int(self.range * TOWER_RANGE_MULT))
        self.cooldown = max(1, int(self.cooldown * TOWER_COOLDOWN_MULT))
        # Mettre à jour l'arme si le niveau a changé
        if hasattr(self, '_weapon_anim'):
            self._refresh_weapon_anim()

        # Appliquer les buffs persistants
        if hasattr(self, '_armin_buff_mult') and self._armin_boosted:
            self.damage = int(self._base_damage * self._armin_buff_mult)

    def update(self, enemies, projectiles):
        if self._animator:
            self._animator.update()

        # Avancer l'animation de l'arme uniquement pendant l'attaque
        if self._weapon_anim:
            if self._attacking:
                self._weapon_anim.update()
                # Fin du cycle unique → retour idle
                if self._weapon_anim.finished:
                    self._attacking = False
                    self._weapon_anim.reset()
                    self._weapon_anim.loop = True
            # Sinon l'arme reste sur la frame 0 (idle)

        if self.timer > 0:
            self.timer -= 1

            # Windup : démarrer l'animation WINDUP_FRAMES avant le tir
            if (self._weapon_anim and not self._attacking
                    and self.timer <= Tower.WINDUP_FRAMES):
                # Vérifier qu'un ennemi est toujours en portée
                range_sq = self.range * self.range
                for e in enemies:
                    if e.is_dead or e._dying:
                        continue
                    dx = self.x - e.x
                    dy = self.y - e.y
                    if dx * dx + dy * dy <= range_sq:
                        self._attacking = True
                        self._weapon_anim.reset()
                        self._weapon_anim.loop = False
                        break
            return

        range_sq = self.range * self.range
        for e in enemies:
            if e.is_dead or e._dying:
                continue
            dx = self.x - e.x
            dy = self.y - e.y
            if dx * dx + dy * dy <= range_sq:
                projectiles.append(Projectile(self.x, self.y, e, self.damage,
                                              proj_type=self.tower_type))
                self.timer = self.cooldown
                # L'animation est déjà lancée par le windup si tout s'est bien passé
                # Sinon on la démarre maintenant (tir immédiat sans windup)
                if self._weapon_anim and not self._attacking:
                    self._attacking = True
                    self._weapon_anim.reset()
                    self._weapon_anim.loop = False
                break

    def draw(self, screen, offset_x, offset_y):
        color = self.TYPE_COLORS.get(self.tower_type, (120, 120, 120))
        bx = offset_x + self._fp_x * GRID_SIZE + self._render_dx
        by = offset_y + self._fp_y * GRID_SIZE + self._render_dy

        has_base_weapon = (self.tower_type in Tower._base_cache
                           or self.tower_type in Tower._weapon_cache)

        if has_base_weapon:
            # ── Système base + arme par niveau ──
            # La base utilise sa taille naturelle (peut déborder vers le haut)
            # L'arme est centrée sur la hitbox

            # 1. Base statique (frame selon level-1, clampée)
            bases = Tower._base_cache.get(self.tower_type, [])
            if bases:
                idx = min(self.level - 1, len(bases) - 1)
                base_surf = bases[idx]
                # Légèrement plus grand que la hitbox + décalé vers le haut
                draw_w = int(self._render_w * 1.15)
                draw_h = int(self._render_h * 1.15)
                base_scaled = pygame.transform.scale(base_surf, (draw_w, draw_h))
                draw_x = bx - (draw_w - self._render_w) // 2
                draw_y = by - (draw_h - self._render_h)   # décale vers le haut
                screen.blit(base_scaled, (draw_x, draw_y))

            # 2. Arme centrée sur la hitbox (carré)
            if self._weapon_anim:
                w_frame = self._weapon_anim.get_frame()
                if w_frame:
                    sq = min(self._render_w, self._render_h)
                    cx = bx + (self._render_w - sq) // 2
                    cy = by + (self._render_h - sq) // 2 - 10
                    w_scaled = pygame.transform.scale(w_frame, (sq, sq))
                    screen.blit(w_scaled, (cx, cy))

        elif self._animator:
            # ── Fallback : système classique ──
            frame = self._animator.get_frame()
            if frame:
                if frame.get_size() != (self._render_w, self._render_h):
                    key = (self.tower_type, self._render_w, self._render_h, self._animator._frame_idx)
                    cached = Tower._scaled_frame_cache.get(key)
                    if cached is None:
                        cropped = _crop_alpha_surface(frame)
                        cached = pygame.transform.scale(cropped, (self._render_w, self._render_h))
                        if len(Tower._scaled_frame_cache) >= _SCALED_FRAME_CACHE_MAX:
                            oldest = next(iter(Tower._scaled_frame_cache))
                            del Tower._scaled_frame_cache[oldest]
                        Tower._scaled_frame_cache[key] = cached
                    frame = cached
                screen.blit(frame, (bx, by))

        # Cercle de portée + indicateur de niveau
        radius = int(self.range)
        pygame.draw.circle(screen, color, (int(self.x)+offset_x, int(self.y)+offset_y), radius, 1)
        if self.level > 1:
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(self.x)+offset_x, int(self.y)+offset_y),
                               radius - 10, 1)
            lvl_font = Tower._get_level_font()
            lbl = lvl_font.render(f"L{self.level}", True, (255, 255, 255))
            screen.blit(lbl, (int(self.x)+offset_x - lbl.get_width() // 2,
                              int(self.y)+offset_y - lbl.get_height() // 2))


# ============================================================
# CLASSE TRAP
# ============================================================
