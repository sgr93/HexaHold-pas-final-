"""
walls.py

Définition MANUELLE des maps : une map différente par mission (mode histoire)
ou une map par défaut pour les parties rapides / modes hors histoire.

La grille fait COLS=14 colonnes (x) et ROWS=18 lignes (y).
Utilise rect(x, y, w, h) pour des blocs rectangulaires.
Utilise col(x, y_start, y_end) pour une colonne verticale.

|ATTRIBUER UNE MAP À UNE MISSION| :

Dans le dictionnaire MISSION_MAPS :
  - La clé (chapter, mission) -> map utilise pour chapitre mission
  - La clé None  -> map utilisée pour toutes les parties rapides / hors histoire.

Exemple :
MISSION_MAPS = {
        None:   MAP_DEFAULT,          # parties rapides
        (1, 0): MAP_CH1_M1,           # Chapitre 1, Mission 1
        (1, 1): MAP_CH1_M2,           # Chapitre 1, Mission 2
        (2, 0): MAP_CH2_M1,           # Chapitre 2, Mission 1
}

Si une mission n'a pas de clé dans MISSION_MAPS, la map None (défaut) est utilisée.
"""

from core.config import COLS, ROWS, END

# UTILITAIRES DE CONSTRUCTION
# Chaque case est un triplet (x, y, wall_type) où wall_type est :
#   "rock"  : tuiles wall_rock_*   (rochers)
#   "tree"  : tuile  wall_tree_*   (arbres)

# Toutes les cases d'un même appel partagent le même wall_type.
# Un mur ne peut pas être un mélange des deux.

WALL_ROCK = "rock"
WALL_TREE = "tree"

def rect(x, y, w, h, wall_type=WALL_ROCK):
    """Rectangle de w×h cases à partir de (x, y)."""
    return [(x + dx, y + dy, wall_type) for dx in range(w) for dy in range(h)]

def col(x, y_start, y_end, wall_type=WALL_ROCK):
    """Colonne verticale sur x entre y_start et y_end (inclus)."""
    return [(x, y, wall_type) for y in range(y_start, y_end + 1)]

def row(y, x_start, x_end, wall_type=WALL_ROCK):
    """Ligne horizontale sur y entre x_start et x_end (inclus)."""
    return [(x, y, wall_type) for x in range(x_start, x_end + 1)]


# MAP PAR DÉFAUT  (parties rapides, modes hors histoire)

MAP_DEFAULT = [
    *rect(2,  4, 2, 2, WALL_ROCK),
    *rect(8,  4, 2, 2, WALL_ROCK),
    *rect(14, 4, 2, 2, WALL_ROCK),

    *rect(4,  8, 2, 2, WALL_TREE),
    *rect(12, 8, 2, 2, WALL_TREE),

    *rect(8, 10, 2, 2, WALL_ROCK),

    *rect(2,  13, 2, 2, WALL_TREE),
    *rect(7,  13, 2, 2, WALL_TREE),
    *rect(14, 13, 2, 2, WALL_TREE),

    *rect(4,  15, 2, 2, WALL_ROCK),
    *rect(12, 15, 2, 2, WALL_ROCK),
]


# MAP MODE INFINI
MAP_INFINITE = [

    *rect(1, 1, 2, 2, WALL_ROCK),
    *rect(6, 1, 2, 2, WALL_TREE),
    *rect(11, 1, 2, 2, WALL_ROCK),
    *rect(15, 1, 2, 2, WALL_TREE),
    *rect(3, 4, 2, 2, WALL_TREE),
    *rect(9, 4, 2, 2, WALL_ROCK),
    *rect(14, 4, 2, 2, WALL_TREE),
    *rect(1, 7, 2, 2, WALL_ROCK),
    *rect(15, 7, 2, 2, WALL_TREE),
    *rect(4, 10, 2, 2, WALL_TREE),
    *rect(10, 10, 2, 2, WALL_ROCK),
    *rect(13, 10, 2, 2, WALL_TREE),
    *rect(2, 13, 2, 2, WALL_ROCK),
    *rect(7, 13, 2, 2, WALL_TREE),
    *rect(12, 13, 2, 2, WALL_ROCK),
]



MAP_A = [
    *rect(2, 2, 2, 2, WALL_ROCK),
    *rect(7, 3, 2, 2, WALL_TREE),
    *rect(12, 4, 2, 2, WALL_ROCK),
    *rect(4, 6, 2, 2, WALL_TREE),
    *rect(10, 6, 2, 2, WALL_TREE),
    *rect(15, 7, 2, 2, WALL_ROCK),
    *rect(3, 10, 2, 2, WALL_ROCK),
    *rect(9, 11, 2, 2, WALL_TREE),
    *rect(6, 14, 2, 2, WALL_ROCK),
    *rect(13, 13, 2, 2, WALL_TREE),
]

MAP_B = [
    *rect(2, 2, 2, 2, WALL_ROCK),
    *rect(8, 3, 2, 2, WALL_TREE),
    *rect(14, 2, 2, 2, WALL_ROCK),
    *rect(5, 5, 2, 2, WALL_TREE),
    *rect(11, 6, 2, 2, WALL_ROCK),
    *rect(3, 8, 2, 2, WALL_ROCK),
    *rect(9, 9, 2, 2, WALL_TREE),
    *rect(15, 10, 2, 2, WALL_ROCK),
    *rect(6, 12, 2, 2, WALL_TREE),
    *rect(12, 13, 2, 2, WALL_ROCK),
]

MAP_C = [
    *rect(2, 2, 2, 2, WALL_TREE),
    *rect(6, 2, 2, 2, WALL_TREE),
    *rect(10, 2, 2, 2, WALL_TREE),
    *rect(14, 2, 2, 2, WALL_TREE),
    *rect(4, 5, 2, 2, WALL_TREE),
    *rect(12, 5, 2, 2, WALL_TREE),
    *rect(2, 8, 2, 2, WALL_ROCK),
    *rect(6, 8, 2, 2, WALL_TREE),
    *rect(10, 8, 2, 2, WALL_TREE),
    *rect(14, 8, 2, 2, WALL_ROCK),
    *rect(4, 11, 2, 2, WALL_TREE),
    *rect(12, 11, 2, 2, WALL_TREE),
    *rect(2, 14, 2, 2, WALL_TREE),
    *rect(8, 14, 2, 2, WALL_TREE),
    *rect(14, 14, 2, 2, WALL_TREE),
]


#J'ai la flemme de faire une map par mission donc
#j'ai fait 3 map qui se repete a chaque chapitre


MISSION_MAPS = {
    None: MAP_A, #Partie rapide ou mode infni
    # Chapitre 1
    (1, 0): MAP_A, #Mission 1
    (1, 1): MAP_B, #Mission 2
    (1, 2): MAP_C, #Mission 3 
    # Chapitre 2
    (2, 0): MAP_A, #Idem
    (2, 1): MAP_B,
    (2, 2): MAP_C,
    # Chapitre 3
    (3, 0): MAP_A, #Idem
    (3, 1): MAP_B,
    (3, 2): MAP_C,
    # Chapitre 4
    (4, 0): MAP_A, #idem
    (4, 1): MAP_B,
    (4, 2): MAP_C,
    # Chapitre 5
    (5, 0): MAP_A, # Idem
    (5, 1): MAP_B,
    (5, 2): MAP_C,
}


# MOTEUR D'APPLICATION 

def _path_exists_from_row0(grid):
    """Vérifie qu'un chemin existe de la rangée 0 jusqu'à END."""
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


def _apply_walls_list(grid, walls_list, label=""):
    """
    Applique une liste de cases bloquées sur la grille.
    Chaque entrée est soit (x, y) soit (x, y, wall_type).
    wall_type est stocké dans grid.wall_types[x][y].
    """
    # Initialise le dictionnaire de types si absent
    if not hasattr(grid, "wall_types"):
        grid.wall_types = {}

    skipped = 0
    for entry in walls_list:
        if len(entry) == 3:
            x, y, wall_type = entry
        else:
            x, y = entry
            wall_type = WALL_ROCK  # fallback compatibilité

        if not (0 <= x < COLS and 0 <= y < ROWS):
            print(f"[walls{label}] ({x},{y}) hors grille — ignorée.")
            skipped += 1
            continue
        if not grid.walkable[x][y]:
            continue
        grid.walkable[x][y] = False
        if not _path_exists_from_row0(grid):
            grid.walkable[x][y] = True
            print(f"[walls{label}] ({x},{y}) retirée — bloquerait tous les chemins.")
            skipped += 1
        else:
            grid.wall_types[(x, y)] = wall_type
            grid.wall_cells.add((x, y))

    total = len(walls_list)
    if skipped:
        print(f"[walls{label}] {skipped}/{total} case(s) ignorée(s).")
    else:
        print(f"[walls{label}] {total} cases appliquées.")


def apply_map_walls(grid, chapter=None, mission=None, infinite=False):
    """
    Applique la map correspondant à (chapter, mission).
    Si aucune map spécifique n'existe, utilise MAP_DEFAULT.
    Si infinite=True, applique MAP_INFINITE.

    Appelé depuis game.py :
        apply_map_walls(grid)                        # partie rapide
        apply_map_walls(grid, chapter=1, mission=0)  # mode histoire
        apply_map_walls(grid, infinite=True)         # mode infini
    """
    if infinite:
        _apply_walls_list(grid, MAP_INFINITE, " (infini)")
        return

    key = (chapter, mission) if chapter is not None else None
    walls_list = MISSION_MAPS.get(key, MISSION_MAPS.get(None, []))

    if key is not None and key not in MISSION_MAPS:
        print(f"[walls] Pas de map pour {key}, utilisation de la map par défaut.")

    label = f" Ch{chapter}-M{mission+1}" if chapter is not None else " (défaut)"
    _apply_walls_list(grid, walls_list, label)


# Alias de compatibilité
def spawn_random_walls(grid, *args, **kwargs):
    """ appelle apply_map_walls """
    apply_map_walls(grid)