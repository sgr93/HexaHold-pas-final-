"""
config.py
---------
Centralise toutes les constantes et paramètres globaux du jeu.

"""

# ----------------------------
# CONFIGURATION DE LA GRILLE
# ----------------------------

ROWS = 18                       # Nombre de lignes du terrain
COLS = 14                       # Nombre de colonnes du terrain
GRID_SIZE = 32                  # Taille d'une case en pixels

GRID_WIDTH  = COLS * GRID_SIZE  # Largeur totale de la grille en pixels
GRID_HEIGHT = ROWS * GRID_SIZE  # Hauteur totale de la grille en pixels
INTERFACE_WIDTH = 200           # Largeur de la zone d'interface (à droite)

# Zone de spawn (en pixels) — les ennemis apparaissent au-dessus de la grille
SPAWN_ZONE_X      = 0
SPAWN_ZONE_Y      = -(GRID_SIZE * 2)   # Au-dessus de la grille (valeur négative)
SPAWN_ZONE_WIDTH  = GRID_WIDTH
SPAWN_ZONE_HEIGHT = GRID_SIZE * 2      # Hauteur = 2 cases

# Points de départ (entrée ennemis) et d'arrivée (base à défendre)
START = (COLS // 2, 0)          # Case centrale en haut
END   = (COLS // 2, ROWS - 1)   # Case centrale en bas

# ----------------------------
# COULEURS
# ----------------------------

BACKGROUND_COLOR = (30, 30, 40)  # Fond sombre

# ----------------------------
# PROGRESSION DU JOUEUR
# ----------------------------

LEVEL_START            = 1
XP_START               = 0
XP_TO_NEXT_LVL_START   = 14
XP_GROWTH_FACTOR       = 1.5
AVAILABLE_TOWERS_INIT  = ["small", "big", "trap"]

# AMÉLIO-1 : le joueur a maintenant des points de vie
PLAYER_HP       = 100           # HP de départ du joueur
PLAYER_HP_REGEN = 0             # Régénération par seconde (0 = désactivé par défaut)

# ----------------------------
# VAGUES D'ENNEMIS
# ----------------------------

WAVE_NUMBER_START        = 1
MAX_WAVES                = 4
WAVE_DURATION            = 30   # Durée max d'une vague normale (secondes)
BOSS_DURATION            = 40   # Durée max d'apparition d'un boss (secondes)
ENEMY_SPAWN_INTERVAL_BASE = 0.8 # Intervalle entre spawns normaux (secondes)

# ----------------------------
# PATHFINDING
# ----------------------------

DANGER_WEIGHT = 3  # Coût additionnel d'une case dans la portée d'une tour

# ----------------------------
# MURS ALÉATOIRES
# ----------------------------

WALLS_ENABLED    = True
WALLS_COUNT      = 4
WALLS_ZONE_START = (2, 4)
WALLS_ZONE_END   = (COLS - 1, ROWS - 6)

# ----------------------------
# CONTRÔLES
# ----------------------------

# AMÉLIO-2 : touche de pause configurable depuis config.py
import pygame
PAUSE_KEY = pygame.K_p   # Touche Espace ou P pour mettre en pause

# ----------------------------
# FENÊTRE
# ----------------------------

DISPLAY_FLAGS   = pygame.RESIZABLE
WINDOW_CAPTION  = "Hexahold"
