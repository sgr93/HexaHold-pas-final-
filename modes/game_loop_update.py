"""
modes/game_loop_update.py

Toute la logique de mise à jour par frame : vagues et spawn d'ennemis,
update entités, régénération HP, compétence ultime, kills, level-up.
"""

import time
import random
import pygame

from core.config import (
    ALL_TOWER_TYPES, BOSS_DURATION, DIFFICULTY_LEVELS, PLAYER_HP_REGEN,
    TOWER_SLOT_COUNT, WAVE_DURATION, XP_GROWTH_FACTOR, XP_REWARD_BOSS, XP_REWARD_NORMAL,
)
import core.save_data as sd
import modes.histoire as hist_mod
from core.entities import Enemy
from modes.game_passives import (
    _apply_sasha_passive_on_wave, _apply_ultimate_end,
    _apply_ultimate_start, _get_ultimate_duration,
)
from modes.game_infinite import _give_infinite_rewards
from modes.game_state import check_and_notify_quests, pick_levelup_choices, start_new_wave


# VAGUES ET SPAWN

def update_waves(gs, current_time):
    """
    Gère les timers de vague, le spawn d'ennemis, la transition boss et la fin de vague.
    Tout le cycle de vie d'une vague passe par ici.
    """
    gs_enemies = gs["enemies"]

    if not gs["boss_active"]:
        gs["wave_timer"] = max(0, WAVE_DURATION - (current_time - gs["last_wave_time"]))

    # L'intervalle de spawn se réduit au fil des vagues
    if gs["game_started"] and gs["wave_number"] <= gs["max_waves"]:
        wn = gs["wave_number"]
        if gs.get("infinite_mode"):
            # accélération plus rapide en mode infini
            gs["enemy_spawn_interval"] = max(0.1, 0.8 - 0.02 * (wn - 1))
        else:
            gs["enemy_spawn_interval"] = max(
                0.2,
                DIFFICULTY_LEVELS[gs["difficulty"]]["spawn_interval"] - 0.05 * (wn - 1)
            )

    # Spawn d'un ennemi si le timing est bon et qu'il en reste à faire apparaître
    if (gs["game_started"]
            and not gs["boss_active"]
            and gs["enemies_spawned_this_wave"] < gs["max_enemies_this_wave"]
            and current_time - gs["last_enemy_spawn"] >= gs["enemy_spawn_interval"]):
        is_fast = random.random() < 0.15  # 15% de chance d'avoir un ennemi rapide
        wn = gs["wave_number"]
        if gs.get("infinite_mode"):
            # augmentation de plus en plus rapides des HP en mode infini
            base_hp = int((15 + wn * 6) * (1.0 + wn * 0.08))
        else:
            base_hp = 15 + (wn - 1) * 4
        hp = int(base_hp * gs["enemy_hp_mult"])
        gs_enemies.append(Enemy(hp=hp, speed=1.6 if is_fast else 1.0, is_fast=is_fast))
        gs["enemies_spawned_this_wave"] += 1
        gs["last_enemy_spawn"]           = current_time

    alive_enemies = [e for e in gs_enemies if not e.is_dead and not e._dying]
    has_boss      = any(e.is_boss for e in alive_enemies)

    # Tous les ennemis normaux sont morts —-> apparition du boss
    if (not gs["boss_active"]
            and gs["enemies_spawned_this_wave"] >= gs["max_enemies_this_wave"]
            and not alive_enemies):
        _spawn_boss(gs, current_time)
        alive_enemies = [e for e in gs_enemies if not e.is_dead and not e._dying]
        has_boss      = any(e.is_boss for e in alive_enemies)

    if gs["boss_active"]:
        gs["boss_timer"] = max(0, BOSS_DURATION - (current_time - gs["boss_start_time"]))

    if gs["boss_active"] and not has_boss:
        _on_boss_defeated(gs)

    # Victoire : plus de vagues et plus d'ennemis vivants
    if gs["wave_number"] > gs["max_waves"] and not alive_enemies:
        gs["game_win"] = True


def _spawn_boss(gs, current_time):
    """
    Fait apparaître le(s) boss de fin de vague.
    En mode histoire, la dernière vague d'un chapitre spawne un boss spécial plus costaud.
    """
    gs["boss_active"]     = True
    gs["boss_start_time"] = current_time
    wn       = gs["wave_number"]
    is_final = (not gs.get("infinite_mode")) and (wn == gs["max_waves"])

    # On vérifie si c'est la dernière mission du chapitre pour le boss de chapitre
    mc_ctx = gs.get("mission_context")
    is_chapter_final_boss = False
    if is_final and mc_ctx is not None and not gs.get("infinite_mode"):
        ch  = mc_ctx.get("chapter", -1)
        msn = mc_ctx.get("mission", -1)
        try:
            last_msn = hist_mod.get_last_mission_index(ch)
            is_chapter_final_boss = (msn == last_msn)
        except Exception:
            pass

    if is_final:
        if is_chapter_final_boss:
            # Boss de fin de chapitre — beaucoup plus gros, avec une skin spéciale
            boss_hp = int((1000 + 200 * (wn - 1)) * gs["enemy_hp_mult"])
            gs["enemies"].append(Enemy(
                hp=boss_hp, speed=0.25, radius=72,
                is_boss=True, is_final_boss=True, is_chapter_boss=True,
                chapter_idx=mc_ctx.get("chapter") if mc_ctx else None,
            ))
        else:
            boss_hp = int((500 + 100 * (wn - 1)) * gs["enemy_hp_mult"])
            gs["enemies"].append(Enemy(hp=boss_hp, speed=0.3, radius=50,
                                       is_boss=True, is_final_boss=True))
    else:
        if gs.get("infinite_mode"):
            # En infini : boss de plus en plus variés selon la vague
            if wn % 5 == 0:
                # Titan Colossal tous les 5 vagues les HP s'accumulent avec les apparitions
                colossal_count = wn // 5
                boss_hp = int((500 + 200 * wn + wn * wn * 10) * gs["enemy_hp_mult"] * colossal_count)
                gs["enemies"].append(Enemy(hp=boss_hp, speed=0.2, radius=80, is_final_boss=True))
            if wn % 10 == 0:
                # Titan Féminin tous les 10 vagues il s'ajoute au Colossal ces vagues-là
                boss_hp = int((300 + 150 * wn + wn * wn * 5) * gs["enemy_hp_mult"])
                gs["enemies"].append(Enemy(hp=boss_hp, speed=0.3, radius=60, is_chapter_boss=True, chapter_idx=0))
            else:
                boss_hp = int((100 + 80 * wn + wn * wn * 3) * gs["enemy_hp_mult"])
                gs["enemies"].append(Enemy(hp=boss_hp, speed=0.45, radius=25, is_boss=True))
        else:
            boss_hp = int((150 + 50 * wn) * gs["enemy_hp_mult"])
            gs["enemies"].append(Enemy(hp=boss_hp, speed=0.45, radius=25, is_boss=True))


def _on_boss_defeated(gs):
    """
    Appelé dès que le boss vient d'être tué.
    Distribue les récompenses de vague et passe à la suivante.
    """
    gs["boss_active"] = False
    wn = gs["wave_number"]

    if gs.get("infinite_mode") and gs.get("save") is not None:
        save_ref = gs["save"]
        done_set = gs.get("infinite_wave_reward_done", set())
        # Le set done_set évite de distribuer les récompenses deux fois si _on_boss_defeated
        # est appelé par erreur plusieurs fois sur la même vague
        if wn not in done_set:
            done_set.add(wn)
            gs["infinite_wave_reward_done"] = done_set
            _give_infinite_rewards(gs, wn, save_ref)
            if wn > save_ref.get("max_wave_reached", 0):
                save_ref["max_wave_reached"] = wn

    # En mode histoire, la dernière vague déclenche directement la victoire
    if not gs.get("infinite_mode") and wn == gs["max_waves"]:
        gs["game_win"] = True
        return

    # On passe les clés de vague à start_new_wave via un sous-dict pour éviter
    # de lui passer tout gs c'est plus propre et plus facile à tester
    sl = {
        "wave_number":               gs["wave_number"],
        "last_wave_time":            gs["last_wave_time"],
        "last_enemy_spawn":          gs["last_enemy_spawn"],
        "mobs_killed_this_wave":     gs["mobs_killed_this_wave"],
        "enemies_spawned_this_wave": gs["enemies_spawned_this_wave"],
        "max_enemies_this_wave":     gs["max_enemies_this_wave"],
        "boss_active":               gs["boss_active"],
        "wave_timer":                gs["wave_timer"],
        "boss_timer":                gs["boss_timer"],
    }
    start_new_wave(sl)
    gs.update(sl)
    _apply_sasha_passive_on_wave(gs)


# UPDATE ENTITÉS

def update_entities(gs, current_time):
    """
    Met à jour toutes les entités du jeu pour cette frame.
    L'ordre ici compte : le joueur en premier, puis les ennemis, puis les tours.
    """
    gs_player      = gs["player"]
    gs_enemies     = gs["enemies"]
    gs_towers      = gs["towers"]
    gs_projectiles = gs["projectiles"]
    gs_goal        = gs["goal"]
    gs_grid        = gs["grid"]

    keys_pressed = pygame.key.get_pressed()
    gs_player.update(keys_pressed, gs_enemies, gs_projectiles, False, gs_grid)

    _update_regen(gs, gs_player, current_time)
    _update_ultimate(gs)
    _update_enemies(gs, gs_enemies, gs_grid, gs_goal, gs_player)

    gs_goal.update()
    for t in gs_towers:
        t.update(gs_enemies, gs_projectiles)

    # On itère à l'envers pour pouvoir supprimer en place sans décaler les indices
    i = len(gs_projectiles) - 1
    while i >= 0:
        gs_projectiles[i].update()
        if not gs_projectiles[i].alive:
            gs_projectiles.pop(i)
        i -= 1


def _update_regen(gs, player, current_time):
    """
    Applique la régénération HP du joueur.
    On accumule les fractions de HP pour ne perdre aucun point de regen entre les frames.
    """
    regen_dt          = current_time - gs["last_regen_time"]
    gs["last_regen_time"] = current_time
    total_regen       = PLAYER_HP_REGEN + getattr(player, "hp_regen", 0.0)
    gs["regen_accumulator"] += total_regen * regen_dt
    if gs["regen_accumulator"] >= 1.0:
        heal = int(gs["regen_accumulator"])
        player.vie = min(player.max_hp, player.vie + heal)
        gs["regen_accumulator"] -= heal


def _update_ultimate(gs):
    """
    Met à jour le timer de l'ultime et le cooldown.
    Le slow des ennemis est appliqué ici plutôt que dans les ennemis eux-mêmes
    pour centraliser la logique dans un seul endroit.
    """
    if not gs.get("ultimate_info"):
        return
    dt = 1.0 / 60.0

    if gs["ultimate_active"]:
        gs["ultimate_timer"] = max(0, gs["ultimate_timer"] - dt)
        if gs["ultimate_timer"] <= 0:
            _apply_ultimate_end(gs)
        # Slow appliqué une seule fois par ennemi
        if gs.get("_ult_slow_enemies"):
            for e in gs["enemies"]:
                if not getattr(e, "_ult_slowed", False):
                    e.speed      = max(0.3, e.speed * 0.5)
                    e._ult_slowed = True
    else:
        # Nettoyage du slow quand l'ultime se termine
        for e in gs["enemies"]:
            if getattr(e, "_ult_slowed", False):
                e.speed       = getattr(e, "base_speed", e.speed * 2)
                e._ult_slowed = False
        if gs["ultimate_cooldown"] > 0:
            gs["ultimate_cooldown"] = max(0, gs["ultimate_cooldown"] - dt)


def _update_enemies(gs, gs_enemies, gs_grid, gs_goal, gs_player):
    """
    Update chaque ennemi et comptabilise les kills.
    On sauvegarde les stats kills en batch plutôt qu'un sd.save() par ennemi tué.
    """
    kills_this_frame = 0
    for e in gs_enemies[:]:
        e.update(gs_grid, gs_goal, player=gs_player)
        if not e.is_dead and not e._dying and e.hp <= 0:
            e.mark_dead()
        if e.is_dead:
            # Boss final tué en mode histoire = victoire immédiate
            if e.is_final_boss and not gs.get("infinite_mode"):
                gs["game_win"] = True
            gs["xp"] += XP_REWARD_BOSS if e.is_boss else XP_REWARD_NORMAL
            if not e.is_boss:
                gs["mobs_killed_this_wave"] += 1
            else:
                gs["player_buff_tokens"] += 1
            kills_this_frame += 1
            gs_enemies.remove(e)

    # Un seul sd.save() pour tous les kills de la frame
    if kills_this_frame > 0 and gs.get("save") is not None:
        gs["save"]["enemies_killed"] = gs["save"].get("enemies_killed", 0) + kills_this_frame
        mode_key = "infini" if gs.get("infinite_mode") else "histoire"
        gs["save"][f"{mode_key}_enemies_killed"] = (
            gs["save"].get(f"{mode_key}_enemies_killed", 0) + kills_this_frame
        )
        check_and_notify_quests(gs)
        sd.save(gs["save"])


# LEVEL-UP

def process_levelup(gs, known_towers, buff_defs, pause_start):
    """
    Vérifie si le joueur monte de niveau et déclenche la bannière de choix.
    La boucle while gère les level-ups multiples d'un coup (rare mais possible).
    Retourne le nouveau pause_start.
    """
    while gs["xp"] >= gs["xp_to_next_level"] and not gs["levelup_pending"]:
        gs["xp"]              -= gs["xp_to_next_level"]
        gs["level"]           += 1
        gs["xp_to_next_level"] = int(gs["xp_to_next_level"] * XP_GROWTH_FACTOR)
        gs["levelup_pending"]  = True
        gs["levelup_choices"]  = pick_levelup_choices(known_towers, count=3)
        if not gs["paused"]:
            pause_start = time.time()
    return pause_start


def apply_levelup_choice(gs, chosen, known_towers, buff_defs):
    """
    Applique le buff choisi dans la bannière de level-up.
    Si c'est une tour, on l'ajoute à l'inventaire. Sinon c'est un buff stat.
    """
    gs_inv    = gs["inventory"]
    gs_towers = gs["towers"]

    # Tour choisie — on l'ajoute directement à l'inventaire
    if chosen in known_towers:
        gs_inv[chosen] = gs_inv.get(chosen, 0) + 1
        return

    if chosen not in buff_defs:
        return

    from modes.game_towers import apply_all_tower_bonuses
    key    = buff_defs[chosen][0]
    player = gs["player"]

    if key == "player_speed":
        player.speed += 0.3
    elif key == "player_damage":
        player.damage += 2
    elif key == "player_cooldown":
        player.attack_cooldown = max(5, player.attack_cooldown - 2)
    elif key == "player_hp":
        player.max_hp += 20
        player.vie = min(player.max_hp, player.vie + 20)
    elif key == "tower_damage":
        gs["tower_damage_bonus"] += 1
        apply_all_tower_bonuses(gs_towers, gs["tower_damage_bonus"], gs["tower_cooldown_bonus"])
    elif key == "tower_cooldown":
        gs["tower_cooldown_bonus"] += 1
        apply_all_tower_bonuses(gs_towers, gs["tower_damage_bonus"], gs["tower_cooldown_bonus"])