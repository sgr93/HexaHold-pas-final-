"""
save_data.py

Gère la sauvegarde persistante : pièces, équipements, progression du joueur.
Tout est stocké dans un fichier JSON à côté du module.
"""

import json
import os
import random
import datetime

_SAVE_FILE = os.path.join(os.path.dirname(__file__), "..", "save.json")

# définition du skill tree 
SKILLTREE_DATA = {
    "skill_points":   0,
    "skills_unlocked": {},
    "skill_levels":   {},
}

# valeurs par défaut d'une nouvelle partie —
# xp_next doit rester aligné avec XP_TO_NEXT_LVL_START dans config.py
_DEFAULT = {
    "level": 1,
    "xp": 0,
    "xp_next": 30,
    "coins": 150,
    "gems": 0,
    "inventory_equipment": [],
    "equipped": {
        "cape":   None,
        "veste":  None,
        "bottes": None,
        "arme":   None,
    },
    "tower_loadout": ["small", "big", "trap"],
    "music_volume": 0.8,
    "sound_volume": 0.8,
    "fullscreen": False,
    "skill_points": 0,
    "quests_completed": {},
    "battles_won": 0,
    "towers_placed": 0,
    "enemies_killed": 0,
    "max_wave_reached": 0,
    "daily_quests_completed": {},
    "last_daily_reset": "",   # date ISO du dernier reset des quotidiennes
    "events_completed": {},
    "player_icon": "icone0.png",
    "tower_chest_total_pulls": 0,
    "tower_chest_pity_epic":   0,
    "tower_chest_pity_legend": 0,
    "towers_unlocked": {t: True for t in ["small", "big", "trap"]},
    "towers_level":   {"small": 1, "big": 1, "trap": 1},
    "towers_copies":  {"small": 0, "big": 0, "trap": 0},
    "coin_chest_pulls": 0,
    "coin_chest_pity_epic":   0,   # pulls depuis dernier Épique+
    "coin_chest_pity_legend": 0,   # pulls depuis dernier Légendaire
    "histoire_unlocked": [0],      # chapitres débloqués
    "histoire_completed": [],      # chapitres terminés
    "difficulty_completed": [],
    "quests_notified": []
}


def load():
    """
    Charge la sauvegarde depuis le fichier JSON.
    Gère aussi la migration des anciennes saves qui utilisaient
    des noms de slots différents (casque/armure/pantalon).
    Si le fichier est corrompu ou absent, on repart d'une save vierge.
    """
    if os.path.exists(_SAVE_FILE):
        try:
            with open(_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # migration des anciens noms de slots vers les nouveaux
            # à garder tant qu'il peut y avoir des saves avec l'ancien format
            equipped = data.get("equipped", {})
            if "casque" in equipped and "cape" not in equipped:
                equipped["cape"] = equipped.pop("casque")
            if "armure" in equipped and "veste" not in equipped:
                equipped["veste"] = equipped.pop("armure")
            if "pantalon" in equipped and "bottes" not in equipped:
                equipped["bottes"] = equipped.pop("pantalon")

            for item in data.get("inventory_equipment", []):
                if item.get("slot") == "casque":   item["slot"]  = "cape"
                if item.get("slot") == "armure":   item["slot"]  = "veste"
                if item.get("slot") == "pantalon": item["slot"]  = "bottes"
                if item.get("name") == "Casque du bataillon": item["name"] = "Cape du bataillon"
                if item.get("image") == "casque.png":  item["image"] = "cape.png"
                if item.get("image") == "armure.png":  item["image"] = "veste.png"
                if item.get("image") == "pantalon.png": item["image"] = "bottes.png"

            # on complète avec les clés manquantes sans écraser ce qui existe
            for k, v in _DEFAULT.items():
                if k not in data:
                    data[k] = v

            _maybe_reset_daily_quests(data)
            return data

        except Exception:
            pass

    # fichier absent ou corrompu — nouvelle partie
    return dict(_DEFAULT)


def _maybe_reset_daily_quests(data):
    """Remet à zéro les quêtes quotidiennes si on est passé à un nouveau jour."""
    today = datetime.date.today().isoformat()
    if data.get("last_daily_reset", "") != today:
        data["daily_quests_completed"] = {}
        data["last_daily_reset"]       = today


def save(data):
    try:
        with open(_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_data] erreur sauvegarde : {e}")


# imports des fichiers qu'on a séparé. A l'origine, ils formaient 1 suel fichier
from core.save_chests import *
from core.save_chests import (
    _try_drop_hero, _get_tower_chest_level, _get_tower_chest_progress,
    _ensure_tower_data, _try_drop_hero_for_tower_chest,
)
from core.save_skills import *
from core.save_skills import _NODE_BONUSES