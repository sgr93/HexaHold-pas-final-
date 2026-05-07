"""
modes/game_end_screens.py

Gestion des écrans de fin de partie selon le mode : infini (popup loot),
histoire (victoire/défaite avec objectifs), normal (game over classique).
Chaque handler renvoie le même tuple de 6 valeurs — c'est volontaire, ça
garde la boucle principale agnostique du mode en cours.
"""

import ui.render as render
from ui.ui import (
    draw_gameover_screen,
    draw_mission_complete_screen,
    draw_mission_failed_screen,
)
import core.save_data as sd
import modes.histoire as hist_mod
from modes.histoire import run_histoire
from modes.game_infinite import _collect_infinite_loot, _draw_infinite_loot_popup
from modes.game_music import play_game_music, play_menu_music
from modes.game_state import _init_new_game, _inject_mission_context, _make_known_towers
from modes.main_ui import run_main_ui


# Loot par défaut si quelque chose s'est mal passé pendant la collecte infinie
_EMPTY_LOOT = {"coins": 0, "gems": 0, "items": []}


def handle_end_screens(screen, gs, grid_cache, current_save, chosen_level,
                       mx, my, mouse_clicked_left, pause_start):
    """
    Dispatcher principal — détermine quel écran de fin afficher et délègue au bon handler.
    known_towers est calculé une seule fois ici pour éviter de le répéter dans chaque sous-fonction.
    Retourne (gs, chosen_level, current_save, known_towers, pause_start, running).
    running vaut False si le joueur quitte sans choisir de niveau.
    """
    known_towers = _make_known_towers(current_save)

    # Partie toujours en cours — rien à faire ici
    if not (gs["game_over"] or gs["game_win"]):
        return gs, chosen_level, current_save, known_towers, pause_start, True

    mc = gs.get("mission_context")

    # Ordre de priorité : infini > histoire > normal
    if gs.get("infinite_mode") and gs["game_over"]:
        return _handle_infinite_loss(
            screen, gs, grid_cache, current_save, chosen_level,
            mx, my, mouse_clicked_left, pause_start
        )

    if gs["game_win"] and mc:
        gs, chosen_level, current_save, known_towers, pause_start = _handle_histoire_win(
            screen, gs, grid_cache, current_save, chosen_level,
            mc, mx, my, mouse_clicked_left, pause_start
        )
        # chosen_level devient None si le joueur ferme la fenêtre sans choisir
        return gs, chosen_level, current_save, known_towers, pause_start, chosen_level is not None

    if gs["game_over"] and mc:
        gs, chosen_level, current_save, known_towers, pause_start = _handle_histoire_loss(
            screen, gs, grid_cache, current_save, chosen_level,
            mc, mx, my, mouse_clicked_left, pause_start
        )
        return gs, chosen_level, current_save, known_towers, pause_start, chosen_level is not None

    # Cas le plus simple — mode normal sans contexte de mission
    return _handle_normal_end(
        screen, gs, grid_cache, current_save, chosen_level,
        mx, my, mouse_clicked_left, pause_start
    )


# MODE INFINI

def _handle_infinite_loss(screen, gs, grid_cache, current_save, chosen_level,
                           mx, my, mouse_clicked_left, pause_start):
    """
    Popup de loot après une défaite en mode infini.
    Le loot est collecté une seule fois via le flag infinite_loot_collected
    pour éviter de doubler les récompenses entre deux frames.
    """
    known_towers = _make_known_towers(current_save)

    # On collecte le loot une seule fois — pas envie de doubler les récompenses
    if not gs.get("infinite_loot_collected") and gs.get("save") is not None:
        gs["infinite_loot_collected"] = True
        gs["_final_loot"] = _collect_infinite_loot(gs, gs["save"])

    done = _draw_infinite_loot_popup(
        screen, gs.get("_final_loot", _EMPTY_LOOT),
        gs.get("wave_number", 1), mx, my, mouse_clicked_left
    )

    if done:
        play_menu_music(current_save.get("music_volume", 0.8))
        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)

        if chosen_level is None:
            # Le joueur a fermé le menu sans choisir de niveau
            return gs, None, current_save, known_towers, None, False

        # Nouveau niveau choisi — on repart proprement
        play_game_music(current_save.get("music_volume", 0.8))
        gs           = _init_new_game(chosen_level, current_save, grid_cache)
        known_towers = _make_known_towers(current_save)
        pause_start  = None

    return gs, chosen_level, current_save, known_towers, pause_start, True


# MODE HISTOIRE

def _handle_histoire_win(screen, gs, grid_cache, current_save, chosen_level,
                         mc, mx, my, mouse_clicked_left, pause_start):
    """
    Écran de victoire histoire. La sauvegarde est protégée par mission_complete_shown
    pour n'écrire sur le disque qu'une seule fois, pas à chaque frame.
    Actions : "next" (mission suivante), "restart" (même mission), "histoire" (sélection).
    """
    # Sauvegarde unique du résultat — on ne veut pas écrire sur le disque à chaque frame
    if not gs.get("mission_complete_shown"):
        gs["mission_complete_shown"] = True
        if gs.get("save") is not None:
            hist_mod.save_mission_result(gs["save"], mc["chapter"], mc["mission"], mc["objectives"])
            current_save = gs["save"]

    has_next = hist_mod.has_next_mission(mc["chapter"], mc["mission"])
    action = draw_mission_complete_screen(
        screen, render.big_font, render.font,
        mc["objectives"], gs["coins_reward"], has_next,
        (mx, my), mouse_clicked_left
    )

    if action == "next":
        next_ch, next_m = hist_mod.get_next_mission(mc["chapter"], mc["mission"])
        chosen_level = {"chapter": next_ch, "mission": next_m, "difficulty": gs.get("difficulty", 2)}
        play_game_music(current_save.get("music_volume", 0.8))
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        gs["mission_context"] = _build_mission_context(next_ch, next_m, current_save)
        pause_start = None

    elif action == "restart":
        # On repart de zéro sur la même mission — chosen_level ne change pas
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        gs["mission_context"] = _build_mission_context(mc["chapter"], mc["mission"], current_save)
        pause_start = None

    elif action == "histoire":
        gs, chosen_level, current_save, pause_start = _go_to_histoire(
            grid_cache, current_save, chosen_level, pause_start
        )

    return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start


def _handle_histoire_loss(screen, gs, grid_cache, current_save, chosen_level,
                          mc, mx, my, mouse_clicked_left, pause_start):
    """
    Écran d'échec histoire. Pas de sauvegarde ici contrairement à la victoire —
    on attend juste que le joueur choisisse de réessayer ou de quitter.
    """
    action = draw_mission_failed_screen(
        screen, render.big_font, render.font,
        mc["objectives"], (mx, my), mouse_clicked_left
    )

    if action == "restart":
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        gs["mission_context"] = _build_mission_context(mc["chapter"], mc["mission"], current_save)
        pause_start = None

    elif action == "histoire":
        gs, chosen_level, current_save, pause_start = _go_to_histoire(
            grid_cache, current_save, chosen_level, pause_start
        )

    return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start


# MODE NORMAL

def _handle_normal_end(screen, gs, grid_cache, current_save, chosen_level,
                       mx, my, mouse_clicked_left, pause_start):
    """
    Fin de partie mode normal — victoire ou game over sans contexte de mission.
    En victoire on affiche les coins gagnés, en défaite juste l'écran standard.
    """
    coins = gs["coins_reward"] if gs["game_win"] else 0
    action = draw_gameover_screen(
        screen, render.big_font, render.font,
        gs["game_win"], (mx, my), mouse_clicked_left, coins
    )

    if action == "restart":
        gs          = _init_new_game(chosen_level, current_save, grid_cache)
        pause_start = None
        return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start, True

    if action == "menu":
        play_menu_music(current_save.get("music_volume", 0.8))
        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)

        if chosen_level is None:
            return gs, None, current_save, _make_known_towers(current_save), None, False

        play_game_music(current_save.get("music_volume", 0.8))
        gs          = _init_new_game(chosen_level, current_save, grid_cache)
        pause_start = None

    return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start, True


# NAVIGATION VERS L'ÉCRAN HISTOIRE

def _go_to_histoire(grid_cache, current_save, chosen_level, pause_start):
    """
    Bascule vers la sélection de missions histoire puis relance le jeu.
    Si run_histoire renvoie None, on retombe sur le menu principal.
    Sinon on recharge le save — il a pu changer pendant la navigation.
    """
    play_menu_music(current_save.get("music_volume", 0.8))
    hist_result = run_histoire(render.screen, render.clock, current_save)

    if hist_result is None:
        # L'écran histoire a été fermé — on retombe sur le menu principal
        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
    else:
        # Mission sélectionnée directement depuis l'histoire
        chosen_level = hist_result
        current_save = sd.load()  # Le save peut avoir été modifié pendant la navigation

    play_game_music(current_save.get("music_volume", 0.8))
    gs = _init_new_game(chosen_level, current_save, grid_cache)
    _inject_mission_context(gs, chosen_level, current_save)

    return gs, chosen_level, current_save, None


# HELPERS INTERNES

def _build_mission_context(chapter, mission, current_save):
    """
    Construit le dict mission_context standard. Centralisé ici parce qu'on
    le dupliquait à 4 endroits — plus simple à maintenir ainsi.
    current_save peut être None, d'où le fallback sur {}.
    """
    return {
        "chapter":                 chapter,
        "mission":                 mission,
        "objectives":              hist_mod.get_mission_objectives(chapter, mission),
        "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
    }