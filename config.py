"""
config.py
---------
Centralise toutes les constantes et paramètres globaux du jeu.
"""

# ----------------------------
# CONFIGURATION DE LA GRILLE
# ----------------------------

ROWS = 18
COLS = 14
GRID_SIZE = 32

GRID_WIDTH  = COLS * GRID_SIZE
GRID_HEIGHT = ROWS * GRID_SIZE
INTERFACE_WIDTH = 200

SPAWN_ZONE_X      = 0
SPAWN_ZONE_Y      = -(GRID_SIZE * 2)
SPAWN_ZONE_WIDTH  = GRID_WIDTH
SPAWN_ZONE_HEIGHT = GRID_SIZE * 2

START = (COLS // 2, 0)
END   = (COLS // 2, ROWS - 1)

# ----------------------------
# COULEURS
# ----------------------------

BACKGROUND_COLOR = (30, 30, 40)

# ----------------------------
# PROGRESSION DU JOUEUR
# ----------------------------

LEVEL_START            = 1
XP_START               = 0
XP_TO_NEXT_LVL_START   = 30
XP_GROWTH_FACTOR       = 2.0
XP_REWARD_NORMAL       = 1   # XP gagnée par un ennemi normal
XP_REWARD_BOSS         = 2   # XP gagnée par un boss (y compris boss final)
AVAILABLE_TOWERS_INIT  = ["small", "big", "trap"]
TOWER_SLOT_COUNT       = 3
ALL_TOWER_TYPES = [
    "small", "big", "trap", "sniper", "mortar", "frost", "poison", "beam", "tesla", "rocket",
    "storm", "arcane", "crystal", "swarm", "burst"
]

MUSIC_PATH = "assets/music"
MUSIC_TRACK_TITLE = "TitleScreen.mp3"
MUSIC_TRACK_MENU = "Menu.mp3"
MUSIC_TRACK_GAME = "Game.mp3"

PLAYER_HP       = 100
PLAYER_HP_REGEN = 0.5   # HP récupérés par seconde

# ----------------------------
# VAGUES D'ENNEMIS
# ----------------------------

WAVE_NUMBER_START        = 1
MAX_WAVES                = 4
WAVE_DURATION            = 30
BOSS_DURATION            = 40
ENEMY_SPAWN_INTERVAL_BASE = 0.8

# ----------------------------
# PATHFINDING
# ----------------------------

DANGER_WEIGHT = 3

# ----------------------------
# MURS
# ----------------------------

WALLS_ENABLED    = True
WALLS_COUNT      = 4
WALLS_ZONE_START = (2, 4)
WALLS_ZONE_END   = (COLS - 1, ROWS - 6)

# ----------------------------
# CONTRÔLES
# ----------------------------

import pygame
PAUSE_KEY = pygame.K_p

# ----------------------------
# FENÊTRE
# ----------------------------

DISPLAY_FLAGS   = pygame.RESIZABLE
WINDOW_CAPTION  = "Hexahold"

# ----------------------------
# NIVEAUX DE DIFFICULTÉ
# ----------------------------

DIFFICULTY_LEVELS = {
    1: {"name": "Facile",         "waves": 2,  "enemy_hp_mult": 0.7,  "spawn_interval": 1.2, "coins_reward": 50 },
    2: {"name": "Normal",         "waves": 3,  "enemy_hp_mult": 1.0,  "spawn_interval": 0.8, "coins_reward": 100},
    3: {"name": "Difficile",      "waves": 4,  "enemy_hp_mult": 1.4,  "spawn_interval": 0.6, "coins_reward": 170},
    4: {"name": "Très Difficile", "waves": 5,  "enemy_hp_mult": 1.9,  "spawn_interval": 0.4, "coins_reward": 260},
    5: {"name": "Cauchemar",      "waves": 6,  "enemy_hp_mult": 2.5,  "spawn_interval": 0.3, "coins_reward": 400},
}

# ----------------------------
# NERF TOURS (équilibrage)
# ----------------------------
TOWER_MAX_LEVEL       = 2     # auparavant 3
TOWER_DAMAGE_MULT     = 0.65
TOWER_COOLDOWN_MULT   = 1.30
TOWER_RANGE_MULT      = 0.90

TRAP_DAMAGE_MULT      = 0.75
TRAP_COOLDOWN_MULT    = 1.20

# ----------------------------
# GACHA / ÉQUIPEMENTS
# ----------------------------

CHEST_COSTS = {
    "wood":   30,
    "silver": 80,
    "gold":   200,
}

RARITIES = ["Commun", "Rare", "Épique", "Légendaire"]
RARITY_COLORS = {
    "Commun":    (180, 180, 180),
    "Rare":      (60,  120, 255),
    "Épique":    (160, 60,  255),
    "Légendaire":(255, 180, 0  ),
}
RARITY_WEIGHTS = {
    "wood":   [60, 30, 9,  1 ],
    "silver": [30, 40, 22, 8 ],
    "gold":   [10, 25, 40, 25],
}

EQUIPMENT_SLOTS = ["casque", "armure", "pantalon", "arme", "tour"]

EQUIPMENT_STATS = {
    "casque":   {"stat": "max_hp",       "label": "Vie max",         "values": {"Commun": 10, "Rare": 20, "Épique": 35, "Légendaire": 60}},
    "armure":   {"stat": "attack_speed", "label": "Vitesse attaque", "values": {"Commun": 3,  "Rare": 6,  "Épique": 10, "Légendaire": 18}},
    "pantalon": {"stat": "speed",        "label": "Vitesse",         "values": {"Commun": 0.3,"Rare": 0.6,"Épique": 1.0,"Légendaire": 1.8}},
    "arme":     {"stat": "damage",       "label": "Puissance att.",  "values": {"Commun": 3,  "Rare": 6,  "Épique": 11, "Légendaire": 20}},
    "tour":     {"stat": "tower_bonus",  "label": "Bonus tour",      "values": {"Commun": 5,  "Rare": 12, "Épique": 22, "Légendaire": 40}},
}
INV_BAR_HEIGHT = 90
