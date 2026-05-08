"""
entity_goal.py

Classe Goal.
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

class Goal:
    """Base à défendre. Si ses HP tombent à 0 → partie perdue."""

    def __init__(self, x, y):
        # Position centrée sur la case de la grille pour rester aligné avec le gameplay
        self.x      = x * GRID_SIZE + GRID_SIZE // 2
        self.y      = y * GRID_SIZE + GRID_SIZE // 2

        self.taille = 15

        self.vie     = 100

        # Animation optionnelle : permet de donner un peu de vie à la base
        path = os.path.join(_ASSETS_BASE, "tiles", "goal.png")
        self._animator = None

        # Si l’asset existe, on active une animation sinon fallback simple
        if os.path.isfile(path):
            try:
                self._animator = spr.SpritesheetAnimator(
                    path, fps=6, target_size=(GRID_SIZE * 2, GRID_SIZE * 2), loop=True
                )
            except Exception as e:
                print(f"[entities] Impossible de charger goal.png : {e}")

    def update(self):
        # Animation de la base
        if self._animator:
            self._animator.update()

    def draw(self, screen, offset_x, offset_y):
        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        # Affichage principal
        if self._animator:
            frame = self._animator.get_frame()
            if frame:
                w, h = frame.get_size()
                screen.blit(frame, (cx - w // 2, cy - h // 2))
        else:
            # visuel minimal si l'affichage principal ne marche pas
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), self.taille)

        # Barre de vie
        pygame.draw.rect(screen, (200, 0, 0), (cx - 20, cy - 25, 40, 5))
        cur_w = int(40 * max(0, self.vie) / 100)
        pygame.draw.rect(screen, (0, 200, 0), (cx - 20, cy - 25, cur_w, 5))