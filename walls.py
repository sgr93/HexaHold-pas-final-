"""
walls.py
--------
Définition MANUELLE des maps : une map différente par mission (mode histoire)
ou une map par défaut pour les parties rapides / modes hors histoire.

════════════════════════════════════════════════════════════════
COMMENT CRÉER / MODIFIER UNE MAP
════════════════════════════════════════════════════════════════

La grille fait COLS=14 colonnes (x) et ROWS=18 lignes (y).
  - (0, 0)   = coin haut-gauche
  - (13, 17) = coin bas-droit
  - Ligne 0  = entrée des ennemis (haut)
  - Ligne 17 = base à défendre   (bas)

  Colonne :  0  1  2  3  4  5  6  7  8  9 10 11 12 13
  Ligne 0  : ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← ennemis
  Ligne 17 : ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← base

Utilise rect(x, y, w, h) pour des blocs rectangulaires.
Utilise col(x, y_start, y_end) pour une colonne verticale.

════════════════════════════════════════════════════════════════
ATTRIBUER UNE MAP À UNE MISSION
════════════════════════════════════════════════════════════════

Dans le dictionnaire MISSION_MAPS :
  - La clé (chapter, mission) pointe sur une liste de cases bloquées.
  - La clé None  → map utilisée pour toutes les parties rapides / hors histoire.

Exemple :
    MISSION_MAPS = {
        None:   MAP_DEFAULT,          # parties rapides
        (1, 0): MAP_CH1_M1,           # Chapitre 1, Mission 1
        (1, 1): MAP_CH1_M2,           # Chapitre 1, Mission 2
        (2, 0): MAP_CH2_M1,           # Chapitre 2, Mission 1
    }

Si une mission n'a pas de clé dans MISSION_MAPS, la map None (défaut) est utilisée.
"""

from config import COLS, ROWS, END


# ════════════════════════════════════════════════════════════════
# UTILITAIRES DE CONSTRUCTION
# ════════════════════════════════════════════════════════════════

def rect(x, y, w, h):
    """Rectangle de w×h cases à partir de (x, y)."""
    return [(x + dx, y + dy) for dx in range(w) for dy in range(h)]

def col(x, y_start, y_end):
    """Colonne verticale sur x entre y_start et y_end (inclus)."""
    return [(x, y) for y in range(y_start, y_end + 1)]

def row(y, x_start, x_end):
    """Ligne horizontale sur y entre x_start et x_end (inclus)."""
    return [(x, y) for x in range(x_start, x_end + 1)]


# ════════════════════════════════════════════════════════════════
# MAP PAR DÉFAUT  (parties rapides, modes hors histoire)
# ════════════════════════════════════════════════════════════════

MAP_DEFAULT = [
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


# ════════════════════════════════════════════════════════════════
# CHAPITRE 1 — LA BATAILLE DE TROST
# ════════════════════════════════════════════════════════════════
#
# Ambiance : village, herbe, rochers, arbres
# Tileset  : MYSTIC BLUE VILLAGE (grass + rocks + trees)
#
#   Colonne :  0  1  2  3  4  5  6  7  8  9 10 11 12 13
#   Ligne 0  : ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← ennemis
#   Ligne 17 : ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← base

# Mission 1 — Tenir le Fort
# Disposition : couloir central ouvert, blocs latéraux symétriques
MAP_CH1_M1 = [
    # Bords gauche (rochers / arbres)
    *rect(0,  2, 1, 3),   # lisière gauche haut
    *rect(0,  9, 1, 3),   # lisière gauche milieu
    *rect(0, 14, 1, 3),   # lisière gauche bas

    # Bords droit
    *rect(13, 2, 1, 3),
    *rect(13, 9, 1, 3),
    *rect(13,14, 1, 3),

    # Obstacles haut (2 blocs)
    *rect(2, 3, 2, 2),
    *rect(9, 3, 2, 2),

    # Obstacles milieu (2 blocs avec couloir central)
    *rect(2, 8, 2, 2),
    *rect(9, 8, 2, 2),

    # Obstacles bas (3 blocs)
    *rect(1, 13, 2, 2),
    *rect(5, 12, 2, 2),
    *rect(10,13, 2, 2),
]

# Mission 2 — La Contre-Attaque
# Disposition : plus dense, les ennemis ont moins de place
MAP_CH1_M2 = [
    # Rangée de rochers en haut
    *rect(1, 2, 2, 2),
    *rect(5, 2, 2, 2),
    *rect(9, 2, 2, 2),

    # Obstacles milieu-haut
    *rect(3, 6, 2, 2),
    *rect(8, 6, 2, 2),

    # Ligne de pierres centrale (chemin forcé)
    *rect(1,  10, 2, 1),
    *rect(6,  10, 2, 1),
    *rect(10, 10, 2, 1),

    # Obstacles bas
    *rect(2,  14, 2, 2),
    *rect(7,  13, 2, 2),
    *rect(11, 14, 2, 2),
]

# Mission 3 — Le Titan de Trost
# Disposition : labyrinthique, boss difficile à esquiver
MAP_CH1_M3 = [
    # Couloirs forcés avec chicanes
    *rect(1,  2, 2, 3),
    *rect(10, 2, 2, 3),

    *rect(3,  6, 2, 2),
    *rect(8,  6, 2, 2),

    *rect(1,  9, 4, 1),   # mur horizontal bas-gauche
    *rect(8,  9, 4, 1),   # mur horizontal bas-droit

    *rect(4,  12, 2, 2),
    *rect(7,  12, 2, 2),

    *rect(1,  15, 2, 2),
    *rect(10, 15, 2, 2),
]


# ════════════════════════════════════════════════════════════════
# TABLE DE ROUTAGE  ← MODIFIE ICI POUR AJOUTER UNE MAP
# ════════════════════════════════════════════════════════════════
#
# Format : (chapter_idx, mission_idx) → liste de cases bloquées
# chapter_idx et mission_idx sont ceux de histoire.py (commencent à 0 et 1)
#
# chapter 1 = "La Bataille de Trost"
#   mission 0 = "Tenir le Fort"
#   mission 1 = "La Contre-Attaque"
#   mission 2 = "Le Titan de Trost"

MISSION_MAPS = {
    None:   MAP_DEFAULT,   # Parties rapides / hors histoire

    (1, 0): MAP_CH1_M1,    # Ch1 Mission 1
    (1, 1): MAP_CH1_M2,    # Ch1 Mission 2
    (1, 2): MAP_CH1_M3,    # Ch1 Mission 3
}


# ════════════════════════════════════════════════════════════════
# MOTEUR D'APPLICATION — ne pas modifier
# ════════════════════════════════════════════════════════════════

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
    """Applique une liste de cases bloquées sur la grille."""
    skipped = 0
    for (x, y) in walls_list:
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

    total = len(walls_list)
    if skipped:
        print(f"[walls{label}] {skipped}/{total} case(s) ignorée(s).")
    else:
        print(f"[walls{label}] {total} cases appliquées.")


def apply_map_walls(grid, chapter=None, mission=None):
    """
    Applique la map correspondant à (chapter, mission).
    Si aucune map spécifique n'existe, utilise MAP_DEFAULT.

    Appelé depuis game.py :
        apply_map_walls(grid)                    # partie rapide
        apply_map_walls(grid, chapter=1, mission=0)  # mode histoire
    """
    key = (chapter, mission) if chapter is not None else None
    walls_list = MISSION_MAPS.get(key, MISSION_MAPS.get(None, []))

    if key is not None and key not in MISSION_MAPS:
        print(f"[walls] Pas de map pour {key}, utilisation de la map par défaut.")

    label = f" Ch{chapter}-M{mission+1}" if chapter is not None else " (défaut)"
    _apply_walls_list(grid, walls_list, label)


# Alias de compatibilité
def spawn_random_walls(grid, *args, **kwargs):
    """Alias conservé pour compatibilité — appelle apply_map_walls."""
    apply_map_walls(grid)