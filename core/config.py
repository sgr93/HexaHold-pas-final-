"""
config.py

Regroupe toutes les constantes et paramètres globaux du jeu 
"""
import pygame

# CONFIGURATION DE LA GRILLE
ROWS = 18
COLS = 20
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


# COULEURS
BACKGROUND_COLOR = (30, 30, 40)

# PROGRESSION DU JOUEUR
LEVEL_START            = 1
XP_START               = 0
XP_TO_NEXT_LVL_START   = 30
XP_GROWTH_FACTOR       = 2.0
XP_REWARD_NORMAL       = 5   # XP gagnée par un ennemi normal
XP_REWARD_BOSS         = 15   # XP gagnée par un boss
AVAILABLE_TOWERS_INIT  = ["small", "big", "trap"]
TOWER_SLOT_COUNT       = 3
ALL_TOWER_TYPES = [
    "small", "big", "sniper", "mortar", "frost", "tesla", "cannon", "laser", "trap", "mine"
]

MUSIC_PATH = "assets/music"
MUSIC_TRACK_TITLE = "TitleScreen.mp3"
MUSIC_TRACK_MENU = "Menu.mp3"
MUSIC_TRACK_GAME = "Game.mp3"

PLAYER_HP = 100
PLAYER_HP_REGEN = 0.5   # HP récupérés par seconde


# VAGUES D'ENNEMIS
WAVE_NUMBER_START        = 1
WAVE_DURATION            = 35
BOSS_DURATION            = 50

# PATHFINDING
DANGER_WEIGHT = 3


# MURS
WALLS_ENABLED    = True
WALLS_COUNT      = 4
WALLS_ZONE_START = (2, 4)
WALLS_ZONE_END   = (COLS - 1, ROWS - 6)


# CONTRÔLES
PAUSE_KEY = pygame.K_p

# FENÊTRE
DISPLAY_FLAGS   = pygame.RESIZABLE
WINDOW_CAPTION  = "Hexahold"


# NIVEAUX DE DIFFICULTÉ (partie rapide)
DIFFICULTY_LEVELS = {
    1: {"name": "Facile",         "waves": 3,  "enemy_hp_mult": 1.0,  "spawn_interval": 1.0, "coins_reward": 50 },
    2: {"name": "Normal",         "waves": 4,  "enemy_hp_mult": 1.5,  "spawn_interval": 0.7, "coins_reward": 100},
    3: {"name": "Difficile",      "waves": 5,  "enemy_hp_mult": 2.0,  "spawn_interval": 0.55,"coins_reward": 170},
    4: {"name": "Très Difficile", "waves": 6,  "enemy_hp_mult": 2.8,  "spawn_interval": 0.4, "coins_reward": 260},
    5: {"name": "Cauchemar",      "waves": 7,  "enemy_hp_mult": 3.8,  "spawn_interval": 0.28,"coins_reward": 400},
}

# Multiplicateurs d'XP de compte par difficulté (partie rapide)
XP_MULTS = {1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 5.0}


# EQUILIBRAGE TOURS
TOWER_MAX_LEVEL       = 3
TOWER_DAMAGE_MULT     = 1.35
TOWER_COOLDOWN_MULT   = 0.9
TOWER_RANGE_MULT      = 1.15

TRAP_DAMAGE_MULT      = 1.35
TRAP_COOLDOWN_MULT    = 0.7


# GACHA / ÉQUIPEMENTS
CHEST_COSTS = {
    "wood":   30,
    "silver": 80,
    "gold":   200,
    "gem_common": 5,
    "gem_epic": 15,
    "gem_legendary": 50,
}

RARITIES = ["Commun", "Rare", "Épique", "Légendaire", "Mythique"]
RARITY_COLORS = {
    "Commun":    (180, 180, 180),
    "Rare":      (60,  120, 255),
    "Épique":    (160, 60,  255),
    "Légendaire":(255, 180, 0  ),
    "Mythique":  (255, 0,   255),
}
RARITY_WEIGHTS = {
    "wood":   [70, 20, 8,   1,  1  ],  # Diminue les chances rares/épiques/légendaires
    "silver": [45, 35, 15,  4,  1  ],
    "gold":   [20, 25, 30,  20, 5  ],
    "gem_common": [5, 15, 30, 35, 15],    # Coffre commun en gemmes : beaucoup de rares
    "gem_epic": [2, 8, 30, 40, 20],      # Coffre épique en gemmes : beaucoup de légendaires
    "gem_legendary": [0, 3, 15, 32, 50], # Coffre légendaire en gemmes : 50% mythique!
}

EQUIPMENT_SLOTS = ["cape", "veste", "bottes", "arme"]

EQUIPMENT_STATS = {
    "cape":   {"stat": "max_hp",       "label": "Vie max",         "values": {"Commun": 10, "Rare": 20, "Épique": 35, "Légendaire": 60, "Mythique": 100}},
    "veste":   {"stat": "attack_speed", "label": "Vitesse attaque", "values": {"Commun": 3,  "Rare": 6,  "Épique": 10, "Légendaire": 18, "Mythique": 30}},
    "bottes": {"stat": "speed",        "label": "Vitesse",         "values": {"Commun": 0.3,"Rare": 0.6,"Épique": 1.0,"Légendaire": 1.8,"Mythique": 3.0}},
    "arme":     {"stat": "damage",       "label": "Puissance att.",  "values": {"Commun": 3,  "Rare": 6,  "Épique": 11, "Légendaire": 20, "Mythique": 35}},
    "tour":     {"stat": "tower_bonus",  "label": "Bonus tour",      "values": {"Commun": 5,  "Rare": 12, "Épique": 22, "Légendaire": 40, "Mythique": 70}},
}
INV_BAR_HEIGHT = 90
