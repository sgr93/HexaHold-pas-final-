"""
save_skills.py
--------------
Arbre de compétences : bonus des nodes appliqués au joueur et aux tours.
"""
import core.save_data as sd

# bonus de chaque node par personnage —
# l'index correspond à la position du node dans l'arbre affiché à l'écran
_NODE_BONUSES = {
    "eren": [
        {"damage": 3},                                          # 0 Rage
        {"crit_chance": 0.20},                                 # 1 Instinct
        {"crit_damage": 0.20},                                 # 2 Furie
        {"max_hp": 15, "hp_regen": 0.2},                       # 3 Endurance
        {"crit_damage": 0.20},                                 # 4 Tranche
        {"damage": 7, "crit_chance": 0.08, "attack_cd": -5},  # 5 Berserker
        {"speed": 0.5},                                        # 6 Esquive
        {"damage": 4, "attack_cd": -2},                        # 7 Percée
        {"defense": 0.08, "max_hp": 20},                       # 8 Acier
        {},                                                    # 9 ULTIME
    ],
    "mikasa": [
        {"speed": 0.5},                                        # 0 Rapidité
        {"crit_chance": 0.10},                                 # 1 Précision
        {"speed": 2.0},                                        # 2 Acrobatie
        {"damage": 4, "crit_damage": 0.03},                    # 3 Tranchant
        {"crit_damage": 0.10},                                 # 4 Asiatique
        {"attack_cd": -1, "speed": 1.0, "crit_damage": 0.25}, # 5 Ackerman
        {"damage": 3, "speed": 1.0},                           # 6 Fulgurance
        {"attack_cd": -2, "damage": 2},                        # 7 Ombre
        {"max_hp": 20, "defense": 0.05},                       # 8 Résistance
        {},                                                    # 9 ULTIME
    ],
    "erwin": [
        {"tower_damage_pct": 0.06},                            # 0 Tactique
        {"coin_bonus_pct": 0.08},                              # 1 Logistique
        {"tower_damage_pct": 0.08, "tower_range_pct": 0.05},  # 2 Formation
        {"trap_damage_pct": 0.12},                             # 3 Embuscade
        {"coin_bonus_pct": 0.12},                              # 4 Ravitaillement
        {"tower_damage_pct": 0.12, "tower_cd_pct": -0.08,
         "tower_range_pct": 0.10},                             # 5 Commandant
        {"trap_cd_pct": -0.10, "trap_damage_pct": 0.08},      # 6 Piège++
        {"xp_bonus_pct": 0.15},                               # 7 XP+
        {"max_hp": 25, "defense": 0.08},                       # 8 Forteresse
        {},                                                    # 9 ULTIME
    ],
}


def apply_skill_tree_node_bonuses(save_data_dict, player):
    """
    Lit les nodes débloqués dans skill_tree_nodes et applique les bonus sur le joueur.
    Les bonus qui concernent les tours sont stockés dans la save pour être
    lus par game.py au moment où une tour est posée.
    """
    nodes_by_char = save_data_dict.get("skill_tree_nodes", {})
    if not nodes_by_char:
        return

    # on remet à zéro les bonus de tours à chaque recalcul pour éviter
    # qu'ils s'accumulent si la fonction est appelée plusieurs fois
    save_data_dict.setdefault("tree_tower_damage_pct", 0.0)
    save_data_dict.setdefault("tree_tower_range_pct",  0.0)
    save_data_dict.setdefault("tree_tower_cd_pct",     0.0)
    save_data_dict.setdefault("tree_trap_damage_pct",  0.0)
    save_data_dict.setdefault("tree_trap_cd_pct",      0.0)
    save_data_dict.setdefault("tree_coin_bonus_pct",   0.0)
    save_data_dict.setdefault("tree_xp_bonus_pct",     0.0)

    for cid, unlocked_indices in nodes_by_char.items():
        char_bonuses = _NODE_BONUSES.get(cid, [])
        for node_idx in unlocked_indices:
            if node_idx >= len(char_bonuses):
                continue
            bn = char_bonuses[node_idx]

            # bonus directs sur le joueur
            if "damage" in bn:
                player.damage += bn["damage"]
            if "speed" in bn:
                player.speed += bn["speed"]
            if "max_hp" in bn:
                player.max_hp += bn["max_hp"]
                player.hp     += bn["max_hp"]
            if "hp_regen" in bn:
                player.hp_regen = getattr(player, "hp_regen", 0) + bn["hp_regen"]
            if "attack_cd" in bn:
                player.attack_cooldown = max(5, player.attack_cooldown + bn["attack_cd"])
            if "crit_chance" in bn:
                player.crit_chance = min(0.95, player.crit_chance + bn["crit_chance"])
            if "crit_damage" in bn:
                player.crit_damage = getattr(player, "crit_damage", 1.5) + bn["crit_damage"]
            if "defense" in bn:
                player.defense = min(0.80, player.defense + bn["defense"])

            # bonus tours et économie — stockés dans la save, lus plus tard par game.py
            if "tower_damage_pct" in bn:
                save_data_dict["tree_tower_damage_pct"] += bn["tower_damage_pct"]
            if "tower_range_pct" in bn:
                save_data_dict["tree_tower_range_pct"]  += bn["tower_range_pct"]
            if "tower_cd_pct" in bn:
                save_data_dict["tree_tower_cd_pct"]     += bn["tower_cd_pct"]
            if "trap_damage_pct" in bn:
                save_data_dict["tree_trap_damage_pct"]  += bn["trap_damage_pct"]
            if "trap_cd_pct" in bn:
                save_data_dict["tree_trap_cd_pct"]      += bn["trap_cd_pct"]
            if "coin_bonus_pct" in bn:
                save_data_dict["tree_coin_bonus_pct"]   += bn["coin_bonus_pct"]
            if "xp_bonus_pct" in bn:
                save_data_dict["tree_xp_bonus_pct"]     += bn["xp_bonus_pct"]


def get_skill_tree_node_bonuses(save_data_dict):
    """
    Retourne tous les bonus actifs liés aux tours et à l'économie.
    Appelé par game.py quand une tour est posée ou qu'une vague se termine.
    """
    return {
        "tower_damage_pct": save_data_dict.get("tree_tower_damage_pct", 0.0),
        "tower_range_pct":  save_data_dict.get("tree_tower_range_pct",  0.0),
        "tower_cd_pct":     save_data_dict.get("tree_tower_cd_pct",     0.0),
        "trap_damage_pct":  save_data_dict.get("tree_trap_damage_pct",  0.0),
        "trap_cd_pct":      save_data_dict.get("tree_trap_cd_pct",      0.0),
        "coin_bonus_pct":   save_data_dict.get("tree_coin_bonus_pct",   0.0),
        "xp_bonus_pct":     save_data_dict.get("tree_xp_bonus_pct",     0.0),
    }


def get_active_ultimate(save_data_dict):
    """
    Retourne l'ultime du personnage choisi si le dernier node (index 9) est débloqué.
    Chaque personnage a son propre ultime avec un cooldown différent.
    """
    ULTIMATES = {
        "eren":   {"name": "Titan Assaillant",   "cooldown": 45},
        "mikasa": {"name": "Lame d'Ackerman",     "cooldown": 40},
        "erwin":  {"name": "Charge du Bataillon", "cooldown": 50},
    }
    locked_char = save_data_dict.get("skill_tree_locked")
    if not locked_char:
        return None

    nodes_by_char = save_data_dict.get("skill_tree_nodes", {})
    unlocked      = nodes_by_char.get(locked_char, [])
    if 9 not in unlocked:
        return None

    ult = ULTIMATES.get(locked_char)
    if ult:
        return {"char": locked_char, **ult}
    return None