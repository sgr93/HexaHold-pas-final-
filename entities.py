"""
entities.py
-----------
Définit toutes les entités du jeu : Player, Goal, Enemy, Tower, Trap, Projectile.
"""

import math
import random
import pygame
from config import (
    GRID_SIZE, COLS, ROWS,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    START, END, PLAYER_HP,
    TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT,
    TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import sprites as spr
import os

# Chemin de base vers les assets (relatif au fichier main.py)
_ASSETS_BASE = os.path.join(os.path.dirname(__file__), "assets", "sprites")


def _direction_from_delta(dx, dy):
    """
    Convertit un vecteur déplacement en direction pour le SpriteSet.
    Retourne : 'down', 'up', 'left', 'right'
    """
    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'
    return 'down' if dy >= 0 else 'up'


# ============================================================
# CLASSE PLAYER
# ============================================================

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
        self.range             = 80
        self.attack_cooldown   = 30
        self.attack_timer      = 0
        self.attack_anim_timer = 0

        self.hp     = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.alive  = True

        self._anim_state = 'idle'
        self._anim_dir   = 'down'
        self._hurt_timer = 0

        self.spriteset = spr.load_spriteset('player', _ASSETS_BASE)
        if self.spriteset:
            self.spriteset.set_state('idle', 'down')

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

        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                if not walkable[cx][cy]:
                    rect_x = cx * GRID_SIZE
                    rect_y = cy * GRID_SIZE
                    nearest_x = max(rect_x, min(x, rect_x + GRID_SIZE))
                    nearest_y = max(rect_y, min(y, rect_y + GRID_SIZE))
                    dx = x - nearest_x
                    dy = y - nearest_y
                    if dx * dx + dy * dy < self.radius * self.radius:
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
            target = min(
                (e for e in enemies
                 if not e.is_dead
                 and math.hypot(self.x - e.x, self.y - e.y) <= self.range),
                key=lambda e: math.hypot(self.x - e.x, self.y - e.y),
                default=None,
            )
            if target:
                projectiles.append(Projectile(self.x, self.y, target, self.damage))
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

            self.spriteset.update()

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
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

        # Clignotement si blessé
        if self._hurt_timer > 0 and self._hurt_timer % 4 < 2:
            pass

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


# ============================================================
# CLASSE GOAL
# ============================================================

class Goal:
    """Base à défendre. HP → 0 = Game Over."""

    def __init__(self, x, y):
        self.x      = x * GRID_SIZE + GRID_SIZE // 2
        self.y      = y * GRID_SIZE + GRID_SIZE // 2
        self.radius = 15
        self.hp     = 100

    def draw(self, screen, offset_x, offset_y):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), self.radius)
        pygame.draw.rect(screen, (200, 0, 0), (cx - 20, cy - 25, 40, 5))
        cur_w = int(40 * max(0, self.hp) / 100)
        pygame.draw.rect(screen, (0, 200, 0), (cx - 20, cy - 25, cur_w, 5))


# ============================================================
# CLASSE ENEMY
# ============================================================

class Enemy:
    """
    Ennemi suivant le Flow Field.
    Animé via SpriteSet selon le type (normal, fast, boss, final boss).
    """

    def __init__(self, hp=20, speed=0.5, radius=10,
                 is_boss=False, is_fast=False, is_final_boss=False):
        self.hp            = hp
        self.max_hp        = hp
        self.speed         = speed
        self.radius        = radius
        self.is_boss       = is_boss
        self.is_fast       = is_fast
        self.is_final_boss = is_final_boss
        self.is_dead       = False

        self.reached_grid            = False
        self.attack_cooldown         = 60
        self.attack_timer            = 0
        self.player_attack_cooldown  = 45
        self.player_attack_timer     = 0

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

        if is_final_boss:
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
            if self.player_attack_timer > 0:
                self.player_attack_timer -= 1

        # Animation
        if self.spriteset:
            ddx = self.x - prev_x
            ddy = self.y - prev_y
            if abs(ddx) > 0.05 or abs(ddy) > 0.05:
                self._anim_dir = _direction_from_delta(ddx, ddy)

            if self._hurt_timer > 0:
                self._hurt_timer -= 1
                if self._anim_state != 'hurt':
                    self._set_anim('hurt')
            elif attacking:
                self._set_anim('attack', self._anim_dir)
            else:
                self._set_anim('walk', self._anim_dir)

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

        if self._hurt_timer > 0 and self._hurt_timer % 4 < 2:
            pass

        if self.spriteset:
            frame = self.spriteset.get_frame()
            if frame:
                fw, fh = frame.get_size()
                screen.blit(frame, (ex - fw // 2, ey - fh // 2))
        else:
            if self.is_final_boss:
                color = (255, 80, 0)
            elif self.is_boss:
                color = (200, 0, 200)
            elif self.is_fast:
                color = (255, 255, 0)
            else:
                color = (200, 50, 50)
            pygame.draw.circle(screen, color, (ex, ey), self.radius)

        pygame.draw.rect(screen, (200, 0, 0), (ex - 10, ey - 15, 20, 3))
        cur_w = int(20 * max(0, self.hp) / max(1, self.max_hp))
        pygame.draw.rect(screen, (0, 200, 0), (ex - 10, ey - 15, cur_w, 3))


# ============================================================
# CLASSE TOWER
# ============================================================

class Tower:
    """Tour placée sur la grille, tir automatique."""

    TYPE_COLORS = {
        "small":        (0, 150, 200),
        "big":          (0, 100, 180),
        "sniper":       (230, 180, 60),
        "mortar":       (180, 90,  50),
        "frost":        (120, 200, 255),
        "poison":       (80, 180, 80),
        "beam":         (180, 60, 220),
        "tesla":        (120, 180, 250),
        "rocket":       (200, 100, 40),
        "storm":        (90, 130, 240),
        "arcane":       (150, 60, 220),
        "crystal":      (80, 220, 220),
        "swarm":        (220, 140, 50),
        "burst":        (200, 70, 70),
        "cannon":       (140, 90, 30),
        "flamethrower": (220, 120, 40),
        "shock":        (255, 180, 60),
        "mine":         (120, 80, 50),
        "laser":        (180, 60, 180),
        "trap":         (100, 100, 100),
    }

    def __init__(self, cells, tower_type, level=1):
        self.cells      = cells
        self.tower_type = tower_type
        self.level      = level
        self.timer      = 0
        self.x = sum(c[0] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.y = sum(c[1] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.set_stats()

    def set_stats(self, damage_bonus=0, cooldown_bonus=0):
        if self.tower_type == "small":
            self.damage   = 5 * self.level + damage_bonus
            self.range    = 3 * GRID_SIZE + (self.level - 1) * 8
            self.cooldown = max(38 - (self.level - 1) * 4 - cooldown_bonus, 8)
        elif self.tower_type == "big":
            self.damage   = 8 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 12
            self.cooldown = max(72 - (self.level - 1) * 9 - cooldown_bonus, 14)
        elif self.tower_type == "sniper":
            self.damage   = 10 * self.level + damage_bonus
            self.range    = 7 * GRID_SIZE + (self.level - 1) * 10
            self.cooldown = max(110 - (self.level - 1) * 12 - cooldown_bonus, 15)
        elif self.tower_type == "mortar":
            self.damage   = 9 * self.level + damage_bonus
            self.range    = 6 * GRID_SIZE + (self.level - 1) * 10
            self.cooldown = max(90 - (self.level - 1) * 11 - cooldown_bonus, 14)
        elif self.tower_type == "frost":
            self.damage   = 4 * self.level + damage_bonus
            self.range    = 4 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(78 - (self.level - 1) * 9 - cooldown_bonus, 12)
        elif self.tower_type == "poison":
            self.damage   = 5 * self.level + damage_bonus
            self.range    = 4 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(52 - (self.level - 1) * 7 - cooldown_bonus, 12)
        elif self.tower_type == "beam":
            self.damage   = 6 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 9
            self.cooldown = max(24 - (self.level - 1) * 4 - cooldown_bonus, 8)
        elif self.tower_type == "tesla":
            self.damage   = 7 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(58 - (self.level - 1) * 8 - cooldown_bonus, 12)
        elif self.tower_type == "rocket":
            self.damage   = 12 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 10
            self.cooldown = max(115 - (self.level - 1) * 13 - cooldown_bonus, 16)
        elif self.tower_type == "storm":
            self.damage   = 4 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(26 - (self.level - 1) * 3 - cooldown_bonus, 7)
        elif self.tower_type == "arcane":
            self.damage   = 8 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 8
            self.cooldown = max(68 - (self.level - 1) * 9 - cooldown_bonus, 12)
        elif self.tower_type == "crystal":
            self.damage   = 5 * self.level + damage_bonus
            self.range    = 4 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(42 - (self.level - 1) * 5 - cooldown_bonus, 10)
        elif self.tower_type == "swarm":
            self.damage   = 3 * self.level + damage_bonus
            self.range    = 3 * GRID_SIZE + (self.level - 1) * 4
            self.cooldown = max(14 - (self.level - 1) * 2 - cooldown_bonus, 5)
        elif self.tower_type == "burst":
            self.damage   = 12 * self.level + damage_bonus
            self.range    = 4 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(130 - (self.level - 1) * 18 - cooldown_bonus, 22)
        elif self.tower_type == "cannon":
            self.damage   = 9 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 8
            self.cooldown = max(82 - (self.level - 1) * 10 - cooldown_bonus, 14)
        elif self.tower_type == "flamethrower":
            self.damage   = 6 * self.level + damage_bonus
            self.range    = 3 * GRID_SIZE + (self.level - 1) * 5
            self.cooldown = max(30 - (self.level - 1) * 4 - cooldown_bonus, 8)
        elif self.tower_type == "shock":
            self.damage   = 7 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(62 - (self.level - 1) * 8 - cooldown_bonus, 12)
        elif self.tower_type == "mine":
            self.damage   = 10 * self.level + damage_bonus
            self.range    = 2 * GRID_SIZE + (self.level - 1) * 4
            self.cooldown = max(160 - (self.level - 1) * 22 - cooldown_bonus, 24)
        elif self.tower_type == "laser":
            self.damage   = 12 * self.level + damage_bonus
            self.range    = 6 * GRID_SIZE + (self.level - 1) * 9
            self.cooldown = max(102 - (self.level - 1) * 13 - cooldown_bonus, 14)
        else:
            self.damage   = 4 * self.level + damage_bonus
            self.range    = 4 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(44 - (self.level - 1) * 7 - cooldown_bonus, 10)

        # Nerf global : tours moins dominantes (moins de dégâts, moins de portée,
        # cooldown plus long). Les bonus (equip/upgrade) restent pris en compte
        # avant application de ces multiplicateurs.
        self.damage = max(1, int(self.damage * TOWER_DAMAGE_MULT))
        self.range = max(1, int(self.range * TOWER_RANGE_MULT))
        self.cooldown = max(1, int(self.cooldown * TOWER_COOLDOWN_MULT))

    def update(self, enemies, projectiles):
        if self.timer > 0:
            self.timer -= 1
            return
        for e in enemies:
            if e.is_dead or e._dying:
                continue
            if math.hypot(self.x - e.x, self.y - e.y) <= self.range:
                projectiles.append(Projectile(self.x, self.y, e, self.damage))
                self.timer = self.cooldown
                break

    def draw(self, screen, offset_x, offset_y):
        color = self.TYPE_COLORS.get(self.tower_type, (120, 120, 120))
        glow  = (max(color[0] - 40, 0), max(color[1] - 40, 0), max(color[2] - 40, 0))

        for cx, cy in self.cells:
            rect = pygame.Rect(offset_x + cx*GRID_SIZE, offset_y + cy*GRID_SIZE,
                               GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, glow, rect)
            inner = rect.inflate(-6, -6)
            pygame.draw.rect(screen, color, inner)

        radius = int(self.range)
        pygame.draw.circle(screen, color, (int(self.x)+offset_x, int(self.y)+offset_y), radius, 1)
        if self.level > 1:
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(self.x)+offset_x, int(self.y)+offset_y),
                               radius - 10, 1)
            lvl_font = pygame.font.SysFont(None, 18)
            lbl = lvl_font.render(f"L{self.level}", True, (255, 255, 255))
            screen.blit(lbl, (int(self.x)+offset_x - lbl.get_width() // 2,
                              int(self.y)+offset_y - lbl.get_height() // 2))


# ============================================================
# CLASSE TRAP
# ============================================================

class Trap:
    """Piège sur la grille (invisible pour le pathfinding)."""

    def __init__(self, cells, trap_type="spikes", level=1):
        self.cells     = cells
        self.trap_type = trap_type
        self.level     = level
        self.timer     = 0
        self.x = sum(c[0] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.y = sum(c[1] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.set_stats()

    def set_stats(self):
        if self.trap_type == "spikes":
            self.damage   = 5 + (self.level - 1) * 10
            self.cooldown = max(60 - (self.level - 1) * 15, 20)
        else:
            self.damage   = 10 * self.level
            self.cooldown = max(50 - (self.level - 1) * 10, 15)

        # Nerf global des pièges (un peu moins qu'on ne touche aux tours).
        self.damage = max(1, int(self.damage * TRAP_DAMAGE_MULT))
        self.cooldown = max(1, int(self.cooldown * TRAP_COOLDOWN_MULT))

    def update(self, enemies, projectiles):
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

    def draw(self, screen, offset_x, offset_y):
        color = (100, 100, 100) if self.timer <= 0 else (150, 60, 60)
        for cx, cy in self.cells:
            rect = pygame.Rect(offset_x + cx*GRID_SIZE, offset_y + cy*GRID_SIZE,
                               GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, color, rect)
            inner = pygame.Rect(offset_x + cx*GRID_SIZE + 4,
                                offset_y + cy*GRID_SIZE + 4,
                                GRID_SIZE - 8, GRID_SIZE - 8)
            pygame.draw.rect(screen, (80, 80, 80), inner)
        if self.level > 1:
            lvl_font = pygame.font.SysFont(None, 16)
            lbl = lvl_font.render(f"L{self.level}", True, (255, 255, 255))
            sx = offset_x + self.cells[0][0] * GRID_SIZE
            sy = offset_y + self.cells[0][1] * GRID_SIZE
            screen.blit(lbl, (sx + 4, sy + 2))


# ============================================================
# CLASSE PROJECTILE
# ============================================================

class Projectile:
    """
    Projectile tiré par le joueur ou une tour.
    Utilise is_dead et _dying pour éviter les dégâts en double.
    """

    def __init__(self, x, y, target, damage, speed=5):
        self.x      = float(x)
        self.y      = float(y)
        self.target = target
        self.damage = damage
        self.speed  = speed
        self.alive  = True

    def update(self):
        if not self.alive or self.target.is_dead or self.target._dying:
            self.alive = False
            return

        dx   = self.target.x - self.x
        dy   = self.target.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            self.target.receive_damage(self.damage)
            if self.target.hp <= 0:
                self.target.mark_dead()
            self.alive = False
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def draw(self, screen, offset_x, offset_y):
        pygame.draw.circle(screen, (255, 255, 0),
                           (int(self.x)+offset_x, int(self.y)+offset_y), 4)
