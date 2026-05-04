"""
grid.py
-------
Gère la grille du jeu :
- Cases marchables / bloquées
- Champ d'intégration (distance minimale vers la base, pondérée par le danger)
- Flow Field (direction optimale par case)
- Champ de danger (portées de tours cumulées)

"""

import heapq
import math
from core.config import COLS, ROWS, GRID_SIZE, END
from core.entities import Tower


class Grid:
    """
    Représente la grille du jeu.

    Fournit :
    - `walkable[x][y]`         : True si la case est praticable
    - `integration_field[x][y]`: coût minimal (distance + danger) vers la base
    - `flow_field[x][y]`       : liste des directions optimales à suivre
    - `danger_field[x][y]`     : danger cumulé des tours (UNIQUEMENT les tours)
    - `recompute()`            : recalcul complet après un changement de la grille
    """

    def __init__(self, towers_ref, danger_weight=3):
        self.towers_ref    = towers_ref
        self.danger_weight = danger_weight

        # Tableau 2D : True = case libre, False = case bloquée (tour ou mur)
        self.walkable = [[True for _ in range(ROWS)] for _ in range(COLS)]

        # Distance minimale (pondérée) vers la base pour chaque case
        self.integration_field = [
            [float("inf") for _ in range(ROWS)] for _ in range(COLS)
        ]

        # Direction(s) optimale(s) à suivre depuis chaque case
        self.flow_field = [
            [[(0, 0)] for _ in range(ROWS)] for _ in range(COLS)
        ]

        # Poids de danger par case (contribué par les tours uniquement)
        self.danger_field = [[0 for _ in range(ROWS)] for _ in range(COLS)]
        self.version = 0
        self.wall_cells = set()

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def in_bounds(self, x, y):
        """Retourne True si (x, y) est dans les limites de la grille."""
        return 0 <= x < COLS and 0 <= y < ROWS

    def dangerous(self, x, y):
        """Retourne True si la case est dans la portée d'au moins une tour."""
        return bool(self.danger_field[x][y])

    def neighbors(self, x, y):
        """Retourne les cases voisines accessibles (haut/bas/gauche/droite)."""
        result = []
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and self.walkable[nx][ny]:
                result.append((nx, ny))
        return result

    # ------------------------------------------------------------------
    # Champ de danger
    # ------------------------------------------------------------------

    def update_danger_field(self):
        """
        Marque les cases dans la portée des tours avec un poids de danger cumulatif.
        Plus une case est proche d'une tour, plus son poids est élevé.

        FIX-GRID-1 : les pièges (Trap) ne contribuent PLUS à ce champ.
            Avant ce correctif, chaque case d'un piège recevait +5 de danger,
            ce qui faisait calculer à Dijkstra un chemin les contournant.
            Les ennemis "esquivaient" donc les pièges.
            Seules les tours (Tower) génèrent du danger — elles tirent des
            projectiles, il est donc logique que les ennemis tentent de les éviter.

        OPTIM-7 (conservé) : itération dans le carré englobant uniquement,
            comparaison de carrés de distances pour éviter math.sqrt.
        """
        # Remise à zéro
        for x in range(COLS):
            for y in range(ROWS):
                self.danger_field[x][y] = 0

        for item in self.towers_ref:
            # FIX-GRID-1 : isinstance(item, Tower) UNIQUEMENT — Trap exclu
            if not isinstance(item, Tower):
                continue

            tower_x       = item.x / GRID_SIZE
            tower_y       = item.y / GRID_SIZE
            range_cells   = item.range / GRID_SIZE
            range_cells_sq = range_cells * range_cells

            # OPTIM-7 : bornes du carré englobant (clampées à la grille)
            x_min = max(0, int(tower_x - range_cells))
            x_max = min(COLS - 1, int(tower_x + range_cells) + 1)
            y_min = max(0, int(tower_y - range_cells))
            y_max = min(ROWS - 1, int(tower_y + range_cells) + 1)

            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    dist_sq = (x - tower_x) ** 2 + (y - tower_y) ** 2
                    if dist_sq <= range_cells_sq:
                        dist   = math.sqrt(dist_sq)  # sqrt uniquement si dans portée
                        weight = max(int((range_cells - dist) * 2), 1)
                        self.danger_field[x][y] += weight

    # ------------------------------------------------------------------
    # Champ d'intégration (Dijkstra)
    # ------------------------------------------------------------------

    def compute_integration_field(self):
        """
        Calcule la distance minimale vers la base (END) pour chaque case.
        Algorithme de Dijkstra — coût = 1 (pas de pondération danger).
        Les ennemis prennent le chemin le plus court sans esquiver les portées de tours.
        """
        for x in range(COLS):
            for y in range(ROWS):
                self.integration_field[x][y] = float("inf")

        ex, ey = END
        self.integration_field[ex][ey] = 0
        open_list = [(0, ex, ey)]

        while open_list:
            cost, x, y = heapq.heappop(open_list)
            for nx, ny in self.neighbors(x, y):
                new_cost = cost + 1  # coût uniforme — plus d'esquive des portées
                if new_cost < self.integration_field[nx][ny]:
                    self.integration_field[nx][ny] = new_cost
                    heapq.heappush(open_list, (new_cost, nx, ny))

    # ------------------------------------------------------------------
    # Flow field
    # ------------------------------------------------------------------

    def compute_flow_field(self):
        """
        Calcule la direction optimale à suivre depuis chaque case.
        Chaque case pointe vers le(s) voisin(s) ayant le coût d'intégration minimal.
        """
        for x in range(COLS):
            for y in range(ROWS):
                min_cost   = self.integration_field[x][y]
                actual_min = float("inf")

                for nx, ny in self.neighbors(x, y):
                    if self.integration_field[nx][ny] < actual_min:
                        actual_min = self.integration_field[nx][ny]

                if actual_min < min_cost:
                    best_dirs = [
                        (nx - x, ny - y)
                        for nx, ny in self.neighbors(x, y)
                        if self.integration_field[nx][ny] == actual_min
                    ]
                else:
                    best_dirs = [(0, 0)]

                self.flow_field[x][y] = best_dirs

    # ------------------------------------------------------------------
    # Recalcul complet
    # ------------------------------------------------------------------

    def recompute(self):
        """
        Recalcul complet : intégration → flow field.
        Le danger_field est désactivé — les ennemis prennent le chemin
        le plus court sans esquiver les portées de tours.
        """
        self.compute_integration_field()
        self.compute_flow_field()
        self.version += 1