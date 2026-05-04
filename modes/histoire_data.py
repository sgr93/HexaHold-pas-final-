"""
histoire_data.py
----------------
Palette, CHAPTERS, MAP_LABELS - donnees du mode histoire.
"""


# ─────────────────────────────────────────────────────────────────
# PALETTE
# ─────────────────────────────────────────────────────────────────
C_BG         = (13,  10,   6)
C_BG2        = (22,  17,   8)
C_WALL       = (60,  48,  20)
C_WALL_LT    = (100, 80,  30)
C_GOLD       = (138, 106, 30)
C_GOLD2      = (196, 154, 46)
C_GOLD3      = (232, 196, 80)
C_PARCHMENT  = (232, 223, 200)
C_PARCHMENT2 = (180, 168, 140)
C_RED        = (139, 26,  26)
C_RED2       = (196, 40,  40)
C_GREEN_D    = (30,  74,  30)
C_GREEN_L    = (58, 138,  58)
C_BROWN_D    = (58,  30,  14)
C_BROWN_L    = (138, 90,  46)
C_PURPLE_D   = (26,  10,  46)
C_PURPLE_L   = (74,  26, 142)
C_LOCKED     = (42,  32,  14)
C_LOCKED_B   = (70,  54,  22)
C_OVERLAY    = (0,    0,   0, 180)
C_PANEL      = (18,  14,   8)
C_PANEL_B    = (196, 154, 46)
C_TEXT       = (232, 223, 200)
C_MUTED      = (160, 148, 118)
C_STAR_ON    = (196, 154, 46)
C_STAR_OFF   = (60,  50,  22)
C_NOTIF_BG   = (18,  14,   8)
C_NOTIF_B    = (196, 154, 46)

# ─────────────────────────────────────────────────────────────────
# DONNÉES DES CHAPITRES
# ─────────────────────────────────────────────────────────────────
# cx, cy : position en % de la surface de carte (0..1)
CHAPTERS = {
    0: {
        "label":      "Ouverture",
        "title":      "Chute du Mur Maria",
        "cx": 0.500, "cy": 0.862,
        "type":       "cinematique",
        "color_out":  C_RED,
        "color_in":   C_RED2,
        "unlock_next": 1,
        "cinematic": [
            "TEXTE DE CINEMATIQUE",
            "L'humanité vit depuis cent ans en paix derrière trois immenses murs...",
            "Wall Maria. Wall Rose. Wall Sheena.",
            "Ce jour-là, tout a changé.",
            "Un titan colossal est apparu au-delà de Wall Maria.",
            "Et le mur... a cédé.",
        ],
    },
    1: {
        "label":      "Chapitre 1",
        "title":      "La Bataille de Trost",
        "cx": 0.500, "cy": 0.670,
        "color_out":  C_GREEN_D,
        "color_in":   C_GREEN_L,
        "unlock_next": 2,
        "missions": [
            {
                "name": "Tenir le Fort",
                "locked": False,
                "objectives": [
                    {"text": "Survivre à 3 vagues d'ennemis", "done": False},
                    {"text": "Ne pas perdre plus de 20 PV",   "done": False},
                    {"text": "Placer 3 tours avant la vague 2","done": False},
                ],
            },
            {
                "name": "La Contre-Attaque",
                "locked": True,
                "objectives": [
                    {"text": "Éliminer 30 ennemis",                 "done": False},
                    {"text": "Terminer en moins de 5 minutes",       "done": False},
                    {"text": "Utiliser uniquement des petites tours","done": False},
                ],
            },
            {
                "name": "Le Titan de Trost",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss sans perdre de PV",       "done": False},
                    {"text": "Atteindre la difficulté Difficile",        "done": False},
                    {"text": "Placer 5 types de tours différents",       "done": False},
                ],
            },
        ],
    },
    2: {
        "label":      "Chapitre 2",
        "title":      "La Forêt des Titans",
        "cx": 0.746, "cy": 0.682,
        "color_out":  (30, 58, 14),
        "color_in":   (58, 122, 30),
        "unlock_next": 3,
        "missions": [
            {
                "name": "Dans les Ombres",
                "locked": False,
                "objectives": [
                    {"text": "Survivre 5 vagues en forêt",         "done": False},
                    {"text": "Ne pas dépasser 3 tours détruites",  "done": False},
                    {"text": "Tuer 50 ennemis",                    "done": False},
                ],
            },
            {
                "name": "Embuscade",
                "locked": True,
                "objectives": [
                    {"text": "Défendre sans tours de type sniper",        "done": False},
                    {"text": "Survivre à un assaut nocturne (×1.5)",      "done": False},
                    {"text": "Tuer le mini-boss en 30 secondes",          "done": False},
                ],
            },
            {
                "name": "Le Titan Féminin",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss en Difficile",              "done": False},
                    {"text": "Ne jamais perdre plus de 50% PV",           "done": False},
                    {"text": "3 étoiles sur la mission précédente",       "done": False},
                ],
            },
        ],
    },
    3: {
        "label":      "Chapitre 3",
        "title":      "Siège du Château Utgard",
        "cx": 0.304, "cy": 0.642,
        "color_out":  C_BROWN_D,
        "color_in":   C_BROWN_L,
        "unlock_next": 4,
        "missions": [
            {
                "name": "Nuit Sans Lune",
                "locked": False,
                "objectives": [
                    {"text": "Survivre jusqu'à l'aube (8 vagues)",      "done": False},
                    {"text": "Protéger 3 survivants alliés",             "done": False},
                    {"text": "Ne pas utiliser de murs supplémentaires",  "done": False},
                ],
            },
            {
                "name": "Assaut des Titans 14m",
                "locked": True,
                "objectives": [
                    {"text": "Affronter des titans classe 14m",          "done": False},
                    {"text": "Garder le château à 50% d'intégrité",     "done": False},
                    {"text": "Terminer avec 5 tours actives",            "done": False},
                ],
            },
            {
                "name": "Dernier Rempart",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss en Très Difficile",       "done": False},
                    {"text": "Aucun ennemi ne franchit le seuil",       "done": False},
                    {"text": "Finir avec tous ses PV",                  "done": False},
                ],
            },
        ],
    },
    4: {
        "label":      "Chapitre 4",
        "title":      "La Chute de Shiganshina",
        "cx": 0.740, "cy": 0.490,
        "color_out":  C_PURPLE_D,
        "color_in":   C_PURPLE_L,
        "unlock_next": 5,
        "missions": [
            {
                "name": "Retour aux Ruines",
                "locked": False,
                "objectives": [
                    {"text": "Survivre à 6 vagues",                  "done": False},
                    {"text": "Éliminer 80 ennemis",                  "done": False},
                    {"text": "Ne pas perdre plus de 40 PV",          "done": False},
                ],
            },
            {
                "name": "Défense du District",
                "locked": True,
                "objectives": [
                    {"text": "Utiliser 5 types de tours différents","done": False},
                    {"text": "Terminer avec 200+ pièces restantes", "done": False},
                    {"text": "Tuer le mini-boss en 45 secondes",    "done": False},
                ],
            },
            {
                "name": "Le Titan Blindé",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss en Cauchemar",          "done": False},
                    {"text": "Ne jamais perdre plus de 25% PV",       "done": False},
                    {"text": "3 étoiles sur les 2 missions précédentes","done": False},
                ],
            },
        ],
    },
    5: {
        "label":      "Chapitre 5",
        "title":      "L'Assaut Final",
        "cx": 0.500, "cy": 0.906,
        "color_out":  (46, 10, 10),
        "color_in":   (142, 26, 26),
        "missions": [
            {
                "name": "Aux Portes de l'Enfer",
                "locked": False,
                "objectives": [
                    {"text": "Survivre à 7 vagues sans perdre de PV","done": False},
                    {"text": "Tuer 120 ennemis",                      "done": False},
                    {"text": "Ne construire que des tours niveau 3",  "done": False},
                ],
            },
            {
                "name": "L'Armée des Titans",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre 3 mini-boss lors d'une même partie","done": False},
                    {"text": "Ne jamais perdre plus de 10% PV",            "done": False},
                    {"text": "Terminer en moins de 8 minutes",              "done": False},
                ],
            },
            {
                "name": "Le Titan Colossal",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le Titan Colossal",                    "done": False},
                    {"text": "Aucun ennemi ne franchit le seuil",            "done": False},
                    {"text": "Finir avec toutes ses étoiles dans ch4",       "done": False},
                ],
            },
        ],
    },
}

# Labels de la carte (texte, cx%, cy%, taille, couleur, gras)
MAP_LABELS = [
    ("TERITOIRE TITAN",    0.50, 0.04, 11, C_GOLD2,     True),
    ("MUR  MARIA",         0.50, 0.09, 11, C_GOLD2,     True),
    ("MUR ROSE",          0.50, 0.225,11, C_GOLD2,     True),
    ("MUR SINA",        0.50, 0.335,11, C_GOLD2,     True),
    ("Teritoire Humain",    0.50, 0.365, 9, C_GOLD,      False),
    ("Mitras",      0.50, 0.508, 9, C_PARCHMENT, False),
    ("District Utopia",    0.50, 0.200, 9, C_PARCHMENT, False),
    ("District d’Orvud",     0.50, 0.268, 9, C_PARCHMENT, False),
    ("District de Yarckel",   0.28, 0.438, 9, C_PARCHMENT, False),
    ("District de Stohess",   0.72, 0.438, 9, C_PARCHMENT, False),
    ("District de Krolva",    0.10, 0.500, 9, C_PARCHMENT, False),
    ("District de Karanes",   0.90, 0.500, 9, C_PARCHMENT, False),
    ("District d’Ehrmich",   0.50, 0.605, 9, C_PARCHMENT, False),
    ("Village de Dauper",     0.32, 0.628, 8, C_PARCHMENT2,False),
    ("Village de Ragako",     0.37, 0.708, 8, C_PARCHMENT2,False),
    ("Château d’Utgard",      0.27, 0.672, 8, C_PARCHMENT2,False),
    ("District de Trost",     0.50, 0.735, 9, C_PARCHMENT, False),
    ("Forêt des Titans",       0.78, 0.678, 8, C_PARCHMENT2,False),
    ("District de Shiganshina",0.50, 0.874, 9, C_PARCHMENT, False),
]


def is_mission_unlocked(save, chapter_idx, mission_idx):
    """La mission 0 de chaque chapitre est toujours accessible si le chapitre est debloque."""
    if mission_idx == 0:
        return chapter_idx in save.get("histoire_unlocked", [0])
    key = f"ch{chapter_idx}_m{mission_idx}_unlocked"
    return save.get(key, False)


def get_mission_best_stars(save, chapter_idx, mission_idx):
    key = f"ch{chapter_idx}_m{mission_idx}_stars"
    return save.get(key, 0)
