"""
game.py
-------
Boucle de jeu principale
"""

import os
import time
import random
import pygame

from config import (
    COLS, ROWS, GRID_SIZE,
    GRID_WIDTH, GRID_HEIGHT,
    START, END,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    LEVEL_START, XP_START, XP_TO_NEXT_LVL_START, XP_GROWTH_FACTOR,
    XP_REWARD_NORMAL, XP_REWARD_BOSS,
    WAVE_NUMBER_START, WAVE_DURATION, BOSS_DURATION,
    DANGER_WEIGHT,
    BACKGROUND_COLOR, PAUSE_KEY,
    DIFFICULTY_LEVELS, PLAYER_HP_REGEN,
    MUSIC_PATH, MUSIC_TRACK_TITLE, MUSIC_TRACK_MENU, MUSIC_TRACK_GAME,
    INV_BAR_HEIGHT,
    ALL_TOWER_TYPES, TOWER_SLOT_COUNT, TOWER_MAX_LEVEL,
)
import render
from render import GridCache
from grid import Grid
from entities import Player, Goal, Enemy, Tower, Trap
from ui import (
    draw_hud, draw_ghost,
    draw_inventory,
    draw_pause_screen, draw_gameover_screen, draw_start_hint,
    draw_levelup_banner,
    draw_toasts,
)
from walls import apply_map_walls
import save_data as sd


# ============================================================
# FONCTIONS UTILITAIRES : PLACEMENT / TOURS
# ============================================================

def make_can_place(grid, start_cell, item_type=None):
    """
    Retourne une fonction can_place(cells) qui vérifie :
      - in_bounds
      - walkable
      - pas de piège déjà présent (pour trap)
      - le chemin START -> END reste possible (flow field)
    """
    cache = {}

    def can_place(cells):
        cache_key = (item_type, tuple(sorted(cells)), grid.version)
        if cache_key in cache:
            return cache[cache_key]
        # 1) Limites + walkable
        for x, y in cells:
            if not grid.in_bounds(x, y):
                cache[cache_key] = False
                return False
            if not grid.walkable[x][y]:
                cache[cache_key] = False
                return False

        # 2) Cas spécial : pièges (pas de chevauchement)
        if item_type == "trap":
            occupied = set()
            for t in grid.towers_ref:
                if hasattr(t, "trap_type"):
                    occupied.update(t.cells)
            result = not any((x, y) in occupied for x, y in cells)
            cache[cache_key] = result
            return result

        # 3) Vérifier que le chemin reste valide
        blocked = []
        actually_changed = False
        for x, y in cells:
            if grid.walkable[x][y]:
                grid.walkable[x][y] = False
                blocked.append((x, y))
                actually_changed = True

        if not actually_changed:
            cache[cache_key] = False
            return False

        grid.compute_integration_field()
        valid = grid.integration_field[start_cell[0]][start_cell[1]] != float("inf")

        # 4) Restore
        for x, y in blocked:
            grid.walkable[x][y] = True
        grid.recompute()
        cache[cache_key] = valid
        return valid

    return can_place


def _is_matching_upgrade_target(tower, item_type, cells):
    t_type = getattr(tower, "tower_type", getattr(tower, "trap_type", None))
    match_type = (t_type == item_type) or (
        item_type == "trap" and t_type == "spikes"
    )
    return match_type and set(tower.cells) == set(cells)


def cells_for_item(item_type, gx, gy):
    """
    Retourne la liste des cellules occupées par un type de tour donné.
    """
    if item_type == "small":
        return [(gx, gy), (gx+1, gy), (gx, gy+1), (gx+1, gy+1)]
    elif item_type == "big":
        return [
            (gx, gy), (gx+1, gy), (gx+2, gy),
            (gx, gy+1), (gx+1, gy+1), (gx+2, gy+1),
        ]
    elif item_type == "trap":
        return [(gx+i, gy+j) for i in range(2) for j in range(4)]
    elif item_type in {"sniper", "rocket", "laser", "cannon"}:
        return [
            (gx, gy), (gx+1, gy),
            (gx, gy+1), (gx+1, gy+1),
        ]
    elif item_type in {
        "mortar", "beam", "tesla", "storm", "arcane", "crystal",
        "flamethrower", "shock", "burst", "swarm", "mine", "poison", "frost"
    }:
        return [(gx, gy), (gx+1, gy), (gx, gy+1), (gx+1, gy+1)]
    return []


def place_tower_on_grid(grid, towers, cells, item_type, grid_cache,
                        damage_bonus=0, cooldown_bonus=0):
    """
    Place une tour ou un piège sur la grille, ou upgrade si déjà présent.
    Retourne True si placement/upgrade effectué, False sinon.
    """
    target_cells = set(cells)
    # Upgrade si même type sur exactement les mêmes cellules
    for t in towers:
        if _is_matching_upgrade_target(t, item_type, target_cells):
            if t.level < TOWER_MAX_LEVEL:
                t.level += 1
                t.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
                if item_type != "trap":
                    grid.recompute()
                    grid_cache.invalidate()
                return True
            return False

    # Nouveau piège
    if item_type == "trap":
        trap = Trap(cells, trap_type="spikes")
        trap.set_stats()
        towers.append(trap)
        grid.recompute()
        grid_cache.invalidate()
        return True

    # Nouvelle tour
    for x, y in cells:
        grid.walkable[x][y] = False
    tower = Tower(cells, item_type)
    tower.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
    towers.append(tower)
    grid.recompute()
    grid_cache.invalidate()
    return True


def apply_tower_bonuses(tower, damage_bonus, cooldown_bonus):
    tower.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)


def apply_all_tower_bonuses(towers, damage_bonus, cooldown_bonus):
    for tower in towers:
        if hasattr(tower, "tower_type"):
            apply_tower_bonuses(tower, damage_bonus, cooldown_bonus)


# ============================================================
# MUSIQUE
# ============================================================

def _find_music_file(track_name):
    base = os.path.join(os.path.dirname(__file__), MUSIC_PATH, track_name)
    if os.path.exists(base):
        return base
    stem, ext = os.path.splitext(track_name)
    for candidate_ext in [".mp3", ".ogg", ".wav"]:
        candidate = os.path.join(os.path.dirname(__file__), MUSIC_PATH, stem + candidate_ext)
        if os.path.exists(candidate):
            return candidate
    return None


def play_music(track_name, volume=0.8):
    if not pygame.mixer.get_init():
        return
    track_path = _find_music_file(track_name)
    if not track_path:
        return
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(track_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
    except Exception:
        pass


def play_title_music(volume=0.8):
    play_music(MUSIC_TRACK_TITLE, volume)


def play_menu_music(volume=0.8):
    play_music(MUSIC_TRACK_MENU, volume)


def play_game_music(volume=0.8):
    play_music(MUSIC_TRACK_GAME, volume)


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
    Inventaire vide au début, tours gagnées uniquement via level-up.
    """
    diff_info      = DIFFICULTY_LEVELS.get(difficulty, DIFFICULTY_LEVELS[2])
    max_waves      = diff_info["waves"]
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
    tower_equipment_bonus = 0
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
                elif stat == "tower_bonus":
                    tower_equipment_bonus += val

    # Inventaire initial : vide au début du niveau
    inventory = {}

    # Murs de la carte
    apply_map_walls(grid)
    grid.recompute()

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
        "tower_equipment_bonus":    tower_equipment_bonus,
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

        # Référence save
        "save":                     save,
        "toasts":                   [],
    }


# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

def _make_known_towers(save):
    if not save:
        return set(ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
    loadout = save.get("tower_loadout", []) or ALL_TOWER_TYPES
    return set(loadout[:TOWER_SLOT_COUNT])


def main():
    render.init_pygame()
    # Chargement des sprites optionnels (silencieux si les fichiers sont absents)
    render.load_wall_image()
    Tower.load_sprites()
    Trap.load_sprites()

    from menu_screen import run_menu, run_title_screen
    from ui import draw_levelup_banner

    current_save = sd.load()
    play_title_music(current_save.get("music_volume", 0.8))

    # Ecran titre
    title_result, current_save = run_title_screen(render.screen, render.clock, current_save)
    if title_result is None:
        pygame.quit()
        return

    # Menu principal
    play_menu_music(current_save.get("music_volume", 0.8))
    result = run_menu(render.screen, render.clock, current_save)
    if result is None or result[0] is None:
        pygame.quit()
        return
    chosen_level, current_save = result

    # Musique de jeu
    play_game_music(current_save.get("music_volume", 0.8))

    grid_cache = GridCache()
    gs         = build_initial_state(chosen_level, current_save)
    grid_cache.invalidate()

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

                elif (event.key == PAUSE_KEY
                      and gs["game_started"]
                      and not gs["game_over"]
                      and not gs["game_win"]
                      and not gs["levelup_pending"]):
                    # Toggle pause
                    if not gs["paused"]:
                        gs["paused"]  = True
                        _pause_start  = time.time()
                    else:
                        gs["paused"]  = False
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
            gs["reward_collected"] = True
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
                gs["enemy_spawn_interval"] = max(
                    0.2,
                    DIFFICULTY_LEVELS[gs["difficulty"]]["spawn_interval"]
                    - 0.05 * (gs["wave_number"] - 1)
                )

            # Spawn d'ennemis normaux
            if (gs["game_started"]
                    and not gs["boss_active"]
                    and gs["enemies_spawned_this_wave"] < gs["max_enemies_this_wave"]
                    and current_time - gs["last_enemy_spawn"] >= gs["enemy_spawn_interval"]):
                is_fast = random.random() < 0.15
                base_hp = 15 + (gs["wave_number"] - 1) * 4
                hp      = int(base_hp * gs["enemy_hp_mult"])
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
                is_final = gs["wave_number"] == gs["max_waves"]
                if is_final:
                    boss_hp = int((500 + 100 * (gs["wave_number"] - 1)) * gs["enemy_hp_mult"])
                    gs_enemies.append(Enemy(hp=boss_hp, speed=0.6, radius=50,
                                            is_boss=True, is_final_boss=True))
                else:
                    boss_hp = int((150 + 50 * gs["wave_number"]) * gs["enemy_hp_mult"])
                    gs_enemies.append(Enemy(hp=boss_hp, speed=0.3, radius=25, is_boss=True))
                alive_enemies  = [e for e in gs_enemies if not e.is_dead and not e._dying]
                has_boss       = any(e.is_boss       for e in alive_enemies)
                has_final_boss = any(e.is_final_boss for e in alive_enemies)

            # Timer boss
            if gs["boss_active"]:
                gs["boss_timer"] = max(0, BOSS_DURATION - (current_time - gs["boss_start_time"]))
                if gs["boss_timer"] <= 0 and has_boss:
                    gs["game_over"] = True

            # Fin de boss
            if gs["boss_active"] and not has_boss:
                gs["boss_active"] = False
                if gs["wave_number"] == gs["max_waves"]:
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
                    gs.update(sl)

            if gs["wave_number"] > gs["max_waves"] and not alive_enemies:
                gs["game_win"] = True
            if not gs["boss_active"] and gs["wave_timer"] <= 0 and gs_enemies:
                gs["game_over"] = True

        # ----------------------------------------------------
        # UPDATE ENTITES
        # ----------------------------------------------------
        if gs["game_started"] and not gs["game_over"] and not is_frozen:
            keys_pressed = pygame.key.get_pressed()
            gs_player.update(keys_pressed, gs_enemies, gs_projectiles, False, gs_grid)

            # Regen HP joueur (hors combat)
            can_regen = not gs["boss_active"] and not gs_enemies
            if can_regen:
                regen_dt = current_time - gs["last_regen_time"]
                gs["last_regen_time"] = current_time
                gs["regen_accumulator"] += PLAYER_HP_REGEN * regen_dt
                if gs["regen_accumulator"] >= 1.0:
                    heal = int(gs["regen_accumulator"])
                    gs_player.hp = min(gs_player.max_hp, gs_player.hp + heal)
                    gs["regen_accumulator"] -= heal
            else:
                gs["last_regen_time"] = current_time

            # Ennemis
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
                    gs_enemies.remove(e)

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

        # Ennemis + barre de vie boss final
        for e in gs_enemies:
            if e.is_final_boss:
                bw2, bh2 = 400, 30
                bx2 = (win_w - bw2) // 2
                by2 = 50
                pygame.draw.rect(render.screen, (200, 0, 0), (bx2, by2, bw2, bh2))
                bfill = int(bw2 * e.hp / max(1, e.max_hp))
                pygame.draw.rect(render.screen, (0, 200, 0), (bx2, by2, bfill, bh2))
                bt = render.big_font.render("BOSS FINAL !", True, (255, 0, 0))
                render.screen.blit(bt, ((win_w - bt.get_width()) // 2, by2 - 40))
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

        if not gs["game_started"]:
            draw_start_hint(render.screen, render.font, offset_x, offset_y)

        # ----------------------------------------------------
        # PANEL GAUCHE : BUFFS JOUEUR (jetons de boss)
        # ----------------------------------------------------
        left_base_x = max(10, offset_x - 210)
        left_base_y = offset_y + 190

        pts_p = render.font.render(
            f"Jetons Joueur : {gs['player_buff_tokens']}", True, (255, 100, 100)
        )
        render.screen.blit(pts_p, (left_base_x + 10, left_base_y))
        left_base_y += 35

        buff_items = {
            "Joueur (Vitesse)":          ("speed",    "player"),
            "Joueur (Dégâts)":           ("damage",   "player"),
            "Joueur (Vit. Attaque)":     ("cooldown", "player"),
            "Joueur (HP +20)":           ("hp",       "player"),
        }
        rects_buffs = {}

        for buff_name, (buff_key, buff_type) in buff_items.items():
            btn_rect = pygame.Rect(left_base_x + 10, left_base_y, 180, 40)
            can_buy  = buff_type == "player" and gs["player_buff_tokens"] > 0
            color    = (80, 50, 50)
            pygame.draw.rect(render.screen, color, btn_rect, border_radius=5)
            b_color  = (255, 255, 255) if can_buy else (150, 50, 50)
            pygame.draw.rect(render.screen, b_color, btn_rect, 2, border_radius=5)
            lbl = render.font.render(buff_name, True, (255, 255, 255))
            render.screen.blit(lbl, (btn_rect.x + 10, btn_rect.y + 10))
            rects_buffs[buff_name] = (btn_rect, buff_key, buff_type)
            left_base_y += 45

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
        in_buff_area = mx < offset_x
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
                        apply_all_tower_bonuses(gs_towers, gs["tower_damage_bonus"] + gs["tower_equipment_bonus"], gs["tower_cooldown_bonus"])
                    elif key == "tower_cooldown":
                        gs["tower_cooldown_bonus"] += 1
                        apply_all_tower_bonuses(gs_towers, gs["tower_damage_bonus"] + gs["tower_equipment_bonus"], gs["tower_cooldown_bonus"])

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

            # Clic buffs (jetons de boss)
            elif in_buff_area:
                for buff_name, (rect, buff_key, buff_type) in rects_buffs.items():
                    if rect.collidepoint(mx, my):
                        if buff_type == "player" and gs["player_buff_tokens"] > 0:
                            gs["player_buff_tokens"] -= 1
                            if buff_key == "speed":
                                gs_player.speed += 0.5
                            elif buff_key == "damage":
                                gs_player.damage += 2
                            elif buff_key == "cooldown":
                                gs_player.attack_cooldown = max(5, gs_player.attack_cooldown - 2)
                            elif buff_key == "hp":
                                gs_player.max_hp += 20
                                gs_player.hp      = min(gs_player.max_hp, gs_player.hp + 20)

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
                        damage_bonus=(gs['tower_damage_bonus'] + gs.get('tower_equipment_bonus', 0)),
                        cooldown_bonus=gs['tower_cooldown_bonus'],
                    )
                    if placed:
                        gs["toasts"].append({"text": "Tour placee", "ttl": 140, "max_ttl": 140, "color": (120, 235, 140)})
                        gs["game_started"] = True
                        if sel in gs["inventory"]:
                            gs["inventory"][sel] -= 1
                            if gs["inventory"][sel] <= 0:
                                del gs["inventory"][sel]
                                if gs["selected_item"] == sel:
                                    gs["selected_item"] = None
                    else:
                        gs["toasts"].append({"text": "Impossible de poser ici", "ttl": 120, "max_ttl": 120, "color": (240, 120, 120)})

        if gs["paused"] and not gs["game_over"] and not gs["game_win"]:
            draw_pause_screen(render.screen, render.big_font, render.font)
        draw_toasts(render.screen, gs.get("toasts", []))

        if gs["game_over"] or gs["game_win"]:
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
                result = run_menu(render.screen, render.clock, current_save)
                if result is None or result[0] is None:
                    running = False
                    continue
                chosen_level, current_save = result
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
