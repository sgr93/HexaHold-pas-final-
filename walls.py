"""
walls.py
--------
Définition MANUELLE de la map : tu places toi-même les murs ici.

Comment modifier la map :
--------------------------
La grille fait COLS=14 colonnes (x) et ROWS=18 lignes (y).
  - (0, 0)   = coin haut-gauche
  - (13, 17) = coin bas-droit

Chaque entrée dans MAP_WALLS est une case bloquée : (x, y)
Utilise la fonction rect(x, y, w, h) pour des blocs rectangulaires.

Ajoute ou supprime des lignes dans MAP_WALLS pour sculpter ta map.
La vérification de chemin garantit qu'un passage reste toujours possible.
"""

from config import COLS, ROWS, END


# ============================================================
# UTILITAIRE : rectangle de cases
# ============================================================

def rect(x, y, w, h):
    """Génère toutes les cases d'un rectangle de w×h cases à partir de (x, y)."""
    return [(x + dx, y + dy) for dx in range(w) for dy in range(h)]


# ============================================================
# DÉFINITION DE LA MAP  ← MODIFIE ICI
# ============================================================
#
# Grille 14 colonnes × 18 lignes :
#   Colonne :  0  1  2  3  4  5  6  7  8  9 10 11 12 13
#   Ligne 0  : ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← entrées ennemis
#   Ligne 17 : ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← base à défendre

MAP_WALLS = [
    # --- Obstacles haut ---
    *rect(2,  4, 2, 2),
    *rect(6,  3, 2, 2),
    *rect(10, 4, 2, 2),

    # --- Obstacles milieu ---
    *rect(3,  8, 2, 2),
    *rect(9,  8, 2, 2),

    # --- Obstacles bas ---
    *rect(1,  13, 2, 2),
    *rect(5,  12, 2, 2),
    *rect(10, 13, 2, 2),
]


# ============================================================
# PLACEMENT DES MURS SUR LA GRILLE
# ============================================================

def _path_exists_from_row0(grid):
    """
    Vérifie qu'un chemin existe depuis AU MOINS UNE case libre de la
    rangée 0 jusqu'à END. Garantit que la map reste jouable.
    """
    ex, ey = END
    if not grid.walkable[ex][ey]:
        return False

    visited = [[False] * ROWS for _ in range(COLS)]
    queue   = []

    for x in range(COLS):
        if grid.walkable[x][0]:
            queue.append((x, 0))
            visited[x][0] = True

    while queue:
        x, y = queue.pop()
        if x == ex and y == ey:
            return True
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < COLS and 0 <= ny < ROWS
                    and not visited[nx][ny] and grid.walkable[nx][ny]):
                visited[nx][ny] = True
                queue.append((nx, ny))
    return False


def apply_map_walls(grid):
    """
    Applique MAP_WALLS sur la grille.
    Si une case coupe tous les chemins, elle est ignorée avec un avertissement.
    """
    skipped = 0
    for (x, y) in MAP_WALLS:
        if not (0 <= x < COLS and 0 <= y < ROWS):
            print(f"[walls] ({x},{y}) hors grille — ignorée.")
            skipped += 1
            continue
        if not grid.walkable[x][y]:
            continue
        grid.walkable[x][y] = False
        if not _path_exists_from_row0(grid):
            grid.walkable[x][y] = True
            print(f"[walls] ({x},{y}) retirée — bloquerait tous les chemins.")
            skipped += 1

    total = len(MAP_WALLS)
    if skipped:
        print(f"[walls] {skipped}/{total} case(s) ignorée(s).")
    else:
        print(f"[walls] {total} cases appliquées.")


# Compatibilité avec l'ancien nom utilisé dans game.py
def spawn_random_walls(grid, *args, **kwargs):
    """Alias conservé pour compatibilité — appelle apply_map_walls."""
    apply_map_walls(grid)