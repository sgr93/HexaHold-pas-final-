"""
ui/render.py

Initialise pygame et expose les objets globaux (screen, clock, fonts).
Gère le système de tilesets et le cache de rendu de la grille.

SYSTÈME DE TILESETS
Les tiles sont rangés dans assets/sprites/tiles/default/ :
    floor_grass.png, floor_grass2.png, floor_path.png ...
    wall_rock_tl/tr/bl/br.png, wall_tree_tl/tr/bl/br.png

Le tileset est unique (dossier "default") pour tous les niveaux —
le paramètre chapter dans load_tileset est conservé pour compatibilité.
"""

import os
import random
import pygame
from core.config import (
    GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH,
    COLS, ROWS, GRID_SIZE, DISPLAY_FLAGS, WINDOW_CAPTION, BACKGROUND_COLOR,
)


# GLOBALS — initialisés dans init_pygame(), utilisés partout dans le projet
screen   = None
clock    = None
font     = None
big_font = None

# Répertoire racine des tilesets — tout part de là
_TILES_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "tiles")

# Tileset actif — chargé par load_tileset(), réinitialisé à chaque nouvelle partie
_tileset = {
    "floor":         [],  # tuiles de sol
    "wall":          [],  # pool complet de murs (fallback)
    "wall_rock_tl":  [],  # coins rock — auto-tiling 4 coins
    "wall_rock_tr":  [],
    "wall_rock_bl":  [],
    "wall_rock_br":  [],
    "wall_tree_tl":  [],  # coins arbre — même système
    "wall_tree_tr":  [],
    "wall_tree_bl":  [],
    "wall_tree_br":  [],
    "floor_map":     {},  # {(x,y): surface} — assignation pré-calculée si besoin
}

_wall_image   = None  # sprite legacy wall.png
_goal_image   = None  # sprite de la base à défendre
_grid_bg_image = None  # fond PNG derrière la grille
_font_cache   = {}    # cache des objets font — évite de les recréer à chaque frame


# SPRITE MURS LEGACY

def load_wall_image():
    """
    Charge wall.png si présent — fallback legacy conservé pour compatibilité.
    Sans ce fichier le jeu continue normalement avec le système de tilesets.
    """
    global _wall_image
    path = os.path.join(_TILES_DIR, "wall.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _wall_image = pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))
        except Exception as e:
            print(f"[render] Impossible de charger wall.png : {e}")


# GOAL

def load_goal_image():
    """Charge goal.png — le sprite de la base que le joueur doit défendre."""
    global _goal_image
    path = os.path.join(_TILES_DIR, "goal.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _goal_image = pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))
        except Exception as e:
            print(f"[render] Impossible de charger goal.png : {e}")


def get_goal_image():
    return _goal_image


# FOND DE GRILLE

def load_grid_bg():
    """
    Charge grid_bg.png comme fond derrière la grille.
    Même fond pour tous les modes — pas de variation par chapitre pour l'instant.
    """
    global _grid_bg_image
    path = os.path.join(_TILES_DIR, "grid_bg.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _grid_bg_image = pygame.transform.scale(img, (GRID_WIDTH, GRID_HEIGHT))
        except Exception as e:
            print(f"[render] Impossible de charger grid_bg.png : {e}")
            _grid_bg_image = None
    else:
        _grid_bg_image = None


def get_grid_bg():
    return _grid_bg_image


# CHARGEMENT DES TILESETS

def _load_images_from_dir(folder, prefix):
    """
    Charge tous les PNG de `folder` dont le nom commence par `prefix`.
    Retourne une liste de surfaces redimensionnées à GRID_SIZE×GRID_SIZE.
    """
    results = []
    if not os.path.isdir(folder):
        return results
    for fname in sorted(os.listdir(folder)):
        if fname.startswith(prefix) and fname.endswith(".png"):
            try:
                img = pygame.image.load(os.path.join(folder, fname)).convert_alpha()
                results.append(pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE)))
            except Exception as e:
                print(f"[render] Impossible de charger {fname} : {e}")
    return results


def load_tileset(chapter=None):
    """
    Charge le tileset depuis assets/sprites/tiles/default/.
    Le paramètre chapter est ignoré — tileset unique pour tous les niveaux,
    mais conservé dans la signature pour ne pas casser les appels existants.
    """
    global _tileset

    folder = os.path.join(_TILES_DIR, "default")

    floor_imgs   = _load_images_from_dir(folder, "floor_")
    wall_rock_tl = _load_images_from_dir(folder, "wall_rock_tl")
    wall_rock_tr = _load_images_from_dir(folder, "wall_rock_tr")
    wall_rock_bl = _load_images_from_dir(folder, "wall_rock_bl")
    wall_rock_br = _load_images_from_dir(folder, "wall_rock_br")
    wall_tree_tl = _load_images_from_dir(folder, "wall_tree_tl")
    wall_tree_tr = _load_images_from_dir(folder, "wall_tree_tr")
    wall_tree_bl = _load_images_from_dir(folder, "wall_tree_bl")
    wall_tree_br = _load_images_from_dir(folder, "wall_tree_br")

    wall_rock_imgs = wall_rock_tl + wall_rock_tr + wall_rock_bl + wall_rock_br
    wall_tree_imgs = wall_tree_tl + wall_tree_tr + wall_tree_bl + wall_tree_br

    if not floor_imgs:
        print("[render] Tileset 'default' : aucun floor_ trouvé, mode couleur.")
    if not wall_rock_imgs:
        print("[render] Tileset 'default' : aucun wall_rock* trouvé.")
    if not wall_tree_imgs:
        print("[render] Tileset 'default' : aucun wall_tree* trouvé.")

    _tileset.update({
        "floor":         floor_imgs,
        "wall":          wall_rock_imgs + wall_tree_imgs,
        "wall_rock_tl":  wall_rock_tl,
        "wall_rock_tr":  wall_rock_tr,
        "wall_rock_bl":  wall_rock_bl,
        "wall_rock_br":  wall_rock_br,
        "wall_tree_tl":  wall_tree_tl,
        "wall_tree_tr":  wall_tree_tr,
        "wall_tree_bl":  wall_tree_bl,
        "wall_tree_br":  wall_tree_br,
        "floor_map":     {},
    })

    print(f"[render] Tileset 'default' : {len(floor_imgs)} floor, "
          f"{len(wall_rock_imgs)} wall_rock, {len(wall_tree_imgs)} wall_tree.")
    load_grid_bg()


def _get_floor_tile(x, y):
    """
    Retourne le tile de sol pour la case (x, y).
    Le premier floor reste majoritaire — les variantes apparaissent sur ~1/8 des cases
    via un hash déterministe pour éviter le scintillement entre frames.
    """
    floors = _tileset["floor"]
    if not floors:
        return None
    if len(floors) == 1:
        return floors[0]
    h = (x * 73856093) ^ (y * 19349663)
    if (h % 8) == 0:
        return floors[1 + ((h >> 3) % (len(floors) - 1))]
    return floors[0]


def _get_wall_tile(x, y, wall_type="rock", grid=None, wall_cells=None):
    """
    Auto-tiling simplifié en 4 coins : chaque mur choisit son coin selon
    la présence de voisins à droite et en bas. Ça donne des jonctions propres
    sans avoir à gérer les 16 cas d'un auto-tiling complet.
    """
    if not grid:
        return None

    right = x + 1 < COLS and (x + 1, y) in wall_cells
    down  = y + 1 < ROWS and (x, y + 1) in wall_cells

    # tl si voisins des deux côtés, tr si seulement en bas, bl si seulement à droite, br sinon
    if right and down:
        suffix = "tl"
    elif not right and down:
        suffix = "tr"
    elif right and not down:
        suffix = "bl"
    else:
        suffix = "br"

    pool = _tileset.get(f"wall_{wall_type}_{suffix}", [])
    return pool[0] if pool else None


# FONTS

def get_font(size_key="md", bold=False):
    """Cache de fonts — on évite de recréer les objets à chaque frame."""
    sizes = {"xs": 14, "sm": 18, "md": 22, "lg": 30, "xl": 48}
    key   = (sizes.get(size_key, 22), bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("arial", key[0], bold=bold)
    return _font_cache[key]


# INITIALISATION PYGAME

def init_pygame():
    """
    Initialise pygame et crée la fenêtre en s'adaptant à la résolution de l'écran.
    On essaie d'ouvrir en taille idéale avec une marge de sécurité, et on clamp
    à un minimum de 600×480 pour les petits écrans.
    """
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    pygame.display.set_caption(WINDOW_CAPTION)

    ideal_w = GRID_WIDTH + INTERFACE_WIDTH + 220
    ideal_h = GRID_HEIGHT + 160
    info    = pygame.display.Info()

    win_w = max(600, min(ideal_w, info.current_w - 40))
    win_h = max(480, min(ideal_h, info.current_h - 80))

    global screen, clock, font, big_font
    screen   = pygame.display.set_mode((win_w, win_h), DISPLAY_FLAGS)
    clock    = pygame.time.Clock()
    font     = get_font("md")
    big_font = get_font("xl", bold=True)


# GRIDCACHE — pré-rendu de la grille avec tilesets

class GridCache:
    """
    Pré-rend la grille (sol + murs) sur une Surface et la restitue en un seul blit.
    On ne reconstruit que si invalidate() a été appelé — typiquement après un placement
    de tour ou un changement de tileset. Ça évite de re-dessiner ~500 tiles à chaque frame.

    Utilisation :
        cache = GridCache()
        cache.invalidate()
        cache.draw(screen, grid, ox, oy, towers=towers)
    """

    def __init__(self):
        self._surface = None
        self._dirty   = True

    def invalidate(self):
        self._dirty = True

    def draw(self, screen, grid, offset_x, offset_y, towers=None):
        if self._dirty or self._surface is None:
            self._rebuild(grid, towers)
        screen.blit(self._surface, (offset_x, offset_y))

    def _rebuild(self, grid, towers=None):
        """Reconstruit la surface complète de la grille."""
        surf = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # On collecte les cellules de mur pour l'auto-tiling
        wall_cells = set()
        if hasattr(grid, "wall_types"):
            wall_cells = set(grid.wall_types.keys())

        bg = get_grid_bg()
        if bg:
            surf.blit(bg, (0, 0))

        tower_cells = set()
        if towers:
            for tower in towers:
                tower_cells.update(tower.cells)

        for x in range(COLS):
            for y in range(ROWS):
                px        = x * GRID_SIZE
                py        = y * GRID_SIZE
                cell_rect = pygame.Rect(px, py, GRID_SIZE, GRID_SIZE)

                if grid.walkable[x][y]:
                    floor_tile = _get_floor_tile(x, y)
                    surf.blit(floor_tile, (px, py)) if floor_tile else pygame.draw.rect(surf, (34, 45, 34), cell_rect)

                elif (x, y) in tower_cells:
                    # Case de tour : on dessine le sol en dessous, la tour s'affichera par-dessus
                    floor_tile = _get_floor_tile(x, y)
                    surf.blit(floor_tile, (px, py)) if floor_tile else pygame.draw.rect(surf, (34, 45, 34), cell_rect)

                else:
                    # Mur : sol + tuile de mur par-dessus pour que le mur ait un fond cohérent
                    wall_type = "rock"
                    if hasattr(grid, "wall_types"):
                        wall_type = grid.wall_types.get((x, y), "rock")
                    wall_tile  = _get_wall_tile(x, y, wall_type, grid, wall_cells)
                    floor_tile = _get_floor_tile(x, y)
                    if wall_tile:
                        if floor_tile:
                            surf.blit(floor_tile, (px, py))
                        surf.blit(wall_tile, (px, py))
                    else:
                        pygame.draw.rect(surf, (80, 75, 70), cell_rect)

                # Ligne de debug désactivée — décommenter pour visualiser les cellules :
                # pygame.draw.rect(surf, (0, 0, 0, 25), cell_rect, 1)

        self._surface = surf
        self._dirty   = False