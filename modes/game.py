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

from config import (
    COLS, ROWS, GRID_SIZE,
    GRID_WIDTH, GRID_HEIGHT,
    START, END,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    LEVEL_START, XP_START, XP_TO_NEXT_LVL_START, XP_GROWTH_FACTOR,
    XP_REWARD_NORMAL, XP_REWARD_BOSS,
    WAVE_NUMBER_START, WAVE_DURATION, BOSS_DURATION,
    DANGER_WEIGHT,
    BACKGROUND_COLOR,
    DIFFICULTY_LEVELS, PLAYER_HP_REGEN,
    MUSIC_PATH, MUSIC_TRACK_TITLE, MUSIC_TRACK_MENU, MUSIC_TRACK_GAME,
    INV_BAR_HEIGHT,
    ALL_TOWER_TYPES, TOWER_SLOT_COUNT, TOWER_MAX_LEVEL,
)
import render
from render import GridCache
from grid import Grid
from entities import Player, Goal, Enemy, Tower, Trap, Projectile
from ui import (
    draw_hud, draw_ghost,
    draw_inventory,
    draw_pause_screen, draw_gameover_screen, draw_start_hint,
    draw_levelup_banner,
    draw_toasts,
    draw_pause_button,
    draw_mission_objectives,
    draw_mission_complete_screen,
    draw_mission_failed_screen,
    draw_skillpoint_anim,
)
from walls import apply_map_walls
import save_data as sd
import quetes
import histoire as hist_mod
from histoire import run_histoire

# Seuils de sauvegarde : on ne sauvegarde qu'en fin de vague, pas à chaque kill
_DIRTY_SAVE = False   # True = save nécessaire, effectuée en fin de frame sûre


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
        if item_type in ("trap", "mine"):
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
    ) or (
        item_type == "mine" and t_type == "mine"
    )
    return match_type and set(tower.cells) == set(cells)


def cells_for_item(item_type, gx, gy):
    """
    Retourne la liste des cellules occupées par un type de tour donné.
    """
    if item_type == "trap":
        return [(gx+i, gy+j) for i in range(2) for j in range(4)]
    # Toutes les tours : 2x2
    return [(gx, gy), (gx+1, gy), (gx, gy+1), (gx+1, gy+1)]


def place_tower_on_grid(grid, towers, cells, item_type, grid_cache,
                        damage_bonus=0, cooldown_bonus=0, levi_callback=None,
                        armin_callback=None):
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
                if item_type not in ("trap", "mine"):
                    grid.recompute()
                    grid_cache.invalidate()
                # Passif Levi injecte via callback si disponible
                if levi_callback:
                    levi_callback(t)
                return True
            return False

    # Nouveau piège (trap ou mine)
    if item_type == "trap":
        trap = Trap(cells, trap_type="spikes")
        trap.set_stats()
        towers.append(trap)
        grid.recompute()
        grid_cache.invalidate()
        return True
    if item_type == "mine":
        mine = Trap(cells, trap_type="mine")
        mine.set_stats()
        towers.append(mine)
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
    # Passif Armin : buff toutes les tours a chaque construction
    if armin_callback:
        armin_callback(towers)
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
    base = os.path.join(os.path.dirname(__file__), "..", MUSIC_PATH, track_name)
    if os.path.exists(base):
        return base
    stem, ext = os.path.splitext(track_name)
    for candidate_ext in [".mp3", ".ogg", ".wav"]:
        candidate = os.path.join(os.path.dirname(__file__), "..", MUSIC_PATH, stem + candidate_ext)
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
    import heroes as _hm
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
    import re
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


# ============================================================
# PASSIFS HEROS
# ============================================================

def _apply_eren_passive(gs, towers, player):
    """Eren : tours dans un rayon de 8 cases autour du joueur = +20% degats."""
    import math
    if gs.get("selected_hero") != "eren":
        return
    from config import GRID_SIZE
    BOOST = 0.10  # fixe, independant du niveau
    radius_px  = 3 * GRID_SIZE
    for t in towers:
        if not hasattr(t, "tower_type"):
            continue
        dist = math.hypot(t.x - player.x, t.y - player.y)
        in_range = dist <= radius_px
        was_boosted = getattr(t, "_eren_boosted", False)
        if in_range and not was_boosted:
            t._eren_boosted = True
            t.damage = int(t.damage * (1.0 + BOOST))
        elif not in_range and was_boosted:
            t._eren_boosted = False
            t.set_stats(damage_bonus=gs.get("tower_damage_bonus", 0),
                        cooldown_bonus=gs.get("tower_cooldown_bonus", 0))


def _apply_armin_passive_on_build(gs, towers):
    """Armin : +40% ATK sur toutes les tours a chaque nouvelle tour construite."""
    if gs.get("selected_hero") != "armin":
        return
    gs["armin_buff_stacks"] = gs.get("armin_buff_stacks", 0) + 1
    total_mult = 1.0 + 0.08 * gs["armin_buff_stacks"]
    for t in towers:
        if not hasattr(t, "tower_type"):
            continue
        base_dmg = getattr(t, "_base_damage", t.damage)
        t._base_damage = base_dmg
        t.damage = int(base_dmg * total_mult)


def _apply_sasha_passive_on_wave(gs):
    """Sasha : ajoute une tour aleatoire dans l'inventaire chaque nouvelle vague."""
    if gs.get("selected_hero") != "sasha":
        return
    import random as _rnd
    import heroes as _hm
    wn = gs.get("wave_number", 1)
    done = gs.setdefault("sasha_towers_given", set())
    if wn in done:
        return
    done.add(wn)
    save = gs.get("save") or {}
    hero_level = _hm.get_hero_level(save, "sasha")
    # 1 tour de base + 1 supplementaire tous les 5 niveaux
    nb = 1 + (hero_level - 1) // 5
    from config import ALL_TOWER_TYPES
    pool = [t for t in ALL_TOWER_TYPES if t not in ("trap",)]
    for _ in range(nb):
        t = _rnd.choice(pool)
        gs["inventory"][t] = gs["inventory"].get(t, 0) + 1
    gs.setdefault("toasts", []).append({
        "text": f"Sasha : +{nb} tour(s) offerte(s) !",
        "ttl": 200, "max_ttl": 200, "color": (160, 120, 80)
    })


def _apply_levi_passive_on_upgrade(gs, tower):
    """Levi : upgrade niveau 1 -> niveau 3 directement."""
    if gs.get("selected_hero") != "levi":
        return False
    # Si la tour etait niveau 1 et vient de passer niveau 2, on la passe niveau 3
    if tower.level == 2:
        tower.level = 3
        tower.set_stats(damage_bonus=gs.get("tower_damage_bonus", 0),
                        cooldown_bonus=gs.get("tower_cooldown_bonus", 0))
        return True
    return False


def _apply_mikasa_passive(gs, screen, player, enemies, offset_x, offset_y):
    """Mikasa : zone de degats continus autour du joueur (120px)."""
    if gs.get("selected_hero") != "mikasa":
        return
    RADIUS  = 80
    DPS     = 4.0   # degats par seconde
    dt      = 1.0 / 60.0
    dmg_per_frame = DPS * dt

    # Dessin de la zone (cercle semi-transparent)
    surf = pygame.Surface((RADIUS * 2 + 4, RADIUS * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(surf, (127, 119, 221, 35), (RADIUS + 2, RADIUS + 2), RADIUS)
    pygame.draw.circle(surf, (127, 119, 221, 80), (RADIUS + 2, RADIUS + 2), RADIUS, 2)
    screen.blit(surf, (int(player.x) + offset_x - RADIUS - 2,
                        int(player.y) + offset_y - RADIUS - 2))

    # Degats aux ennemis dans la zone
    for e in enemies:
        if e.is_dead or e._dying:
            continue
        dist = math.hypot(e.x - player.x, e.y - player.y)
        if dist <= RADIUS:
            e.hp -= dmg_per_frame
            if e.hp <= 0 and not e.is_dead:
                e.is_dead = True


def _draw_eren_passive_zone(screen, player, offset_x, offset_y):
    """Dessine le cercle de portee d'Eren (informatif)."""
    from config import GRID_SIZE
    RADIUS = 3 * GRID_SIZE
    surf   = pygame.Surface((RADIUS * 2 + 4, RADIUS * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(surf, (213, 90, 48, 20), (RADIUS + 2, RADIUS + 2), RADIUS)
    pygame.draw.circle(surf, (213, 90, 48, 60), (RADIUS + 2, RADIUS + 2), RADIUS, 1)
    screen.blit(surf, (int(player.x) + offset_x - RADIUS - 2,
                        int(player.y) + offset_y - RADIUS - 2))


def _get_ultimate_duration(char_id):
    """Retourne la durée en secondes de l'effet ultime selon le personnage."""
    return {"eren": 8.0, "mikasa": 10.0, "erwin": 12.0}.get(char_id, 8.0)


def _apply_ultimate_start(gs):
    """Active les effets de l'ultime selon le personnage."""
    char = gs["ultimate_info"]["char"]
    player = gs["player"]
    if char == "eren":
        gs["_ult_orig_damage"] = player.damage
        player.damage = int(player.damage * 2)
        gs["_ult_slow_enemies"] = True
    elif char == "mikasa":
        gs["_ult_orig_speed"]      = player.speed
        gs["_ult_orig_attack_cd"]  = player.attack_cooldown
        player.speed           = player.speed * 2
        player.attack_cooldown = max(3, player.attack_cooldown // 2)
    elif char == "erwin":
        gs["_ult_tower_fire_rate"] = True   # flag lu par les tours


def _apply_ultimate_end(gs):
    """Retire les effets de l'ultime."""
    char = gs["ultimate_info"]["char"]
    player = gs["player"]
    if char == "eren":
        player.damage = gs.pop("_ult_orig_damage", player.damage)
        gs.pop("_ult_slow_enemies", None)
    elif char == "mikasa":
        player.speed           = gs.pop("_ult_orig_speed",     player.speed)
        player.attack_cooldown = gs.pop("_ult_orig_attack_cd", player.attack_cooldown)
    elif char == "erwin":
        gs.pop("_ult_tower_fire_rate", None)
    gs["ultimate_active"] = False
    gs["ultimate_timer"]  = 0


def _give_infinite_rewards(gs, wave_number, save):
    """
    Accumule les recompenses de vague dans gs["infinite_loot"].
    Tout est donne en une seule fois au moment du game over.
    """
    import random as _rnd
    wn = wave_number

    loot = gs.setdefault("infinite_loot", {
        "coins": 0, "gems": 0, "items": []
    })

    # Pieces
    loot["coins"] += 20 + wn * 8

    # Gemmes
    if wn >= 36:
        gems = _rnd.randint(3, 6)
    elif wn >= 21:
        gems = _rnd.randint(1, 3)
    elif wn >= 11:
        gems = 1 if _rnd.random() < 0.6 else 0
    else:
        gems = 0
    loot["gems"] += gems

    # Equipement
    if wn >= 36:
        rarities = ["Epique", "Legendaire", "Mythique"]
        weights  = [20, 45, 35]
    elif wn >= 21:
        rarities = ["Rare", "Epique", "Legendaire"]
        weights  = [30, 50, 20]
    elif wn >= 11:
        rarities = ["Commun", "Rare", "Epique"]
        weights  = [20, 55, 25]
    elif wn >= 6:
        rarities = ["Commun", "Rare"]
        weights  = [60, 40]
    else:
        rarities = ["Commun"]
        weights  = [100]

    nb_equip = 2 if wn >= 21 else 1
    for _ in range(nb_equip):
        from config import EQUIPMENT_SLOTS, EQUIPMENT_STATS, RARITY_COLORS
        import random as _r2
        # Convertir nom de rarete avec accents pour config
        RARITY_MAP = {
            "Commun": "Commun", "Rare": "Rare",
            "Epique": "Epique", "Legendaire": "Legendaire", "Mythique": "Mythique"
        }
        rarity_key = _r2.choices(rarities, weights=weights, k=1)[0]
        rarity_cfg = rarity_key  # les clefs dans EQUIPMENT_STATS sans accents
        # Chercher la vraie cle avec accent si besoin
        for r in ["Commun", "Rare", "Epique", "Legendaire", "Mythique"]:
            if r.lower() == rarity_key.lower():
                rarity_cfg = r
                break
        slot      = _r2.choice(EQUIPMENT_SLOTS)
        stat_info = EQUIPMENT_STATS[slot]
        # Trouver la valeur (cherche avec ou sans accent)
        value = None
        for k, v in stat_info["values"].items():
            if k.lower().replace("é","e").replace("è","e") == rarity_cfg.lower().replace("é","e"):
                value = v
                break
        if value is None:
            value = list(stat_info["values"].values())[0]
        NAMES = {"cape":"Cape","veste":"Veste","bottes":"Bottes","arme":"Lames","tour":"Relique"}
        IMGS  = {"cape":"cape.png","veste":"veste.png","bottes":"bottes.png",
                 "arme":"lames.png","tour":"tour.png"}
        # Couleur rarity
        col = list(RARITY_COLORS.get(rarity_cfg, (180,180,180)))
        item = {
            "slot": slot, "rarity": rarity_cfg, "stat": stat_info["stat"],
            "value": value, "label": stat_info["label"],
            "name": NAMES.get(slot, slot), "image": IMGS.get(slot, ""),
            "color": col,
        }
        loot["items"].append(item)


def _collect_infinite_loot(gs, save):
    """
    Credite le loot accumule dans la save et retourne le dict pour affichage.
    Appele une seule fois au moment du game over en mode infini.
    """
    loot = gs.get("infinite_loot", {"coins": 0, "gems": 0, "items": []})
    save["coins"] = save.get("coins", 0) + loot["coins"]
    save["gems"]  = save.get("gems",  0) + loot["gems"]
    for item in loot["items"]:
        save.setdefault("inventory_equipment", []).append(item)

    wn = gs.get("wave_number", 1)

    # Hero drop a partir de la vague 28
    if wn >= 28:
        if wn >= 40:
            hero_chance = 0.40
            pool = ["levi", "mikasa", "armin", "sasha"]
        elif wn >= 35:
            hero_chance = 0.25
            pool = ["armin", "sasha", "levi", "mikasa"]
        else:
            hero_chance = 0.12
            pool = ["armin", "sasha"]
        import heroes as _hm
        if random.random() < hero_chance:
            hero_id = random.choice(pool)
            _hm.init_heroes_save(save)
            _hm.add_hero_copy(save, hero_id)
            hdef = _hm.HEROES[hero_id]
            loot.setdefault("hero_drop", []).append({
                "id":     hero_id,
                "name":   hdef["name"],
                "rarity": hdef["rarity"],
                "color":  list(_hm.RARITY_COLORS.get(hdef["rarity"], (180, 180, 180))),
            })

    xp_gain = sum(10 + 3 * w for w in range(1, wn + 1))
    save["xp"] = save.get("xp", 0) + xp_gain
    xp_next = save.get("xp_next", 30)
    while save["xp"] >= xp_next:
        save["xp"] -= xp_next
        save["level"] = save.get("level", 1) + 1
        save["skill_points"] = save.get("skill_points", 0) + 1
        save["pending_skillpoint_anim"] = True
        xp_next = int(xp_next * XP_GROWTH_FACTOR)
    save["xp_next"] = xp_next
    sd.save(save)
    return loot


def _draw_infinite_loot_popup(screen, loot, wave_reached, mx, my, clicked):
    """
    Popup affiché à la mort en mode infini.
    Montre le total pieces/gemmes + tous les equipements droppe, style coffre.
    Retourne True si le joueur clique sur "Continuer".
    """
    import theme as _theme

    W, H = min(520, screen.get_width() - 40), min(560, screen.get_height() - 40)
    rx   = (screen.get_width()  - W) // 2
    ry   = (screen.get_height() - H) // 2
    pop  = pygame.Rect(rx, ry, W, H)

    # Fond semi-transparent global
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Panel principal
    _theme.draw_panel(screen, pop, color=(18, 12, 30),
                      border_color=(130, 80, 200), radius=_theme.RADIUS_LG, border_w=2)
    _theme.draw_corner_ornaments(screen, pop, size=8, color=(130, 80, 200))

    f_ti  = _theme.font(_theme.SZ_SECTION)
    f_lbl = _theme.font(_theme.SZ_LABEL, body=True)
    f_sm  = _theme.font(_theme.SZ_SMALL, body=True)
    f_xs  = _theme.font(_theme.SZ_TINY,  body=True)

    py = pop.y + 14

    # Titre
    t1 = f_ti.render("Partie terminee", True, (180, 100, 255))
    screen.blit(t1, (pop.centerx - t1.get_width()//2, py))
    py += t1.get_height() + 2

    t2 = f_xs.render(f"Vague atteinte : {wave_reached}", True, (120, 70, 180))
    screen.blit(t2, (pop.centerx - t2.get_width()//2, py))
    py += t2.get_height() + 8

    _theme.draw_gold_rule(screen, pop.x + 16, py, W - 32)
    py += 10

    # Pieces + Gemmes
    coins = loot.get("coins", 0)
    gems  = loot.get("gems",  0)

    row_y = py
    # Pieces
    coin_icon = _theme.load_sprite("pieces.png", (22, 22))
    if coin_icon:
        screen.blit(coin_icon, (pop.x + 20, row_y))
    c_s = f_lbl.render(f"+{coins} pieces", True, _theme.GOLD_LIGHT)
    screen.blit(c_s, (pop.x + 48, row_y + (22 - c_s.get_height())//2))

    # Gemmes
    gem_icon = _theme.load_sprite("gemmes.png", (22, 22))
    gx = pop.x + 20 + W//2 - 20
    if gem_icon:
        screen.blit(gem_icon, (gx, row_y))
    if gems > 0:
        g_s = f_lbl.render(f"+{gems} gemmes", True, (180, 140, 255))
        screen.blit(g_s, (gx + 28, row_y + (22 - g_s.get_height())//2))
    py += 30

    _theme.draw_gold_rule(screen, pop.x + 16, py, W - 32)
    py += 10

    # Equipements
    items = loot.get("items", [])
    if items:
        lbl_eq = f_xs.render("Equipements obtenus :", True, (100, 70, 140))
        screen.blit(lbl_eq, (pop.x + 16, py))
        py += lbl_eq.get_height() + 6

        CELL   = 54
        COLS_P = (W - 32) // (CELL + 6)
        for idx, item in enumerate(items):
            col_i  = idx % COLS_P
            row_i  = idx // COLS_P
            cx     = pop.x + 16 + col_i * (CELL + 6)
            cy_item = py + row_i * (CELL + 6)
            if cy_item + CELL > pop.bottom - 50:
                break
            cell = pygame.Rect(cx, cy_item, CELL, CELL)
            col  = tuple(item.get("color", (180, 180, 180)))
            _theme.draw_panel(screen, cell, color=(20, 14, 30),
                              border_color=col, radius=_theme.RADIUS_MD, border_w=2)
            img_name = item.get("image", "")
            img = _theme.load_sprite(img_name, (CELL - 10, CELL - 10)) if img_name else None
            if img:
                screen.blit(img, (cx + 5, cy_item + 5))
            else:
                lbl = f_xs.render(item.get("name", "?")[:5], True, col)
                screen.blit(lbl, (cx + CELL//2 - lbl.get_width()//2,
                                  cy_item + CELL//2 - lbl.get_height()//2))
            # Rarity label en bas de la cellule
            rar = f_xs.render(item.get("rarity", "")[:3], True, col)
            screen.blit(rar, (cx + CELL//2 - rar.get_width()//2, cy_item + CELL - 13))

        rows_used = (len(items) + COLS_P - 1) // COLS_P
        py += rows_used * (CELL + 6) + 4
    else:
        no_eq = f_xs.render("Aucun equipement obtenu.", True, (80, 60, 100))
        screen.blit(no_eq, (pop.centerx - no_eq.get_width()//2, py))
        py += no_eq.get_height() + 8

    # Heros droppe (mode infini vague 20+)
    hero_drops = loot.get("hero_drop", [])
    if hero_drops:
        import theme as _th2
        hd_lbl = f_xs.render("Heros obtenus :", True, (140, 100, 200))
        screen.blit(hd_lbl, (pop.x + 16, py))
        py += hd_lbl.get_height() + 4
        for hd in hero_drops:
            col = tuple(hd.get("color", (180, 180, 180)))
            hd_s = f_sm.render(f"{hd['name']}  [{hd['rarity']}]", True, col)
            screen.blit(hd_s, (pop.x + 16, py))
            py += hd_s.get_height() + 3

    # Bouton Continuer
    btn_w, btn_h = 160, 36
    btn = pygame.Rect(pop.centerx - btn_w//2, pop.bottom - btn_h - 14, btn_w, btn_h)
    hov = btn.collidepoint(mx, my)
    _theme.draw_panel(screen, btn,
                      color=(40, 20, 70) if hov else (25, 12, 45),
                      border_color=(180, 100, 255) if hov else (100, 60, 160),
                      radius=_theme.RADIUS_MD, border_w=2)
    cont = f_lbl.render("Continuer", True, (220, 180, 255) if hov else (160, 120, 220))
    screen.blit(cont, (btn.centerx - cont.get_width()//2,
                       btn.centery - cont.get_height()//2))

    return clicked and hov
    """
    Dessine le bouton de compétence ultime en bas à droite de la grille.
    Cliquable (ou touche Q). Affiche cooldown + durée restante si actif.
    """
    import math as _math
    CHAR_COLORS = {"eren": (213, 90, 48), "mikasa": (127, 119, 221), "erwin": (29, 158, 117)}
    CHAR_ICONS  = {"eren": "eren_normal.png", "mikasa": "mikasa_normal.png", "erwin": "erwin_normal.png"}

    info        = gs["ultimate_info"]
    char        = info["char"]
    name        = info["name"]
    color       = CHAR_COLORS.get(char, (200, 160, 30))
    cooldown    = gs.get("ultimate_cooldown", 0)
    cooldown_max = gs.get("ultimate_cooldown_max", 1)
    active      = gs.get("ultimate_active", False)
    ult_timer   = gs.get("ultimate_timer", 0)
    ult_dur     = _get_ultimate_duration(char)
    ready       = not active and cooldown <= 0

    BTN  = 64
    PAD  = 8
    bx   = offset_x + GRID_WIDTH - BTN - PAD
    by   = offset_y + GRID_HEIGHT - BTN - PAD

    btn_rect = pygame.Rect(bx, by, BTN, BTN)
    tick     = pygame.time.get_ticks()

    # Fond
    if active:
        pulse = int(40 + 30 * _math.sin(tick * 0.008))
        theme_col = (*color, 120 + pulse)
        import theme as _theme
        _theme.draw_rect_alpha(screen, theme_col, btn_rect, radius=12)
        pygame.draw.rect(screen, color, btn_rect, 3, border_radius=12)
    elif ready:
        pulse = int(20 + 15 * _math.sin(tick * 0.005))
        import theme as _theme
        _theme.draw_rect_alpha(screen, (*color, 60 + pulse), btn_rect, radius=12)
        pygame.draw.rect(screen, color, btn_rect, 2, border_radius=12)
    else:
        import theme as _theme
        _theme.draw_rect_alpha(screen, (20, 15, 10, 200), btn_rect, radius=12)
        pygame.draw.rect(screen, (70, 60, 45), btn_rect, 2, border_radius=12)

    # Icône personnage (petit sprite)
    import theme as _theme
    icon = _theme.load_sprite(CHAR_ICONS.get(char, ""), (BTN - 10, BTN - 10))
    if icon:
        tmp = icon.copy()
        if not ready and not active:
            tmp.set_alpha(80)
        screen.blit(tmp, (bx + 5, by + 5))

    # Arc de cooldown (cercle) par-dessus si en recharge
    if not ready and not active:
        ratio = 1.0 - (cooldown / max(cooldown_max, 1))
        arc_rect = pygame.Rect(bx + 4, by + 4, BTN - 8, BTN - 8)
        # Overlay sombre
        dark_surf = pygame.Surface((BTN, BTN), pygame.SRCALPHA)
        pygame.draw.rect(dark_surf, (0, 0, 0, 150), dark_surf.get_rect(), border_radius=12)
        screen.blit(dark_surf, (bx, by))
        # Texte cooldown
        f_cd = pygame.font.SysFont("arial", 18, bold=True)
        cd_txt = f_cd.render(f"{int(cooldown)}s", True, (220, 200, 160))
        screen.blit(cd_txt, (bx + BTN//2 - cd_txt.get_width()//2,
                             by + BTN//2 - cd_txt.get_height()//2))

    # Durée restante si actif
    if active:
        f_dur = pygame.font.SysFont("arial", 14, bold=True)
        dur_txt = f_dur.render(f"{ult_timer:.1f}s", True, (255, 255, 200))
        screen.blit(dur_txt, (bx + BTN//2 - dur_txt.get_width()//2, by - 18))

    # Label nom + touche
    f_lbl = pygame.font.SysFont("arial", 10)
    lbl = f_lbl.render(f"[Q] {name[:12]}", True, color if ready or active else (80, 70, 55))
    screen.blit(lbl, (bx + BTN//2 - lbl.get_width()//2, by + BTN + 3))

    # Click souris sur le bouton
    if clicked and btn_rect.collidepoint(mx, my) and ready:
        gs["ultimate_active"]   = True
        gs["ultimate_cooldown"] = gs["ultimate_cooldown_max"]
        gs["ultimate_timer"]    = _get_ultimate_duration(char)
        _apply_ultimate_start(gs)


def _draw_ultimate_button(screen, gs, offset_x, offset_y, mx, my, clicked):
    """
    Dessine le bouton de competence ultime en bas a droite de la grille.
    Activable par clic ou touche Q.
    """
    import math as _math
    CHAR_COLORS = {"eren": (213, 90, 48), "mikasa": (127, 119, 221), "erwin": (29, 158, 117)}
    CHAR_ICONS  = {"eren": "eren_normal.png", "mikasa": "mikasa_normal.png", "erwin": "erwin_normal.png"}

    info         = gs["ultimate_info"]
    char         = info["char"]
    name         = info["name"]
    color        = CHAR_COLORS.get(char, (200, 160, 30))
    cooldown     = gs.get("ultimate_cooldown", 0)
    cooldown_max = gs.get("ultimate_cooldown_max", 1)
    active       = gs.get("ultimate_active", False)
    ult_timer    = gs.get("ultimate_timer", 0)
    ready        = not active and cooldown <= 0

    BTN  = 64
    PAD  = 8
    bx   = offset_x + GRID_WIDTH - BTN - PAD
    by   = offset_y + GRID_HEIGHT - BTN - PAD

    btn_rect = pygame.Rect(bx, by, BTN, BTN)
    tick     = pygame.time.get_ticks()

    import theme as _theme
    if active:
        pulse = int(40 + 30 * _math.sin(tick * 0.008))
        _theme.draw_rect_alpha(screen, (*color, 120 + pulse), btn_rect, radius=12)
        pygame.draw.rect(screen, color, btn_rect, 3, border_radius=12)
    elif ready:
        pulse = int(20 + 15 * _math.sin(tick * 0.005))
        _theme.draw_rect_alpha(screen, (*color, 60 + pulse), btn_rect, radius=12)
        pygame.draw.rect(screen, color, btn_rect, 2, border_radius=12)
    else:
        _theme.draw_rect_alpha(screen, (20, 15, 10, 200), btn_rect, radius=12)
        pygame.draw.rect(screen, (70, 60, 45), btn_rect, 2, border_radius=12)

    icon = _theme.load_sprite(CHAR_ICONS.get(char, ""), (BTN - 10, BTN - 10))
    if icon:
        tmp = icon.copy()
        if not ready and not active:
            tmp.set_alpha(80)
        screen.blit(tmp, (bx + 5, by + 5))

    if not ready and not active:
        dark_surf = pygame.Surface((BTN, BTN), pygame.SRCALPHA)
        pygame.draw.rect(dark_surf, (0, 0, 0, 150), dark_surf.get_rect(), border_radius=12)
        screen.blit(dark_surf, (bx, by))
        f_cd = pygame.font.SysFont("arial", 18, bold=True)
        cd_txt = f_cd.render(f"{int(cooldown)}s", True, (220, 200, 160))
        screen.blit(cd_txt, (bx + BTN//2 - cd_txt.get_width()//2,
                             by + BTN//2 - cd_txt.get_height()//2))

    if active:
        f_dur = pygame.font.SysFont("arial", 14, bold=True)
        dur_txt = f_dur.render(f"{ult_timer:.1f}s", True, (255, 255, 200))
        screen.blit(dur_txt, (bx + BTN//2 - dur_txt.get_width()//2, by - 18))

    f_lbl = pygame.font.SysFont("arial", 10)
    lbl = f_lbl.render(f"[Q] {name[:12]}", True, color if ready or active else (80, 70, 55))
    screen.blit(lbl, (bx + BTN//2 - lbl.get_width()//2, by + BTN + 3))

    if clicked and btn_rect.collidepoint(mx, my) and ready:
        gs["ultimate_active"]   = True
        gs["ultimate_cooldown"] = gs["ultimate_cooldown_max"]
        gs["ultimate_timer"]    = _get_ultimate_duration(char)
        _apply_ultimate_start(gs)


def main():
    render.init_pygame()
    # Chargement des sprites optionnels (silencieux si les fichiers sont absents)
    render.load_wall_image()
    Tower.load_sprites()
    Trap.load_sprites()
    # Préchargement des sprites de projectiles (silencieux si fichiers absents)
    from config import ALL_TOWER_TYPES
    for _pt in ALL_TOWER_TYPES + ["player"]:
        Projectile._load_sprite(_pt)

    from title_screen import run_title_screen
    from main_ui import run_main_ui
    from ui import draw_levelup_banner

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