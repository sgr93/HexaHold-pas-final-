"""
walls.py
--------
Génère des murs aléatoires 2×2 dans une zone définie de la grille.
Utilisé au démarrage pour créer des obstacles variés.

"""

import random
import heapq
from config import COLS, ROWS, START, END


def _path_exists(grid):
    """Retourne True si un chemin praticable existe entre START et END."""
    sx, sy = START
    ex, ey = END
    if not grid.walkable[sx][sy] or not grid.walkable[ex][ey]:
        return False
    visited = [[False] * ROWS for _ in range(COLS)]
    queue = [(sx, sy)]
    visited[sx][sy] = True
    while queue:
        x, y = queue.pop()
        if x == ex and y == ey:
            return True
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and not visited[nx][ny] and grid.walkable[nx][ny]:
                visited[nx][ny] = True
                queue.append((nx, ny))
    return False


def spawn_random_walls(grid, num_walls, zone_start=(0, 0), zone_end=(COLS - 2, ROWS - 2)):
    """
    Place `num_walls` blocs 2×2 aléatoires dans la grille.

    Paramètres :
        grid        : objet Grid (modifié en place)
        num_walls   : nombre de blocs à tenter de placer
        zone_start  : coin haut-gauche de la zone autorisée (cases)
        zone_end    : coin bas-droit de la zone autorisée (cases)

    FIX #4 : zone_end est clampé à (COLS-2, ROWS-2) pour garantir que
        le bloc 2×2 tient entièrement dans la grille, même si l'appelant
        passe une borne trop grande.
    FIX-WALL-PATH : chaque mur placé est vérifié pour ne pas bloquer le chemin
        START→END. Si c'est le cas, il est immédiatement retiré.

    Si le nombre de tentatives est épuisé avant d'avoir placé tous les blocs,
    un avertissement est affiché mais le jeu continue normalement.
    """
    # Clamp : garantit que le bloc 2×2 ne déborde jamais hors grille
    zone_end = (min(zone_end[0], COLS - 2), min(zone_end[1], ROWS - 2))

    placed       = 0
    max_attempts = num_walls * 20
    attempts     = 0

    while placed < num_walls and attempts < max_attempts:
        attempts += 1
        x = random.randint(zone_start[0], zone_end[0])
        y = random.randint(zone_start[1], zone_end[1])

        # Vérifie que les 4 cases du bloc sont libres
        if (grid.walkable[x][y]     and grid.walkable[x + 1][y] and
                grid.walkable[x][y + 1] and grid.walkable[x + 1][y + 1]):
            # Place temporairement le bloc
            grid.walkable[x][y]         = False
            grid.walkable[x + 1][y]     = False
            grid.walkable[x][y + 1]     = False
            grid.walkable[x + 1][y + 1] = False
            # FIX-WALL-PATH : annule si le chemin est coupe
            if _path_exists(grid):
                placed += 1
            else:
                grid.walkable[x][y]         = True
                grid.walkable[x + 1][y]     = True
                grid.walkable[x][y + 1]     = True
                grid.walkable[x + 1][y + 1] = True

    if placed < num_walls:
        print(f"[walls] Attention : seulement {placed}/{num_walls} blocs placés "
              f"(tentatives épuisées après {attempts}).")
