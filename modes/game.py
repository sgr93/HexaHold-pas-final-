"""
game.py

Point d'entrée du jeu. Initialisation pygame, écrans de navigation,
puis boucle principale qui délègue à :
  - modes/game_state.py       → état initial, vagues, quêtes, récompenses
  - modes/game_loop_update.py → update entités, ultime, kills, level-up
  - modes/game_loop_render.py → rendu, HUD, placement, pause, fins de partie
"""

import time
import pygame

from core.config import (
    ALL_TOWER_TYPES, BACKGROUND_COLOR, GRID_SIZE,
    GRID_WIDTH, GRID_HEIGHT, INV_BAR_HEIGHT,
)
import ui.render as render
from ui.render import GridCache
from core.entities import Tower, Trap, Projectile
import core.save_data as sd
from modes.game_music import play_title_music, play_menu_music, play_game_music
from modes.game_passives import _apply_ultimate_start, _get_ultimate_duration
from modes.game_state import (
    _init_new_game, _inject_mission_context, _make_known_towers,
    _resume_from_pause, collect_win_reward, evaluate_mission_objectives,
)
from modes.game_loop_update import process_levelup, update_entities, update_waves
from modes.game_loop_render import (
    handle_levelup_banner, handle_pause_screen, handle_tower_placement,
    render_hud, render_inventory, render_passives_and_ultimate, render_world,
)
from modes.game_end_screens import handle_end_screens
from modes.title_screen import run_title_screen
from modes.main_ui import run_main_ui
from ui.ui import draw_mission_objectives, draw_toasts


# Buffs disponibles au level-up — la clé est le label affiché, la valeur est l'identifiant interne
BUFF_DEFS = {
    "Vitesse Joueur": ("player_speed",),
    "Dégâts Joueur":  ("player_damage",),
    "Vit. Attaque":   ("player_cooldown",),
    "HP +20":         ("player_hp",),
    "Dégâts Tours":   ("tower_damage",),
    "Vit. Tours":     ("tower_cooldown",),
}


def main():
    # Initialisation pygame et chargement des sprites — tout ça avant d'afficher quoi que ce soit
    render.init_pygame()
    render.load_wall_image()
    Tower.load_sprites()
    Trap.load_sprites()
    for pt in ALL_TOWER_TYPES + ["player"]:
        Projectile._load_sprite(pt)

    current_save = sd.load()
    play_title_music(current_save.get("music_volume", 0.8))

    # Écran titre — si le joueur ferme sans jouer, on sort proprement
    title_result, current_save = run_title_screen(render.screen, render.clock, current_save)
    if title_result != "play":
        pygame.quit()
        return

    play_menu_music(current_save.get("music_volume", 0.8))
    chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
    if chosen_level is None:
        pygame.quit()
        return

    play_game_music(current_save.get("music_volume", 0.8))

    grid_cache   = GridCache()
    gs           = _init_new_game(chosen_level, current_save, grid_cache)
    _inject_mission_context(gs, chosen_level, current_save)
    known_towers = _make_known_towers(current_save)
    pause_start  = None
    running      = True

    # BOUCLE PRINCIPALE
    while running:
        render.clock.tick(60)
        render.screen.fill(BACKGROUND_COLOR)

        # Background optionnel derrière la grille — scalé à la taille de la fenêtre
        bg = render.get_grid_bg()
        if bg:
            render.screen.blit(pygame.transform.scale(bg, render.screen.get_size()), (0, 0))

        # EVENTS
        mouse_clicked_left = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Escape désélectionne d'abord l'item, ferme le jeu seulement si rien de sélectionné
                    if gs["selected_item"]:
                        gs["selected_item"] = None
                    elif not gs["levelup_pending"]:
                        running = False

                elif event.key == pygame.K_p:
                    # Pause au clavier — même logique que le bouton dans le HUD
                    if (gs["game_started"] and not gs["game_over"]
                            and not gs["game_win"] and not gs["levelup_pending"]):
                        if not gs["paused"]:
                            gs["paused"] = True
                            pause_start  = time.time()
                        else:
                            gs["paused"] = False
                            pause_start  = _resume_from_pause(gs, pause_start)

                elif event.key == pygame.K_q:
                    # Touche Q pour l'ultime — toutes les conditions doivent être réunies
                    if (gs.get("ultimate_info") and not gs.get("ultimate_active")
                            and gs.get("ultimate_cooldown", 0) <= 0
                            and gs.get("game_started") and not gs.get("paused")
                            and not gs.get("game_over") and not gs.get("game_win")):
                        gs["ultimate_active"]   = True
                        gs["ultimate_cooldown"] = gs["ultimate_cooldown_max"]
                        gs["ultimate_timer"]    = _get_ultimate_duration(gs["ultimate_info"]["char"])
                        _apply_ultimate_start(gs)

            elif event.type == pygame.VIDEORESIZE:
                # La grille se recentre automatiquement grâce aux offsets calculés plus bas
                render.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                grid_cache.invalidate()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked_left = True

        # COORDONNÉES — recalculées à chaque frame pour supporter le redimensionnement
        win_w, win_h = render.screen.get_size()
        offset_x     = (win_w - GRID_WIDTH) // 2
        offset_y     = max(40, (win_h - INV_BAR_HEIGHT - GRID_HEIGHT) // 2)
        mx, my       = pygame.mouse.get_pos()
        gx           = (mx - offset_x) // GRID_SIZE
        gy           = (my - offset_y) // GRID_SIZE

        # ÉTAT GLOBAL — game_over peut être déclenché par la base ou par la mort du joueur
        if not gs["game_over"]:
            gs["game_over"] = gs["goal"].vie <= 0
        if not gs["game_over"] and not gs["player"].alive:
            gs["game_over"] = True

        if gs["game_win"]:
            collect_win_reward(gs)  # Protégé en interne contre les appels multiples

        # On gèle les timers tant que le joueur n'a pas posé sa première tour
        current_time = time.time()
        if not gs["game_started"]:
            gs["last_wave_time"]   = current_time
            gs["last_enemy_spawn"] = current_time
            gs["last_regen_time"]  = current_time

        # Toasts : décrémenter et nettoyer les expirés
        for toast in gs.get("toasts", [])[:]:
            toast["ttl"] -= 1
            if toast["ttl"] <= 0:
                gs["toasts"].remove(toast)

        # is_frozen regroupe tous les états où la logique de jeu doit être suspendue
        is_frozen = gs["paused"] or gs["game_over"] or gs["game_win"] or gs["levelup_pending"]

        # UPDATE LOGIQUE
        if not is_frozen:
            update_waves(gs, current_time)

        if gs["game_started"] and not gs["game_over"] and not is_frozen:
            update_entities(gs, current_time)
        elif gs["game_over"] or gs["game_win"]:
            # On vide les projectiles en vol pour éviter qu'ils continuent après la fin
            gs["projectiles"].clear()

        pause_start = process_levelup(gs, known_towers, BUFF_DEFS, pause_start)

        # RENDU
        render_world(render.screen, gs, grid_cache, offset_x, offset_y)
        evaluate_mission_objectives(gs)  # Après le rendu pour avoir les données à jour

        pause_toggle = render_hud(render.screen, gs, offset_x, offset_y, mx, my, mouse_clicked_left)
        if pause_toggle == "toggle":
            if not gs["paused"]:
                gs["paused"] = True
                pause_start  = time.time()
            else:
                gs["paused"] = False
                pause_start  = _resume_from_pause(gs, pause_start)

        inv_rects, in_inv_area, in_grid_area, available_towers = render_inventory(
            render.screen, gs, win_w, win_h, mx, my, mouse_clicked_left, offset_x, offset_y
        )
        handle_tower_placement(
            render.screen, gs, grid_cache, gx, gy, mx, my,
            offset_x, offset_y, in_grid_area, in_inv_area,
            available_towers, mouse_clicked_left,
        )

        pause_start = handle_levelup_banner(
            render.screen, gs, known_towers, BUFF_DEFS, mx, my, mouse_clicked_left, pause_start
        )

        gs, chosen_level, current_save, known_towers, pause_start, running = handle_pause_screen(
            render.screen, gs, grid_cache, current_save, chosen_level,
            mx, my, mouse_clicked_left, pause_start,
        )
        if not running:
            break

        draw_toasts(render.screen, gs.get("toasts", []))
        render_passives_and_ultimate(render.screen, gs, offset_x, offset_y, mx, my, mouse_clicked_left)

        # Objectifs de mission affichés seulement si on est en mode histoire avec des objectifs
        mc = gs.get("mission_context")
        if mc and mc.get("objectives"):
            draw_mission_objectives(render.screen, offset_x, offset_y, mc["objectives"])

        gs, chosen_level, current_save, known_towers, pause_start, running = handle_end_screens(
            render.screen, gs, grid_cache, current_save, chosen_level,
            mx, my, mouse_clicked_left, pause_start,
        )
        if not running:
            break

        pygame.display.flip()

    pygame.quit()