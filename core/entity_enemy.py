"""
entity_enemy.py
---------------
Classe Enemy.
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


class Enemy:
    """
    Ennemi suivant le Flow Field.
    Animé via SpriteSet selon le type (normal, fast, boss, final boss).
    """

    def __init__(self, hp=20, speed=0.5, radius=10,
                 is_boss=False, is_fast=False, is_final_boss=False, is_chapter_boss=False,
                 chapter_idx=None):
        self.hp            = hp
        self.max_hp        = hp
        self.speed         = speed
        self.radius        = radius
        self.is_boss       = is_boss
        self.is_fast       = is_fast
        self.is_final_boss = is_final_boss
        self.is_chapter_boss = is_chapter_boss
        self.is_dead       = False

        self.reached_grid            = False
        self.attack_cooldown         = 60
        self.attack_timer            = 0
        self.player_attack_cooldown  = 45
        self.player_attack_timer     = 0
        self.attack_anim_timer       = 0

        entry_col = random.randint(0, COLS - 1)
        self.entry_col = entry_col

        self.x = float(entry_col * GRID_SIZE + GRID_SIZE // 2)
        self.y = float(SPAWN_ZONE_Y + random.randint(0, SPAWN_ZONE_HEIGHT - 1))

        self.seed = random.randint(0, 1_000_000)

        self.target_x = float(entry_col * GRID_SIZE + GRID_SIZE // 2)
        self.target_y = float(GRID_SIZE // 2)

        self._anim_state = 'walk'
        self._anim_dir   = 'down'
        self._hurt_timer = 0
        self._dying      = False

        if is_chapter_boss:
            if chapter_idx == 5:
                asset_type = 'boss_final'
            else:
                asset_type = 'boss_chapter'
        elif is_final_boss:
            asset_type = 'boss_final'
        elif is_boss:
            asset_type = 'boss'
        elif is_fast:
            asset_type = 'enemy_fast'
        else:
            asset_type = 'enemy_normal'

        self.spriteset = spr.load_spriteset(asset_type, _ASSETS_BASE)
        if self.spriteset:
            self.spriteset.set_state('walk', 'down')

    def get_cell(self):
        return int(self.x // GRID_SIZE), int(self.y // GRID_SIZE)

    def push_out_of_block(self, grid):
        gx, gy = self.get_cell()
        if grid.in_bounds(gx, gy) and grid.walkable[gx][gy]:
            return
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = gx + dx, gy + dy
                if grid.in_bounds(nx, ny) and grid.walkable[nx][ny]:
                    self.x = nx * GRID_SIZE + GRID_SIZE // 2
                    self.y = ny * GRID_SIZE + GRID_SIZE // 2
                    return

    def _set_anim(self, state, direction=None):
        direction = direction or self._anim_dir
        if self.spriteset and (state != self._anim_state or direction != self._anim_dir):
            self._anim_state = state
            self._anim_dir   = direction
            self.spriteset.set_state(state, direction)

    def update(self, grid, goal, player=None):
        if self.is_dead:
            return

        if self._dying:
            if self.spriteset:
                self.spriteset.update()
                if self.spriteset.is_finished():
                    self.is_dead = True
            else:
                self.is_dead = True
            return

        prev_x, prev_y = self.x, self.y
        attacking = False

        # Phase 1 : rejoindre la grille
        if not self.reached_grid:
            dx   = self.target_x - self.x
            dy   = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += dx / dist * self.speed
                self.y += dy / dist * self.speed
            if abs(self.x - self.target_x) < 2 and abs(self.y - self.target_y) < 2:
                self.reached_grid = True
        else:
            # Phase 2 : suivre le flow field
            self.push_out_of_block(grid)
            gx, gy = self.get_cell()
            if grid.in_bounds(gx, gy):
                dirs = grid.flow_field[gx][gy]
                if isinstance(dirs, list):
                    if dirs:
                        idx = (self.seed + gx * 73 + gy * 31) % len(dirs)
                        dx, dy = dirs[idx]
                    else:
                        dx, dy = 0, 0
                else:
                    dx, dy = dirs
                self.x += dx * self.speed
                self.y += dy * self.speed

        # Attaque de la base
        dist_goal = math.hypot(self.x - goal.x, self.y - goal.y)
        if dist_goal <= self.radius + goal.radius:
            attacking = True
            if self.attack_timer <= 0:
                goal.hp = max(0, goal.hp - 5)
                self.attack_timer = self.attack_cooldown
                self.attack_anim_timer = 20
        if self.attack_timer > 0:
            self.attack_timer -= 1

        # Attaque du joueur
        if player and player.alive:
            dist_p = math.hypot(self.x - player.x, self.y - player.y)
            if dist_p <= self.radius + player.radius:
                attacking = True
                if self.player_attack_timer <= 0:
                    player.take_damage(3 if not self.is_boss else 8)
                    self.player_attack_timer = self.player_attack_cooldown
                    self.attack_anim_timer = 20
            if self.player_attack_timer > 0:
                self.player_attack_timer -= 1

        # Animation
        if self.spriteset:
            ddx = self.x - prev_x
            ddy = self.y - prev_y
            if abs(ddx) > 0.05 or abs(ddy) > 0.05:
                self._anim_dir = _direction_from_delta(ddx, ddy)

            if self.attack_anim_timer > 0:
                self.attack_anim_timer -= 1
                if self._anim_state != 'attack':
                    self._anim_state = 'attack'
                    self.spriteset.set_state('attack', self._anim_dir)
            elif self._hurt_timer > 0:
                self._hurt_timer -= 1
                if self._anim_state != 'hurt':
                    self._set_anim('hurt')
            else:
                self._set_anim('walk', self._anim_dir)

            if self.spriteset:
                self.spriteset.set_walk_speed(self.speed, base_speed=1.0)
            self.spriteset.update()

    def receive_damage(self, amount):
        self.hp -= amount
        self._hurt_timer = 6
        if self.spriteset:
            self._set_anim('hurt', self._anim_dir)

    def mark_dead(self):
        self.hp = 0
        if self.spriteset:
            self._dying = True
            self._set_anim('death', self._anim_dir)
        else:
            self.is_dead = True

    def draw(self, screen, offset_x, offset_y):
        if self.is_dead:
            return

        ex = int(self.x) + offset_x
        ey = int(self.y) + offset_y

        if self.spriteset:
            frame = self.spriteset.get_frame()
            if frame:
                fw, fh = frame.get_size()
                screen.blit(frame, (ex - fw // 2, ey - fh // 2))
        else:
            if self.is_chapter_boss:
                color = (80, 0, 140)   # violet foncé — boss de fin de chapitre
            elif self.is_final_boss:
                color = (255, 80, 0)
            elif self.is_boss:
                color = (200, 0, 200)
            elif self.is_fast:
                color = (255, 255, 0)
            else:
                color = (200, 50, 50)
            pygame.draw.circle(screen, color, (ex, ey), self.radius)
            # Anneau lumineux pour le boss de chapitre
            if self.is_chapter_boss:
                pygame.draw.circle(screen, (180, 60, 255), (ex, ey), self.radius, 3)

        # Barre de vie — plus grande pour le boss de chapitre
        if self.is_chapter_boss:
            bar_w, bar_h = 60, 8
        elif self.is_final_boss or self.is_boss:
            bar_w, bar_h = 40, 6
        else:
            bar_w, bar_h = 20, 3
        bar_y_off = self.radius + bar_h + 4
        pygame.draw.rect(screen, (200, 0, 0),
                         (ex - bar_w // 2, ey - bar_y_off, bar_w, bar_h))
        cur_w = int(bar_w * max(0, self.hp) / max(1, self.max_hp))
        bar_color = (180, 60, 255) if self.is_chapter_boss else (0, 200, 0)
        pygame.draw.rect(screen, bar_color,
                         (ex - bar_w // 2, ey - bar_y_off, cur_w, bar_h))
        if self.is_chapter_boss and bar_h >= 6:
            pygame.draw.rect(screen, (220, 120, 255),
                             (ex - bar_w // 2, ey - bar_y_off, bar_w, bar_h), 1)


# ============================================================
# CLASSE TOWER
# ============================================================
