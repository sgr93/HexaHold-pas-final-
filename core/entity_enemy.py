"""
entity_enemy.py

Classe Enemy.
"""
import math
import random
import os
import pygame
from core.config import (
    GRID_SIZE, COLS, ROWS, SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, START, END,
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

        # Stats de base : la survie de l’ennemi repose surtout sur ça
        self.hp            = hp
        self.max_hp        = hp
        self.speed         = speed
        self.radius        = radius

        # Flags de gameplay : servent à adapter comportement + difficulté + visuel
        self.is_boss       = is_boss
        self.is_fast       = is_fast
        self.is_final_boss = is_final_boss
        self.is_chapter_boss = is_chapter_boss
        self.is_dead       = False

        # Gestion des attaques : empêche le spam et rythme les combats
        self.reached_grid            = False
        self.attack_cooldown         = 60
        self.attack_timer            = 0
        self.player_attack_cooldown  = 45
        self.player_attack_timer     = 0
        self.attack_anim_timer       = 0

        # Position d’entrée : chaque ennemi spawn sur une colonne aléatoire
        # ça évite les vagues trop prévisibles
        entry_col = random.randint(0, COLS - 1)
        self.entry_col = entry_col

        # Spawn hors grille puis entrée progressive dans la zone jouable
        self.x = float(entry_col * GRID_SIZE + GRID_SIZE // 2)
        self.y = float(SPAWN_ZONE_Y + random.randint(0, SPAWN_ZONE_HEIGHT - 1))

        # Seed utilisée pour casser la symétrie dans le flow field
        self.seed = random.randint(0, 1_000_000)

        # Point cible initial : l’ennemi "s’aligne" avant de commencer à jouer
        self.target_x = float(entry_col * GRID_SIZE + GRID_SIZE // 2)
        self.target_y = float(GRID_SIZE // 2)

        # États d’animation : permettent de donner une identité visuelle à l’ennemi
        self._anim_state = 'walk'
        self._anim_dir   = 'down'
        self._hurt_timer = 0
        self._dying      = False

        # Choix du set d’assets : ici on transforme les flags gameplay en identité visuelle
        if is_chapter_boss:
            if chapter_idx == 5:
                asset_type = 'boss_final'   # boss ultime du chapitre final
            else:
                asset_type = 'boss_chapter' # boss intermédiaire mais sérieux
        elif is_final_boss:
            asset_type = 'boss_final'
        elif is_boss:
            asset_type = 'boss'
        elif is_fast:
            asset_type = 'enemy_fast'
        else:
            asset_type = 'enemy_normal'

        # Chargement du sprite set correspondant au rôle de l’ennemi
        self.spriteset = spr.load_spriteset(asset_type, _ASSETS_BASE)
        if self.spriteset:
            self.spriteset.set_state('walk', 'down')  # état neutre au spawn

    def get_cell(self):
        # Convertit position monde -> grille pour interagir avec le flow field
        return int(self.x // GRID_SIZE), int(self.y // GRID_SIZE)

    def push_out_of_block(self, grid):
        # Corrige les cas où l’ennemi se retrouve dans une case invalide
        gx, gy = self.get_cell()

        if grid.in_bounds(gx, gy) and grid.walkable[gx][gy]:
            return

        # On cherche une case voisine valide pour éviter de bloquer l’ennemi
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = gx + dx, gy + dy
                if grid.in_bounds(nx, ny) and grid.walkable[nx][ny]:
                    self.x = nx * GRID_SIZE + GRID_SIZE // 2
                    self.y = ny * GRID_SIZE + GRID_SIZE // 2
                    return

    def _set_anim(self, state, direction=None):
        # Évite de recharger la même animation en boucle
        direction = direction or self._anim_dir
        if self.spriteset and (state != self._anim_state or direction != self._anim_dir):
            self._anim_state = state
            self._anim_dir   = direction
            self.spriteset.set_state(state, direction)

    def update(self, grid, goal, player=None):
        if self.is_dead:
            return

        # Tant que l’ennemi "meurt", on laisse jouer son animation jusqu’au bout
        if self._dying:
            if self.spriteset:
                self.spriteset.update()
                if self.spriteset.is_finished():
                    self.is_dead = True
            else:
                self.is_dead = True
            return

        prev_x, prev_y = self.x, self.y

        # --- L’ennemi entre sur la map ---
        if not self.reached_grid:
            dx   = self.target_x - self.x
            dy   = self.target_y - self.y
            dist = math.hypot(dx, dy)

            if dist > 0:
                self.x += dx / dist * self.speed
                self.y += dy / dist * self.speed

            # Une fois aligné, il devient un vrai agent du flow field
            if abs(self.x - self.target_x) < 2 and abs(self.y - self.target_y) < 2:
                self.reached_grid = True

        else:
            # --- Déplacement principal via flow field ---
            # C’est ici que l’ennemi “comprend” la carte et suit le chemin global
            self.push_out_of_block(grid)
            gx, gy = self.get_cell()

            if grid.in_bounds(gx, gy):
                dirs = grid.flow_field[gx][gy]

                # Plusieurs directions = légère variation entre ennemis évite une file indienne d'ennemis
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

        # --- Interaction avec la base ---
        # L’ennemi devient agressif uniquement s’il touche la zone cible
        dist_goal = math.hypot(self.x - goal.x, self.y - goal.y)
        if dist_goal <= self.radius + goal.radius:
            if self.attack_timer <= 0:
                goal.hp = max(0, goal.hp - 5)
                self.attack_timer = self.attack_cooldown
                self.attack_anim_timer = 20 

        if self.attack_timer > 0:
            self.attack_timer -= 1

        # --- Interaction avec le joueur ---
        if player and player.alive:
            dist_p = math.hypot(self.x - player.x, self.y - player.y)

            if dist_p <= self.radius + player.radius:
                if self.player_attack_timer <= 0:
                    # Les boss frappent plus fort pour forcer le positionnement
                    player.take_damage(3 if not self.is_boss else 8)
                    self.player_attack_timer = self.player_attack_cooldown
                    self.attack_anim_timer = 20

            if self.player_attack_timer > 0:
                self.player_attack_timer -= 1

        # --- Gestion des animations ---
        if self.spriteset:
            ddx = self.x - prev_x
            ddy = self.y - prev_y

            # On adapte la direction uniquement si mouvement significatif
            if abs(ddx) > 0.05 or abs(ddy) > 0.05:
                self._anim_dir = _direction_from_delta(ddx, ddy)

            # Priorité visuelle : attaque > blessure > marche
            if self.attack_anim_timer > 0:
                self.attack_anim_timer -= 1
                self._set_anim('attack', self._anim_dir)

            elif self._hurt_timer > 0:
                self._hurt_timer -= 1
                self._set_anim('hurt')

            else:
                self._set_anim('walk', self._anim_dir)

            self.spriteset.set_walk_speed(self.speed, base_speed=1.0)
            self.spriteset.update()

    def receive_damage(self, amount):
        # Impact immédiat
        self.hp -= amount
        self._hurt_timer = 6
        self._set_anim('hurt', self._anim_dir)

    def mark_dead(self):
        # On différencie mort instantanée et mort animée
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
            # fallback visuel : permet de tester sans assets
            if self.is_chapter_boss:
                color = (80, 0, 140)
            elif self.is_final_boss:
                color = (255, 80, 0)
            elif self.is_boss:
                color = (200, 0, 200)
            elif self.is_fast:
                color = (255, 255, 0)
            else:
                color = (200, 50, 50)

            pygame.draw.circle(screen, color, (ex, ey), self.radius)

            # repère visuel pour que le joueur identifie immédiatement un boss de chapitre
            if self.is_chapter_boss:
                pygame.draw.circle(screen, (180, 60, 255), (ex, ey), self.radius, 3)

        # --- barre de vie ---
        # plus l’ennemi est important, plus la lisibilité de sa vie est renforcée
        if self.is_chapter_boss:
            bar_w, bar_h = 60, 8
        elif self.is_final_boss or self.is_boss:
            bar_w, bar_h = 40, 6
        else:
            bar_w, bar_h = 20, 3

        bar_y_off = self.radius + bar_h + 4

        # fond rouge = vie perdue
        pygame.draw.rect(screen, (200, 0, 0),
                         (ex - bar_w // 2, ey - bar_y_off, bar_w, bar_h))

        cur_w = int(bar_w * max(0, self.hp) / max(1, self.max_hp))

        bar_color = (180, 60, 255) if self.is_chapter_boss else (0, 200, 0)

        # vie restante = indicateur principal de progression du combat
        pygame.draw.rect(screen, bar_color,
                         (ex - bar_w // 2, ey - bar_y_off, cur_w, bar_h))

        # petit contour pour les boss importants (meilleure lisibilité en fight intense)
        if self.is_chapter_boss and bar_h >= 6:
            pygame.draw.rect(screen, (220, 120, 255),
                             (ex - bar_w // 2, ey - bar_y_off, bar_w, bar_h), 1)