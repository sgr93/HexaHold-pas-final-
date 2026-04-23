"""
render.py
---------
Initialise pygame et expose les objets globaux (screen, clock, fonts).
Gère le système de tilesets par chapitre.

════════════════════════════════════════════════════════════════
SYSTÈME DE TILESETS
════════════════════════════════════════════════════════════════

Les tiles sont rangés dans :
    assets/sprites/tiles/
        default/          ← fallback (grille sobre, toujours présent)
        ch1/              ← Chapitre 1 : MYSTIC BLUE VILLAGE
            floor_grass.png
            floor_grass2.png
            floor_path.png
            floor_path2.png
            floor_stone.png
            floor_stone2.png
            wall_rock.png
            wall_rock_cracked.png
            wall_tree.png
        ch2/              ← Chapitre 2 : à compléter
        ...

Chaque tileset peut définir :
  - floor_*  : tuiles de sol (cases marchables)
  - wall_*   : tuiles de mur (cases bloquées)

La variation de sol (1 tile sur ~8 = variante) évite la répétition
visuelle sans aucune complexité supplémentaire.
"""

import os
import random
import pygame
from config import (
    GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH,
    COLS, ROWS, GRID_SIZE,
    DISPLAY_FLAGS, WINDOW_CAPTION, BACKGROUND_COLOR
)

# ─────────────────────────────────────────────────────────────────
# SPRITE MURS (legacy, conservé pour compatibilité)
# ─────────────────────────────────────────────────────────────────
_wall_image = None

def load_wall_image():
    """
    Charge assets/sprites/tiles/wall.png si présent (fallback legacy).
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


# ─────────────────────────────────────────────────────────────────
# SYSTÈME DE TILESETS PAR CHAPITRE
# ─────────────────────────────────────────────────────────────────

# Tileset actif (chargé par load_tileset)
_tileset = {
    "floor":      [],   # liste de surfaces sol
    "wall":       [],   # liste de surfaces mur (wall_stone, wall_tree...)
    "floor_map":  {},   # {(x,y): surface} — assignation pré-calculée par case
}

# Répertoire racine des tilesets
_TILES_DIR = os.path.join(os.path.dirname(__file__), "assets", "sprites", "tiles")

# Sprite du goal (base à défendre) — assets/sprites/tiles/goal.png
_goal_image = None

def load_goal_image():
    """Charge assets/sprites/tiles/goal.png si présent."""
    global _goal_image
    path = os.path.join(_TILES_DIR, "goal.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _goal_image = pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))
            print("[render] goal.png chargé.")
        except Exception as e:
            print(f"[render] Impossible de charger goal.png : {e}")

def get_goal_image():
    """Retourne le sprite du goal, ou None si absent."""
    return _goal_image

# Table de correspondance chapitre → dossier de tileset
CHAPTER_TILESET = {
    None: "default",   # parties rapides
    1:    "ch1",       # Chapitre 1 — MYSTIC BLUE VILLAGE
    # 2: "ch2",        # ← ajouter ici les prochains chapitres
}


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
            path = os.path.join(folder, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (GRID_SIZE, GRID_SIZE))
                results.append(img)
            except Exception as e:
                print(f"[render] Impossible de charger {fname} : {e}")
    return results


def load_tileset(chapter=None):
    """
    Charge le tileset correspondant au chapitre donné.
    Appelé depuis game.py avant de lancer une partie.

    Exemple :
        render.load_tileset(chapter=1)   # Chapitre 1
        render.load_tileset()            # Partie rapide (défaut)
    """
    global _tileset

    folder_name = CHAPTER_TILESET.get(chapter, CHAPTER_TILESET.get(None, "default"))
    folder = os.path.join(_TILES_DIR, folder_name)

    floor_imgs = _load_images_from_dir(folder, "floor_")
    wall_imgs  = _load_images_from_dir(folder, "wall_")

    # Fallback : si le dossier est vide ou absent, on reste en mode couleur unie
    if not floor_imgs:
        print(f"[render] Tileset '{folder_name}' : aucun floor_ trouvé, mode couleur.")
    if not wall_imgs:
        print(f"[render] Tileset '{folder_name}' : aucun wall_ trouvé, fallback wall.png.")

    _tileset["floor"]     = floor_imgs
    _tileset["wall"]      = wall_imgs
    _tileset["floor_map"] = {}   # sera rempli à la première reconstruction du cache

    print(f"[render] Tileset '{folder_name}' : {len(floor_imgs)} floor, {len(wall_imgs)} wall.")


def _get_floor_tile(x, y):
    """
    Retourne le tile de sol — floor_grass.png, identique sur toutes les cases.
    """
    floors = _tileset["floor"]
    if not floors:
        return None
    return floors[0]


def _get_wall_tile(x, y):
    """
    Retourne la surface de mur pour la case (x, y).
    Légère variation pour éviter les murs uniformes.
    """
    walls = _tileset["wall"]
    if not walls:
        return _wall_image   # fallback legacy
    idx = (x * 11 + y * 7) % len(walls)
    return walls[idx]


# ─────────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────────

_font_cache = {}

def get_font(size_key="md", bold=False):
    """Retourne une font en cache."""
    sizes = {"xs": 14, "sm": 18, "md": 22, "lg": 30, "xl": 48}
    size = sizes.get(size_key, 22)
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("arial", size, bold=bold)
    return _font_cache[key]


# ─────────────────────────────────────────────────────────────────
# INITIALISATION PYGAME
# ─────────────────────────────────────────────────────────────────

def init_pygame():
    """Initialise pygame, crée la fenêtre adaptée à la résolution de l'écran."""
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    pygame.display.set_caption(WINDOW_CAPTION)

    ideal_w = GRID_WIDTH + INTERFACE_WIDTH + 220
    ideal_h = GRID_HEIGHT + 160

    info  = pygame.display.Info()
    scr_w = info.current_w
    scr_h = info.current_h

    MARGIN_W = 40
    MARGIN_H = 80

    win_w = min(ideal_w, scr_w - MARGIN_W)
    win_h = min(ideal_h, scr_h - MARGIN_H)
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


# ─────────────────────────────────────────────────────────────────
# GRIDCACHE — pré-rendu de la grille avec tilesets
# ─────────────────────────────────────────────────────────────────

class GridCache:
    """
    Pré-rend la grille (sol + murs + grille) sur une Surface
    et la restitue en un seul blit chaque frame.

    Utilisation :
        cache = GridCache()
        cache.invalidate()
        cache.draw(screen, grid, ox, oy, towers=towers)
    """

    def __init__(self):
        self._surface = None
        self._dirty   = True

    def invalidate(self):
        """Marque le cache comme obsolète."""
        self._dirty = True

    def draw(self, screen, grid, offset_x, offset_y, towers=None):
        if self._dirty or self._surface is None:
            self._rebuild(grid, towers)
        screen.blit(self._surface, (offset_x, offset_y))

    def _rebuild(self, grid, towers=None):
        """Reconstruit la surface avec tiles de sol et de mur."""
        surf = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        tower_cells = set()
        if towers:
            for tower in towers:
                tower_cells.update(tower.cells)

        for x in range(COLS):
            for y in range(ROWS):
                px = x * GRID_SIZE
                py = y * GRID_SIZE
                cell_rect = pygame.Rect(px, py, GRID_SIZE, GRID_SIZE)

                if grid.walkable[x][y]:
                    # ── Case marchable : tile de sol ──
                    floor_tile = _get_floor_tile(x, y)
                    if floor_tile:
                        surf.blit(floor_tile, (px, py))
                    else:
                        # Fallback couleur (vert foncé)
                        pygame.draw.rect(surf, (34, 45, 34), cell_rect)

                else:
                    # ── Case bloquée ──
                    if (x, y) in tower_cells:
                        # Case occupée par une tour : sol en dessous seulement
                        # (le sprite de la tour sera dessiné par-dessus après)
                        floor_tile = _get_floor_tile(x, y)
                        if floor_tile:
                            surf.blit(floor_tile, (px, py))
                        else:
                            pygame.draw.rect(surf, (34, 45, 34), cell_rect)
                    else:
                        # ── Case bloquée par un mur ──
                        wall_tile = _get_wall_tile(x, y)
                        if wall_tile:
                            floor_tile = _get_floor_tile(x, y)
                            if floor_tile:
                                surf.blit(floor_tile, (px, py))
                            surf.blit(wall_tile, (px, py))
                        else:
                            # Fallback couleur (gris pierre)
                            pygame.draw.rect(surf, (80, 75, 70), cell_rect)

                # Grille invisible (les tiles donnent la lecture spatiale)
                # Décommenter la ligne suivante pour déboguer le placement de tours :
                # pygame.draw.rect(surf, (0, 0, 0, 25), cell_rect, 1)

        self._surface = surf
        self._dirty   = False