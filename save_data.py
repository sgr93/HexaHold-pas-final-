"""
save_data.py
------------
Gère la sauvegarde persistante : pièces, équipements obtenus, équipements équipés.
Utilise un simple fichier JSON.
"""

import json
import os
import random

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
        "name": "Armure Renforcée",
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

    # ─── Branche LÉGENDAIRE (Ultime) ───
    "legend_1": {
        "name": "Puissance Légendaire",
        "category": "legend",
        "level": 5,
        "cost": 5,
        "requires": ["force_4", "speed_4", "resist_4"],
        "bonus": {"player_damage": 10, "player_speed": 3, "max_hp": 50},
        "description": "Dégâts +10, Vitesse +3, Vie +50"
    },
    "legend_2": {
        "name": "Maître des Tours",
        "category": "legend",
        "level": 5,
        "cost": 5,
        "requires": ["tower_4", "power_3"],
        "bonus": {"tower_damage": 0.25, "tower_range": 0.25, "xp_gain": 0.3, "coin_gain": 0.3},
        "description": "Dégâts tour +25%, Portée +25%, XP/Pièces +30%"
    },
}

_DEFAULT = {
    "coins": 150,
    "inventory_equipment": [],   # liste de dicts {slot, rarity, stat, value, name}
    "equipped": {                # slot -> index dans inventory_equipment ou None
        "casque":   None,
        "armure":   None,
        "pantalon": None,
        "arme":     None,
        "tour":     None,
    },
    "tower_loadout": ["small", "big", "sniper"],
    "music_volume": 0.8,
    "sound_volume": 0.8,
    "fullscreen": False,
    "skill_points": 3,
    "skills_unlocked": {sid: False for sid in SKILLS.keys()},
}


def load():
    if os.path.exists(_SAVE_FILE):
        try:
            with open(_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge keys manquantes
            for k, v in _DEFAULT.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass
    return dict(_DEFAULT)


def save(data):
    try:
        with open(_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_data] Erreur sauvegarde : {e}")


def open_chest(save_data_dict, chest_type):
    """
    Ouvre un coffre du type donné (wood/silver/gold).
    Déduit les pièces, génère un équipement aléatoire.
    Retourne (success, item_dict_or_error_msg).
    """
    from config import CHEST_COSTS, RARITIES, RARITY_WEIGHTS, EQUIPMENT_SLOTS, EQUIPMENT_STATS, RARITY_COLORS

    cost = CHEST_COSTS.get(chest_type, 9999)
    if save_data_dict["coins"] < cost:
        return False, f"Pas assez de pièces (coût : {cost})"

    save_data_dict["coins"] -= cost

    weights = RARITY_WEIGHTS[chest_type]
    rarity  = random.choices(RARITIES, weights=weights, k=1)[0]

    slot     = random.choice(EQUIPMENT_SLOTS)
    stat_info = EQUIPMENT_STATS[slot]
    value    = stat_info["values"][rarity]

    SLOT_NAMES = {
        "casque":   "Casque",
        "armure":   "Armure",
        "pantalon": "Pantalon",
        "arme":     "Arme",
        "tour":     "Tour Bonus",
    }

    item = {
        "slot":    slot,
        "rarity":  rarity,
        "stat":    stat_info["stat"],
        "value":   value,
        "label":   stat_info["label"],
        "name":    f"{rarity} {SLOT_NAMES[slot]}",
        "color":   list(RARITY_COLORS[rarity]),
    }

    save_data_dict["inventory_equipment"].append(item)
    save(save_data_dict)
    return True, item


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
