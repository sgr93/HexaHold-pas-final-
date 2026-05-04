"""
heroes.py
---------
Definit les 5 heros jouables, leurs raretees, passifs et systeme de niveau.

Raretees : Commun / Rare / Legendaire
Montee en niveau (doublons) :
  Commun    : +10% ATK/HP par niveau
  Rare      : +20% ATK/HP par niveau
  Legendaire: +30% ATK/HP par niveau
"""

import os
import theme

# ============================================================
# DEFINITION DES HEROS
# ============================================================

HEROES = {
    "eren": {
        "name":     "Eren Jaeger",
        "rarity":   "Commun",
        "unlocked": True,   # Debloque de base
        "cost_gems": 0,
        "sprite_select":   "eren_select.png",    # PNG pour le selecteur
        "sprite_portrait": "eren_portrait.png",  # PNG pour accueil + equipement
        "sprite_ingame":   "_Eren_Scouting_Legion_2.png",  # Spritesheet RPG Maker
        "passive_name": "Titan des Murs",
        "passive_desc": "Les tours dans un rayon de 8 cases\nauront +20% de degats.",
        "passive_id":   "eren_boost_nearby",
        "color": (213, 90, 48),
    },
    "armin": {
        "name":     "Armin Arlert",
        "rarity":   "Rare",
        "unlocked": False,
        "cost_gems": 30,
        "sprite_select":   "armin_select.png",
        "sprite_portrait": "armin_portrait.png",
        "sprite_ingame":   "_Armin_Scouting_Legion_2.png",
        "passive_name": "Stratege",
        "passive_desc": "Chaque tour construite donne\n+40% d'ATK a toutes les tours.",
        "passive_id":   "armin_build_buff",
        "color": (200, 180, 80),
    },
    "sasha": {
        "name":     "Sasha Blouse",
        "rarity":   "Rare",
        "unlocked": False,
        "cost_gems": 30,
        "sprite_select":   "sasha_select.png",
        "sprite_portrait": "sasha_portrait.png",
        "sprite_ingame":   "_Sasha.png",
        "passive_name": "Instinct de Chasseuse",
        "passive_desc": "Une tour aleatoire supplementaire\nest ajoutee a l'inventaire\nchaque vague.",
        "passive_id":   "sasha_extra_tower",
        "color": (160, 120, 80),
    },
    "levi": {
        "name":     "Levi Ackerman",
        "rarity":   "Legendaire",
        "unlocked": False,
        "cost_gems": 80,
        "sprite_select":   "levi_select.png",
        "sprite_portrait": "levi_portrait.png",
        "sprite_ingame":   "_Rivaille_Without_Cloak.png",
        "passive_name": "Capitaine de l'Humanite",
        "passive_desc": "Ameliorer une tour niveau 1\nla passe directement niveau 3.",
        "passive_id":   "levi_instant_max",
        "color": (160, 200, 220),
    },
    "mikasa": {
        "name":     "Mikasa Ackerman",
        "rarity":   "Legendaire",
        "unlocked": False,
        "cost_gems": 80,
        "sprite_select":   "mikasa_select.png",
        "sprite_portrait": "mikasa_portrait.png",
        "sprite_ingame":   "_Mikasa_Scouting_Legion_2.png",
        "passive_name": "Lame de l'Ackerman",
        "passive_desc": "Inflige des degats continus\na tous les ennemis dans\nun rayon de 120px.",
        "passive_id":   "mikasa_aoe_damage",
        "color": (127, 119, 221),
    },
}

RARITY_ORDER    = ["Commun", "Rare", "Legendaire"]
RARITY_COLORS   = {
    "Commun":     (180, 180, 180),
    "Rare":       (80, 140, 255),
    "Legendaire": (255, 180, 0),
}
RARITY_LVL_BONUS = {
    "Commun":     0.10,
    "Rare":       0.20,
    "Legendaire": 0.30,
}

# Stats de base des heros en jeu (ATK et HP au niveau 1)
HERO_BASE_STATS = {
    "eren":   {"atk":  8, "hp": 180},
    "armin":  {"atk":  6, "hp": 160},
    "sasha":  {"atk":  7, "hp": 150},
    "levi":   {"atk": 10, "hp": 200},
    "mikasa": {"atk":  9, "hp": 190},
}

# Ordre d'affichage dans le selecteur
HERO_ORDER = ["eren", "armin", "sasha", "levi", "mikasa"]


# ============================================================
# FONCTIONS SAVE
# ============================================================

def get_hero_save(save, hero_id):
    """Retourne le dict de save d'un heros (copies / niveau)."""
    heroes_save = save.setdefault("heroes", {})
    if hero_id not in heroes_save:
        heroes_save[hero_id] = {"copies": 0, "level": 1}
        if HEROES[hero_id]["unlocked"]:
            heroes_save[hero_id]["copies"] = 1
    return heroes_save[hero_id]


def init_heroes_save(save):
    """Initialise la save des heros si necessaire."""
    if "heroes" not in save:
        save["heroes"] = {}
    for hid, hdef in HEROES.items():
        if hid not in save["heroes"]:
            save["heroes"][hid] = {
                "copies": 1 if hdef["unlocked"] else 0,
                "level":  1,
            }
    if "selected_hero" not in save:
        save["selected_hero"] = "eren"


def is_hero_unlocked(save, hero_id):
    """Retourne True si le heros est debloque (au moins 1 copie)."""
    init_heroes_save(save)
    return save["heroes"].get(hero_id, {}).get("copies", 0) >= 1


def add_hero_copy(save, hero_id):
    """Ajoute une copie d'un heros (gacha). Monte le niveau si deja possede."""
    init_heroes_save(save)
    h = save["heroes"][hero_id]
    h["copies"] = h.get("copies", 0) + 1
    # Monte de niveau tous les 2 copies supplementaires (1 pour debloquer)
    copies = h["copies"]
    if copies > 1:
        h["level"] = 1 + (copies - 1) // 2
    return h["level"]


def get_hero_level(save, hero_id):
    init_heroes_save(save)
    return save["heroes"].get(hero_id, {}).get("level", 1)


def get_hero_stat_multiplier(save, hero_id):
    """
    Retourne le multiplicateur de stats (ATK et HP) selon le niveau du heros.
    Exemple : Rare niveau 3 => 1.0 + 0.20 * (3-1) = 1.40 => +40% ATK/HP en jeu.
    """
    lvl    = get_hero_level(save, hero_id)
    rarity = HEROES[hero_id]["rarity"]
    bonus  = RARITY_LVL_BONUS[rarity]
    return 1.0 + bonus * (lvl - 1)


def get_hero_ingame_stats(save, hero_id):
    """
    Retourne les stats finales du heros en jeu (ATK et HP) avec le bonus de niveau.
    Usage : stats = get_hero_ingame_stats(save, hero_id)
            stats["atk"], stats["hp"]
    """
    mult = get_hero_stat_multiplier(save, hero_id)
    base = HERO_BASE_STATS[hero_id]
    return {
        "atk": round(base["atk"] * mult),
        "hp":  round(base["hp"]  * mult),
    }


def get_hero_passive_bonus(save, hero_id):
    """
    Multiplicateur fixe du passif (independant du niveau).
    Le niveau du heros booste uniquement ATK/HP via get_hero_stat_multiplier().
    """
    return 1.0


def get_selected_hero(save):
    init_heroes_save(save)
    return save.get("selected_hero", "eren")


def select_hero(save, hero_id):
    if is_hero_unlocked(save, hero_id):
        save["selected_hero"] = hero_id
        return True
    return False


# ============================================================
# CHARGEMENT DES SPRITES HEROS
# ============================================================

_SPRITES_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")

def load_hero_sprite(name, size=None):
    """Charge un sprite heros depuis assets/sprites/."""
    return theme.load_sprite(name, size)


def get_ingame_sprite_path(hero_id):
    """Retourne le chemin du spritesheet RPG Maker pour ce heros."""
    fname = HEROES[hero_id]["sprite_ingame"]
    return os.path.join(_SPRITES_DIR, fname)