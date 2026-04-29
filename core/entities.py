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

# Taille max du cache de frames scalées (évite fuite mémoire)
_SCALED_FRAME_CACHE_MAX = 512

# Chemin de base vers les assets (relatif au fichier main.py)
_ASSETS_BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")


def _crop_alpha_surface(surface):
    """Rogne les marges transparentes d'une surface pour mieux remplir sa hitbox visuelle."""
    rect = surface.get_bounding_rect(min_alpha=10)
    if rect.width <= 0 or rect.height <= 0:
        return surface
    return surface.subsurface(rect).copy()


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
            import heroes as _hm
            from sprites import SpriteSet

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
            import traceback
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

        path = os.path.join(_ASSETS_BASE, "tiles", "goal.png")
        self._animator = None
        if os.path.isfile(path):
            try:
                self._animator = spr.SpritesheetAnimator(
                    path, fps=6, target_size=(GRID_SIZE * 2, GRID_SIZE * 2), loop=True
                )
            except Exception as e:
                print(f"[entities] Impossible de charger goal.png : {e}")

    def update(self):
        if self._animator:
            self._animator.update()

    def draw(self, screen, offset_x, offset_y):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y
        if self._animator:
            frame = self._animator.get_frame()
            if frame:
                w, h = frame.get_size()
                screen.blit(frame, (cx - w // 2, cy - h // 2))
        else:
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

    def __init__(self, cells, tower_type, level=1):
        self.cells      = cells
        self.tower_type = tower_type
        self.level      = level
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
        """Instancie (ou met à jour) l'animateur de l'arme selon self.level."""
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
        elif self.tower_type == "tesla":
            self.damage   = 7 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(58 - (self.level - 1) * 8 - cooldown_bonus, 12)
        elif self.tower_type == "cannon":
            self.damage   = 9 * self.level + damage_bonus
            self.range    = 5 * GRID_SIZE + (self.level - 1) * 8
            self.cooldown = max(82 - (self.level - 1) * 10 - cooldown_bonus, 14)
        elif self.tower_type == "laser":
            self.damage   = 12 * self.level + damage_bonus
            self.range    = 6 * GRID_SIZE + (self.level - 1) * 9
            self.cooldown = max(102 - (self.level - 1) * 13 - cooldown_bonus, 14)
        else:
            self.damage   = 4 * self.level + damage_bonus
            self.range    = 4 * GRID_SIZE + (self.level - 1) * 7
            self.cooldown = max(44 - (self.level - 1) * 7 - cooldown_bonus, 10)

        self.damage   = max(1, int(self.damage * TOWER_DAMAGE_MULT))
        self.range    = max(1, int(self.range * TOWER_RANGE_MULT))
        self.cooldown = max(1, int(self.cooldown * TOWER_COOLDOWN_MULT))
        # Mettre à jour l'arme si le niveau a changé
        if hasattr(self, '_weapon_anim'):
            self._refresh_weapon_anim()

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

    def __init__(self, cells, trap_type="spikes", level=1):
        self.cells     = cells
        self.trap_type = trap_type
        self.level     = level
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
        if self.trap_type == "spikes":
            self.damage   = 5 + (self.level - 1) * 10 + damage_bonus
            self.cooldown = max(60 - (self.level - 1) * 15 - cooldown_bonus, 20)
        elif self.trap_type == "mine":
            self.damage   = 30 + (self.level - 1) * 20 + damage_bonus
            self.cooldown = max(200 - (self.level - 1) * 40 - cooldown_bonus, 60)
        else:
            self.damage   = 10 * self.level + damage_bonus
            self.cooldown = max(50 - (self.level - 1) * 10 - cooldown_bonus, 15)

        self.damage   = max(1, int(self.damage * TRAP_DAMAGE_MULT))
        self.cooldown = max(1, int(self.cooldown * TRAP_COOLDOWN_MULT))

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

class Projectile:
    """
    Projectile tiré par le joueur ou une tour.

    Sprites dans assets/sprites/projectiles/ :
        <type>.png          spritesheet animée en vol (frames horizontales, hauteur = taille frame)
        <type>_impact.png   spritesheet d'impact jouée une fois au moment du hit

    Convention : le sprite en vol pointe vers la DROITE (0°).
    Si les fichiers sont absents, fallback sur le cercle jaune.
    """

    # Taille d'affichage des projectiles sans sprite (fallback)
    SPRITE_SIZE = 16

    # Taille d'affichage des projectiles animés (pixels carrés)
    ANIM_SIZE = 18

    # Taille d'affichage de l'impact
    IMPACT_SIZE = 64

    # Offset d'angle par type
    ANGLE_OFFSET = {
        "player": 180,
    }

    # Cache des animateurs maîtres — partagés, clonés par instance
    _anim_cache: dict   = {}   # {type_key: SpritesheetAnimator | None}
    _impact_cache: dict = {}   # {type_key: SpritesheetAnimator | None}
    # Cache legacy (image statique) conservé pour la compatibilité
    _sprite_cache: dict = {}

    @classmethod
    def _find_sprite_path(cls, type_key, suffix=""):
        folder = os.path.join(_ASSETS_BASE, "projectiles")
        name   = f"{type_key}{suffix}.png"
        direct = os.path.join(folder, name)
        if os.path.isfile(direct):
            return direct
        target = name.lower()
        if os.path.isdir(folder):
            for fname in os.listdir(folder):
                if fname.lower() == target:
                    return os.path.join(folder, fname)
        return None

    @classmethod
    def _load_sprite(cls, type_key):
        """
        Charge le projectile : d'abord spritesheet animée, sinon image statique legacy.
        Charge aussi l'impact si <type>_impact.png existe.
        """
        # Déjà traité
        if type_key in cls._anim_cache:
            return cls._sprite_cache.get(type_key)

        proj_path   = cls._find_sprite_path(type_key)
        impact_path = cls._find_sprite_path(type_key, "_impact")

        # ── Projectile en vol ──
        if proj_path:
            try:
                img = pygame.image.load(proj_path).convert_alpha()
                h = img.get_height()
                n = img.get_width() // h
                if n > 1:
                    # Spritesheet animée
                    cls._anim_cache[type_key] = spr.SpritesheetAnimator(
                        proj_path, fps=12, target_size=(cls.ANIM_SIZE, cls.ANIM_SIZE), loop=True
                    )
                    cls._sprite_cache[type_key] = None  # pas de sprite statique
                    print(f"[Projectile] Anim chargée : {os.path.basename(proj_path)} ({n} frames)")
                else:
                    # Image statique legacy
                    surface = pygame.transform.scale(img, (cls.SPRITE_SIZE, cls.SPRITE_SIZE))
                    cls._sprite_cache[type_key] = surface
                    cls._anim_cache[type_key]   = None
                    print(f"[Projectile] Sprite statique : {os.path.basename(proj_path)}")
            except Exception as e:
                print(f"[Projectile] Erreur {type_key}.png : {e}")
                cls._anim_cache[type_key]   = None
                cls._sprite_cache[type_key] = None
        else:
            cls._anim_cache[type_key]   = None
            cls._sprite_cache[type_key] = None

        # ── Impact ──
        if impact_path:
            try:
                cls._impact_cache[type_key] = spr.SpritesheetAnimator(
                    impact_path, fps=14, target_size=(cls.IMPACT_SIZE, cls.IMPACT_SIZE), loop=False
                )
                print(f"[Projectile] Impact chargé : {os.path.basename(impact_path)}")
            except Exception as e:
                print(f"[Projectile] Erreur impact {type_key} : {e}")
                cls._impact_cache[type_key] = None
        else:
            cls._impact_cache[type_key] = None

        return cls._sprite_cache.get(type_key)

    def __init__(self, x, y, target, damage, speed=5, proj_type="player"):
        self.x         = float(x)
        self.y         = float(y)
        self.target    = target
        self.damage    = damage
        self.speed     = speed
        self.alive     = True
        self.proj_type = proj_type

        # S'assurer que les animateurs sont chargés
        self._sprite = Projectile._load_sprite(proj_type)

        # Cloner l'animateur en vol (indépendant par instance)
        master_anim = Projectile._anim_cache.get(proj_type)
        self._anim = spr._clone_animator(master_anim) if master_anim else None

        # Animateur d'impact (None tant qu'on n'a pas touché)
        self._impact_anim  = None
        self._impacting    = False   # True après le hit, pendant l'anim d'impact
        self._impact_x     = 0.0
        self._impact_y     = 0.0

        self._angle = 0.0

    def update(self):
        if self._impacting:
            # Jouer l'animation d'impact jusqu'à la fin
            if self._impact_anim:
                self._impact_anim.update()
                if self._impact_anim.finished:
                    self.alive = False
            else:
                self.alive = False
            return

        if not self.alive or self.target.is_dead or self.target._dying:
            self.alive = False
            return

        # Avancer l'animation en vol
        if self._anim:
            self._anim.update()

        dx   = self.target.x - self.x
        dy   = self.target.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            # Impact
            self.target.receive_damage(self.damage)
            if self.target.hp <= 0:
                self.target.mark_dead()

            master_impact = Projectile._impact_cache.get(self.proj_type)
            if master_impact:
                self._impact_anim = spr._clone_animator(master_impact)
                self._impact_anim.reset()
                self._impacting = True
                self._impact_x  = self.target.x
                self._impact_y  = self.target.y
            else:
                self.alive = False
        else:
            self._angle = -math.degrees(math.atan2(dy, dx))
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def draw(self, screen, offset_x, offset_y):
        if self._impacting:
            # Dessiner l'impact à la position du hit
            if self._impact_anim:
                frame = self._impact_anim.get_frame()
                if frame:
                    cx = int(self._impact_x) + offset_x
                    cy = int(self._impact_y) + offset_y
                    s  = Projectile.IMPACT_SIZE
                    screen.blit(frame, (cx - s // 2, cy - s // 2))
            return

        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        if self._anim:
            # Sprite animé en vol, orienté vers la cible
            frame = self._anim.get_frame()
            if frame:
                angle_off = Projectile.ANGLE_OFFSET.get(self.proj_type, 0)
                rotated   = pygame.transform.rotate(frame, self._angle + angle_off)
                rw, rh    = rotated.get_size()
                screen.blit(rotated, (cx - rw // 2, cy - rh // 2))
        elif self._sprite is not None:
            # Sprite statique legacy
            angle_off = Projectile.ANGLE_OFFSET.get(self.proj_type, 0)
            rotated   = pygame.transform.rotate(self._sprite, self._angle + angle_off)
            rw, rh    = rotated.get_size()
            screen.blit(rotated, (cx - rw // 2, cy - rh // 2))
        else:
            pygame.draw.circle(screen, (255, 255, 0), (cx, cy), 4)


# ============================================================
# HELPER GHOST
# ============================================================

def get_tower_preview(tower_type, width_px, height_px):
    """
    Retourne une surface scalée à (width_px, height_px) représentant
    la frame courante du sprite du type de tour donné.
    Retourne None si aucun sprite n'est chargé pour ce type.
    """
    master = Tower._anim_cache.get(tower_type)
    if master is None:
        return None
    frame = master.get_frame()
    if frame is None:
        return None
    cropped = _crop_alpha_surface(frame)
    preview_w = max(1, int(width_px * 0.94))
    preview_h = max(1, int(height_px * 0.94))
    scaled = pygame.transform.scale(cropped, (preview_w, preview_h))
    if preview_w == width_px and preview_h == height_px:
        return scaled
    surf = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
    surf.blit(scaled, ((width_px - preview_w) // 2, (height_px - preview_h) // 2))
    return surf