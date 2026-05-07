"""
modes/game_end_screens.py
-------------------------
Gestion des écrans de fin de partie :
  - mode infini  → popup loot
  - mode histoire → victoire (étoiles) ou défaite
  - mode normal  → game over / victoire
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
from modes.game_infinite import (
    _collect_infinite_loot,
    _draw_infinite_loot_popup,
)
from modes.game_music import play_game_music, play_menu_music
from modes.game_state import (
    _init_new_game,
    _inject_mission_context,
    _make_known_towers,
)
from modes.main_ui import run_main_ui


def handle_end_screens(screen, gs, grid_cache, current_save, chosen_level,
                        mx, my, mouse_clicked_left, pause_start):
    """
    Dispatche vers le bon écran de fin selon le mode de jeu.
    Retourne (gs, chosen_level, current_save, known_towers, pause_start, running).
    """
    known_towers = _make_known_towers(current_save)

    if not (gs["game_over"] or gs["game_win"]):
        return gs, chosen_level, current_save, known_towers, pause_start, True

    mc = gs.get("mission_context")

    if gs.get("infinite_mode") and gs["game_over"]:
        return _handle_infinite_loss(
            screen, gs, grid_cache, current_save, chosen_level,
            mx, my, mouse_clicked_left, pause_start
        )

    if gs["game_win"] and mc:
        gs, chosen_level, current_save, known_towers, pause_start = _handle_histoire_win(
            screen, gs, grid_cache, current_save, chosen_level, mc, mx, my, mouse_clicked_left, pause_start
        )
        return gs, chosen_level, current_save, known_towers, pause_start, chosen_level is not None

    if gs["game_over"] and mc:
        gs, chosen_level, current_save, known_towers, pause_start = _handle_histoire_loss(
            screen, gs, grid_cache, current_save, chosen_level, mc, mx, my, mouse_clicked_left, pause_start
        )
        return gs, chosen_level, current_save, known_towers, pause_start, chosen_level is not None

    return _handle_normal_end(
        screen, gs, grid_cache, current_save, chosen_level, mx, my, mouse_clicked_left, pause_start
    )



# MODE INFINI

def _handle_infinite_loss(screen, gs, grid_cache, current_save, chosen_level,
                           mx, my, mouse_clicked_left, pause_start):
    known_towers = _make_known_towers(current_save)
    if not gs.get("infinite_loot_collected") and gs.get("save") is not None:
        gs["infinite_loot_collected"] = True
        gs["_final_loot"] = _collect_infinite_loot(gs, gs["save"])

    done = _draw_infinite_loot_popup(
        screen,
        gs.get("_final_loot", {"coins": 0, "gems": 0, "items": []}),
        gs.get("wave_number", 1), mx, my, mouse_clicked_left,
    )
    if done:
        play_menu_music(current_save.get("music_volume", 0.8))
        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
        if chosen_level is None:
            return gs, None, current_save, known_towers, None, False
        play_game_music(current_save.get("music_volume", 0.8))
        gs           = _init_new_game(chosen_level, current_save, grid_cache)
        known_towers = _make_known_towers(current_save)
        pause_start  = None

    return gs, chosen_level, current_save, known_towers, pause_start, True


# MODE HISTOIRE

def _handle_histoire_win(screen, gs, grid_cache, current_save, chosen_level,
                          mc, mx, my, mouse_clicked_left, pause_start):
    if not gs.get("mission_complete_shown"):
        gs["mission_complete_shown"] = True
        if gs.get("save") is not None:
            hist_mod.save_mission_result(gs["save"], mc["chapter"], mc["mission"], mc["objectives"])
            current_save = gs["save"]

    has_next = hist_mod.has_next_mission(mc["chapter"], mc["mission"])
    action   = draw_mission_complete_screen(
        screen, render.big_font, render.font,
        mc["objectives"], gs["coins_reward"], has_next, (mx, my), mouse_clicked_left,
    )

    if action == "next":
        next_ch, next_m = hist_mod.get_next_mission(mc["chapter"], mc["mission"])
        chosen_level    = {"chapter": next_ch, "mission": next_m, "difficulty": gs.get("difficulty", 2)}
        play_game_music(current_save.get("music_volume", 0.8))
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        gs["mission_context"] = {
            "chapter":    next_ch,
            "mission":    next_m,
            "objectives": hist_mod.get_mission_objectives(next_ch, next_m),
            "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
        }
        pause_start = None

    elif action == "restart":
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        gs["mission_context"] = {
            "chapter":    mc["chapter"],
            "mission":    mc["mission"],
            "objectives": hist_mod.get_mission_objectives(mc["chapter"], mc["mission"]),
            "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
        }
        pause_start = None

    elif action == "histoire":
        gs, chosen_level, current_save, pause_start = _go_to_histoire(
            grid_cache, current_save, chosen_level, pause_start
        )

    return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start


def _handle_histoire_loss(screen, gs, grid_cache, current_save, chosen_level,
                           mc, mx, my, mouse_clicked_left, pause_start):
    from ui.ui import draw_mission_failed_screen
    action = draw_mission_failed_screen(
        screen, render.big_font, render.font,
        mc["objectives"], (mx, my), mouse_clicked_left,
    )
    if action == "restart":
        gs = _init_new_game(chosen_level, current_save, grid_cache)
        gs["mission_context"] = {
            "chapter":    mc["chapter"],
            "mission":    mc["mission"],
            "objectives": hist_mod.get_mission_objectives(mc["chapter"], mc["mission"]),
            "enemies_killed_at_start": (current_save or {}).get("enemies_killed", 0),
        }
        pause_start = None

    elif action == "histoire":
        gs, chosen_level, current_save, pause_start = _go_to_histoire(
            grid_cache, current_save, chosen_level, pause_start
        )

    return gs, chosen_level, current_save, _make_known_towers(current_save), pause_start


# MODE NORMAL

def _handle_normal_end(screen, gs, grid_cache, current_save, chosen_level,
                        mx, my, mouse_clicked_left, pause_start):
    action = draw_gameover_screen(
        screen, render.big_font, render.font,
        gs["game_win"], (mx, my), mouse_clicked_left,
        gs["coins_reward"] if gs["game_win"] else 0,
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
    """Navigation vers l'écran histoire puis retour en jeu."""
    play_menu_music(current_save.get("music_volume", 0.8))
    hist_result = run_histoire(render.screen, render.clock, current_save)
    if hist_result is None:
        chosen_level, current_save = run_main_ui(render.screen, render.clock, current_save)
    else:
        chosen_level = hist_result
        current_save = sd.load()
    play_game_music(current_save.get("music_volume", 0.8))
    gs = _init_new_game(chosen_level, current_save, grid_cache)
    _inject_mission_context(gs, chosen_level, current_save)
    return gs, chosen_level, current_save, None