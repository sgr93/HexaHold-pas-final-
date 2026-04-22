"""
save_data.py
------------
Gère la sauvegarde persistante : pièces, équipements obtenus, équipements équipés.
Utilise un simple fichier JSON.
"""

import json
import os
import random
import datetime

_SAVE_FILE = os.path.join(os.path.dirname(__file__), "save.json")

# ─────────────────────────────────────────────────────────────────
# DONNÉES DE SKILLTREE
# ─────────────────────────────────────────────────────────────────
SKILLTREE_DATA = {
    "skill_points": 0,        # Points de compétence disponibles
    "skills_unlocked": {},    # {skill_id: True/False}
    "skill_levels": {},       # {skill_id: level_number}
}

# Définition complète de l'arbre de compétences
SKILLS = {
    # ─── Branche FORCE ───
    "force_1": {
        "name": "Force Basique",
        "category": "force",
        "level": 1,
        "cost": 1,
        "requires": [],
        "bonus": {"player_damage": 2},
        "description": "+2 Dégâts de base au joueur"
    },
    "force_2": {
        "name": "Coup Critique",
        "category": "force",
        "level": 2,
        "cost": 2,
        "requires": ["force_1"],
        "bonus": {"crit_chance": 0.1},
        "description": "+10% Chance de coup critique"
    },
    "force_3": {
        "name": "Maîtrise du Combat",
        "category": "force",
        "level": 3,
        "cost": 3,
        "requires": ["force_2"],
        "bonus": {"player_damage": 5, "attack_speed": 2},
        "description": "+5 Dégâts, +2 Vitesse attaque"
    },
    "force_4": {
        "name": "Frappe Surhumaine",
        "category": "force",
        "level": 4,
        "cost": 4,
        "requires": ["force_3", "force_2"],
        "bonus": {"player_damage": 8, "crit_damage": 1.5},
        "description": "+8 Dégâts, crit x1.5"
    },

    # ─── Branche RAPIDITÉ ───
    "speed_1": {
        "name": "Agilité",
        "category": "speed",
        "level": 1,
        "cost": 1,
        "requires": [],
        "bonus": {"player_speed": 1},
        "description": "+1 Vitesse de mouvement"
    },
    "speed_2": {
        "name": "Esquive",
        "category": "speed",
        "level": 2,
        "cost": 2,
        "requires": ["speed_1"],
        "bonus": {"dodge_chance": 0.08},
        "description": "+8% Chance d'esquiver"
    },
    "speed_3": {
        "name": "Vive Arme",
        "category": "speed",
        "level": 3,
        "cost": 2,
        "requires": ["speed_1"],
        "bonus": {"attack_speed": 3},
        "description": "+3 Vitesse attaque"
    },
    "speed_4": {
        "name": "Reflex Ultime",
        "category": "speed",
        "level": 4,
        "cost": 4,
        "requires": ["speed_2", "speed_3"],
        "bonus": {"player_speed": 2, "dodge_chance": 0.15, "attack_speed": 2},
        "description": "Vitesse +2, Esquive +15%, Vitesse attaque +2"
    },

    # ─── Branche RÉSISTANCE ───
    "resist_1": {
        "name": "Peau Dure",
        "category": "resist",
        "level": 1,
        "cost": 1,
        "requires": [],
        "bonus": {"max_hp": 20},
        "description": "+20 Points de vie max"
    },
    "resist_2": {
        "name": "Veste Renforcée",
        "category": "resist",
        "level": 2,
        "cost": 2,
        "requires": ["resist_1"],
        "bonus": {"defense": 0.1},
        "description": "-10% Dégâts reçus"
    },
    "resist_3": {
        "name": "Régénération",
        "category": "resist",
        "level": 3,
        "cost": 2,
        "requires": ["resist_1"],
        "bonus": {"hp_regen": 0.3},
        "description": "+0.3 HP régénérés par sec"
    },
    "resist_4": {
        "name": "Vitalité Légendaire",
        "category": "resist",
        "level": 4,
        "cost": 4,
        "requires": ["resist_2", "resist_3"],
        "bonus": {"max_hp": 40, "defense": 0.15, "hp_regen": 0.2},
        "description": "Vie +40, Défense +15%, Regen +0.2/s"
    },

    # ─── Branche MAÎTRISE DES TOURS ───
    "tower_1": {
        "name": "Renforcement Tour",
        "category": "tower",
        "level": 1,
        "cost": 2,
        "requires": [],
        "bonus": {"tower_damage": 0.1},
        "description": "+10% Dégâts traversal"
    },
    "tower_2": {
        "name": "Tours Rapides",
        "category": "tower",
        "level": 2,
        "cost": 2,
        "requires": ["tower_1"],
        "bonus": {"tower_cooldown": -0.1},
        "description": "-10% Temps de recharge"
    },
    "tower_3": {
        "name": "Portée Accrue",
        "category": "tower",
        "level": 2,
        "cost": 2,
        "requires": ["tower_1"],
        "bonus": {"tower_range": 0.1},
        "description": "+10% Portée des tours"
    },
    "tower_4": {
        "name": "Synergie Totale",
        "category": "tower",
        "level": 3,
        "cost": 3,
        "requires": ["tower_2", "tower_3"],
        "bonus": {"tower_damage": 0.15, "tower_cooldown": -0.1, "tower_range": 0.15},
        "description": "Dégâts +15%, Recharge -10%, Portée +15%"
    },

    # ─── Branche PUISSANCE ───
    "power_1": {
        "name": "Confiance",
        "category": "power",
        "level": 1,
        "cost": 1,
        "requires": [],
        "bonus": {"xp_gain": 0.1},
        "description": "+10% Expérience gagnée"
    },
    "power_2": {
        "name": "Accumulation",
        "category": "power",
        "level": 2,
        "cost": 2,
        "requires": ["power_1"],
        "bonus": {"coin_gain": 0.1},
        "description": "+10% Pièces gagnées"
    },
    "power_3": {
        "name": "Synergie Magique",
        "category": "power",
        "level": 3,
        "cost": 3,
        "requires": ["power_1", "power_2"],
        "bonus": {"xp_gain": 0.2, "coin_gain": 0.2},
        "description": "XP +20%, Pièces +20%"
    },

    # ─── Compétences HYBRIDES (entre 2 branches) ───
    "hybrid_force_speed": {
        "name": "Frappe Éclair",
        "category": "hybrid",
        "branches": ["force", "speed"],
        "level": 3,
        "cost": 3,
        "requires": ["force_2", "speed_1"],
        "bonus": {"player_damage": 3, "attack_speed": 3},
        "description": "+3 Dégâts, +3 Vitesse attaque"
    },
    "hybrid_speed_resist": {
        "name": "Évasion Blindée",
        "category": "hybrid",
        "branches": ["speed", "resist"],
        "level": 3,
        "cost": 3,
        "requires": ["speed_2", "resist_1"],
        "bonus": {"dodge_chance": 0.1, "max_hp": 15},
        "description": "+10% Esquive, +15 Vie max"
    },
    "hybrid_resist_tower": {
        "name": "Fortification",
        "category": "hybrid",
        "branches": ["resist", "tower"],
        "level": 3,
        "cost": 3,
        "requires": ["resist_2", "tower_1"],
        "bonus": {"defense": 0.08, "tower_damage": 0.1},
        "description": "-8% Dégâts reçus, +10% Dégâts tours"
    },
    "hybrid_tower_power": {
        "name": "Investissement",
        "category": "hybrid",
        "branches": ["tower", "power"],
        "level": 3,
        "cost": 2,
        "requires": ["tower_1", "power_1"],
        "bonus": {"tower_range": 0.08, "coin_gain": 0.15},
        "description": "+8% Portée tours, +15% Pièces"
    },
    "hybrid_power_force": {
        "name": "Rage Intérieure",
        "category": "hybrid",
        "branches": ["power", "force"],
        "level": 3,
        "cost": 3,
        "requires": ["power_1", "force_1"],
        "bonus": {"xp_gain": 0.15, "player_damage": 4, "crit_chance": 0.05},
        "description": "+15% XP, +4 Dégâts, +5% Crit"
    },

}

_DEFAULT = {
    "level": 1,
    "xp": 0,
    "xp_next": 30,              # Aligné sur XP_TO_NEXT_LVL_START = 30 dans config.py
    "coins": 150,
    "gems": 0,
    "inventory_equipment": [],   # liste de dicts {slot, rarity, stat, value, name}
    "equipped": {                # slot -> index dans inventory_equipment ou None
        "cape":   None,
        "veste":   None,
        "bottes": None,
        "arme":     None,
        "tour":     None,
    },
    "tower_loadout": ["small", "big", "sniper"],
    "music_volume": 0.8,
    "sound_volume": 0.8,
    "fullscreen": False,
    "skill_points": 3,
    "skills_unlocked": {sid: False for sid in SKILLS.keys()},
    "quests_completed": {},
    "battles_won": 0,
    "towers_placed": 0,
    "enemies_killed": 0,
    "max_wave_reached": 0,
    "daily_quests_completed": {},
    "last_daily_reset": "",      # date ISO "YYYY-MM-DD" du dernier reset des quêtes quotidiennes
    "events_completed": {},
    "player_icon": "icone0.png",
    # Gacha tours
    "tower_chest_total_pulls": 0,
    "tower_chest_pity_epic":   0,
    "tower_chest_pity_legend": 0,
    "towers_unlocked": {t: True for t in ["small", "big", "trap"]},
    "towers_level":   {"small": 1, "big": 1, "trap": 1},
    "towers_copies":  {"small": 0, "big": 0, "trap": 0},
    "coin_chest_pulls": 0,
    "coin_chest_pity_epic":   0,   # pulls depuis dernier Épique+
    "coin_chest_pity_legend": 0,   # pulls depuis dernier Légendaire
    "histoire_unlocked": [0],   # chapitres débloqués
    "histoire_completed": []    # chapitres terminés
}


def load():
    if os.path.exists(_SAVE_FILE):
        try:
            with open(_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Migration ancienne sauvegarde : casque -> cape, armure -> veste, pantalon -> bottes
            equipped = data.get("equipped", {})
            if "casque" in equipped and "cape" not in equipped:
                equipped["cape"] = equipped.pop("casque")
            if "armure" in equipped and "veste" not in equipped:
                equipped["veste"] = equipped.pop("armure")
            if "pantalon" in equipped and "bottes" not in equipped:
                equipped["bottes"] = equipped.pop("pantalon")
            for item in data.get("inventory_equipment", []):
                if item.get("slot") == "casque":
                    item["slot"] = "cape"
                if item.get("slot") == "armure":
                    item["slot"] = "veste"
                if item.get("slot") == "pantalon":
                    item["slot"] = "bottes"
                if item.get("name") == "Casque du bataillon":
                    item["name"] = "Cape du bataillon"
                if item.get("image") == "casque.png":
                    item["image"] = "cape.png"
                if item.get("image") == "armure.png":
                    item["image"] = "veste.png"
                if item.get("image") == "pantalon.png":
                    item["image"] = "bottes.png"

            # Merge keys manquantes
            for k, v in _DEFAULT.items():
                if k not in data:
                    data[k] = v

            # Reset des quêtes quotidiennes si on est un nouveau jour
            _maybe_reset_daily_quests(data)

            return data
        except Exception:
            pass
    return dict(_DEFAULT)


def _maybe_reset_daily_quests(data):
    """Réinitialise daily_quests_completed si la date a changé depuis le dernier reset."""
    today = datetime.date.today().isoformat()
    if data.get("last_daily_reset", "") != today:
        data["daily_quests_completed"] = {}
        data["last_daily_reset"] = today


def save(data):
    try:
        with open(_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_data] Erreur sauvegarde : {e}")


EQUIPMENT_SELL_VALUES = {
    "Commun":    20,
    "Rare":      60,
    "Épique":    150,
    "Légendaire": 400,
    "Mythique":  1000,
}


def sell_equipment(save_data_dict, item_idx):
    """
    Vend un équipement de l'inventaire.
    Retourne (success, coins_gained, error_msg).
    """
    inv = save_data_dict.get("inventory_equipment", [])
    if item_idx < 0 or item_idx >= len(inv):
        return False, 0, "Objet invalide"

    item = inv[item_idx]
    rarity = item.get("rarity", "Commun")
    coins = EQUIPMENT_SELL_VALUES.get(rarity, 20)

    # Vérifier que l'objet n'est pas équipé
    equipped = save_data_dict.get("equipped", {})
    for slot, idx in equipped.items():
        if idx == item_idx:
            return False, 0, "Impossible de vendre un objet équipé"

    # Supprimer l'objet et mettre à jour les indices équipés
    inv.pop(item_idx)
    new_equipped = {}
    for slot, idx in equipped.items():
        if idx is None:
            new_equipped[slot] = None
        elif idx > item_idx:
            new_equipped[slot] = idx - 1
        else:
            new_equipped[slot] = idx
    save_data_dict["equipped"] = new_equipped
    save_data_dict["coins"] = save_data_dict.get("coins", 0) + coins
    save(save_data_dict)
    return True, coins, ""


def open_chest(save_data_dict, chest_type):
    """
    Ouvre un coffre du type donné (wood/silver/gold).
    Déduit les pièces, génère un équipement aléatoire.
    Retourne (success, item_dict_or_error_msg).
    """
    from config import CHEST_COSTS, RARITIES, RARITY_WEIGHTS, EQUIPMENT_SLOTS, EQUIPMENT_STATS, RARITY_COLORS

    cost = CHEST_COSTS.get(chest_type, 9999)

    # Détecter la currency (gemmes ou pièces)
    is_gem_chest = chest_type.startswith("gem_")
    if is_gem_chest:
        if save_data_dict.get("gems", 0) < cost:
            return False, f"Pas assez de gemmes (coût : {cost} 💎)"
        save_data_dict["gems"] = save_data_dict.get("gems", 0) - cost
    else:
        if save_data_dict.get("coins", 0) < cost:
            return False, f"Pas assez de pièces (coût : {cost})"
        save_data_dict["coins"] -= cost

    # Pour le coffre pièces "wood" : utiliser les poids par niveau + pitié
    if chest_type == "wood":
        save_data_dict["coin_chest_pulls"] = save_data_dict.get("coin_chest_pulls", 0) + 1
        save_data_dict.setdefault("coin_chest_pity_epic",   0)
        save_data_dict.setdefault("coin_chest_pity_legend", 0)
        save_data_dict["coin_chest_pity_epic"]   += 1
        save_data_dict["coin_chest_pity_legend"] += 1

        coin_lvl     = get_coin_chest_level(save_data_dict)
        epic_thr, legend_thr = COIN_CHEST_PITY.get(coin_lvl, (30, 100))

        if save_data_dict["coin_chest_pity_legend"] >= legend_thr:
            rarity = "Légendaire"
            save_data_dict["coin_chest_pity_epic"]   = 0
            save_data_dict["coin_chest_pity_legend"] = 0
        elif save_data_dict["coin_chest_pity_epic"] >= epic_thr:
            rarity = "Épique"
            save_data_dict["coin_chest_pity_epic"]   = 0
        else:
            weights_dict = COIN_CHEST_WEIGHTS_BY_LEVEL.get(coin_lvl, COIN_CHEST_WEIGHTS_BY_LEVEL[1])
            rar_list     = list(weights_dict.keys())
            wt_list      = [weights_dict[r] for r in rar_list]
            rarity       = random.choices(rar_list, weights=wt_list, k=1)[0]
            if rarity in ("Épique", "Légendaire"):
                save_data_dict["coin_chest_pity_epic"]   = 0
            if rarity == "Légendaire":
                save_data_dict["coin_chest_pity_legend"] = 0
    else:
        weights = RARITY_WEIGHTS[chest_type]
        rarity  = random.choices(RARITIES, weights=weights, k=1)[0]

    slot     = random.choice(EQUIPMENT_SLOTS)
    stat_info = EQUIPMENT_STATS[slot]
    value    = stat_info["values"].get(rarity, stat_info["values"]["Commun"])

    EQUIPMENT_NAMES = {
        "cape":   "Cape du bataillon",
        "veste":   "Veste de garnison",
        "bottes": "Bottes tactique",
        "arme":     "Lames jumelles",
        "tour":     "Insigne de commandement",
    }
    EQUIPMENT_IMAGES = {
        "cape":   "cape.png",
        "veste":   "veste.png",
        "bottes": "bottes.png",
        "arme":     "lames.png",
        "tour":     "tour.png",
    }

    item = {
        "slot":    slot,
        "rarity":  rarity,
        "stat":    stat_info["stat"],
        "value":   value,
        "label":   stat_info["label"],
        "name":    EQUIPMENT_NAMES[slot],
        "image":   EQUIPMENT_IMAGES[slot],
        "color":   list(RARITY_COLORS.get(rarity, (180, 180, 180))),
    }

    save_data_dict["inventory_equipment"].append(item)
    save(save_data_dict)
    return True, item


# ─────────────────────────────────────────────────────────────────
# SYSTÈME NIVEAU COFFRE PIÈCES
# ─────────────────────────────────────────────────────────────────

# Seuils de pulls pour passer au niveau suivant (identiques au coffre tours)
COIN_CHEST_LEVEL_THRESHOLDS = [0, 10, 30, 60, 100, 150, 210, 285, 370, 470, 600]

# Poids d'équipement par niveau du coffre pièces (Commun → Mythique)
# Lv1 : quasi que Commun, Lv10 : beaucoup de Légendaire/Mythique
COIN_CHEST_WEIGHTS_BY_LEVEL = {
    1:  {"Commun": 80, "Rare": 17, "Épique":  2, "Légendaire": 1, "Mythique":  0},
    2:  {"Commun": 65, "Rare": 26, "Épique":  7, "Légendaire": 2, "Mythique":  0},
    3:  {"Commun": 52, "Rare": 32, "Épique": 12, "Légendaire": 3, "Mythique":  1},
    4:  {"Commun": 40, "Rare": 35, "Épique": 17, "Légendaire": 6, "Mythique":  2},
    5:  {"Commun": 30, "Rare": 35, "Épique": 22, "Légendaire": 9, "Mythique":  4},
    6:  {"Commun": 22, "Rare": 33, "Épique": 26, "Légendaire":13, "Mythique":  6},
    7:  {"Commun": 15, "Rare": 30, "Épique": 30, "Légendaire":17, "Mythique":  8},
    8:  {"Commun":  9, "Rare": 25, "Épique": 32, "Légendaire":22, "Mythique": 12},
    9:  {"Commun":  5, "Rare": 18, "Épique": 32, "Légendaire":28, "Mythique": 17},
    10: {"Commun":  2, "Rare": 11, "Épique": 27, "Légendaire":35, "Mythique": 25},
}


def get_coin_chest_level(save_data_dict):
    """Retourne le niveau actuel du coffre pièces (1-10)."""
    total = save_data_dict.get("coin_chest_pulls", 0)
    level = 1
    for i, threshold in enumerate(COIN_CHEST_LEVEL_THRESHOLDS):
        if total >= threshold:
            level = i + 1
        else:
            break
    return min(level, 10)


# Pitié coffre pièces : (epic_threshold, legend_threshold) par niveau
COIN_CHEST_PITY = {
    1:  (30, 100),
    2:  (28,  90),
    3:  (25,  80),
    4:  (22,  70),
    5:  (20,  60),
    6:  (17,  50),
    7:  (15,  40),
    8:  (12,  30),
    9:  (10,  25),
    10: ( 8,  20),
}


def get_coin_chest_progress(save_data_dict):
    """Retourne (pulls_dans_ce_niveau, pulls_pour_prochain_niveau, niveau_actuel)."""
    total = save_data_dict.get("coin_chest_pulls", 0)
    level = get_coin_chest_level(save_data_dict)
    if level >= 10:
        return total, total, 10
    current_threshold = COIN_CHEST_LEVEL_THRESHOLDS[level - 1]
    next_threshold    = COIN_CHEST_LEVEL_THRESHOLDS[level]
    pulls_in_level    = total - current_threshold
    pulls_needed      = next_threshold - current_threshold
    return pulls_in_level, pulls_needed, level

# Raretés des tours
TOWER_RARITIES = ["Commun", "Rare", "Épique", "Légendaire"]
TOWER_RARITY_COLORS = {
    "Commun":    (180, 180, 180),
    "Rare":      (60,  120, 255),
    "Épique":    (160,  60, 255),
    "Légendaire":(255, 180,   0),
}

# Les 12 tours avec leur rareté de base (détermine la difficulté à obtenir)
TOWER_POOL = {
    "small":   {"rarity": "Commun",    "label": "Tour Rapide",   "desc": "Tour basique, tir rapide"},
    "big":     {"rarity": "Commun",    "label": "Tour Lourde",   "desc": "Plus de dégâts, moins rapide"},
    "trap":    {"rarity": "Commun",    "label": "Piège",         "desc": "Piège au sol, ralentit"},
    "frost":   {"rarity": "Rare",      "label": "Gèleuse",       "desc": "Ralentit les ennemis"},
    "poison":  {"rarity": "Rare",      "label": "Venimeuse",     "desc": "Dégâts sur la durée"},
    "burst":   {"rarity": "Rare",      "label": "Fusée",         "desc": "Dégâts de zone"},
    "mine":    {"rarity": "Rare",      "label": "Mine",          "desc": "Explose au contact"},
    "mortar":  {"rarity": "Épique",    "label": "Mortier",       "desc": "Longue portée, gros dégâts"},
    "sniper":  {"rarity": "Épique",    "label": "Sniper",        "desc": "Très longue portée"},
    "tesla":   {"rarity": "Épique",    "label": "Tesla",         "desc": "Chaîne l'électricité"},
    "cannon":  {"rarity": "Légendaire","label": "Canon",         "desc": "Puissance maximale"},
    "laser":   {"rarity": "Légendaire","label": "Laser lourd",   "desc": "Rayon continu dévastateur"},
    "beam":    {"rarity": "Légendaire","label": "Laser",         "desc": "Faisceaux d'énergie"},
}

# Poids de tirage par niveau du coffre (Commun, Rare, Épique, Légendaire)
# Lv1 : presque que Commun, très rare Épique, pas de Légendaire
# Plus le niveau monte, plus les hautes raretés deviennent accessibles
TOWER_CHEST_WEIGHTS_BY_LEVEL = {
    1:  {"Commun": 80, "Rare": 18, "Épique":  2, "Légendaire":  0},
    2:  {"Commun": 70, "Rare": 24, "Épique":  5, "Légendaire":  1},
    3:  {"Commun": 58, "Rare": 30, "Épique": 10, "Légendaire":  2},
    4:  {"Commun": 48, "Rare": 33, "Épique": 15, "Légendaire":  4},
    5:  {"Commun": 38, "Rare": 35, "Épique": 20, "Légendaire":  7},
    6:  {"Commun": 28, "Rare": 35, "Épique": 26, "Légendaire": 11},
    7:  {"Commun": 20, "Rare": 33, "Épique": 30, "Légendaire": 17},
    8:  {"Commun": 13, "Rare": 29, "Épique": 33, "Légendaire": 25},
    9:  {"Commun":  7, "Rare": 23, "Épique": 35, "Légendaire": 35},
    10: {"Commun":  3, "Rare": 17, "Épique": 35, "Légendaire": 45},
}
# Alias pour compatibilité (utilise le niveau 1 par défaut)
TOWER_CHEST_WEIGHTS = TOWER_CHEST_WEIGHTS_BY_LEVEL[1]

# Niveau du coffre : seuils pour passer au niveau suivant
# Index = niveau actuel (0-based), valeur = nb de pulls nécessaires pour atteindre ce niveau
# Niveau 1 = 0 pulls, niveau 2 = 10, niveau 3 = 20, niveau 4 = 35, niveau 5 = 55, niveau 6 = 80...
TOWER_CHEST_LEVEL_THRESHOLDS = [0, 10, 30, 60, 100, 150, 210, 285, 370, 470, 600]

# Pitié : garantis selon le niveau du coffre
# Niveau -> (nb pulls pour garantir Épique, nb pulls pour garantir Légendaire)
TOWER_CHEST_PITY = {
    1: (22, 100),
    2: (20, 90),
    3: (18, 80),
    4: (16, 70),
    5: (14, 60),
    6: (12, 50),
    7: (10, 40),
    8: (8,  30),
    9: (6,  25),
    10: (5, 20),
}

# Coût du coffre tour (en gemmes), réduit à chaque niveau
TOWER_CHEST_COSTS = {1: 5, 2: 5, 3: 4, 4: 4, 5: 3, 6: 3, 7: 2, 8: 2, 9: 1, 10: 1}

# Montée de niveau des tours possédées
# Tour niveau X nécessite X copies supplémentaires pour passer au niveau X+1
TOWER_UPGRADE_COST = [1, 2, 3, 5, 8]  # coût en copies pour niveau 1→2, 2→3, etc.

# Tours débloquées dès le départ (avant tout tirage)
TOWER_DEFAULT_UNLOCKED = ["small", "big", "trap"]


def _get_tower_chest_level(save_data_dict):
    """Retourne le niveau actuel du coffre tours (1-10)."""
    total_pulls = save_data_dict.get("tower_chest_total_pulls", 0)
    level = 1
    for i, threshold in enumerate(TOWER_CHEST_LEVEL_THRESHOLDS):
        if total_pulls >= threshold:
            level = i + 1
        else:
            break
    return min(level, 10)


def _get_tower_chest_progress(save_data_dict):
    """Retourne (pulls_dans_ce_niveau, pulls_pour_prochain_niveau, niveau_actuel)."""
    total = save_data_dict.get("tower_chest_total_pulls", 0)
    level = _get_tower_chest_level(save_data_dict)
    if level >= 10:
        return total, total, 10
    current_threshold = TOWER_CHEST_LEVEL_THRESHOLDS[level - 1]
    next_threshold = TOWER_CHEST_LEVEL_THRESHOLDS[level]
    pulls_in_level = total - current_threshold
    pulls_needed = next_threshold - current_threshold
    return pulls_in_level, pulls_needed, level


def _ensure_tower_data(save_data_dict):
    """Initialise les données de tours si absentes."""
    save_data_dict.setdefault("tower_chest_total_pulls", 0)
    save_data_dict.setdefault("tower_chest_pity_epic", 0)    # pulls depuis dernier Épique+
    save_data_dict.setdefault("tower_chest_pity_legend", 0)  # pulls depuis dernier Légendaire
    save_data_dict.setdefault("towers_unlocked", {t: True for t in TOWER_DEFAULT_UNLOCKED})
    save_data_dict.setdefault("towers_level", {t: 1 for t in TOWER_DEFAULT_UNLOCKED})
    save_data_dict.setdefault("towers_copies", {t: 0 for t in TOWER_DEFAULT_UNLOCKED})


def open_tower_chest(save_data_dict, count=1):
    """
    Ouvre 1 ou 5 coffres tour (en gemmes).
    Retourne (success, [résultats]) — résultats = liste de dicts {tower_id, rarity, is_new, ...}
    """
    _ensure_tower_data(save_data_dict)
    level = _get_tower_chest_level(save_data_dict)
    cost_per = TOWER_CHEST_COSTS.get(level, 5)
    total_cost = cost_per * count

    if save_data_dict.get("gems", 0) < total_cost:
        return False, f"Pas assez de gemmes (coût : {total_cost} 💎)"

    save_data_dict["gems"] -= total_cost
    results = []

    pity_epic   = save_data_dict["tower_chest_pity_epic"]
    pity_legend = save_data_dict["tower_chest_pity_legend"]
    epic_threshold, legend_threshold = TOWER_CHEST_PITY.get(level, (22, 100))

    for _ in range(count):
        save_data_dict["tower_chest_total_pulls"] += 1
        pity_epic   += 1
        pity_legend += 1

        # Poids selon le niveau actuel du coffre
        weights_lv = TOWER_CHEST_WEIGHTS_BY_LEVEL.get(level, TOWER_CHEST_WEIGHTS_BY_LEVEL[1])

        # Déterminer la rareté (avec pitié)
        if pity_legend >= legend_threshold:
            rarity = "Légendaire"
            pity_legend = 0
            pity_epic   = 0
        elif pity_epic >= epic_threshold:
            rarity = "Épique"
            pity_epic = 0
        else:
            pool_rarities = list(weights_lv.keys())
            pool_weights  = [weights_lv[r] for r in pool_rarities]
            rarity = random.choices(pool_rarities, weights=pool_weights, k=1)[0]
            if rarity in ("Épique", "Légendaire"):
                pity_epic = 0
            if rarity == "Légendaire":
                pity_legend = 0

        # Choisir une tour de cette rareté
        candidates = [tid for tid, td in TOWER_POOL.items() if td["rarity"] == rarity]
        if not candidates:
            candidates = list(TOWER_POOL.keys())
        tower_id = random.choice(candidates)
        tower_info = TOWER_POOL[tower_id]

        towers_unlocked = save_data_dict["towers_unlocked"]
        towers_copies   = save_data_dict["towers_copies"]
        towers_level    = save_data_dict["towers_level"]

        is_new = tower_id not in towers_unlocked or not towers_unlocked.get(tower_id)
        if is_new:
            towers_unlocked[tower_id] = True
            towers_level[tower_id]    = 1
            towers_copies[tower_id]   = 0
        else:
            # Ajouter la copie — la montée de niveau est MANUELLE (via upgrade_tower)
            towers_copies[tower_id] = towers_copies.get(tower_id, 0) + 1

        cur_lvl   = towers_level.get(tower_id, 1)
        copies_now = towers_copies.get(tower_id, 0)
        needed     = TOWER_UPGRADE_COST[cur_lvl - 1] if cur_lvl <= len(TOWER_UPGRADE_COST) else None
        can_upgrade = (needed is not None) and (copies_now >= needed)

        results.append({
            "tower_id":    tower_id,
            "label":       tower_info["label"],
            "rarity":      rarity,
            "rarity_color": list(TOWER_RARITY_COLORS[rarity]),
            "is_new":      is_new,
            "level":       cur_lvl,
            "copies":      copies_now,
            "needed":      needed,
            "can_upgrade": can_upgrade,
            "desc":        tower_info["desc"],
        })

    save_data_dict["tower_chest_pity_epic"]   = pity_epic
    save_data_dict["tower_chest_pity_legend"] = pity_legend
    save(save_data_dict)
    return True, results


def upgrade_tower(save_data_dict, tower_id):
    """Essaie de monter de niveau une tour manuellement. Retourne (success, msg)."""
    _ensure_tower_data(save_data_dict)
    if not save_data_dict["towers_unlocked"].get(tower_id):
        return False, "Tour non débloquée"
    cur_lvl = save_data_dict["towers_level"].get(tower_id, 1)
    if cur_lvl > len(TOWER_UPGRADE_COST):
        return False, "Niveau max atteint"
    needed = TOWER_UPGRADE_COST[cur_lvl - 1]
    copies = save_data_dict["towers_copies"].get(tower_id, 0)
    if copies < needed:
        return False, f"Besoin de {needed} copies ({copies}/{needed})"
    save_data_dict["towers_copies"][tower_id] -= needed
    save_data_dict["towers_level"][tower_id]   = cur_lvl + 1
    save(save_data_dict)
    return True, f"Tour montée au niveau {cur_lvl + 1}!"


# ─────────────────────────────────────────────────────────────────
# FONCTIONS DE SKILLTREE
# ─────────────────────────────────────────────────────────────────

def add_skill_points(save_data_dict, amount):
    """Ajoute des points de compétence au joueur."""
    save_data_dict["skill_points"] = save_data_dict.get("skill_points", 0) + amount
    save(save_data_dict)


def can_unlock_skill(save_data_dict, skill_id):
    """
    Vérifie si une compétence peut être acquise.
    Retourne (can_unlock, error_message).
    """
    if skill_id not in SKILLS:
        return False, "Compétence inexistante"
    
    skill = SKILLS[skill_id]
    
    # Vérifier si déjà acquise
    if save_data_dict.get("skills_unlocked", {}).get(skill_id, False):
        return False, "Compétence déjà acquise"
    
    # Vérifier les points de skill
    if save_data_dict.get("skill_points", 0) < skill["cost"]:
        return False, f"Pas assez de points ({save_data_dict.get('skill_points', 0)}/{skill['cost']})"
    
    # Vérifier les dépendances
    for req_id in skill.get("requires", []):
        if not save_data_dict.get("skills_unlocked", {}).get(req_id, False):
            req_skill = SKILLS.get(req_id, {})
            return False, f"Requis : {req_skill.get('name', req_id)}"
    
    return True, ""


def unlock_skill(save_data_dict, skill_id):
    """
    Déverrouille une compétence et déduit les points de skill.
    Retourne (success, message).
    """
    can_unlock, msg = can_unlock_skill(save_data_dict, skill_id)
    if not can_unlock:
        return False, msg
    
    skill = SKILLS[skill_id]
    save_data_dict["skill_points"] -= skill["cost"]
    
    if "skills_unlocked" not in save_data_dict:
        save_data_dict["skills_unlocked"] = {}
    
    save_data_dict["skills_unlocked"][skill_id] = True
    save(save_data_dict)
    return True, f"Compétence acquise : {skill['name']}!"


def get_active_bonuses(save_data_dict):
    """
    Calcule tous les bonus actifs du joueur basé sur les compétences aquises.
    Retourne un dictionnaire de bonus cumulés.
    """
    bonuses = {
        "player_damage": 0,
        "player_speed": 0,
        "max_hp": 0,
        "attack_speed": 0,
        "defense": 0,
        "hp_regen": 0,
        "crit_chance": 0,
        "crit_damage": 0,
        "dodge_chance": 0,
        "tower_damage": 0,
        "tower_cooldown": 0,
        "tower_range": 0,
        "xp_gain": 0,
        "coin_gain": 0,
    }
    
    unlocked = save_data_dict.get("skills_unlocked", {})
    for skill_id, is_unlocked in unlocked.items():
        if is_unlocked and skill_id in SKILLS:
            skill = SKILLS[skill_id]
            for bonus_key, bonus_value in skill.get("bonus", {}).items():
                bonuses[bonus_key] = bonuses.get(bonus_key, 0) + bonus_value
    
    return bonuses


def apply_skill_bonuses_to_player(save_data_dict, player):
    """
    Applique tous les bonus du skill tree et des équipements sur l'objet Player.
    À appeler après build_initial_state() quand les équipements ont déjà été traités
    (pour ne pas doubler les bonus d'équipement).
    Seuls les bonus de compétences pures sont appliqués ici.
    """
    bonuses = get_active_bonuses(save_data_dict)

    # Dégâts joueur
    player.damage += bonuses.get("player_damage", 0)

    # Vitesse de déplacement
    player.speed += bonuses.get("player_speed", 0)

    # HP max (et HP courants proportionnellement)
    hp_bonus = bonuses.get("max_hp", 0)
    if hp_bonus:
        player.max_hp += hp_bonus
        player.hp     += hp_bonus  # on donne aussi les HP directement

    # Vitesse d'attaque : bonus = réduction du cooldown en frames
    atk_spd = bonuses.get("attack_speed", 0)
    if atk_spd:
        player.attack_cooldown = max(5, player.attack_cooldown - int(atk_spd))

    # Chance de coup critique (0.0 → 1.0)
    player.crit_chance  = min(0.95, player.crit_chance + bonuses.get("crit_chance", 0))

    # Multiplicateur de dégâts critiques
    crit_dmg_bonus = bonuses.get("crit_damage", 0)
    if crit_dmg_bonus:
        player.crit_damage += crit_dmg_bonus

    # Esquive (0.0 → max 0.80 pour éviter l'invincibilité)
    player.dodge_chance = min(0.80, player.dodge_chance + bonuses.get("dodge_chance", 0))

    # Défense (réduction des dégâts reçus, plafonnée à 80%)
    player.defense = min(0.80, player.defense + bonuses.get("defense", 0))