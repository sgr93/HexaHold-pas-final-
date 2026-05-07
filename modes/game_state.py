"""
modes/game_state.py
-------------------
État initial du jeu, gestion des vagues, objectifs de mission,
quêtes et récompense de victoire.
"""
import re
import time
import random

from core.config import (
    ALL_TOWER_TYPES,
    AVAILABLE_TOWERS_INIT,
    BOSS_DURATION,
    DANGER_WEIGHT,
    DIFFICULTY_LEVELS,
    END,
    GRID_SIZE,
    LEVEL_START,
    PLAYER_HP_REGEN,
    START,
    TOWER_SLOT_COUNT,
    WAVE_DURATION,
    WAVE_NUMBER_START,
    XP_GROWTH_FACTOR,
    XP_START,
    XP_TO_NEXT_LVL_START,
)
import ui.render as render
from core.grid import Grid
from core.entities import Player, Goal
from core.walls import apply_map_walls
import core.save_data as sd
import core.quetes as quetes
import modes.histoire as hist_mod
import core.heroes as _hm


# ============================================================
# HELPERS TOURS
# ============================================================

def pick_levelup_choices(available_towers, count=3):
    """Retourne `count` options aléatoires parmi les tours disponibles."""
    options = list(available_towers)
    random.shuffle(options)
    choices = []
    for option in options:
        if option not in choices:
            choices.append(option)
        if len(choices) == count:
            break
    return choices


def pick_starting_tower_choices(loadout, count=3):
    """Retourne `count` tours aléatoires parmi le loadout de départ."""
    choices = list(loadout)
    if len(choices) < count:
        choices = list(loadout) + list(ALL_TOWER_TYPES)
    random.shuffle(choices)
    unique = []
    for option in choices:
        if option not in unique:
            unique.append(option)
        if len(unique) == count:
            break
    return unique


def _make_known_towers(save):
    if not save:
        return set(ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
    loadout = save.get("tower_loadout", []) or AVAILABLE_TOWERS_INIT
    return set(loadout[:TOWER_SLOT_COUNT])


# ============================================================
# HELPERS SESSION
# ============================================================

def _resume_from_pause(gs, pause_start):
    """Recale tous les timers après une pause et retourne None."""
    if pause_start is not None:
        paused_duration = time.time() - pause_start
        gs["last_wave_time"]   += paused_duration
        gs["last_enemy_spawn"] += paused_duration
        gs["last_regen_time"]  += paused_duration
        if gs["boss_start_time"] > 0:
            gs["boss_start_time"] += paused_duration
    return None


def _init_new_game(chosen_level, current_save, grid_cache):
    """Construit l'état initial et initialise le level-up de départ."""
    gs = build_initial_state(chosen_level, current_save)
    grid_cache.invalidate()
    gs["levelup_pending"] = True
    loadout = (gs.get("save") or {}).get("tower_loadout", []) or AVAILABLE_TOWERS_INIT
    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
    return gs


def _inject_mission_context(gs, chosen_level, current_save):
    """Injecte le mission_context dans gs si chosen_level est un dict histoire."""
    if not isinstance(chosen_level, dict) or chosen_level.get("infinite"):
        return
    ch_idx = chosen_level.get("chapter", 0)
    m_idx  = chosen_level.get("mission", 0)
    gs["mission_context"] = {
        "chapter":    ch_idx,
        "mission":    m_idx,
        "objectives": hist_mod.get_mission_objectives(ch_idx, m_idx),
        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
    }


# ============================================================
# VAGUES
# ============================================================

def start_new_wave(state):
    """Prépare la vague suivante à partir d'un dict d'état partiel."""
    state["wave_number"]              += 1
    state["last_wave_time"]            = time.time()
    state["last_enemy_spawn"]          = time.time()
    state["mobs_killed_this_wave"]     = 0
    state["enemies_spawned_this_wave"] = 0
    if state.get("infinite_mode"):
        # Mode infini : nombre d'ennemis augmente de 1 par vague
        state["max_enemies_this_wave"] = 8 + (state["wave_number"] - 1)  # Commence à 8, +1 par vague
    else:
        state["max_enemies_this_wave"] = 5 + state["wave_number"] * 2
    state["boss_active"]               = False
    state["wave_timer"]                = WAVE_DURATION
    state["boss_timer"]                = BOSS_DURATION


# ============================================================
# ÉTAT INITIAL
# ============================================================

def build_initial_state(difficulty=2, save=None):
    """
    Crée l'état initial complet du jeu selon la difficulté choisie.
    difficulty peut être un int ou un dict {chapter, mission, difficulty}.
    """
    chapter  = None
    mission  = None
    infinite = False
    if isinstance(difficulty, dict):
        chapter    = difficulty.get("chapter")
        mission    = difficulty.get("mission")
        infinite   = difficulty.get("infinite", False)
        difficulty = difficulty.get("difficulty", 2)

    diff_info      = DIFFICULTY_LEVELS.get(difficulty, DIFFICULTY_LEVELS[2])
    max_waves      = diff_info["waves"] if not infinite else 9999
    spawn_interval = diff_info["spawn_interval"]
    hp_mult        = diff_info["enemy_hp_mult"]

    towers      = []
    projectiles = []
    enemies     = []

    grid = Grid(towers_ref=towers, danger_weight=DANGER_WEIGHT)
    grid.recompute()

    goal   = Goal(*END)
    player = Player(
        START[0] * GRID_SIZE + GRID_SIZE // 2,
        START[1] * GRID_SIZE + GRID_SIZE // 2,
    )

    if save:
        equipped = save.get("equipped", {})
        inv      = save.get("inventory_equipment", [])
        for slot, idx in equipped.items():
            if idx is not None and 0 <= idx < len(inv):
                item = inv[idx]
                stat = item["stat"]
                val  = item["value"]
                if stat == "max_hp":
                    player.max_hp += val
                    player.hp     += val
                elif stat == "attack_speed":
                    player.attack_cooldown = max(5, player.attack_cooldown - val)
                elif stat == "speed":
                    player.speed += val
                elif stat == "damage":
                    player.damage += val

    apply_map_walls(grid, chapter=chapter, mission=mission, infinite=infinite)
    grid.recompute()

    tileset_chapter = chapter if chapter is not None else 1
    render.load_tileset(chapter=tileset_chapter)

    selected_hero = _hm.get_selected_hero(save) if save else "eren"
    _hm.init_heroes_save(save)

    if save:
        hero_stats     = _hm.get_hero_ingame_stats(save, selected_hero)
        player.damage  = hero_stats["atk"]
        player.max_hp  = hero_stats["hp"]
        player.hp      = hero_stats["hp"]
        sd.apply_skill_bonuses_to_player(save, player)

    player.load_hero_sprite(selected_hero)

    ultimate_info = sd.get_active_ultimate(save) if save else None
    goal_hp = 100
    goal.hp = goal_hp

    return {
        "level":                     LEVEL_START,
        "xp":                        XP_START,
        "xp_to_next_level":          XP_TO_NEXT_LVL_START,
        "game_started":              False,
        "paused":                    False,
        "game_over":                 False,
        "game_win":                  False,
        "player_buff_tokens":        0,
        "tower_damage_bonus":        0,
        "tower_cooldown_bonus":      0,
        "inventory":                 {},
        "selected_item":             None,
        "wave_number":               WAVE_NUMBER_START,
        "max_waves":                 max_waves,
        "wave_timer":                WAVE_DURATION,
        "last_wave_time":            time.time(),
        "boss_active":               False,
        "boss_timer":                BOSS_DURATION,
        "boss_start_time":           0,
        "enemies_spawned_this_wave": 0,
        "max_enemies_this_wave":     5 + WAVE_NUMBER_START * 2,
        "mobs_killed_this_wave":     0,
        "last_enemy_spawn":          time.time(),
        "enemy_spawn_interval":      spawn_interval,
        "enemy_hp_mult":             hp_mult,
        "infinite_mode":             infinite,
        "towers":                    towers,
        "projectiles":               projectiles,
        "enemies":                   enemies,
        "grid":                      grid,
        "goal":                      goal,
        "player":                    player,
        "levelup_pending":           False,
        "levelup_choices":           [],
        "levelup_rects":             [],
        "regen_accumulator":         0.0,
        "last_regen_time":           time.time(),
        "difficulty":                difficulty,
        "coins_reward":              diff_info["coins_reward"],
        "reward_collected":          False,
        "goal_max_hp":               goal_hp,
        "infinite_mode":             infinite,
        "infinite_wave_reward_done": set(),
        "save":                      save,
        "toasts":                    [],
        "mission_context":           None,
        "mission_complete_shown":    False,
        "skillpoint_anim_timer":     0,
        "selected_hero":             selected_hero,
        "armin_buff_stacks":         0,
        "sasha_towers_given":        set(),
        "ultimate_info":             ultimate_info,
        "ultimate_cooldown_max":     ultimate_info["cooldown"] if ultimate_info else 0,
        "ultimate_cooldown":         0,
        "ultimate_active":           False,
        "ultimate_timer":            0,
    }


# ============================================================
# OBJECTIFS DE MISSION
# ============================================================

def evaluate_mission_objectives(gs):
    """
    Évalue les objectifs de la mission en cours et met à jour objective["done"].
    Appelée à chaque frame (légère car pas d'I/O).
    """
    mc = gs.get("mission_context")
    if not mc:
        return
    for obj in mc["objectives"]:
        if obj.get("done"):
            continue
        text = obj["text"].lower()

        if "survivre" in text and "vague" in text:
            m = re.search(r"(\d+)", text)
            if m and (gs.get("wave_number", 1) > int(m.group(1)) or gs.get("game_win", False)):
                obj["done"] = True

        elif "ne pas perdre" in text and "pv" in text:
            m = re.search(r"(\d+)", text)
            player = gs.get("player")
            if m and player and player.max_hp - player.hp <= int(m.group(1)):
                obj["done"] = True

        elif "tous ses pv" in text or "tous les pv" in text:
            player = gs.get("player")
            if player and gs.get("game_win") and player.hp >= player.max_hp:
                obj["done"] = True

        elif "placer" in text and "tour" in text:
            m = re.search(r"(\d+)", text)
            if m:
                towers = [t for t in gs.get("towers", []) if hasattr(t, "tower_type")]
                if len(towers) >= int(m.group(1)):
                    obj["done"] = True

        elif any(w in text for w in ("éliminer", "tuer", "battez")):
            m = re.search(r"(\d+)", text)
            if m and gs.get("save"):
                kills_total    = gs["save"].get("enemies_killed", 0)
                kills_at_start = mc.get("enemies_killed_at_start", 0)
                if kills_total - kills_at_start >= int(m.group(1)):
                    obj["done"] = True

        elif "vaincre" in text and "boss" in text:
            if gs.get("game_win", False):
                obj["done"] = True

        elif any(w in text for w in ("terminer", "compléter", "survivre")) and gs.get("game_win"):
            obj["done"] = True


# ============================================================
# QUÊTES
# ============================================================

def check_and_notify_quests(gs):
    save = gs.get("save")
    if save is None:
        return
    # Persister dans la save plutôt que dans gs
    notified = save.setdefault("quests_notified", [])

    for q_id, quest in quetes.QUETES.items():
        if q_id in notified:
            continue
        if save.get("quests_completed", {}).get(q_id, False):
            notified.append(q_id)
            continue
        if quetes.check_quest_completion(q_id, save, gs):
            notified.append(q_id)
            gs["toasts"].append({
                "text":    f"Quête: {quest['nom']} !",
                "ttl":     300,
                "max_ttl": 300,
                "color":   (255, 215, 0),
            })
    sd.save(save)

# ============================================================
# RÉCOMPENSE VICTOIRE
# ============================================================

def collect_win_reward(gs):
    """Distribue XP/coins/quêtes à la victoire (une seule fois)."""
    if gs.get("reward_collected") or gs.get("save") is None:
        return
    save = gs["save"]
    save["coins"]       = save.get("coins", 0) + gs["coins_reward"]
    save["battles_won"] = save.get("battles_won", 0) + 1
    _mode_key = "infini" if gs.get("infinite_mode") else "histoire"
    save[f"{_mode_key}_battles_won"] = save.get(f"{_mode_key}_battles_won", 0) + 1

    if not gs.get("infinite_mode") and gs.get("mission_context") is None:
        _diff_done = save.get("difficulty_completed", [])
        _cur_diff  = gs.get("difficulty", 2)
        if _cur_diff not in _diff_done:
            _diff_done.append(_cur_diff)
            save["difficulty_completed"] = _diff_done

    gs["reward_collected"] = True

    xp_gain    = gs["coins_reward"] // 2
    save["xp"] = save.get("xp", 0) + xp_gain
    xp_next    = save.get("xp_next", 30)
    while save["xp"] >= xp_next:
        save["xp"]          -= xp_next
        save["level"]        = save.get("level", 1) + 1
        save["skill_points"] = save.get("skill_points", 0) + 1
        save["pending_skillpoint_anim"] = True
        xp_next = int(xp_next * XP_GROWTH_FACTOR)
    save["xp_next"] = xp_next

    quetes.mark_daily_quest_done(save, "quotidienne_combat_1")
    if save.get("battles_won", 0) % 3 == 0:
        quetes.mark_daily_quest_done(save, "quotidienne_combat_3")

    check_and_notify_quests(gs)
    sd.save(save)