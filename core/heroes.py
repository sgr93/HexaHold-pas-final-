"""
heroes.py
---------
Définit les 5 héros jouables, leurs raretés, passifs et système de niveau.

Raretés : Commun / Rare / Légendaire
Monter en niveau se fait en tirant des doublons au gacha —
plus la rareté est haute, plus chaque niveau apporte de bonus.
"""

import os
import ui.theme as theme


HEROES = {
    "eren": {
        "name":     "Eren Jaeger",
        "rarity":   "Commun",
        "unlocked": True,   # débloqué de base, pas besoin de gems
        "cost_gems": 0,
        "sprite_select":   "eren_select.png",
        "sprite_portrait": "eren_portrait.png",
        "sprite_ingame":   "_Eren_Scouting_Legion_2.png",
        "passive_name": "Titan des Murs",
        "passive_desc": "Les tours dans un rayon de 8 cases\nauront +20% de dégats.",
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
        "passive_name": "Stratège",
        "passive_desc": "Chaque tour construite donne\n+40% d'ATK à toutes les tours.",
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
        "passive_desc": "Une tour aléatoire supplémentaire\nest ajoutée à l'inventaire\nchaque vague.",
        "passive_id":   "sasha_extra_tower",
        "color": (160, 120, 80),
    },
    "levi": {
        "name":     "Levi Ackerman",
        "rarity":   "Légendaire",
        "unlocked": False,
        "cost_gems": 80,
        "sprite_select":   "levi_select.png",
        "sprite_portrait": "levi_portrait.png",
        "sprite_ingame":   "_Rivaille_Without_Cloak.png",
        "passive_name": "Capitaine de l'Humanité",
        # son passif change complètement la stratégie de montée en niveau des tours
        "passive_desc": "Améliorer une tour niveau 1\nla passe directement niveau 3.",
        "passive_id":   "levi_instant_max",
        "color": (160, 200, 220),
    },
    "mikasa": {
        "name":     "Mikasa Ackerman",
        "rarity":   "Légendaire",
        "unlocked": False,
        "cost_gems": 80,
        "sprite_select":   "mikasa_select.png",
        "sprite_portrait": "mikasa_portrait.png",
        "sprite_ingame":   "_Mikasa_Scouting_Legion_2.png",
        "passive_name": "Lame de l'Ackerman",
        "passive_desc": "Inflige des dégats continus\nà tous les ennemis dans\nun rayon de 120px.",
        "passive_id":   "mikasa_aoe_damage",
        "color": (127, 119, 221),
    },
}

RARITY_ORDER  = ["Commun", "Rare", "Légendaire"]
RARITY_COLORS = {
    "Commun":     (180, 180, 180),
    "Rare":       (80, 140, 255),
    "Légendaire": (255, 180, 0),
}

# bonus ATK/HP par niveau selon la rareté — les légendaires montent beaucoup plus vite
RARITY_LVL_BONUS = {
    "Commun":     0.10,
    "Rare":       0.20,
    "Légendaire": 0.30,
}

HERO_BASE_STATS = {
    "eren":   {"atk":  8, "hp": 180},
    "armin":  {"atk":  6, "hp": 160},
    "sasha":  {"atk":  7, "hp": 150},
    "levi":   {"atk": 10, "hp": 200},
    "mikasa": {"atk":  9, "hp": 190},
}

HERO_ORDER = ["eren", "armin", "sasha", "levi", "mikasa"]


def get_hero_save(save, hero_id):
    """Retourne la save d'un héros, la crée si elle n'existe pas encore."""
    heroes_save = save.setdefault("heroes", {})
    if hero_id not in heroes_save:
        heroes_save[hero_id] = {"copies": 0, "level": 1}
        if HEROES[hero_id]["unlocked"]:
            heroes_save[hero_id]["copies"] = 1
    return heroes_save[hero_id]


def init_heroes_save(save):
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
    init_heroes_save(save)
    return save["heroes"].get(hero_id, {}).get("copies", 0) >= 1


def add_hero_copy(save, hero_id):
    """
    Ajoute un doublon du héros — la première copie débloque, les suivantes
    font monter le niveau tous les 2 doublons.
    """
    init_heroes_save(save)
    h = save["heroes"][hero_id]
    h["copies"] = h.get("copies", 0) + 1
    copies = h["copies"]
    if copies > 1:
        h["level"] = 1 + (copies-1) // 2
    return h["level"]


def get_hero_level(save, hero_id):
    init_heroes_save(save)
    return save["heroes"].get(hero_id, {}).get("level", 1)


def get_hero_stat_multiplier(save, hero_id):
    """
    Calcule le multiplicateur de stats selon le niveau et la rareté.
    Un légendaire niveau 3 gagne +60% alors qu'un commun niveau 3 ne gagne que +20%.
    """
    lvl    = get_hero_level(save, hero_id)
    rarity = HEROES[hero_id]["rarity"]
    bonus  = RARITY_LVL_BONUS[rarity]
    return 1.0 + bonus*(lvl-1)


def get_hero_ingame_stats(save, hero_id):
    """Retourne les stats ATK et HP finales du héros avec le bonus de niveau appliqué."""
    mult = get_hero_stat_multiplier(save, hero_id)
    base = HERO_BASE_STATS[hero_id]
    return {
        "atk": round(base["atk"] * mult),
        "hp":  round(base["hp"]  * mult),
    }


def get_hero_passive_bonus(save, hero_id):
    # le passif est fixe, indépendant du niveau — seul ATK/HP scale
    return 1.0


def get_selected_hero(save):
    init_heroes_save(save)
    return save.get("selected_hero", "eren")


def select_hero(save, hero_id):
    if is_hero_unlocked(save, hero_id):
        save["selected_hero"] = hero_id
        return True
    return False


_SPRITES_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")

def load_hero_sprite(name, size=None):
    return theme.load_sprite(name, size)


def get_ingame_sprite_path(hero_id):
    fname = HEROES[hero_id]["sprite_ingame"]
    return os.path.join(_SPRITES_DIR, fname)