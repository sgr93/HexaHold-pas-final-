"""
save_skills.py
--------------
Arbre de competences : points, deblocage, bonus appliques au joueur.
Extrait de save_data.py.
"""
import core.save_data as sd

def add_skill_points(save_data_dict, amount):
    """Ajoute des points de compétence au joueur."""
    save_data_dict["skill_points"] = save_data_dict.get("skill_points", 0) + amount
    sd.save(save_data_dict)


def can_unlock_skill(save_data_dict, skill_id):
    """
    Vérifie si une compétence peut être acquise.
    Retourne (can_unlock, error_message).
    """
    if skill_id not in sd.SKILLS:
        return False, "Compétence inexistante"
    
    skill = sd.SKILLS[skill_id]
    
    # Vérifier si déjà acquise
    if save_data_dict.get("skills_unlocked", {}).get(skill_id, False):
        return False, "Compétence déjà acquise"
    
    # Vérifier les points de skill
    if save_data_dict.get("skill_points", 0) < skill["cost"]:
        return False, f"Pas assez de points ({save_data_dict.get('skill_points', 0)}/{skill['cost']})"
    
    # Vérifier les dépendances
    for req_id in skill.get("requires", []):
        if not save_data_dict.get("skills_unlocked", {}).get(req_id, False):
            req_skill = sd.SKILLS.get(req_id, {})
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
    
    skill = sd.SKILLS[skill_id]
    save_data_dict["skill_points"] -= skill["cost"]
    
    if "skills_unlocked" not in save_data_dict:
        save_data_dict["skills_unlocked"] = {}
    
    save_data_dict["skills_unlocked"][skill_id] = True
    sd.save(save_data_dict)
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
        if is_unlocked and skill_id in sd.SKILLS:
            skill = sd.SKILLS[skill_id]
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

    # Appliquer aussi les bonus du NOUVEAU skill tree (talents_screen — skill_tree_nodes)
    apply_skill_tree_node_bonuses(save_data_dict, player)


# ─────────────────────────────────────────────────────────────────
# NOUVEAU SYSTÈME — BONUS NODES DU SKILL TREE (talents_screen.py)
# ─────────────────────────────────────────────────────────────────

# Mapping des effets de chaque nœud par personnage
# index du nœud → dict de bonus appliqués au joueur/tours
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
        {},                                                    # 9 ULTIME (géré séparément)
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
        {},                                                    # 9 ULTIME (géré séparément)
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
        {},                                                    # 9 ULTIME (géré séparément)
    ],
}


def apply_skill_tree_node_bonuses(save_data_dict, player):
    """
    Lit skill_tree_nodes (nouveau système, talents_screen.py) et applique
    les bonus correspondants sur l'objet player.
    Les bonus tours (tower_damage_pct, etc.) sont stockés dans save pour
    être lus par game.py au moment du placement.
    """
    nodes_by_char = save_data_dict.get("skill_tree_nodes", {})
    if not nodes_by_char:
        return

    # Réinitialiser les bonus de tours dans la save pour éviter les doublons
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

            # ── Bonus joueur directs ──
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

            # ── Bonus tours / économie stockés dans save ──
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
    Retourne un dict résumant tous les bonus actifs du skill tree (nouveau système).
    Utilisé par game.py pour les tours et l'économie.
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
    Retourne la competence ultime du personnage choisi.
    Disponible uniquement si le noeud 10 (index 9) du skill tree est debloque.
    """
    ULTIMATES = {
        "eren":   {"name": "Titan Assaillant",     "cooldown": 45},
        "mikasa": {"name": "Lame d'Ackerman",       "cooldown": 40},
        "erwin":  {"name": "Charge du Bataillon",   "cooldown": 50},
    }
    locked_char = save_data_dict.get("skill_tree_locked")
    if not locked_char:
        return None

    # Vérifier que le noeud 10 (index 9) est bien débloqué
    nodes_by_char = save_data_dict.get("skill_tree_nodes", {})
    unlocked = nodes_by_char.get(locked_char, [])
    if 9 not in unlocked:
        return None

    ult = ULTIMATES.get(locked_char)
    if ult:
        return {"char": locked_char, **ult}
    return None