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

_SAVE_FILE = os.path.join(os.path.dirname(__file__), "..", "save.json")

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
    },
    "tower_loadout": ["small", "big", "sniper"],
    "music_volume": 0.8,
    "sound_volume": 0.8,
    "fullscreen": False,
    "skill_points": 0,
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


# Modules freres : enregistres comme attributs apres re-export
from core.save_chests import *
from core.save_chests import (
    _try_drop_hero, _get_tower_chest_level, _get_tower_chest_progress, _ensure_tower_data, _try_drop_hero_for_tower_chest,
)
from core.save_skills import *
from core.save_skills import _NODE_BONUSES
