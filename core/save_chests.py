"""
save_chests.py
--------------
Coffres (pieces & tours), equipement et upgrade des tours.
Extrait de save_data.py.
"""
import random
import save_data as sd
import heroes as _hm
from config import CHEST_COSTS, RARITIES, RARITY_WEIGHTS, EQUIPMENT_SLOTS, EQUIPMENT_STATS, RARITY_COLORS
import traceback; traceback.print_exc()

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
    sd.save(save_data_dict)
    return True, coins, ""


def _try_drop_hero(save_data_dict, chest_type):
    """
    Tente de dropper un heros dans un coffre gemmes.
    Taux : gem_common=8%, gem_epic=18%, gem_legendary=35%
    Retourne un dict heros si drop, None sinon.
    """

    DROP_RATES = {
        "gem_common":    0.08,
        "gem_epic":      0.18,
        "gem_legendary": 0.35,
    }
    # Pool de heros par rarity du coffre
    HERO_POOL = {
        "gem_common":    ["eren", "armin", "sasha"],
        "gem_epic":      ["armin", "sasha", "levi", "mikasa"],
        "gem_legendary": ["levi", "mikasa"],
    }

    rate = DROP_RATES.get(chest_type, 0)
    if random.random() > rate:
        return None

    pool = HERO_POOL.get(chest_type, list(_hm.HEROES.keys()))
    # Filtrer selon la rarity du coffre : common peut dropper Commun/Rare, legendary = Legendaire seulement
    hero_id = random.choice(pool)
    hdef    = _hm.HEROES[hero_id]

    # Ajouter la copie
    _hm.init_heroes_save(save_data_dict)
    level = _hm.add_hero_copy(save_data_dict, hero_id)

    return {
        "type":   "hero",
        "id":     hero_id,
        "name":   hdef["name"],
        "rarity": hdef["rarity"],
        "level":  level,
        "copies": save_data_dict["heroes"][hero_id]["copies"],
        "passive_name": hdef["passive_name"],
        "sprite_select": hdef["sprite_select"],
        "color":  list(_hm.RARITY_COLORS.get(hdef["rarity"], (180, 180, 180))),
    }


def open_chest(save_data_dict, chest_type):
    """
    Ouvre un coffre du type donné (wood/silver/gold).
    Déduit les pièces, génère un équipement aléatoire.
    Retourne (success, item_dict_or_error_msg).
    """

    cost = CHEST_COSTS.get(chest_type, 9999)

    # Détecter la currency (gemmes ou pièces)
    is_gem_chest = chest_type.startswith("gem_")
    if is_gem_chest:
        if save_data_dict.get("gems", 0) < cost:
            return False, f"Pas assez de gemmes (cout : {cost} gemmes)"
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
    }
    EQUIPMENT_IMAGES = {
        "cape":   "cape.png",
        "veste":   "veste.png",
        "bottes": "bottes.png",
        "arme":     "lames.png",
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
    sd.save(save_data_dict)
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
    # Commun
    "small":   {"rarity": "Commun",    "label": "Tour Rapide",  "desc": "Tour basique, tir rapide"},
    "big":     {"rarity": "Commun",    "label": "Tour Lourde",  "desc": "Plus de dégâts, moins rapide"},
    "trap":    {"rarity": "Commun",    "label": "Piège",        "desc": "Piège au sol"},
    # Rare
    "frost":   {"rarity": "Rare",      "label": "Gèleuse",      "desc": "Ralentit les ennemis"},
    "mine":    {"rarity": "Rare",      "label": "Mine",         "desc": "Explose au contact"},
    # Épique
    "mortar":  {"rarity": "Épique",    "label": "Mortier",      "desc": "Longue portée, gros dégâts"},
    "sniper":  {"rarity": "Épique",    "label": "Sniper",       "desc": "Très longue portée"},
    "tesla":   {"rarity": "Épique",    "label": "Tesla",        "desc": "Chaîne l'électricité"},
    # Légendaire
    "cannon":  {"rarity": "Légendaire","label": "Canon",        "desc": "Puissance maximale"},
    "laser":   {"rarity": "Légendaire","label": "Laser",        "desc": "Rayon continu dévastateur"},
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


def _try_drop_hero_for_tower_chest(save_data_dict, rarity):
    """
    Tente de dropper un heros dans un coffre tour a gemmes.
    Filtre par rarity : Legendaire/Epique -> heros Rare/Legendaire, Commun -> heros Commun.
    Retourne un dict result ou None.
    """

    RARITY_MAP = {
        "Légendaire": ["levi", "mikasa"],
        "Épique":     ["armin", "sasha"],
        "Commun":     ["eren"],
    }
    pool = RARITY_MAP.get(rarity, ["eren"])
    hero_id = random.choice(pool)
    hdef    = _hm.HEROES[hero_id]

    _hm.init_heroes_save(save_data_dict)
    level = _hm.add_hero_copy(save_data_dict, hero_id)
    copies = save_data_dict["heroes"][hero_id]["copies"]

    # Couleur basee sur la rarete du heros (pas du coffre)
    HERO_RARITY_COLORS = {
        "Commun":     (180, 180, 180),
        "Rare":       (80,  140, 255),
        "Legendaire": (255, 180,   0),
    }
    color = HERO_RARITY_COLORS.get(hdef["rarity"], (180, 180, 180))

    return {
        "type":          "hero",
        "tower_id":      f"hero_{hero_id}",
        "id":            hero_id,
        "label":         hdef["name"],
        "name":          hdef["name"],
        "rarity":        hdef["rarity"],
        "rarity_color":  list(color),
        "is_new":        copies == 1,
        "level":         level,
        "copies":        copies,
        "needed":        None,
        "can_upgrade":   False,
        "desc":          f"Passif : {hdef['passive_name']} - {hdef['passive_desc'].split(chr(10))[0]}",
        "passive_name":  hdef["passive_name"],
        "sprite_select": hdef["sprite_select"],
    }


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
        return False, f"Pas assez de gemmes (cout : {total_cost} gemmes)"

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
        # Chance de dropper un heros a la place
        hero_drop_chance = 0.30 if rarity in ("Légendaire", "Épique") else 0.10
        if random.random() < hero_drop_chance:
            try:
                hero_res = _try_drop_hero_for_tower_chest(save_data_dict, rarity)
                if hero_res:
                    results.append(hero_res)
                    continue
            except Exception as e:
                print(f"[gacha] Erreur drop hero: {e}")

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
    sd.save(save_data_dict)
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
    sd.save(save_data_dict)
    return True, f"Tour montée au niveau {cur_lvl + 1}!"


# ─────────────────────────────────────────────────────────────────
# FONCTIONS DE SKILLTREE
# ─────────────────────────────────────────────────────────────────
