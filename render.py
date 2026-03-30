"""
render.py
---------
Initialise pygame et expose les objets globaux (screen, clock, fonts).

"""

import pygame
from config import (
    GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH,
    COLS, ROWS, GRID_SIZE,
    DISPLAY_FLAGS, WINDOW_CAPTION, BACKGROUND_COLOR
)

# --- Initialisation pygame (unique point d'entrée) ---
def init_pygame():
    """Initialise pygame, crée la fenêtre adaptée à la résolution de l'écran."""
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    pygame.display.set_caption(WINDOW_CAPTION)

    # Taille idéale du jeu (grille + panels gauche/droite + marges)
    ideal_w = GRID_WIDTH + INTERFACE_WIDTH + 220   # panel gauche inclus
    ideal_h = GRID_HEIGHT + 160                    # HUD haut + inventaire bas

    # Résolution disponible de l'écran
    info  = pygame.display.Info()
    scr_w = info.current_w
    scr_h = info.current_h

    # Marge de sécurité pour la barre des tâches / décorations de fenêtre
    MARGIN_W = 40
    MARGIN_H = 80

    # On s'adapte à l'écran sans dépasser la taille idéale
    win_w = min(ideal_w, scr_w - MARGIN_W)
    win_h = min(ideal_h, scr_h - MARGIN_H)

    # Garantir un minimum raisonnable
    win_w = max(win_w, 600)
    win_h = max(win_h, 480)

    global screen, clock, font, big_font
    screen   = pygame.display.set_mode((win_w, win_h), DISPLAY_FLAGS)
    clock    = pygame.time.Clock()
    font     = pygame.font.SysFont(None, 22)
    big_font = pygame.font.SysFont(None, 48)

screen   = None
clock    = None
font     = None
big_font = None


# ------------------------------------
# OPTIM-GRID : Cache de rendu de la grille
# ------------------------------------

class GridCache:
    """
    Pré-rend la grille (cases marchables/bloquées + lignes) sur une Surface
    et la restitue en un seul blit chaque frame.

    Utilisation :
        cache = GridCache()
        cache.invalidate()            # à appeler après grid.recompute()
        cache.draw(screen, grid, ox, oy)  # dans la boucle de rendu
    """

    def __init__(self):
        self._surface = None  # Surface pré-rendue
        self._dirty   = True  # True → recalcul nécessaire

    def invalidate(self):
        """Marque le cache comme obsolète (à appeler après tout recompute)."""
        self._dirty = True

    def draw(self, screen, grid, offset_x, offset_y):
        """
        Dessine la grille sur l'écran.
        Si le cache est invalide, reconstruit la surface d'abord.
        """
        if self._dirty or self._surface is None:
            self._rebuild(grid)

        screen.blit(self._surface, (offset_x, offset_y))

    def _rebuild(self, grid):
        """Reconstruit la surface en parcourant toutes les cases."""
        surf = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))  # Transparent

        for x in range(COLS):
            for y in range(ROWS):
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                if not grid.walkable[x][y]:
                    pygame.draw.rect(surf, (80, 80, 200), rect)
                pygame.draw.rect(surf, (50, 50, 50), rect, 1)

        self._surface = surf
        self._dirty   = False