"""
modes/game_loop_render.py

Tout ce qui est affiché dans la boucle principale : grille et entités, HUD,
inventaire, placement de tours, bannière level-up, écran pause.
Les écrans de fin de partie sont dans modes/game_end_screens.py.
"""

import pygame
from core.config import (
    GRID_HEIGHT, GRID_WIDTH, INV_BAR_HEIGHT,
    SPAWN_ZONE_HEIGHT, SPAWN_ZONE_WIDTH, SPAWN_ZONE_X, SPAWN_ZONE_Y, START,
)
import ui.render as render
from ui.ui import (
    draw_ghost, draw_hud, draw_inventory, draw_levelup_banner,
    draw_pause_button, draw_pause_screen, draw_start_hint,
)
import core.save_data as sd
import modes.histoire as hist_mod
from modes.game_towers import (
    _is_matching_upgrade_target, cells_for_item, make_can_place, place_tower_on_grid,
)
from modes.game_passives import (
    _apply_armin_passive_on_build, _apply_eren_passive,
    _apply_levi_passive_on_upgrade, _apply_mikasa_passive,
)
from modes.game_infinite import _draw_ultimate_button
from modes.game_music import play_game_music, play_menu_music
from modes.game_state import (
    _init_new_game, _inject_mission_context, _make_known_towers,
    _resume_from_pause, check_and_notify_quests,
)
from modes.game_loop_update import apply_levelup_choice
from modes.main_ui import run_main_ui


# RENDU GRILLE ET ENTITÉS

def render_world(screen, gs, grid_cache, offset_x, offset_y):
    """Dessine la grille, les entités et le joueur."""
    grid_cache.draw(screen, gs["grid"], offset_x, offset_y, towers=gs["towers"])

    # Zone de spawn en surbrillance jaune tant que le joueur n'a pas encore posé de tour
    if not gs["game_started"]:
        spawn_surf = pygame.Surface((SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT), pygame.SRCALPHA)
        spawn_surf.fill((255, 255, 0, 60))
        screen.blit(spawn_surf, (offset_x + SPAWN_ZONE_X, offset_y + SPAWN_ZONE_Y))

    # L'ordre ici est volontaire : pièges en dessous des ennemis, tours et projectiles par-dessus,
    # et le joueur tout en haut pour qu'il soit toujours visible
    for t in gs["towers"]:
        if hasattr(t, "trap_type"):
            t.draw(screen, offset_x, offset_y)
    for e in gs["enemies"]:
        e.draw(screen, offset_x, offset_y)
    gs["goal"].draw(screen, offset_x, offset_y)
    for t in gs["towers"]:
        if hasattr(t, "tower_type"):
            t.draw(screen, offset_x, offset_y)
    for p in gs["projectiles"]:
        p.draw(screen, offset_x, offset_y)
    gs["player"].draw(screen, offset_x, offset_y)


# HUD ET OVERLAYS

def render_hud(screen, gs, offset_x, offset_y, mx, my, mouse_clicked_left):
    """
    Affiche le HUD complet et le bouton pause.
    Retourne "toggle" si le bouton pause est cliqué, sinon None.
    """
    player = gs["player"]
    draw_hud(
        screen, render.font, render.big_font,
        gs["level"], gs["xp"], gs["xp_to_next_level"],
        gs["wave_number"], gs["max_waves"],
        gs["mobs_killed_this_wave"], gs["max_enemies_this_wave"],
        gs["boss_active"], gs["boss_timer"], gs["wave_timer"],
        offset_x, offset_y,
        player_hp=player.vie, player_max_hp=player.max_hp,
    )
    # Le bouton pause n'a rien à faire pendant un level-up ou sur les écrans de fin —
    # ça évite des états bizarres si le joueur clique au mauvais moment
    if gs["game_started"] and not gs["game_over"] and not gs["game_win"] and not gs["levelup_pending"]:
        pause_btn_rect = draw_pause_button(screen, offset_x, offset_y, mx, my)
        if mouse_clicked_left and pause_btn_rect.collidepoint(mx, my):
            return "toggle"
    # Hint "pose une tour pour commencer" — affiché seulement avant le premier placement
    if not gs["game_started"]:
        draw_start_hint(screen, render.font, offset_x, offset_y)
    return None


def render_passives_and_ultimate(screen, gs, offset_x, offset_y, mx, my, mouse_clicked_left):
    """Applique les effets visuels des passifs héros et affiche le bouton ultime si dispo."""
    if not gs.get("game_started") or gs.get("game_over") or gs.get("game_win"):
        return
    hero = gs.get("selected_hero", "eren")
    # On n'appelle que le passif du héros sélectionné — chacun a sa propre logique visuelle
    if hero == "mikasa":
        _apply_mikasa_passive(gs, screen, gs["player"], gs.get("enemies", []), offset_x, offset_y)
    elif hero == "eren":
        _apply_eren_passive(gs, gs.get("towers", []), gs["player"])
    # Bouton ultime uniquement si le héros en a un (ultimate_info est None sinon)
    if gs.get("ultimate_info"):
        _draw_ultimate_button(screen, gs, offset_x, offset_y, mx, my, mouse_clicked_left)


# INVENTAIRE ET PLACEMENT

def render_inventory(screen, gs, win_w, win_h, mx, my, mouse_clicked_left, offset_x, offset_y):
    """
    Affiche la barre d'inventaire et gère la sélection au clic.
    Retourne (inv_rects, in_inv_area, in_grid_area, available_towers).
    """
    # On filtre les tours à 0 — inutile de les afficher dans la barre
    available_towers = {t: qty for t, qty in gs["inventory"].items() if qty > 0}

    if not available_towers:
        hint_lbl = render.font.render(
            "Choisissez vos tours via les level-up.", True, (180, 180, 180)
        )
        screen.blit(hint_lbl, (offset_x + 10, offset_y + GRID_HEIGHT + 10))

    inv_rects    = draw_inventory(screen, render.font, available_towers, gs["selected_item"], win_w, win_h)
    in_inv_area  = my >= win_h - INV_BAR_HEIGHT
    in_grid_area = (
        offset_x <= mx < offset_x + GRID_WIDTH
        and offset_y <= my < offset_y + GRID_HEIGHT
        and not in_inv_area
    )

    # Clic sur un item : le sélectionne, ou le désélectionne si c'était déjà lui
    if (mouse_clicked_left and not gs["game_over"] and not gs["game_win"]
            and not gs["paused"] and not gs["levelup_pending"] and in_inv_area):
        for item_type, rect in inv_rects.items():
            if rect.collidepoint(mx, my):
                gs["selected_item"] = None if gs["selected_item"] == item_type else item_type
                break

    return inv_rects, in_inv_area, in_grid_area, available_towers


def handle_tower_placement(screen, gs, grid_cache, gx, gy, mx, my,
                            offset_x, offset_y, in_grid_area, in_inv_area,
                            available_towers, mouse_clicked_left):
    """
    Affiche le ghost de tour et pose la tour si le clic est valide.
    Décrémente l'inventaire et sauvegarde les stats de placement.
    """
    sel = gs["selected_item"]
    if not sel or sel not in available_towers:
        return
    # Pas de placement pendant la pause, le game over ou un level-up en attente
    if gs["game_over"] or gs["paused"] or gs["levelup_pending"]:
        return

    cells        = cells_for_item(sel, gx, gy)
    can_place_fn = make_can_place(gs["grid"], START, sel)
    # is_upgrade : on pose sur une tour existante compatible plutôt que sur une case vide
    is_upgrade   = any(_is_matching_upgrade_target(t, sel, cells) for t in gs["towers"])

    if not cells:
        return
    # Ghost affiché dès que la souris est sur la grille, même sans clic
    if in_grid_area:
        draw_ghost(screen, cells, gx, gy, sel, gs["towers"], can_place_fn, offset_x, offset_y)
    if not (mouse_clicked_left and in_grid_area and not in_inv_area):
        return
    if not (is_upgrade or can_place_fn(cells)):
        return

    tower_level = gs.get("save", {}).get("towers_level", {}).get(sel, 1)
    placed = place_tower_on_grid(
        gs["grid"], gs["towers"], cells, sel, grid_cache,
        damage_bonus=gs["tower_damage_bonus"],
        cooldown_bonus=gs["tower_cooldown_bonus"],
        tower_level=tower_level,
        # Les callbacks passifs sont injectés ici plutôt que dans place_tower_on_grid
        # pour garder cette fonction agnostique du système de héros
        levi_callback=(lambda t: _apply_levi_passive_on_upgrade(gs, t))
                       if gs.get("selected_hero") == "levi" else None,
        armin_callback=(lambda towers: _apply_armin_passive_on_build(gs, towers))
                        if gs.get("selected_hero") == "armin" else None,
    )

    if placed:
        gs["player"].push_out_of_block(gs["grid"])
        gs["toasts"].append({"text": "Tour placée", "ttl": 140, "max_ttl": 140, "color": (120, 235, 140)})
        gs["game_started"] = True
        if gs.get("save") is not None:
            gs["save"]["towers_placed"] = gs["save"].get("towers_placed", 0) + 1
            # Stats séparées par mode pour les quêtes — infini et histoire ont des objectifs différents
            mode_key = "infini" if gs.get("infinite_mode") else "histoire"
            gs["save"][f"{mode_key}_towers_placed"] = gs["save"].get(f"{mode_key}_towers_placed", 0) + 1
            check_and_notify_quests(gs)
            sd.save(gs["save"])
        if sel in gs["inventory"]:
            gs["inventory"][sel] -= 1
            # Si on vient d'utiliser le dernier exemplaire, on désélectionne automatiquement
            if gs["inventory"][sel] <= 0:
                del gs["inventory"][sel]
                if gs["selected_item"] == sel:
                    gs["selected_item"] = None
    else:
        gs["toasts"].append({"text": "Impossible de poser ici", "ttl": 120, "max_ttl": 120, "color": (240, 120, 120)})


# BANNIÈRE LEVEL-UP

def handle_levelup_banner(screen, gs, known_towers, buff_defs, mx, my, mouse_clicked_left, pause_start):
    """
    Affiche la bannière de level-up et applique le choix du joueur.
    Retourne le nouveau pause_start (remis à jour après reprise).
    """
    if not gs["levelup_pending"]:
        return pause_start
    chosen = draw_levelup_banner(
        screen, render.big_font, render.font,
        gs["levelup_choices"], (mx, my), mouse_clicked_left,
    )
    if chosen:
        apply_levelup_choice(gs, chosen, known_towers, buff_defs)
        gs["levelup_pending"] = False
        # On reprend le timer de pause pour ne pas compter le temps passé sur le choix
        pause_start = _resume_from_pause(gs, pause_start)
    return pause_start


# ÉCRAN PAUSE

def handle_pause_screen(screen, gs, grid_cache, current_save, chosen_level,
                         mx, my, mouse_clicked_left, pause_start):
    """
    Affiche l'écran pause et gère les actions resume / restart / menu.
    Retourne (gs, chosen_level, current_save, known_towers, pause_start, running).
    """
    if not gs["paused"] or gs["game_over"] or gs["game_win"]:
        return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start, True

    pause_action = draw_pause_screen(
        screen, render.big_font, render.font,
        mouse_pos=(mx, my), clicked=mouse_clicked_left,
    )

    if pause_action == "resume":
        gs["paused"] = False
        pause_start  = _resume_from_pause(gs, pause_start)

    elif pause_action == "restart":
        gs["paused"] = False
        prev_mc = gs.get("mission_context")
        # En mode histoire, chosen_level doit être reconstruit depuis le contexte
        # parce qu'il peut avoir changé si on a enchaîné plusieurs missions
        if prev_mc:
            chosen_level = {
                "chapter":    prev_mc["chapter"],
                "mission":    prev_mc["mission"],
                "difficulty": gs.get("difficulty", 2),
            }
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        if prev_mc:
            gs["mission_context"] = {
                "chapter":                 prev_mc["chapter"],
                "mission":                 prev_mc["mission"],
                "objectives":              hist_mod.get_mission_objectives(prev_mc["chapter"], prev_mc["mission"]),
                "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
            }
        pause_start = None

    elif pause_action == "menu":
        gs["paused"] = False
        pause_start  = None
        play_menu_music(current_save.get("music_volume", 0.8))
        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
        if chosen_level is None:
            return gs, None, current_save, _make_known_towers(current_save), None, False
        play_game_music(current_save.get("music_volume", 0.8))
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        _inject_mission_context(gs, chosen_level, current_save)

    return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start, True
