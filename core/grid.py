"""
grid.py

Tout ce qui concerne la grille de jeu — cases bloquées, chemins, directions.
"""

import heapq
import math
from core.config import COLS, ROWS, GRID_SIZE, END
from core.entities import Tower


class Grid:
    """
    La grille sur laquelle les tours sont posées et les ennemis se déplacent.
    Plutôt que de calculer un chemin par ennemi, on précalcule une direction
    par case et les ennemis la lisent directement — beaucoup plus léger.
    """

    def __init__(self, towers_ref, danger_weight=3):
        self.towers_ref    = towers_ref
        self.danger_weight = danger_weight

        # True = case libre, False = bloquée par une tour
        self.walkable = [[True for _ in range(ROWS)] for _ in range(COLS)]

        # distance de chaque case jusqu'à la base, inf si inaccessible
        self.integration_field = [
            [float("inf") for _ in range(ROWS)] for _ in range(COLS)
        ]

        # direction à suivre depuis chaque case pour aller vers la base
        # on peut en avoir plusieurs si deux chemins sont aussi courts
        self.flow_field = [
            [[(0,0)] for _ in range(ROWS)] for _ in range(COLS)
        ]

        # danger cumulé des tours sur chaque case — pas utilisé activement
        # pour le déplacement pour l'instant mais gardé au cas où
        self.danger_field = [[0 for _ in range(ROWS)] for _ in range(COLS)]

        # permet aux ennemis de savoir si le chemin a changé depuis leur dernier calcul
        self.version    = 0
        self.wall_cells = set()

    def in_bounds(self, x, y):
        return 0 <= x < COLS and 0 <= y < ROWS

    def dangerous(self, x, y):
        return bool(self.danger_field[x][y])

    def neighbors(self, x, y):
        # pas de diagonales — sinon les ennemis passent entre deux tours
        # placées en coin et ça fait bizarre visuellement
        result = []
        for dx,dy in ((0,1),(1,0),(0,-1),(-1,0)):
            nx,ny = x+dx, y+dy
            if self.in_bounds(nx,ny) and self.walkable[nx][ny]:
                result.append((nx,ny))
        return result

    def update_danger_field(self):
        """
        Calcule pour chaque case à quel point elle est exposée aux tirs des tours.
        On n'inclut pas les pièges ici — si on le faisait les ennemis les contourneraient
        automatiquement et les mines ne serviraient plus à rien sur les chemins principaux.
        """
        for x in range(COLS):
            for y in range(ROWS):
                self.danger_field[x][y] = 0

        for item in self.towers_ref:
            if not isinstance(item, Tower):
                continue

            tower_x        = item.x / GRID_SIZE
            tower_y        = item.y / GRID_SIZE
            range_cells    = item.range / GRID_SIZE
            range_cells_sq = range_cells*range_cells

            # on itère seulement dans le carré autour de la tour, pas toute la grille
            x_min = max(0,      int(tower_x - range_cells))
            x_max = min(COLS-1, int(tower_x + range_cells)+1)
            y_min = max(0,      int(tower_y - range_cells))
            y_max = min(ROWS-1, int(tower_y + range_cells)+1)

            for x in range(x_min, x_max+1):
                for y in range(y_min, y_max+1):
                    dist_sq = (x-tower_x)**2 + (y-tower_y)**2
                    if dist_sq <= range_cells_sq:
                        dist   = math.sqrt(dist_sq)
                        weight = max(int((range_cells-dist)*2), 1)
                        self.danger_field[x][y] += weight

    def compute_integration_field(self):
        """
        Dijkstra depuis la base pour donner à chaque case son coût pour y arriver.
        Si le joueur bouche complètement un passage les cases derrière restent à inf
        et les ennemis qui spawneraient là seraient bloqués.
        """
        for x in range(COLS):
            for y in range(ROWS):
                self.integration_field[x][y] = float("inf")

        ex,ey = END
        self.integration_field[ex][ey] = 0
        open_list = [(0, ex,ey)]

        while open_list:
            cost,x,y = heapq.heappop(open_list)
            for nx,ny in self.neighbors(x,y):
                # coût uniforme pour l'instant — si on voulait que les ennemis
                # évitent les tours il suffirait d'ajouter le danger ici
                new_cost = cost + 1
                if new_cost < self.integration_field[nx][ny]:
                    self.integration_field[nx][ny] = new_cost
                    heapq.heappush(open_list, (new_cost,nx,ny))

    def compute_flow_field(self):
        """
        Construit les directions à partir des coûts calculés par Dijkstra.
        On garde les ex aequo pour que les ennemis se répartissent sur plusieurs
        cases plutôt que de tous s'entasser sur le même pixel dans les couloirs longs.
        """
        for x in range(COLS):
            for y in range(ROWS):
                min_cost   = self.integration_field[x][y]
                actual_min = float("inf")

                for nx,ny in self.neighbors(x,y):
                    if self.integration_field[nx][ny] < actual_min:
                        actual_min = self.integration_field[nx][ny]

                if actual_min < min_cost:
                    best_dirs = [
                        (nx-x, ny-y)
                        for nx,ny in self.neighbors(x,y)
                        if self.integration_field[nx][ny] == actual_min
                    ]
                else:
                    best_dirs = [(0,0)]

                self.flow_field[x][y] = best_dirs

    def recompute(self):
        """
        À appeler dès qu'une tour est posée ou retirée.
        Les ennemis déjà sur la map verront le changement de version
        et mettront à jour leur direction au prochain update.
        """
        self.compute_integration_field()
        self.compute_flow_field()
        self.version += 1