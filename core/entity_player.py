"""
entity_player.py
----------------
Classe Player.
"""
import math
import random
import os
import pygame
from config import (
    GRID_SIZE, COLS, ROWS,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    START, END, PLAYER_HP,
    TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT,
    TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import sprites as spr
from entity_helpers import (
    _crop_alpha_surface, _direction_from_delta,
    _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)
from entity_projectile import Projectile
import heroes as _hm
from sprites import SpriteSet
import traceback

class Player:
    """
    Joueur contrôlé au clavier.
    Animé via SpriteSet roguelike Char1 (si présent).
    """

    def __init__(self, x, y):
        self.x      = float(x)
        self.y      = float(y)
        self.speed  = 3
        self.radius = 12

        self.damage            = 5
        self.range             = 110
        self.attack_cooldown   = 30
        self.attack_timer      = 0
        self.attack_anim_timer = 0

        self.hp     = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.alive  = True

        # Stats de combat avancées (alimentées par skill tree / équipements)
        self.crit_chance  = 0.0   # 0.0 → 1.0
        self.crit_damage  = 1.5   # multiplicateur sur coup critique
        self.dodge_chance = 0.0   # 0.0 → 1.0
        self.defense      = 0.0   # réduction % des dégâts reçus (0.0 → 1.0)

        self._anim_state = 'idle'
        self._anim_dir   = 'down'
        self._hurt_timer = 0

        self.spriteset = spr.load_spriteset('player', _ASSETS_BASE)
        if self.spriteset:
            self.spriteset.set_state('idle', 'down')

    def load_hero_sprite(self, hero_id):
        """
        Charge le spritesheet RPG Maker du heros selectionne.
        Cherche dans assets/sprites/player/<hero_id>.png en priorité,
        puis assets/sprites/player/<sprite_ingame>.
        """
        try:

            hdef  = _hm.HEROES.get(hero_id, {})
            fname = hdef.get("sprite_ingame", "")
            if not fname:
                return

            # Cherche d'abord <hero_id>.png (nom simplifie), puis le nom original
            candidates = [
                os.path.join(_ASSETS_BASE, "player", hero_id + ".png"),
                os.path.join(_ASSETS_BASE, "player", fname),
                os.path.join(_ASSETS_BASE, fname),
            ]
            path = None
            for c in candidates:
                if os.path.isfile(c):
                    path = c
                    break

            if not path:
                print(f"[entities] load_hero_sprite({hero_id}): aucun fichier trouve parmi {candidates}")
                return

            print(f"[entities] Chargement sprite heros : {path}")
            self.spriteset = SpriteSet.from_rpgmaker_sheet(path, target_size=(40, 40))
            self.spriteset.set_state('idle', 'down')
        except Exception as e:
            print(f"[entities] load_hero_sprite({hero_id}): {e}")
            traceback.print_exc()

    @property
    def _x_min(self): return self.radius

    @property
    def _x_max(self): return COLS * GRID_SIZE - self.radius

    @property
    def _y_min(self): return self.radius

    @property
    def _y_max(self): return ROWS * GRID_SIZE - self.radius

    def _can_move_to(self, x, y, walkable):
        min_cx = max(0, int((x - self.radius) // GRID_SIZE))
        max_cx = min(COLS - 1, int((x + self.radius) // GRID_SIZE))
        min_cy = max(0, int((y - self.radius) // GRID_SIZE))
        max_cy = min(ROWS - 1, int((y + self.radius) // GRID_SIZE))

        r_sq = self.radius * self.radius  # BUG-E1 : comparaison carrée directe
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                if not walkable[cx][cy]:
                    rect_x = cx * GRID_SIZE
                    rect_y = cy * GRID_SIZE
                    nearest_x = max(rect_x, min(x, rect_x + GRID_SIZE))
                    nearest_y = max(rect_y, min(y, rect_y + GRID_SIZE))
                    dx = x - nearest_x
                    dy = y - nearest_y
                    if dx * dx + dy * dy < r_sq:
                        return False
        return True

    def update(self, keys_pressed, enemies, projectiles, waiting_for_tower, grid=None):
        if not self.alive:
            if self.spriteset:
                self.spriteset.update()
            return

        prev_x, prev_y = self.x, self.y
        moving   = False
        attacking = False

        # Mouvement désactivé si on est en mode placement de tour
        if not waiting_for_tower:
            dx = 0.0
            dy = 0.0
            if keys_pressed[pygame.K_LEFT]:
                dx -= self.speed
                moving = True
            if keys_pressed[pygame.K_RIGHT]:
                dx += self.speed
                moving = True
            if keys_pressed[pygame.K_UP]:
                dy -= self.speed
                moving = True
            if keys_pressed[pygame.K_DOWN]:
                dy += self.speed
                moving = True

            if dx != 0 and grid is not None:
                new_x = max(self._x_min, min(self._x_max, self.x + dx))
                if self._can_move_to(new_x, self.y, grid.walkable):
                    self.x = new_x
            else:
                self.x = max(self._x_min, min(self._x_max, self.x + dx))

            if dy != 0 and grid is not None:
                new_y = max(self._y_min, min(self._y_max, self.y + dy))
                if self._can_move_to(self.x, new_y, grid.walkable):
                    self.y = new_y
            else:
                self.y = max(self._y_min, min(self._y_max, self.y + dy))

        # Attaque automatique
        if self.attack_timer > 0:
            self.attack_timer -= 1
        else:
            range_sq = self.range * self.range
            target = None
            best_dist_sq = None
            for e in enemies:
                if e.is_dead:
                    continue
                dx = self.x - e.x
                dy = self.y - e.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= range_sq and (best_dist_sq is None or dist_sq < best_dist_sq):
                    target = e
                    best_dist_sq = dist_sq
            if target:
                damage = self.damage
                if self.crit_chance > 0 and random.random() < self.crit_chance:
                    damage = int(damage * self.crit_damage)
                projectiles.append(Projectile(self.x, self.y, target, damage,
                                              proj_type="player"))
                self.attack_timer      = self.attack_cooldown
                self.attack_anim_timer = 5
                attacking = True

        if self.attack_anim_timer > 0:
            self.attack_anim_timer -= 1
            attacking = True

        if self._hurt_timer > 0:
            self._hurt_timer -= 1

        # Animation
        if self.spriteset:
            dx = self.x - prev_x
            dy = self.y - prev_y
            if abs(dx) > 0.1 or abs(dy) > 0.1:
                self._anim_dir = _direction_from_delta(dx, dy)

            if attacking:
                new_state = 'attack'
            elif moving:
                new_state = 'walk'
            else:
                new_state = 'idle'

            if new_state != self._anim_state:
                self._anim_state = new_state
                self.spriteset.set_state(new_state, self._anim_dir)
            elif self._anim_dir != self.spriteset._dir:
                self.spriteset.set_state(new_state, self._anim_dir)

            if new_state == 'walk':
                self.spriteset.set_walk_speed(self.speed, base_speed=3)
            self.spriteset.update()

    def take_damage(self, amount):
        # Esquive : chance de complètement éviter le coup
        if self.dodge_chance > 0 and random.random() < self.dodge_chance:
            self._hurt_timer = 3  # petit clignotement visuel sans dégâts
            return False

        # Réduction par défense
        effective = max(1, int(amount * (1.0 - min(self.defense, 0.80))))
        self.hp = max(0, self.hp - effective)
        self._hurt_timer = 8
        if self.spriteset and self._anim_state not in ('death', 'hurt'):
            self.spriteset.set_state('hurt', self._anim_dir)
            self._anim_state = 'hurt'
        if self.hp <= 0 and self.alive:
            self.alive = False
            if self.spriteset:
                self.spriteset.set_state('death', self._anim_dir)
                self._anim_state = 'death'
            return True
        return False

    def draw(self, screen, offset_x, offset_y):
        if not self.alive and (not self.spriteset or self.spriteset.is_finished()):
            return

        px = int(self.x) + offset_x
        py = int(self.y) + offset_y

        if self.spriteset:
            frame = self.spriteset.get_frame()
            if frame:
                fw, fh = frame.get_size()
                screen.blit(frame, (px - fw // 2, py - fh // 2))
        else:
            pygame.draw.circle(screen, (0, 255, 0), (px, py), self.radius)
            pygame.draw.circle(screen, (0, 255, 0), (px, py), self.range, 1)
            if self.attack_anim_timer > 0:
                sq = 15
                pygame.draw.rect(screen, (255, 255, 0),
                                 pygame.Rect(px - sq//2, py - sq//2, sq, sq))

        # Barre de vie
        bar_w, bar_h = 30, 4
        bx = px - bar_w // 2
        by = py - self.radius - 8
        pygame.draw.rect(screen, (200, 0, 0), (bx, by, bar_w, bar_h))
        fill_w = int(bar_w * max(0, self.hp) / max(1, self.max_hp))
        pygame.draw.rect(screen, (0, 200, 0), (bx, by, fill_w, bar_h))
