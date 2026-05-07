"""
entity_player.py
----------------
Tout ce qui concerne le joueur. Déplacement, attaque, animation, dégâts.
Assez costaud comme classe, faire attention si on modifie les stats.
"""
import math
import random
import os
import pygame
from core.config import (
    GRID_SIZE, COLS, ROWS, SPAWN_ZONE_X, SPAWN_ZONE_Y,
    SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, START, END,
    PLAYER_HP, TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT,
    TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import ui.sprites as spr
from core.entity_helpers import (
    _crop_alpha_surface, _direction_from_delta,
    _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)
from core.entity_projectile import Projectile
import core.heroes as _hm
from ui.sprites import SpriteSet
import traceback


class Player:
    """
    Le joueur, contrôlé au clavier.
    Utilise le SpriteSet roguelike Char1 si le fichier est dispo,
    sinon on fallback sur un cercle vert (pas très glamour mais ça marche).
    """

    def __init__(self, x, y):
        self.x     = float(x)
        self.y     = float(y)
        self.speed = 3
        self.radius = 12

        # Stats d'attaque de base - peuvent être boostées par le skill tree
        self.damage          = 5
        self.range           = 110
        self.attack_cooldown = 30
        self.attack_timer    = 0
        self.attack_anim_timer = 0

        self.hp     = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.alive  = True

        # Stats avancées (tout est à 0 par défaut, le skill tree s'occupe du reste)
        self.crit_chance  = 0.0   # entre 0 et 1
        self.crit_damage  = 1.5   # x1.5 sur un crit, classique
        self.dodge_chance = 0.0   # chance d'esquiver complètement un coup
        self.defense      = 0.0   # % de réduction des dégâts reçus (plafonné à 80%)

        # État interne pour l'animation
        self._anim_state = 'idle'
        self._anim_dir   = 'down'
        self._hurt_timer = 0   # fait clignoter le perso quand il prend un coup

        # Chargement du spriteset - pas de panique si ça rate, on a le fallback
        self.spriteset = spr.load_spriteset('player', _ASSETS_BASE)
        if self.spriteset:
            self.spriteset.set_state('idle', 'down')

    def load_hero_sprite(self, hero_id):
        """
        Charge le sprite RPG Maker du héros choisi.
        On cherche d'abord assets/sprites/player/<hero_id>.png,
        puis le nom de sprite défini dans HEROES si le premier est pas trouvé.
        """
        try:
            hdef  = _hm.HEROES.get(hero_id, {})
            fname = hdef.get("sprite_ingame", "")
            if not fname:
                # pas de sprite défini pour ce héros, on laisse tomber
                return

            # ordre de priorité : nom simplifié > nom original dans la config
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
                print(f"[entities] load_hero_sprite({hero_id}): fichier introuvable dans {candidates}")
                return

            print(f"[entities] chargement sprite : {path}")
            self.spriteset = SpriteSet.from_rpgmaker_sheet(path, target_size=(40, 40))
            self.spriteset.set_state('idle', 'down')

        except Exception as e:
            print(f"[entities] load_hero_sprite({hero_id}) a planté : {e}")
            traceback.print_exc()

    # Limites de déplacement en pixels - dépendent de la taille de la grille
    @property
    def _x_min(self): return self.radius

    @property
    def _x_max(self): return COLS * GRID_SIZE - self.radius

    @property
    def _y_min(self): return self.radius

    @property
    def _y_max(self): return ROWS * GRID_SIZE - self.radius

    def _can_move_to(self, x, y, walkable):
        """Vérifie qu'aucune tuile non-walkable ne bloque le déplacement."""
        # on calcule les cases couvertes par le cercle du joueur
        min_cx = max(0, int((x - self.radius) // GRID_SIZE))
        max_cx = min(COLS - 1, int((x + self.radius) // GRID_SIZE))
        min_cy = max(0, int((y - self.radius) // GRID_SIZE))
        max_cy = min(ROWS - 1, int((y + self.radius) // GRID_SIZE))

        r_sq = self.radius * self.radius  # comparaison en distance² pour éviter sqrt
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                if not walkable[cx][cy]:
                    rect_x = cx * GRID_SIZE
                    rect_y = cy * GRID_SIZE
                    # point le plus proche de la tuile par rapport au joueur
                    nearest_x = max(rect_x, min(x, rect_x + GRID_SIZE))
                    nearest_y = max(rect_y, min(y, rect_y + GRID_SIZE))
                    dx = x - nearest_x
                    dy = y - nearest_y
                    if dx*dx + dy*dy < r_sq:
                        return False  # collision détectée
        return True

    def update(self, keys_pressed, enemies, projectiles, waiting_for_tower, grid=None):
        # si le joueur est mort on met quand même l'anim à jour (animation de mort)
        if not self.alive:
            if self.spriteset:
                self.spriteset.update()
            return

        prev_x, prev_y = self.x, self.y
        moving    = False
        attacking = False

        # Déplacement - bloqué si on est en train de poser une tour
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

            # déplacement horizontal avec détection de collision si grid dispo
            if dx != 0 and grid is not None:
                new_x = max(self._x_min, min(self._x_max, self.x + dx))
                if self._can_move_to(new_x, self.y, grid.walkable):
                    self.x = new_x
            else:
                self.x = max(self._x_min, min(self._x_max, self.x + dx))

            # pareil pour le vertical
            if dy != 0 and grid is not None:
                new_y = max(self._y_min, min(self._y_max, self.y + dy))
                if self._can_move_to(self.x, new_y, grid.walkable):
                    self.y = new_y
            else:
                self.y = max(self._y_min, min(self._y_max, self.y + dy))

        # --- Attaque automatique ---
        # on cherche l'ennemi le plus proche dans le range et on lui envoie un projectile
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
                dist_sq = dx*dx + dy*dy
                if dist_sq <= range_sq and (best_dist_sq is None or dist_sq < best_dist_sq):
                    target = e
                    best_dist_sq = dist_sq

            if target:
                damage = self.damage
                # crit ? on lance le dé
                if self.crit_chance > 0 and random.random() < self.crit_chance:
                    damage = int(damage * self.crit_damage)

                projectiles.append(Projectile(self.x, self.y, target, damage, proj_type="player"))
                self.attack_timer      = self.attack_cooldown
                self.attack_anim_timer = 5
                attacking = True

        # petit timer pour garder l'anim d'attaque quelques frames
        if self.attack_anim_timer > 0:
            self.attack_anim_timer -= 1
            attacking = True

        if self._hurt_timer > 0:
            self._hurt_timer -= 1

        # --- Mise à jour animation ---
        if self.spriteset:
            dx = self.x - prev_x
            dy = self.y - prev_y

            # on met à jour la direction si le joueur s'est déplacé
            if abs(dx) > 0.1 or abs(dy) > 0.1:
                self._anim_dir = _direction_from_delta(dx, dy)

            # priorité : attack > walk > idle
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
                # même état mais direction changée
                self.spriteset.set_state(new_state, self._anim_dir)

            if new_state == 'walk':
                self.spriteset.set_walk_speed(self.speed, base_speed=3)

            self.spriteset.update()

    def take_damage(self, amount):
        """
        Applique des dégâts au joueur.
        Retourne True si le joueur vient de mourir, False sinon.
        """
        # tentative d'esquive - si ça passe, juste un petit clignotement
        if self.dodge_chance > 0 and random.random() < self.dodge_chance:
            self._hurt_timer = 3
            return False

        # la défense réduit les dégâts, mais on garantit au moins 1 de dégât
        effective = max(1, int(amount * (1.0 - min(self.defense, 0.80))))
        self.hp = max(0, self.hp - effective)
        self._hurt_timer = 8

        if self.spriteset and self._anim_state not in ('death', 'hurt'):
            self.spriteset.set_state('hurt', self._anim_dir)
            self._anim_state = 'hurt'

        # mort ?
        if self.hp <= 0 and self.alive:
            self.alive = False
            if self.spriteset:
                self.spriteset.set_state('death', self._anim_dir)
                self._anim_state = 'death'
            return True

        return False

    def draw(self, screen, offset_x, offset_y):
        # on n'affiche plus rien une fois l'animation de mort terminée
        if not self.alive and (not self.spriteset or self.spriteset.is_finished()):
            return

        px = int(self.x) + offset_x
        py = int(self.y) + offset_y

        if self.spriteset:
            frame = self.spriteset.get_frame()
            if frame:
                fw, fh = frame.get_size()
                screen.blit(frame, (px - fw//2, py - fh//2))
        else:
            # fallback visuel si pas de sprite - cercle vert basique
            pygame.draw.circle(screen, (0, 255, 0), (px, py), self.radius)
            pygame.draw.circle(screen, (0, 255, 0), (px, py), self.range, 1)
            if self.attack_anim_timer > 0:
                sq = 15
                pygame.draw.rect(screen, (255, 255, 0),
                                 pygame.Rect(px - sq//2, py - sq//2, sq, sq))

        # barre de vie au-dessus du perso
        bar_w, bar_h = 30, 4
        bx = px - bar_w // 2
        by = py - self.radius - 8
        pygame.draw.rect(screen, (200, 0, 0), (bx, by, bar_w, bar_h))
        fill_w = int(bar_w * max(0, self.hp) / max(1, self.max_hp))
        pygame.draw.rect(screen, (0, 200, 0), (bx, by, fill_w, bar_h))