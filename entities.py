"""
entities.py
-----------
Definit toutes les entites du jeu : Player, Goal, Enemy, Tower, Trap, Projectile, sprites

"""

import math
import random
import pygame
from config import (
    GRID_SIZE, COLS, ROWS,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    START, END, PLAYER_HP,
)
import sprites as spr

# Chemin de base vers les assets (relatif au fichier main.py)
import os
_ASSETS_BASE = os.path.join(os.path.dirname(__file__), "assets", "sprites")


def _direction_from_delta(dx, dy):
    """
    Convertit un vecteur deplacement en direction pour le SpriteSet.
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
    Joueur controle au clavier.
    SPRITE-1 : anime via SpriteSet roguelike Char1.
    """

    def __init__(self, x, y):
        self.x      = float(x)
        self.y      = float(y)
        self.speed  = 3
        self.radius = 12

        self.damage          = 5
        self.range           = 80
        self.attack_cooldown = 30
        self.attack_timer    = 0
        self.attack_anim_timer = 0

        self.hp     = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.alive  = True

        # Etat d'animation interne
        self._anim_state    = 'idle'
        self._anim_dir      = 'down'
        self._hurt_timer    = 0    # frames de clignotement apres degats

        # SPRITE-1 : charge le spriteset (None si assets absents)
        self.spriteset = spr.load_spriteset('player', _ASSETS_BASE)
        if self.spriteset:
            self.spriteset.set_state('idle', 'down')

    # --- Limites ---
    @property
    def _x_min(self): return self.radius
    @property
    def _x_max(self): return COLS * GRID_SIZE - self.radius
    @property
    def _y_min(self): return self.radius
    @property
    def _y_max(self): return ROWS * GRID_SIZE - self.radius

    def update(self, keys_pressed, enemies, projectiles, waiting_for_tower):
        if not self.alive:
            if self.spriteset:
                self.spriteset.update()
            return

        prev_x, prev_y = self.x, self.y
        moving = False

        if not waiting_for_tower:
            if keys_pressed[pygame.K_LEFT]:
                self.x -= self.speed; moving = True
            if keys_pressed[pygame.K_RIGHT]:
                self.x += self.speed; moving = True
            if keys_pressed[pygame.K_UP]:
                self.y -= self.speed; moving = True
            if keys_pressed[pygame.K_DOWN]:
                self.y += self.speed; moving = True

            self.x = max(self._x_min, min(self._x_max, self.x))
            self.y = max(self._y_min, min(self._y_max, self.y))

        # Attaque automatique
        attacking = False
        if self.attack_timer > 0:
            self.attack_timer -= 1
        else:
            target = min(
                (e for e in enemies if not e.is_dead
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

        # --- Choix de l'etat d'animation ---
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

        # Clignotement rouge si blesse
        if self._hurt_timer > 0 and self._hurt_timer % 4 < 2:
            pass  # skip le dessin = effet flash

        if self.spriteset:
            frame = self.spriteset.get_frame()
            if frame:
                # Centre le sprite sur la position du joueur
                fw, fh = frame.get_size()
                screen.blit(frame, (px - fw // 2, py - fh // 2))
        else:
            # SPRITE-4 : fallback cercle vert
            pygame.draw.circle(screen, (0, 255, 0), (px, py), self.radius)
            pygame.draw.circle(screen, (0, 255, 0), (px, py), self.range, 1)
            if self.attack_anim_timer > 0:
                sq = 15
                pygame.draw.rect(screen, (255, 255, 0),
                                 pygame.Rect(px - sq//2, py - sq//2, sq, sq))

        # Barre de vie (toujours affichee)
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
    """Base a defendre. HP → 0 = Game Over."""

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
    SPRITE-2/3 : anime avec le SpriteSet correspondant au type.
    Etat d'animation drive par l'etat du jeu (walk, attack, hurt, death).
    """

    def __init__(self, hp=20, speed=0.5, radius=10,
                 is_boss=False, is_fast=False, is_final_boss=False):
        self.hp          = hp
        self.max_hp      = hp
        self.speed       = speed
        self.radius      = radius
        self.is_boss     = is_boss
        self.is_fast     = is_fast
        self.is_final_boss = is_final_boss
        self.is_dead     = False

        self.reached_grid   = False
        self.attack_cooldown = 60
        self.attack_timer   = 0
        self.player_attack_cooldown = 45
        self.player_attack_timer    = 0

        # Spawn : colonne d'entrée aléatoire sur la rangée du haut
        entry_col = random.randint(0, COLS - 1)
        self.entry_col = entry_col

        # Position de spawn au-dessus de la grille dans la colonne choisie
        self.x = float(entry_col * GRID_SIZE + GRID_SIZE // 2)
        self.y = float(SPAWN_ZONE_Y + random.randint(0, SPAWN_ZONE_HEIGHT - 1))

        self.seed = random.randint(0, 1_000_000)

        # Cible d'entrée : case (entry_col, 0), première rangée de la grille
        self.target_x = float(entry_col * GRID_SIZE + GRID_SIZE // 2)
        self.target_y = float(GRID_SIZE // 2)

        # Animation interne
        self._anim_state = 'walk'
        self._anim_dir   = 'down'
        self._hurt_timer = 0
        self._dying      = False   # True = animation mort en cours, pas encore supprime

        # SPRITE-2/3 : choix du type d'asset
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
        """Change l'etat d'animation si besoin."""
        direction = direction or self._anim_dir
        if self.spriteset and (state != self._anim_state or direction != self._anim_dir):
            self._anim_state = state
            self._anim_dir   = direction
            self.spriteset.set_state(state, direction)

    def update(self, grid, goal, player=None):
        if self.is_dead:
            return

        # Si en train de mourir, on attend la fin de l'anim avant de signaler
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

        # === PHASE 1 : aller vers la grille ===
        if not self.reached_grid:
            dx   = self.target_x - self.x
            dy   = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += dx / dist * self.speed
                self.y += dy / dist * self.speed
            if abs(self.x - self.target_x) < 2 and abs(self.y - self.target_y) < 2:
                self.reached_grid = True

        # === PHASE 2 : suivre le flow field ===
        else:
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

        # === ATTAQUE BASE ===
        dist_goal = math.hypot(self.x - goal.x, self.y - goal.y)
        if dist_goal <= self.radius + goal.radius:
            attacking = True
            if self.attack_timer <= 0:
                goal.hp = max(0, goal.hp - 5)
                self.attack_timer = self.attack_cooldown
        if self.attack_timer > 0:
            self.attack_timer -= 1

        # === ATTAQUE JOUEUR (AMELIO-3) ===
        if player and player.alive:
            dist_p = math.hypot(self.x - player.x, self.y - player.y)
            if dist_p <= self.radius + player.radius:
                attacking = True
                if self.player_attack_timer <= 0:
                    player.take_damage(3 if not self.is_boss else 8)
                    self.player_attack_timer = self.player_attack_cooldown
            if self.player_attack_timer > 0:
                self.player_attack_timer -= 1

        # === DIRECTION D'ANIMATION ===
        if self.spriteset:
            ddx = self.x - prev_x
            ddy = self.y - prev_y
            if abs(ddx) > 0.05 or abs(ddy) > 0.05:
                self._anim_dir = _direction_from_delta(ddx, ddy)

            if self._hurt_timer > 0:
                self._hurt_timer -= 1
                # On garde l'etat hurt quelques frames
                if self._anim_state != 'hurt':
                    self._set_anim('hurt')
            elif attacking:
                self._set_anim('attack', self._anim_dir)
            else:
                self._set_anim('walk', self._anim_dir)

            self.spriteset.update()

    def receive_damage(self, amount):
        """
        Inflige des degats et declenche l'animation hurt.
        Separe de mark_dead pour permettre l'anim hurt avant la mort.
        """
        self.hp -= amount
        self._hurt_timer = 6
        if self.spriteset:
            self._set_anim('hurt', self._anim_dir)

    def mark_dead(self):
        """
        Marque l'ennemi comme mourant.
        L'animation death est jouee ; is_dead passe a True quand elle se termine.
        Si pas de sprite, is_dead = True immediatement.
        """
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

        # Clignotement rouge si blesse
        if self._hurt_timer > 0 and self._hurt_timer % 4 < 2:
            pass  # skip frame = flash

        if self.spriteset:
            frame = self.spriteset.get_frame()
            if frame:
                fw, fh = frame.get_size()
                screen.blit(frame, (ex - fw // 2, ey - fh // 2))
        else:
            # SPRITE-4 : fallback cercle colore
            if self.is_final_boss:
                color = (255, 80, 0)
            elif self.is_boss:
                color = (200, 0, 200)
            elif self.is_fast:
                color = (255, 255, 0)
            else:
                color = (200, 50, 50)
            pygame.draw.circle(screen, color, (ex, ey), self.radius)

        # Barre de vie (toujours)
        pygame.draw.rect(screen, (200, 0, 0), (ex - 10, ey - 15, 20, 3))
        cur_w = int(20 * max(0, self.hp) / max(1, self.max_hp))
        pygame.draw.rect(screen, (0, 200, 0), (ex - 10, ey - 15, cur_w, 3))


# ============================================================
# CLASSE TOWER
# ============================================================

class Tower:
    """Tour placee sur la grille, tir automatique. Pas de sprite (geometrique)."""

    def __init__(self, cells, tower_type, level=1):
        self.cells      = cells
        self.tower_type = tower_type
        self.level      = level
        self.timer      = 0
        self.x = sum(c[0] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.y = sum(c[1] for c in cells) / len(cells) * GRID_SIZE + GRID_SIZE / 2
        self.set_stats()

    def set_stats(self):
        if self.tower_type == "small":
            self.damage   = 10 * self.level
            self.range    = 3 * GRID_SIZE + (self.level - 1) * 10
            self.cooldown = max(30 - (self.level - 1) * 5, 5)
        else:
            self.damage   = 6 * self.level
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 15
            self.cooldown = max(60 - (self.level - 1) * 10, 10)

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
        for cx, cy in self.cells:
            rect = pygame.Rect(offset_x + cx*GRID_SIZE, offset_y + cy*GRID_SIZE,
                               GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(screen, (0, 150, 200), rect)
        pygame.draw.circle(screen, (0, 200, 0),
                           (int(self.x)+offset_x, int(self.y)+offset_y), self.range, 1)


# ============================================================
# CLASSE TRAP
# ============================================================

class Trap:
    """Piege sur la grille. FIX-GRID-1 : invisible au pathfinding."""

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
                e.receive_damage(self.damage)   # utilise receive_damage pour l'anim
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
            inner = pygame.Rect(offset_x + cx*GRID_SIZE + 4, offset_y + cy*GRID_SIZE + 4,
                                GRID_SIZE - 8, GRID_SIZE - 8)
            pygame.draw.rect(screen, (80, 80, 80), inner)


# ============================================================
# CLASSE PROJECTILE
# ============================================================

class Projectile:
    """
    Projectile tire par le joueur ou une tour.
    FIX-ENT-4 : utilise is_dead et _dying pour eviter les degats en double.
    """

    def __init__(self, x, y, target, damage, speed=5):
        self.x      = float(x)
        self.y      = float(y)
        self.target = target
        self.damage = damage
        self.speed  = speed
        self.alive  = True

    def update(self):
        # Cible morte ou en train de mourir → on abandonne
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