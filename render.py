"""
render.py
---------
Initialise pygame et expose les objets globaux (screen, clock, fonts).

"""

import os
import pygame
from config import (
    GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH,
    COLS, ROWS, GRID_SIZE,
    DISPLAY_FLAGS, WINDOW_CAPTION, BACKGROUND_COLOR
)

# Sprite optionnel pour les cases de mur
_wall_image = None

def load_wall_image():
    """
    Charge assets/sprites/tiles/wall.png si présent.
    Appelé après init_pygame(). Sans ce fichier le jeu continue normalement.
    """
    global _wall_image
    path = os.path.join(os.path.dirname(__file__), "assets", "sprites", "tiles", "wall.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _wall_image = pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))
        except Exception as e:
            print(f"[render] Impossible de charger wall.png : {e}")

# --- Font cache ---
_font_cache = {}

def get_font(size_key="md", bold=False):
    """Retourne une font en cache."""
    sizes = {"xs": 14, "sm": 18, "md": 22, "lg": 30, "xl": 48}
    size = sizes.get(size_key, 22)
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("arial", size, bold=bold)
    return _font_cache[key]

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
    font     = get_font("md")
    big_font = get_font("xl", bold=True)

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

    def draw(self, screen, grid, offset_x, offset_y, towers=None):
        """
        Dessine la grille sur l'écran.
        towers: liste des tours pour savoir quelles cases ne pas colorier
        """
        if self._dirty or self._surface is None:
            self._rebuild(grid, towers)

        screen.blit(self._surface, (offset_x, offset_y))

    def _rebuild(self, grid, towers=None):
        """Reconstruit la surface en parcourant toutes les cases."""
        surf = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))  # Transparent

        # Créer un set des cases occupées par des tours
        tower_cells = set()
        if towers:
            for tower in towers:
                tower_cells.update(tower.cells)

        for x in range(COLS):
            for y in range(ROWS):
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                if not grid.walkable[x][y]:
                    # Afficher sprite mur SEULEMENT si ce n'est pas une tour
                    if (x, y) not in tower_cells and _wall_image:
                        surf.blit(_wall_image, rect.topleft)
                pygame.draw.rect(surf, (50, 50, 50), rect, 1)

        self._surface = surf
        self._dirty   = False