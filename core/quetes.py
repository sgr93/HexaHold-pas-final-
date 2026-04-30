"""
quetes.py
---------
Système de gestion des quêtes avec support facile pour ajouter/modifier les quêtes.
Inclut les trois sections : Quotidiennes, Missions, Événements
"""

# ============================================================
# DÉFINITION DES QUÊTES
# ============================================================
# Format : {
#   "quest_id": {
#       "nom": "Nom de la quête",
#       "description": "Description courte",
#       "section": "quotidiennes" | "missions" | "evenements",
#       "xp": 10,
#       "pieces": 50,
#       "gemmes": 0,  (optionnel, 0 par défaut)
#       "condition": lambda save, game_state -> bool
#   }
# }

QUETES = {
    # ────────────────────────────────────────────────────────────────
    # QUÊTES QUOTIDIENNES
    # ────────────────────────────────────────────────────────────────
    "quotidienne_combat_1": {
        "nom": "Combat du jour",
        "description": "Terminez 1 niveau",
        "section": "quotidiennes",
        "xp": 15,
        "pieces": 30,
        "gemmes": 0,
        "condition": lambda save, gs: save.get("daily_quests_completed", {}).get("quotidienne_combat_1", False)
    },
    "quotidienne_combat_3": {
        "nom": "Guerrier du jour",
        "description": "Terminez 3 niveaux",
        "section": "quotidiennes",
        "xp": 25,
        "pieces": 75,
        "gemmes": 0,
        "condition": lambda save, gs: save.get("daily_quests_completed", {}).get("quotidienne_combat_3", False)
    },
    "quotidienne_niveau": {
        "nom": "Augmentation de puissance",
        "description": "Montez de 1 niveau",
        "section": "quotidiennes",
        "xp": 20,
        "pieces": 50,
        "gemmes": 0,
        "condition": lambda save, gs: save.get("daily_quests_completed", {}).get("quotidienne_niveau", False)
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES MISSIONS
    # ────────────────────────────────────────────────────────────────
    "mission_niveau_5": {
        "nom": "Guerrier confirmé",
        "description": "Atteindre le niveau 5",
        "section": "missions",
        "xp": 50,
        "pieces": 200,
        "gemmes": 0,
        "condition": lambda save, game_state: save.get("level", 1) >= 5
    },
    "mission_niveau_10": {
        "nom": "Maître des combats",
        "description": "Atteindre le niveau 10",
        "section": "missions",
        "xp": 100,
        "pieces": 400,
        "gemmes": 1,
        "condition": lambda save, game_state: save.get("level", 1) >= 10
    },
    "mission_3_combats": {
        "nom": "Triple attaque",
        "description": "Remportez 3 combats",
        "section": "missions",
        "xp": 40,
        "pieces": 150,
        "gemmes": 0,
        "condition": lambda save, game_state: save.get("battles_won", 0) >= 3
    },
    "mission_5_combats": {
        "nom": "Inarrêtable",
        "description": "Remportez 5 combats",
        "section": "missions",
        "xp": 70,
        "pieces": 300,
        "gemmes": 1,
        "condition": lambda save, game_state: save.get("battles_won", 0) >= 5
    },
    "mission_premiere_tour": {
        "nom": "Constructeur",
        "description": "Placez votre première tour",
        "section": "missions",
        "xp": 10,
        "pieces": 50,
        "gemmes": 0,
        "condition": lambda save, game_state: save.get("towers_placed", 0) >= 1
    },
    "mission_10_tours": {
        "nom": "Architecte militaire",
        "description": "Placez 10 tours",
        "section": "missions",
        "xp": 60,
        "pieces": 250,
        "gemmes": 1,
        "condition": lambda save, game_state: save.get("towers_placed", 0) >= 10
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES ÉVÉNEMENTS - HISTOIRE
    # ────────────────────────────────────────────────────────────────
    "event_histoire_1": {
        "nom": "Le commencement",
        "description": "Complétez le niveau 1 en difficulté Normal",
        "section": "evenements",
        "xp": 30,
        "pieces": 100,
        "gemmes": 0,
        "condition": lambda save, game_state: save.get("events_completed", {}).get("event_histoire_1", False)
    },
    "event_histoire_2": {
        "nom": "Rencontre du boss",
        "description": "Atteignez le boss final en niveau 2",
        "section": "evenements",
        "xp": 50,
        "pieces": 200,
        "gemmes": 1,
        "condition": lambda save, game_state: save.get("events_completed", {}).get("event_histoire_2", False)
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES ÉVÉNEMENTS - GUERRE
    # ────────────────────────────────────────────────────────────────
    "event_guerre_1": {
        "nom": "Premières victimes",
        "description": "Battez 50 ennemis",
        "section": "evenements",
        "xp": 40,
        "pieces": 150,
        "gemmes": 0,
        "condition": lambda save, game_state: save.get("enemies_killed", 0) >= 50
    },
    "event_guerre_2": {
        "nom": "Carnage",
        "description": "Battez 200 ennemis",
        "section": "evenements",
        "xp": 80,
        "pieces": 400,
        "gemmes": 2,
        "condition": lambda save, game_state: save.get("enemies_killed", 0) >= 200
    },
    "event_guerre_3": {
        "nom": "Généralissime",
        "description": "Complétez le niveau 5 en difficulté Très Difficile",
        "section": "evenements",
        "xp": 100,
        "pieces": 500,
        "gemmes": 2,
        "condition": lambda save, game_state: save.get("events_completed", {}).get("event_guerre_3", False)
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES ÉVÉNEMENTS - INFINI
    # ────────────────────────────────────────────────────────────────
    "event_infini_1": {
        "nom": "Commençant l'infini",
        "description": "Atteignez la vague 10",
        "section": "evenements",
        "xp": 60,
        "pieces": 300,
        "gemmes": 1,
        "condition": lambda save, game_state: save.get("max_wave_reached", 0) >= 10
    },
    "event_infini_2": {
        "nom": "Guerrier sans fin",
        "description": "Atteignez la vague 30",
        "section": "evenements",
        "xp": 120,
        "pieces": 600,
        "gemmes": 3,
        "condition": lambda save, game_state: save.get("max_wave_reached", 0) >= 30
    },
    "event_infini_3": {
        "nom": "Légende vivante",
        "description": "Atteignez la vague 50",
        "section": "evenements",
        "xp": 200,
        "pieces": 1000,
        "gemmes": 5,
        "condition": lambda save, game_state: save.get("max_wave_reached", 0) >= 50
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES PROGRESSION PROFIL (gemmes faciles)
    # ────────────────────────────────────────────────────────────────
    "profil_niveau_5": {
        "nom": "Rang Intermédiaire",
        "description": "Atteignez le niveau 5 de profil",
        "section": "missions",
        "xp": 30,
        "pieces": 100,
        "gemmes": 5,
        "condition": lambda save, game_state: save.get("level", 1) >= 5
    },
    "profil_niveau_10": {
        "nom": "Rang Avancé",
        "description": "Atteignez le niveau 10 de profil",
        "section": "missions",
        "xp": 60,
        "pieces": 200,
        "gemmes": 15,
        "condition": lambda save, game_state: save.get("level", 1) >= 10
    },
    "profil_niveau_20": {
        "nom": "Rang Expert",
        "description": "Atteignez le niveau 20 de profil",
        "section": "missions",
        "xp": 100,
        "pieces": 400,
        "gemmes": 30,
        "condition": lambda save, game_state: save.get("level", 1) >= 20
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES MÉDAILLES CHAPITRES (récompenses gemmes)
    # ────────────────────────────────────────────────────────────────
    "ch1_toutes_etoiles": {
        "nom": "Maître de Trost",
        "description": "Obtenez toutes les étoiles du Chapitre 1",
        "section": "evenements",
        "xp": 80,
        "pieces": 300,
        "gemmes": 20,
        "condition": lambda save, game_state: all(
            save.get(f"ch1_m{i}_stars", 0) == 3 for i in range(3)
        )
    },
    "ch2_toutes_etoiles": {
        "nom": "Maître de la Forêt",
        "description": "Obtenez toutes les étoiles du Chapitre 2",
        "section": "evenements",
        "xp": 120,
        "pieces": 500,
        "gemmes": 35,
        "condition": lambda save, game_state: all(
            save.get(f"ch2_m{i}_stars", 0) == 3 for i in range(3)
        )
    },
    "ch3_toutes_etoiles": {
        "nom": "Maître d'Utgard",
        "description": "Obtenez toutes les étoiles du Chapitre 3",
        "section": "evenements",
        "xp": 160,
        "pieces": 700,
        "gemmes": 50,
        "condition": lambda save, game_state: all(
            save.get(f"ch3_m{i}_stars", 0) == 3 for i in range(3)
        )
    },
    "ch4_toutes_etoiles": {
        "nom": "Maître de Shiganshina",
        "description": "Obtenez toutes les étoiles du Chapitre 4",
        "section": "evenements",
        "xp": 200,
        "pieces": 1000,
        "gemmes": 75,
        "condition": lambda save, game_state: all(
            save.get(f"ch4_m{i}_stars", 0) == 3 for i in range(3)
        )
    },
    "ch5_toutes_etoiles": {
        "nom": "Légende de l'Humanité",
        "description": "Obtenez toutes les étoiles du Chapitre 5",
        "section": "evenements",
        "xp": 300,
        "pieces": 2000,
        "gemmes": 150,
        "condition": lambda save, game_state: all(
            save.get(f"ch5_m{i}_stars", 0) == 3 for i in range(3)
        )
    },

    # ────────────────────────────────────────────────────────────────
    # QUÊTES QUOTIDIENNES SUPPLÉMENTAIRES
    # ────────────────────────────────────────────────────────────────
    "quotidienne_gemme": {
        "nom": "Chercheur de Trésors",
        "description": "Jouez 2 niveaux en mode histoire",
        "section": "quotidiennes",
        "xp": 20,
        "pieces": 50,
        "gemmes": 2,
        "condition": lambda save, gs: save.get("daily_quests_completed", {}).get("quotidienne_gemme", False)
    },
    "quotidienne_enemies_50": {
        "nom": "Chasseur du jour",
        "description": "Tuez 50 ennemis aujourd'hui",
        "section": "quotidiennes",
        "xp": 30,
        "pieces": 80,
        "gemmes": 3,
        "condition": lambda save, gs: save.get("daily_quests_completed", {}).get("quotidienne_enemies_50", False)
    },
}


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def get_quests_by_section(section):
    """Retourne toutes les quêtes d'une section donnée."""
    return {qid: q for qid, q in QUETES.items() if q["section"] == section}




def check_quest_completion(quest_id, save, game_state=None):
    """Vérifie si une quête est complétée en fonction de sa condition."""
    if quest_id not in QUETES:
        return False
    quest = QUETES[quest_id]
    try:
        return quest["condition"](save, game_state)
    except Exception:
        return False


def mark_quest_completed(save, quest_id):
    """Marque une quête comme complétée dans les données de sauvegarde."""
    if quest_id not in save.get("quests_completed", {}):
        if "quests_completed" not in save:
            save["quests_completed"] = {}
        save["quests_completed"][quest_id] = True
    return True


def mark_daily_quest_done(save, quest_id):
    """
    Marque une quête quotidienne comme accomplie pour aujourd'hui.
    Le reset automatique est géré dans save_data.load() via _maybe_reset_daily_quests.
    """
    if "daily_quests_completed" not in save:
        save["daily_quests_completed"] = {}
    save["daily_quests_completed"][quest_id] = True


def has_quest_been_completed(save, quest_id):
    """Vérifie si une quête a déjà été complétée et récompensée."""
    return save.get("quests_completed", {}).get(quest_id, False)


def claim_quest_reward(save, quest_id):
    """Réclame la récompense d'une quête et marque comme complétée."""
    if quest_id not in QUETES:
        return False, "Quête inexistante"
    
    if has_quest_been_completed(save, quest_id):
        return False, "Quête déjà récompensée"
    
    quest = QUETES[quest_id]
    save["coins"] = save.get("coins", 0) + quest["pieces"]
    save["gems"] = save.get("gems", 0) + quest.get("gemmes", 0)

    # Ajout XP avec calcul de level-up
    xp_to_add = quest["xp"]
    save["xp"] = save.get("xp", 0) + xp_to_add
    xp_next_default = 30  # Aligné sur XP_TO_NEXT_LVL_START
    xp_growth = 2.0       # Aligné sur XP_GROWTH_FACTOR
    xp_next = save.get("xp_next", xp_next_default)
    while save["xp"] >= xp_next:
        save["xp"] -= xp_next
        save["level"] = save.get("level", 1) + 1
        save["skill_points"] = save.get("skill_points", 0) + 1
        save["pending_skillpoint_anim"] = True
        xp_next = int(xp_next * xp_growth)
    save["xp_next"] = xp_next
    
    mark_quest_completed(save, quest_id)
    
    return True, quest


def get_available_quests(save, game_state=None):
    """Retourne les quêtes disponibles (complétées et non récompensées)."""
    available = {}
    for quest_id, quest in QUETES.items():
        if not has_quest_been_completed(save, quest_id):
            is_completed = check_quest_completion(quest_id, save, game_state)
            if is_completed:
                available[quest_id] = quest
    return available


def get_quest_progress(save, quest_id):
    """Retourne l'état de progression d'une quête."""
    is_completed = check_quest_completion(quest_id, save)
    is_claimed = has_quest_been_completed(save, quest_id)
    
    return {
        "completed": is_completed,
        "claimed": is_claimed,
        "available": is_completed and not is_claimed
    }