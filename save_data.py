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
