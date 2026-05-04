"""
game.py
-------
Boucle de jeu principale
"""
import math
import os
import time
import random
import pygame
from core.config import (
    COLS, ROWS, GRID_SIZE, GRID_WIDTH, GRID_HEIGHT, START, END, SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, LEVEL_START, XP_START, XP_TO_NEXT_LVL_START, XP_GROWTH_FACTOR, XP_REWARD_NORMAL, XP_REWARD_BOSS, WAVE_NUMBER_START, WAVE_DURATION, BOSS_DURATION, DANGER_WEIGHT, BACKGROUND_COLOR, DIFFICULTY_LEVELS, PLAYER_HP_REGEN, MUSIC_PATH, MUSIC_TRACK_TITLE, MUSIC_TRACK_MENU, MUSIC_TRACK_GAME, INV_BAR_HEIGHT, ALL_TOWER_TYPES, TOWER_SLOT_COUNT, TOWER_MAX_LEVEL,
)
import ui.render as render
from ui.render import GridCache
from core.grid import Grid
from core.entities import Player, Goal, Enemy, Tower, Trap, Projectile
from ui.ui import (
    draw_hud, draw_ghost, draw_inventory, draw_pause_screen, draw_gameover_screen, draw_start_hint, draw_levelup_banner, draw_toasts, draw_pause_button, draw_mission_objectives, draw_mission_complete_screen, draw_mission_failed_screen, draw_skillpoint_anim,
)
from core.walls import apply_map_walls
import core.save_data as sd
import core.quetes as quetes
import modes.histoire as hist_mod
from modes.histoire import run_histoire
from modes.game_towers import (
    make_can_place, _is_matching_upgrade_target, cells_for_item, place_tower_on_grid, apply_tower_bonuses, apply_all_tower_bonuses,
)
from modes.game_music import (
    _find_music_file, play_music, play_title_music, play_menu_music, play_game_music,
)
from modes.game_passives import (
    _apply_eren_passive, _apply_armin_passive_on_build, _apply_sasha_passive_on_wave, _apply_levi_passive_on_upgrade, _apply_mikasa_passive, _draw_eren_passive_zone, _get_ultimate_duration, _apply_ultimate_start, _apply_ultimate_end,
)
from modes.game_infinite import (
    _give_infinite_rewards, _collect_infinite_loot, _draw_infinite_loot_popup, _draw_ultimate_button,
)
import core.heroes as _hm
import re
from core.config import ALL_TOWER_TYPES
from modes.title_screen import run_title_screen
from modes.main_ui import run_main_ui
from ui.ui import draw_levelup_banner

# Seuils de sauvegarde : on ne sauvegarde qu'en fin de vague, pas à chaque kill
_DIRTY_SAVE = False   # True = save nécessaire, effectuée en fin de frame sûre




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


# ============================================================
# VAGUES / ETAT INITIAL
# ============================================================

def start_new_wave(state):
    """
    Prépare la vague suivante à partir d'un dict d'état partiel.
    """
    state["wave_number"]              += 1
    state["last_wave_time"]            = time.time()
    state["last_enemy_spawn"]          = time.time()
    state["mobs_killed_this_wave"]     = 0
    state["enemies_spawned_this_wave"] = 0
    state["max_enemies_this_wave"]     = 5 + state["wave_number"] * 2
    state["boss_active"]               = False
    state["wave_timer"]                = WAVE_DURATION
    state["boss_timer"]                = BOSS_DURATION


def build_initial_state(difficulty=2, save=None):
    """
    Crée l'état initial complet du jeu selon la difficulté choisie.
    difficulty peut être un int (difficulté classique) ou un dict {chapter, mission, difficulty}
    provenant du mode histoire.
    """
    # Extraire chapitre/mission/difficulté si mode histoire
    chapter  = None
    mission  = None
    infinite = False
    if isinstance(difficulty, dict):
        chapter  = difficulty.get("chapter")
        mission  = difficulty.get("mission")
        infinite = difficulty.get("infinite", False)
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

    # Bonus d'équipement
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

    # Inventaire initial : vide au début du niveau
    inventory = {}

    # Murs de la carte (spécifiques au chapitre/mission si mode histoire,
    # ou map dédiée pour le mode infini)
    apply_map_walls(grid, chapter=chapter, mission=mission, infinite=infinite)
    grid.recompute()

    # Tileset visuel : ch1 pour mode histoire, infini et parties rapides
    # (textures cohérentes sur tous les modes)
    tileset_chapter = chapter if chapter is not None else 1
    render.load_tileset(chapter=tileset_chapter)

    # Heros selectionne et passif
    selected_hero = _hm.get_selected_hero(save) if save else "eren"
    _hm.init_heroes_save(save)

    # Appliquer les stats ATK/HP du heros selon son niveau (doublons)
    if save:
        hero_stats = _hm.get_hero_ingame_stats(save, selected_hero)
        # On remplace les stats de base du joueur par celles du heros
        player.damage  = hero_stats["atk"]
        player.max_hp  = hero_stats["hp"]
        player.hp      = hero_stats["hp"]

    # Appliquer les bonus du skill tree sur le joueur (après équipements)
    if save:
        sd.apply_skill_bonuses_to_player(save, player)

    # Charger le sprite du heros selectionne
    player.load_hero_sprite(selected_hero)

    # Compétence ultime (nœud 9 débloqué)
    ultimate_info = sd.get_active_ultimate(save) if save else None

    # HP de la base : constants, la difficulté joue sur les ennemis pas sur la base
    goal_hp = 100
    goal.hp = goal_hp

    return {
        # Progression
        "level":                    LEVEL_START,
        "xp":                       XP_START,
        "xp_to_next_level":         XP_TO_NEXT_LVL_START,

        # Etat de jeu
        "game_started":             False,
        "paused":                   False,
        "game_over":                False,
        "game_win":                 False,

        # Inventaire tours / buffs
        "player_buff_tokens":       0,
        "tower_damage_bonus":       0,
        "tower_cooldown_bonus":     0,
        "inventory":                inventory,
        "selected_item":            None,

        # Vagues
        "wave_number":              WAVE_NUMBER_START,
        "max_waves":                max_waves,
        "wave_timer":               WAVE_DURATION,
        "last_wave_time":           time.time(),
        "boss_active":              False,
        "boss_timer":               BOSS_DURATION,
        "boss_start_time":          0,
        "enemies_spawned_this_wave": 0,
        "max_enemies_this_wave":    5 + WAVE_NUMBER_START * 2,
        "mobs_killed_this_wave":    0,
        "last_enemy_spawn":         time.time(),
        "enemy_spawn_interval":     spawn_interval,
        "enemy_hp_mult":            hp_mult,

        # Entités
        "towers":                   towers,
        "projectiles":              projectiles,
        "enemies":                  enemies,
        "grid":                     grid,
        "goal":                     goal,
        "player":                   player,

        # Level-up banner
        "levelup_pending":          False,
        "levelup_choices":          [],
        "levelup_rects":            [],

        # Regen HP
        "regen_accumulator":        0.0,
        "last_regen_time":          time.time(),

        # Difficulté
        "difficulty":               difficulty,
        "coins_reward":             diff_info["coins_reward"],
        "reward_collected":          False,
        "goal_max_hp":              goal_hp,
        "infinite_mode":            infinite,
        "infinite_wave_reward_done": set(),  # vagues déjà récompensées

        # Référence save
        "save":                     save,
        "toasts":                   [],

        # Contexte mission histoire (None si hors mode histoire)
        "mission_context":          None,
        "mission_complete_shown":   False,

        # Animation skill point gagné
        "skillpoint_anim_timer":    0,

        # Heros
        "selected_hero":            selected_hero,
        "armin_buff_stacks":        0,
        "sasha_towers_given":       set(),

        # Competence ultime
        "ultimate_info":            ultimate_info,
        "ultimate_cooldown_max":    ultimate_info["cooldown"] if ultimate_info else 0,
        "ultimate_cooldown":        0,               # 0 = prête, >0 = en recharge (secondes)
        "ultimate_active":          False,
        "ultimate_timer":           0,               # durée restante de l'effet actif
    }


# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

def _make_known_towers(save):
    if not save:
        return set(ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
    loadout = save.get("tower_loadout", []) or ALL_TOWER_TYPES
    return set(loadout[:TOWER_SLOT_COUNT])


def _evaluate_mission_objectives(gs):
    """
    Évalue les objectifs de la mission en cours et met à jour objective["done"].
    Appelée à chaque frame (légère car pas d'I/O).
    """
    mc = gs.get("mission_context")
    if not mc:
        return
    objs = mc["objectives"]

    for obj in objs:
        if obj.get("done"):
            continue
        text = obj["text"].lower()

        # "Survivre à N vagues"
        if "survivre" in text and "vague" in text:
            m = re.search(r"(\d+)", text)
            if m and (gs.get("wave_number", 1) > int(m.group(1)) or gs.get("game_win", False)):
                obj["done"] = True

        # "Ne pas perdre plus de N PV"
        elif "ne pas perdre" in text and "pv" in text:
            m = re.search(r"(\d+)", text)
            player = gs.get("player")
            if m and player:
                if player.max_hp - player.hp <= int(m.group(1)):
                    obj["done"] = True

        # "Finir avec tous ses PV"
        elif "tous ses pv" in text or "tous les pv" in text:
            player = gs.get("player")
            if player and gs.get("game_win") and player.hp >= player.max_hp:
                obj["done"] = True

        # "Placer N tours"
        elif "placer" in text and "tour" in text:
            m = re.search(r"(\d+)", text)
            if m:
                towers = [t for t in gs.get("towers", []) if hasattr(t, "tower_type")]
                if len(towers) >= int(m.group(1)):
                    obj["done"] = True

        # "Éliminer / Tuer N ennemis"
        # BUG4 FIX : comparer les kills depuis le début de la mission,
        # pas le total cumulé depuis le début du compte.
        elif any(w in text for w in ("éliminer", "tuer", "battez")):
            m = re.search(r"(\d+)", text)
            if m and gs.get("save"):
                kills_total = gs["save"].get("enemies_killed", 0)
                kills_at_start = mc.get("enemies_killed_at_start", 0)
                if kills_total - kills_at_start >= int(m.group(1)):
                    obj["done"] = True

        # "Vaincre le boss"
        elif "vaincre" in text and "boss" in text:
            if gs.get("game_win", False):
                obj["done"] = True

        # Victoire générale
        elif any(w in text for w in ("terminer", "compléter", "survivre")) and gs.get("game_win"):
            obj["done"] = True


def _check_and_notify_quests(gs):
    """
    Vérifie les quêtes nouvellement complétées et émet des toasts.
    Utilise gs["quests_notified"] pour ne jamais afficher deux fois le même toast.
    NE sauvegarde PAS sur disque — la sauvegarde est faite en dehors des boucles chaudes.
    """
    save = gs.get("save")
    if save is None:
        return
    # Set en mémoire : quêtes déjà notifiées cette session (reset à chaque nouvelle partie)
    notified = gs.setdefault("quests_notified", set())

    for q_id, quest in quetes.QUETES.items():
        if q_id in notified:
            continue
        if save.get("quests_completed", {}).get(q_id, False):
            # Déjà réclamée — on marque notifiée pour ne plus la re-checker
            notified.add(q_id)
            continue
        if quetes.check_quest_completion(q_id, save, gs):
            notified.add(q_id)
            gs["toasts"].append({
                "text": f"Quête: {quest['nom']} !",
                "ttl": 300,
                "max_ttl": 300,
                "color": (255, 215, 0)
            })



def main():
    render.init_pygame()
    # Chargement des sprites optionnels (silencieux si les fichiers sont absents)
    render.load_wall_image()
    Tower.load_sprites()
    Trap.load_sprites()
    # Préchargement des sprites de projectiles (silencieux si fichiers absents)
    for _pt in ALL_TOWER_TYPES + ["player"]:
        Projectile._load_sprite(_pt)


    current_save = sd.load()
    play_title_music(current_save.get("music_volume", 0.8))

    # Ecran titre
    title_result, current_save = run_title_screen(render.screen, render.clock, current_save)
    if title_result != "play":
        pygame.quit()
        return

    # Interface principale (barre de navigation)
    play_menu_music(current_save.get("music_volume", 0.8))
    chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
    if chosen_level is None:
        pygame.quit()
        return

    # Musique de jeu
    play_game_music(current_save.get("music_volume", 0.8))

    grid_cache = GridCache()
    gs         = build_initial_state(chosen_level, current_save)
    grid_cache.invalidate()

    # Si on vient du mode histoire, charger les objectifs de la mission
    if isinstance(chosen_level, dict):
        ch_idx  = chosen_level.get("chapter", 0)
        m_idx   = chosen_level.get("mission", 0)
        gs["mission_context"] = {
            "chapter":    ch_idx,
            "mission":    m_idx,
            "objectives": hist_mod.get_mission_objectives(ch_idx, m_idx),
            "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
        }

    # Choix initial de tour au lancement du niveau
    gs["levelup_pending"] = True
    start_loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
    gs["levelup_choices"] = pick_starting_tower_choices(start_loadout[:TOWER_SLOT_COUNT])

    _pause_start = None
    running      = True

    # Buffs possibles
    buff_defs = {
        "Vitesse Joueur":   ("player_speed",),
        "Dégâts Joueur":    ("player_damage",),
        "Vit. Attaque":     ("player_cooldown",),
        "HP +20":           ("player_hp",),
        "Dégâts Tours":     ("tower_damage",),
        "Vit. Tours":       ("tower_cooldown",),
    }

    known_towers = _make_known_towers(current_save)

    while running:
        # ----------------------------------------------------
        # EVENTS
        # ----------------------------------------------------
        render.clock.tick(60)
        render.screen.fill(BACKGROUND_COLOR)
        _bg = render.get_grid_bg()
        if _bg:
            _bg_full = pygame.transform.scale(_bg, render.screen.get_size())
            render.screen.blit(_bg_full, (0, 0))

        mouse_clicked_left = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if gs["selected_item"]:
                        gs["selected_item"] = None
                    elif not gs["levelup_pending"]:
                        running = False

                elif event.key == pygame.K_p:
                    # Touche P : bascule pause (uniquement si le jeu est en cours)
                    if (gs["game_started"] and not gs["game_over"]
                            and not gs["game_win"] and not gs["levelup_pending"]):
                        if not gs["paused"]:
                            gs["paused"] = True
                            _pause_start = time.time()
                        else:
                            gs["paused"] = False
                            if _pause_start is not None:
                                paused_duration = time.time() - _pause_start
                                gs["last_wave_time"]   += paused_duration
                                gs["last_enemy_spawn"] += paused_duration
                                gs["last_regen_time"]  += paused_duration
                                if gs["boss_start_time"] > 0:
                                    gs["boss_start_time"] += paused_duration
                                _pause_start = None



            elif event.type == pygame.VIDEORESIZE:
                render.screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE
                )
                grid_cache.invalidate()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked_left = True

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                if (gs.get("ultimate_info") and not gs.get("ultimate_active")
                        and gs.get("ultimate_cooldown", 0) <= 0
                        and gs.get("game_started") and not gs.get("paused")
                        and not gs.get("game_over") and not gs.get("game_win")):
                    gs["ultimate_active"]   = True
                    gs["ultimate_cooldown"] = gs["ultimate_cooldown_max"]
                    gs["ultimate_timer"]    = _get_ultimate_duration(gs["ultimate_info"]["char"])
                    _apply_ultimate_start(gs)

        # ----------------------------------------------------
        # CALCUL DES OFFSETS / SOURIS
        # ----------------------------------------------------
        win_w, win_h = render.screen.get_size()

        total_width = GRID_WIDTH
        offset_x    = (win_w - total_width) // 2
        usable_h    = win_h - INV_BAR_HEIGHT
        offset_y    = max(40, (usable_h - GRID_HEIGHT) // 2)

        mx, my = pygame.mouse.get_pos()
        gx = (mx - offset_x) // GRID_SIZE
        gy = (my - offset_y) // GRID_SIZE

        # Raccourcis d'état
        gs_grid        = gs["grid"]
        gs_towers      = gs["towers"]
        gs_enemies     = gs["enemies"]
        gs_projectiles = gs["projectiles"]
        gs_goal        = gs["goal"]
        gs_player      = gs["player"]
        gs_inv         = gs["inventory"]

        available_towers = {t: qty for t, qty in gs_inv.items() if qty > 0}

        # ----------------------------------------------------
        # GAME OVER / WIN CHECK
        # ----------------------------------------------------
        if not gs["game_over"]:
            gs["game_over"] = gs_goal.hp <= 0
        if not gs["game_over"] and not gs_player.alive:
            gs["game_over"] = True

        if gs["game_win"] and not gs.get("reward_collected") and gs.get("save") is not None:
            gs["save"]["coins"] = gs["save"].get("coins", 0) + gs["coins_reward"]
            gs["save"]["battles_won"] = gs["save"].get("battles_won", 0) + 1
            _mode_key = "infini" if gs.get("infinite_mode") else "histoire"
            gs["save"][f"{_mode_key}_battles_won"] = gs["save"].get(f"{_mode_key}_battles_won", 0) + 1
            # Marquer la difficulté de partie rapide comme complétée
            if not gs.get("infinite_mode") and gs.get("mission_context") is None:
                _diff_done = gs["save"].get("difficulty_completed", [])
                _cur_diff  = gs.get("difficulty", 2)
                if _cur_diff not in _diff_done:
                    _diff_done.append(_cur_diff)
                    gs["save"]["difficulty_completed"] = _diff_done
            gs["reward_collected"] = True

            # XP de compte : monte le niveau du menu et donne des skill points
            xp_gain = gs["coins_reward"] // 2  # XP proportionnelle à la difficulté
            save = gs["save"]
            save["xp"] = save.get("xp", 0) + xp_gain
            xp_next = save.get("xp_next", 30)
            while save["xp"] >= xp_next:
                save["xp"] -= xp_next
                save["level"] = save.get("level", 1) + 1
                save["skill_points"] = save.get("skill_points", 0) + 1
                save["pending_skillpoint_anim"] = True
                xp_next = int(xp_next * XP_GROWTH_FACTOR)
            save["xp_next"] = xp_next

            # Marquer les quêtes quotidiennes de combat accomplies
            quetes.mark_daily_quest_done(gs["save"], "quotidienne_combat_1")
            # quotidienne_combat_3 nécessite 3 victoires : géré via battles_won
            battles = gs["save"].get("battles_won", 0)
            if battles > 0 and battles % 3 == 0:
                quetes.mark_daily_quest_done(gs["save"], "quotidienne_combat_3")

            _check_and_notify_quests(gs)
            sd.save(gs["save"])

        # ----------------------------------------------------
        # GESTION DES VAGUES / BOSS
        # ----------------------------------------------------
        current_time = time.time()

        if not gs["game_started"]:
            gs["last_wave_time"]   = current_time
            gs["last_enemy_spawn"] = current_time
            gs["last_regen_time"]  = current_time
        if gs.get("toasts"):
            for toast in gs["toasts"][:]:
                toast["ttl"] -= 1
                if toast["ttl"] <= 0:
                    gs["toasts"].remove(toast)

        is_frozen = gs["paused"] or gs["game_over"] or gs["game_win"] or gs["levelup_pending"]

        if not is_frozen:
            # Timer de vague
            if not gs["boss_active"]:
                gs["wave_timer"] = max(0, WAVE_DURATION - (current_time - gs["last_wave_time"]))

            # Spawn interval dynamique
            if gs["game_started"] and gs["wave_number"] <= gs["max_waves"]:
                wn = gs["wave_number"]
                if gs.get("infinite_mode"):
                    # Mode infini : spawn de plus en plus rapide
                    gs["enemy_spawn_interval"] = max(0.15, 0.8 - 0.015 * (wn - 1))
                else:
                    gs["enemy_spawn_interval"] = max(
                        0.2,
                        DIFFICULTY_LEVELS[gs["difficulty"]]["spawn_interval"]
                        - 0.05 * (wn - 1)
                    )

            # Spawn d'ennemis normaux
            if (gs["game_started"]
                    and not gs["boss_active"]
                    and gs["enemies_spawned_this_wave"] < gs["max_enemies_this_wave"]
                    and current_time - gs["last_enemy_spawn"] >= gs["enemy_spawn_interval"]):
                is_fast = random.random() < 0.15
                wn = gs["wave_number"]
                if gs.get("infinite_mode"):
                    base_hp = int((15 + wn * 6) * (1.0 + wn * 0.08))
                else:
                    base_hp = 15 + (wn - 1) * 4
                hp = int(base_hp * gs["enemy_hp_mult"])
                gs_enemies.append(Enemy(hp=hp, speed=1.6 if is_fast else 1.0, is_fast=is_fast))
                gs["enemies_spawned_this_wave"] += 1
                gs["last_enemy_spawn"]           = current_time

            # Etat des ennemis
            alive_enemies  = [e for e in gs_enemies if not e.is_dead and not e._dying]
            has_boss       = any(e.is_boss       for e in alive_enemies)
            has_final_boss = any(e.is_final_boss for e in alive_enemies)

            # Passage en mode boss
            if (not gs["boss_active"]
                    and gs["enemies_spawned_this_wave"] >= gs["max_enemies_this_wave"]
                    and not alive_enemies):
                gs["boss_active"]     = True
                gs["boss_start_time"] = current_time
                wn       = gs["wave_number"]
                is_final = (not gs.get("infinite_mode")) and (wn == gs["max_waves"])

                # Détection boss de fin de chapitre (mode histoire uniquement)
                mc_ctx = gs.get("mission_context")
                is_chapter_final_boss = False
                if is_final and mc_ctx is not None and not gs.get("infinite_mode"):
                    ch  = mc_ctx.get("chapter", -1)
                    msn = mc_ctx.get("mission", -1)
                    try:
                        last_msn = hist_mod.get_last_mission_index(ch)
                        is_chapter_final_boss = (msn == last_msn)
                    except Exception:
                        is_chapter_final_boss = False

                if is_final:
                    if is_chapter_final_boss:
                        # Boss de fin de CHAPITRE : plus fort, plus gros, sprite unique
                        boss_hp = int((1000 + 200 * (wn - 1)) * gs["enemy_hp_mult"])
                        gs_enemies.append(Enemy(hp=boss_hp, speed=0.25, radius=72,
                                                is_boss=True, is_final_boss=True,
                                                is_chapter_boss=True,
                                                chapter_idx=mc_ctx.get("chapter") if mc_ctx else None))
                    else:
                        # Boss de fin de mission normale
                        boss_hp = int((500 + 100 * (wn - 1)) * gs["enemy_hp_mult"])
                        gs_enemies.append(Enemy(hp=boss_hp, speed=0.3, radius=50,
                                                is_boss=True, is_final_boss=True))
                else:
                    if gs.get("infinite_mode"):
                        boss_hp = int((100 + 80 * wn + wn * wn * 3) * gs["enemy_hp_mult"])
                    else:
                        boss_hp = int((150 + 50 * wn) * gs["enemy_hp_mult"])
                    gs_enemies.append(Enemy(hp=boss_hp, speed=0.45, radius=25, is_boss=True))
                alive_enemies  = [e for e in gs_enemies if not e.is_dead and not e._dying]
                has_boss       = any(e.is_boss       for e in alive_enemies)
                has_final_boss = any(e.is_final_boss for e in alive_enemies)

            # Timer boss
            if gs["boss_active"]:
                gs["boss_timer"] = max(0, BOSS_DURATION - (current_time - gs["boss_start_time"]))
                pass

            # Fin de boss
            if gs["boss_active"] and not has_boss:
                gs["boss_active"] = False
                wn = gs["wave_number"]

                # Mode infini : accumuler les recompenses + mise a jour record
                if gs.get("infinite_mode") and gs.get("save") is not None:
                    save_ref = gs["save"]
                    done_set = gs.get("infinite_wave_reward_done", set())
                    if wn not in done_set:
                        done_set.add(wn)
                        gs["infinite_wave_reward_done"] = done_set
                        _give_infinite_rewards(gs, wn, save_ref)
                        if wn > save_ref.get("max_wave_reached", 0):
                            save_ref["max_wave_reached"] = wn

                if not gs.get("infinite_mode") and wn == gs["max_waves"]:
                    gs["game_win"] = True
                else:
                    sl = {
                        "wave_number": gs["wave_number"],
                        "last_wave_time": gs["last_wave_time"],
                        "last_enemy_spawn": gs["last_enemy_spawn"],
                        "mobs_killed_this_wave": gs["mobs_killed_this_wave"],
                        "enemies_spawned_this_wave": gs["enemies_spawned_this_wave"],
                        "max_enemies_this_wave": gs["max_enemies_this_wave"],
                        "boss_active": gs["boss_active"],
                        "wave_timer": gs["wave_timer"],
                        "boss_timer": gs["boss_timer"],
                    }
                    start_new_wave(sl)
                    # Mode infini : plus d'ennemis a chaque vague
                    if gs.get("infinite_mode"):
                        next_wn = sl["wave_number"]
                        sl["max_enemies_this_wave"] = 6 + next_wn * 3
                    gs.update(sl)
                    # Passif Sasha : tour supplementaire
                    _apply_sasha_passive_on_wave(gs)

            if gs["wave_number"] > gs["max_waves"] and not alive_enemies:
                gs["game_win"] = True
                pass

        # ----------------------------------------------------
        # UPDATE ENTITES
        # ----------------------------------------------------
        if gs["game_started"] and not gs["game_over"] and not is_frozen:
            keys_pressed = pygame.key.get_pressed()
            gs_player.update(keys_pressed, gs_enemies, gs_projectiles, False, gs_grid)

            # Regen HP joueur — toujours active, plus rapide hors combat
            regen_dt = current_time - gs["last_regen_time"]
            gs["last_regen_time"] = current_time
            base_regen = PLAYER_HP_REGEN
            bonus_regen = getattr(gs_player, "hp_regen", 0.0)
            total_regen = base_regen + bonus_regen
            gs["regen_accumulator"] += total_regen * regen_dt
            if gs["regen_accumulator"] >= 1.0:
                heal = int(gs["regen_accumulator"])
                gs_player.hp = min(gs_player.max_hp, gs_player.hp + heal)
                gs["regen_accumulator"] -= heal

            # ── Update ultime ──────────────────────────────────
            if gs.get("ultimate_info"):
                dt = 1.0 / 60.0  # ~60fps
                if gs["ultimate_active"]:
                    gs["ultimate_timer"] = max(0, gs["ultimate_timer"] - dt)
                    if gs["ultimate_timer"] <= 0:
                        _apply_ultimate_end(gs)

                    # Eren : ralentir les ennemis à chaque frame
                    if gs.get("_ult_slow_enemies"):
                        for e in gs["enemies"]:
                            if not getattr(e, "_ult_slowed", False):
                                e.speed = max(0.3, e.speed * 0.5)
                                e._ult_slowed = True
                else:
                    # Retirer le slow sur les ennemis si l'ultime vient de finir
                    for e in gs["enemies"]:
                        if getattr(e, "_ult_slowed", False):
                            e.speed = getattr(e, "base_speed", e.speed * 2)
                            e._ult_slowed = False
                    if gs["ultimate_cooldown"] > 0:
                        gs["ultimate_cooldown"] = max(0, gs["ultimate_cooldown"] - dt)

            # Ennemis — on accumule les kills et on ne sauvegarde qu'une fois
            kills_this_frame = 0
            for e in gs_enemies[:]:
                e.update(gs_grid, gs_goal, player=gs_player)

                if not e.is_dead and not e._dying and e.hp <= 0:
                    e.mark_dead()

                if e.is_dead:
                    if e.is_final_boss:
                        gs["game_win"] = True
                    gs["xp"] += XP_REWARD_BOSS if e.is_boss else XP_REWARD_NORMAL
                    if not e.is_boss:
                        gs["mobs_killed_this_wave"] += 1
                    else:
                        gs["player_buff_tokens"] += 1

                    kills_this_frame += 1
                    gs_enemies.remove(e)

            # Mise à jour save + quêtes une seule fois par frame si des kills ont eu lieu
            if kills_this_frame > 0 and gs.get("save") is not None:
                gs["save"]["enemies_killed"] = gs["save"].get("enemies_killed", 0) + kills_this_frame
                _mk_mode = "infini" if gs.get("infinite_mode") else "histoire"
                gs["save"][f"{_mk_mode}_enemies_killed"] = gs["save"].get(f"{_mk_mode}_enemies_killed", 0) + kills_this_frame
                # Vérification quêtes déclenchée une seule fois (pas à chaque kill)
                _check_and_notify_quests(gs)
                # Sauvegarde différée : une seule écriture disque par frame max
                sd.save(gs["save"])

            # Goal
            gs_goal.update()

            # Tours
            for t in gs_towers:
                t.update(gs_enemies, gs_projectiles)

            i = len(gs_projectiles) - 1
            while i >= 0:
                gs_projectiles[i].update()
                if not gs_projectiles[i].alive:
                    gs_projectiles.pop(i)
                i -= 1

        elif gs["game_over"] or gs["game_win"]:
            gs_projectiles.clear()

        # ----------------------------------------------------
        # LEVEL UP → déclenche la bannière
        # ----------------------------------------------------
        while gs["xp"] >= gs["xp_to_next_level"] and not gs["levelup_pending"]:
            gs["xp"]               -= gs["xp_to_next_level"]
            gs["level"]            += 1
            gs["xp_to_next_level"]  = int(gs["xp_to_next_level"] * XP_GROWTH_FACTOR)
            gs["levelup_pending"]   = True
            gs["levelup_choices"] = pick_levelup_choices(known_towers, count=3)

            # Le level in-game ne donne PAS de skill point
            # Les skill points sont donnés uniquement lors du level-up du compte (menu)

            if not gs["paused"]:
                _pause_start = time.time()

        # ----------------------------------------------------
        # RENDU GRILLE + ENTITES
        # ----------------------------------------------------
        grid_cache.draw(render.screen, gs_grid, offset_x, offset_y, towers=gs_towers)

        # Zone de spawn visible tant que le jeu n'a pas commencé
        if not gs["game_started"]:
            spawn_surf = pygame.Surface((SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT), pygame.SRCALPHA)
            spawn_surf.fill((255, 255, 0, 60))
            render.screen.blit(spawn_surf, (offset_x + SPAWN_ZONE_X, offset_y + SPAWN_ZONE_Y))

        # Pièges
        for t in gs_towers:
            if hasattr(t, "trap_type"):
                t.draw(render.screen, offset_x, offset_y)

        # Ennemis 
        for e in gs_enemies:
            e.draw(render.screen, offset_x, offset_y)

        # Goal
        gs_goal.draw(render.screen, offset_x, offset_y)

        # Tours
        for t in gs_towers:
            if hasattr(t, "tower_type"):
                t.draw(render.screen, offset_x, offset_y)

        # Projectiles
        for p in gs_projectiles:
            p.draw(render.screen, offset_x, offset_y)

        # Évaluation des objectifs de mission (légère, chaque frame)
        _evaluate_mission_objectives(gs)

        # Joueur
        gs_player.draw(render.screen, offset_x, offset_y)

        # HUD
        draw_hud(
            render.screen, render.font, render.big_font,
            gs["level"], gs["xp"], gs["xp_to_next_level"],
            gs["wave_number"], gs["max_waves"],
            gs["mobs_killed_this_wave"], gs["max_enemies_this_wave"],
            gs["boss_active"], gs["boss_timer"], gs["wave_timer"],
            offset_x, offset_y,
            player_hp=gs_player.hp, player_max_hp=gs_player.max_hp,
        )

        # Bouton pause (icône cliquable)
        if gs["game_started"] and not gs["game_over"] and not gs["game_win"] and not gs["levelup_pending"]:
            pause_btn_rect = draw_pause_button(render.screen, offset_x, offset_y, mx, my)
            if mouse_clicked_left and pause_btn_rect.collidepoint(mx, my):
                if not gs["paused"]:
                    gs["paused"] = True
                    _pause_start = time.time()
                else:
                    gs["paused"] = False
                    if _pause_start is not None:
                        paused_duration = time.time() - _pause_start
                        gs["last_wave_time"]   += paused_duration
                        gs["last_enemy_spawn"] += paused_duration
                        gs["last_regen_time"]  += paused_duration
                        if gs["boss_start_time"] > 0:
                            gs["boss_start_time"] += paused_duration
                        _pause_start = None

        if not gs["game_started"]:
            draw_start_hint(render.screen, render.font, offset_x, offset_y)

        # ----------------------------------------------------
        # INVENTAIRE BAS
        # ----------------------------------------------------
        if not available_towers:
            hint_lbl = render.font.render("Choisissez vos tours via les level-up.", True, (180, 180, 180))
            render.screen.blit(hint_lbl, (offset_x + 10, offset_y + GRID_HEIGHT + 10))

        inv_rects = draw_inventory(
            render.screen, render.font,
            available_towers, gs["selected_item"],
            win_w, win_h
        )

        # ----------------------------------------------------
        # ZONES DE CLIC
        # ----------------------------------------------------
        in_buff_area = False
        in_shop_area = False
        in_inv_area  = my >= win_h - INV_BAR_HEIGHT
        in_grid_area = (not in_buff_area and not in_shop_area and not in_inv_area
                        and offset_x <= mx < offset_x + GRID_WIDTH
                        and offset_y <= my < offset_y + GRID_HEIGHT)

        # ----------------------------------------------------
        # LEVEL-UP BANNER (par-dessus tout)
        # ----------------------------------------------------
        if gs["levelup_pending"]:
            chosen = draw_levelup_banner(
                render.screen,
                render.big_font,
                render.font,
                gs["levelup_choices"],
                (mx, my),
                mouse_clicked_left,
            )
            if chosen:
                if chosen in known_towers:
                    gs_inv[chosen] = gs_inv.get(chosen, 0) + 1
                elif chosen in buff_defs:
                    key = buff_defs[chosen][0]
                    if key == "player_speed":
                        gs_player.speed += 0.3
                    elif key == "player_damage":
                        gs_player.damage += 2
                    elif key == "player_cooldown":
                        gs_player.attack_cooldown = max(5, gs_player.attack_cooldown - 2)
                    elif key == "player_hp":
                        gs_player.max_hp += 20
                        gs_player.hp = min(gs_player.max_hp, gs_player.hp + 20)
                    elif key == "tower_damage":
                        gs["tower_damage_bonus"] += 1
                        apply_all_tower_bonuses(gs_towers, gs["tower_damage_bonus"], gs["tower_cooldown_bonus"])
                    elif key == "tower_cooldown":
                        gs["tower_cooldown_bonus"] += 1
                        apply_all_tower_bonuses(gs_towers, gs["tower_damage_bonus"], gs["tower_cooldown_bonus"])

                gs["levelup_pending"] = False
                # Recalage des timers après pause forcée
                if _pause_start is not None:
                    paused_duration = time.time() - _pause_start
                    gs["last_wave_time"]   += paused_duration
                    gs["last_enemy_spawn"] += paused_duration
                    gs["last_regen_time"]  += paused_duration
                    if gs["boss_start_time"] > 0:
                        gs["boss_start_time"] += paused_duration
                    _pause_start = None

        # ----------------------------------------------------
        # CLICS HORS LEVEL-UP
        # ----------------------------------------------------
        if (mouse_clicked_left
                and not gs["game_over"]
                and not gs["game_win"]
                and not gs["paused"]
                and not gs["levelup_pending"]):

            # Clic inventaire
            if in_inv_area:
                for item_type, rect in inv_rects.items():
                    if rect.collidepoint(mx, my):
                        gs["selected_item"] = None if gs["selected_item"] == item_type else item_type
                        break

        # ----------------------------------------------------
        # GHOST + PLACEMENT
        # ----------------------------------------------------
        sel = gs["selected_item"]
        if (sel and sel in available_towers
                and not gs["game_over"]
                and not gs["paused"]
                and not gs["levelup_pending"]):
            cells = cells_for_item(sel, gx, gy)

            if cells:
                can_place_fn = make_can_place(gs_grid, START, sel)

                is_upgrade = any(
                    _is_matching_upgrade_target(t, sel, cells)
                    for t in gs_towers
                )

                if in_grid_area:
                    draw_ghost(
                        render.screen, cells, gx, gy, sel, gs_towers,
                        can_place_fn, offset_x, offset_y,
                    )

                if (mouse_clicked_left
                        and in_grid_area
                        and not in_inv_area
                        and (is_upgrade or can_place_fn(cells))):

                    placed = place_tower_on_grid(
                        gs_grid, gs_towers, cells, sel, grid_cache,
                        damage_bonus=(gs['tower_damage_bonus']),
                        cooldown_bonus=gs['tower_cooldown_bonus'],
                        levi_callback=(lambda t: _apply_levi_passive_on_upgrade(gs, t))
                                       if gs.get("selected_hero") == "levi" else None,
                        armin_callback=(lambda towers: _apply_armin_passive_on_build(gs, towers))
                                        if gs.get("selected_hero") == "armin" else None,
                    )
                    if placed:
                        gs["toasts"].append({"text": "Tour placée", "ttl": 140, "max_ttl": 140, "color": (120, 235, 140)})
                        gs["game_started"] = True

                        # Incrémenter le compteur de tours placées
                        if gs.get("save") is not None:
                            gs["save"]["towers_placed"] = gs["save"].get("towers_placed", 0) + 1
                            _tp_mode = "infini" if gs.get("infinite_mode") else "histoire"
                            gs["save"][f"{_tp_mode}_towers_placed"] = gs["save"].get(f"{_tp_mode}_towers_placed", 0) + 1
                            _check_and_notify_quests(gs)
                            sd.save(gs["save"])
                        
                        if sel in gs["inventory"]:
                            gs["inventory"][sel] -= 1
                            if gs["inventory"][sel] <= 0:
                                del gs["inventory"][sel]
                                if gs["selected_item"] == sel:
                                    gs["selected_item"] = None
                    else:
                        gs["toasts"].append({"text": "Impossible de poser ici", "ttl": 120, "max_ttl": 120, "color": (240, 120, 120)})

        if gs["paused"] and not gs["game_over"] and not gs["game_win"]:
            pause_action = draw_pause_screen(
                render.screen, render.big_font, render.font,
                mouse_pos=(mx, my), clicked=mouse_clicked_left
            )
            if pause_action == "resume":
                gs["paused"] = False
                if _pause_start is not None:
                    paused_duration = time.time() - _pause_start
                    gs["last_wave_time"]   += paused_duration
                    gs["last_enemy_spawn"] += paused_duration
                    gs["last_regen_time"]  += paused_duration
                    if gs["boss_start_time"] > 0:
                        gs["boss_start_time"] += paused_duration
                    _pause_start = None
            elif pause_action == "restart":
                gs["paused"] = False
                _pause_start = None
                # Conserver le mission_context courant avant de reconstruire l'état
                _prev_mc = gs.get("mission_context")
                # BUG2 FIX : s'assurer que chosen_level reflète bien la mission en cours
                if _prev_mc:
                    chosen_level = {
                        "chapter":    _prev_mc["chapter"],
                        "mission":    _prev_mc["mission"],
                        "difficulty": gs.get("difficulty", 2),
                    }
                gs = build_initial_state(chosen_level, current_save)
                # BUG1 FIX : réinjecter le mission_context après build_initial_state
                if _prev_mc:
                    gs["mission_context"] = {
                        "chapter":    _prev_mc["chapter"],
                        "mission":    _prev_mc["mission"],
                        "objectives": hist_mod.get_mission_objectives(_prev_mc["chapter"], _prev_mc["mission"]),
                        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                    }
                grid_cache.invalidate()
                gs["levelup_pending"] = True
                loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                known_towers = _make_known_towers(current_save)
            elif pause_action == "menu":
                gs["paused"] = False
                _pause_start = None
                play_menu_music(current_save.get("music_volume", 0.8))
                chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
                if chosen_level is None:
                    running = False
                    continue
                play_game_music(current_save.get("music_volume", 0.8))
                gs = build_initial_state(chosen_level, current_save)
                # BUG3 FIX : réinjecter le mission_context si on revient sur une mission histoire
                if isinstance(chosen_level, dict) and "chapter" in chosen_level:
                    _ch = chosen_level["chapter"]
                    _m  = chosen_level["mission"]
                    gs["mission_context"] = {
                        "chapter":    _ch,
                        "mission":    _m,
                        "objectives": hist_mod.get_mission_objectives(_ch, _m),
                        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                    }
                grid_cache.invalidate()
                gs["levelup_pending"] = True
                loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                known_towers = _make_known_towers(current_save)
        draw_toasts(render.screen, gs.get("toasts", []))

        # ── Passifs heros visuels + effets temps reel ──────
        if gs.get("game_started") and not gs.get("game_over") and not gs.get("game_win"):
            hero = gs.get("selected_hero", "eren")
            if hero == "mikasa":
                _apply_mikasa_passive(gs, render.screen, gs_player,
                                      gs.get("enemies", []), offset_x, offset_y)
            elif hero == "eren":
                _apply_eren_passive(gs, gs.get("towers", []), gs_player)

        # ── Bouton compétence ultime (bas droite de la grille) ──
        if gs.get("ultimate_info") and gs.get("game_started") and not gs.get("game_over") and not gs.get("game_win"):
            _draw_ultimate_button(render.screen, gs, offset_x, offset_y, mx, my, mouse_clicked_left)

        # Animation skill point : gérée dans le menu (main_ui.py)

        # Panneau objectifs de mission (mode histoire)
        mc = gs.get("mission_context")
        if mc and mc.get("objectives"):
            draw_mission_objectives(render.screen, offset_x, offset_y, mc["objectives"])

        if gs["game_over"] or gs["game_win"]:
            mc = gs.get("mission_context")

            # --- Mode infini : GAME OVER → popup loot (prioritaire) ---
            if gs.get("infinite_mode") and gs["game_over"]:
                if not gs.get("infinite_loot_collected") and gs.get("save") is not None:
                    gs["infinite_loot_collected"] = True
                    gs["_final_loot"] = _collect_infinite_loot(gs, gs["save"])

                final_loot   = gs.get("_final_loot", {"coins": 0, "gems": 0, "items": []})
                wave_reached = gs.get("wave_number", 1)
                done = _draw_infinite_loot_popup(
                    render.screen, final_loot, wave_reached, mx, my, mouse_clicked_left
                )
                if done:
                    play_menu_music(current_save.get("music_volume", 0.8))
                    chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
                    if chosen_level is None:
                        running = False
                        continue
                    play_game_music(current_save.get("music_volume", 0.8))
                    gs = build_initial_state(chosen_level, current_save)
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None

            # --- Mode histoire : victoire → popup étoiles ---
            elif gs["game_win"] and mc:
                # Sauvegarder le résultat une seule fois
                if not gs.get("mission_complete_shown"):
                    gs["mission_complete_shown"] = True
                    if gs.get("save") is not None:
                        hist_mod.save_mission_result(
                            gs["save"], mc["chapter"], mc["mission"], mc["objectives"]
                        )
                        current_save = gs["save"]  # synchroniser

                has_next = hist_mod.has_next_mission(mc["chapter"], mc["mission"])
                action = draw_mission_complete_screen(
                    render.screen, render.big_font, render.font,
                    mc["objectives"],
                    gs["coins_reward"],
                    has_next,
                    (mx, my), mouse_clicked_left,
                )
                if action == "next":
                    next_ch, next_m = hist_mod.get_next_mission(mc["chapter"], mc["mission"])
                    # Mettre à jour chosen_level pour la nouvelle mission
                    chosen_level = {"chapter": next_ch, "mission": next_m, "difficulty": gs.get("difficulty", 2)}
                    play_game_music(current_save.get("music_volume", 0.8))
                    gs = build_initial_state(chosen_level, current_save)
                    gs["mission_context"] = {
                        "chapter":    next_ch,
                        "mission":    next_m,
                        "objectives": hist_mod.get_mission_objectives(next_ch, next_m),
                        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                    }
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None
                elif action == "restart":
                    gs = build_initial_state(chosen_level, current_save)
                    gs["mission_context"] = {
                        "chapter":    mc["chapter"],
                        "mission":    mc["mission"],
                        "objectives": hist_mod.get_mission_objectives(mc["chapter"], mc["mission"]),
                        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                    }
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None
                elif action == "histoire":
                    play_menu_music(current_save.get("music_volume", 0.8))
                    hist_result = run_histoire(render.screen, render.clock, current_save)
                    if hist_result is None:
                        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
                        if chosen_level is None:
                            running = False
                            continue
                    else:
                        chosen_level = hist_result
                        current_save = sd.load()
                    play_game_music(current_save.get("music_volume", 0.8))
                    gs = build_initial_state(chosen_level, current_save)
                    if isinstance(chosen_level, dict):
                        ch_idx = chosen_level.get("chapter", 0)
                        m_idx  = chosen_level.get("mission", 0)
                        gs["mission_context"] = {
                            "chapter":    ch_idx,
                            "mission":    m_idx,
                            "objectives": hist_mod.get_mission_objectives(ch_idx, m_idx),
                            "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                        }
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None

            # --- Mode histoire : DÉFAITE → écran game over avec option rejouer/carte ---
            elif gs["game_over"] and mc:
                action = draw_mission_failed_screen(
                    render.screen, render.big_font, render.font,
                    mc["objectives"],
                    (mx, my), mouse_clicked_left,
                )
                if action == "restart":
                    gs = build_initial_state(chosen_level, current_save)
                    gs["mission_context"] = {
                        "chapter":    mc["chapter"],
                        "mission":    mc["mission"],
                        "objectives": hist_mod.get_mission_objectives(mc["chapter"], mc["mission"]),
                        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                    }
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None
                elif action == "histoire":
                    play_menu_music(current_save.get("music_volume", 0.8))
                    hist_result = run_histoire(render.screen, render.clock, current_save)
                    if hist_result is None:
                        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
                        if chosen_level is None:
                            running = False
                            continue
                    else:
                        chosen_level = hist_result
                        current_save = sd.load()
                    play_game_music(current_save.get("music_volume", 0.8))
                    gs = build_initial_state(chosen_level, current_save)
                    if isinstance(chosen_level, dict):
                        ch_idx = chosen_level.get("chapter", 0)
                        m_idx  = chosen_level.get("mission", 0)
                        gs["mission_context"] = {
                            "chapter":    ch_idx,
                            "mission":    m_idx,
                            "objectives": hist_mod.get_mission_objectives(ch_idx, m_idx),
                            "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
                        }
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None

            # --- Mode normal (hors histoire) ---
            else:
                action = draw_gameover_screen(
                    render.screen,
                    render.big_font,
                    render.font,
                    gs["game_win"],
                    (mx, my),
                    mouse_clicked_left,
                    gs["coins_reward"] if gs["game_win"] else 0,
                )
                if action == "restart":
                    gs = build_initial_state(chosen_level, current_save)
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None
                    continue
                elif action == "menu":
                    play_menu_music(current_save.get("music_volume", 0.8))
                    chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
                    if chosen_level is None:
                        running = False
                        continue
                    play_game_music(current_save.get("music_volume", 0.8))
                    gs = build_initial_state(chosen_level, current_save)
                    grid_cache.invalidate()
                    gs["levelup_pending"] = True
                    loadout = (gs.get("save") or {}).get("tower_loadout", []) or ALL_TOWER_TYPES
                    gs["levelup_choices"] = pick_starting_tower_choices(loadout[:TOWER_SLOT_COUNT])
                    known_towers = _make_known_towers(current_save)
                    _pause_start = None
                    continue

        pygame.display.flip()

    pygame.quit()