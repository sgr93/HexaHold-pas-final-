"""
main_ui.py
----------
Interface principale de HexaHold.
Gère la navigation entre tous les onglets via la barre du bas.

Retourne :
  dict ou int  → niveau choisi (partie rapide ou histoire)
  None         → quitter
"""

import pygame
import save_data as sd
import theme
import hud
from histoire import run_histoire


def run_main_ui(screen: pygame.Surface,
                clock:  pygame.time.Clock,
                save:   dict):
    """
    Boucle de l'interface principale.
    Retourne (chosen_level, save) ou (None, save).
    """
    hud.init()

    active_tab   = "accueil"
    chosen_level = None

    # Imports des écrans onglets
    from screens.accueil_screen    import AccueilScreen
    from screens.quetes_screen     import QuetesScreen
    from screens.equipement_screen import EquipementScreen
    from screens.gacha_screen      import GachaScreen
    from screens.talents_screen    import TalentsScreen
    from screens.parametres_screen import ParametresScreen

    screens = {
        "accueil":    AccueilScreen(save),
        "quetes":     QuetesScreen(save),
        "equipement": EquipementScreen(save),
        "gacha":      GachaScreen(save),
        "talents":    TalentsScreen(save),
        "parametres": ParametresScreen(save),
    }

    running = True
    while running:
        w, h = screen.get_size()
        mx, my = pygame.mouse.get_pos()
        clicked = False
        scroll_dy = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, save
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None, save
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.MOUSEWHEEL:
                scroll_dy = event.y

        # Fond pierre
        theme.draw_stone_bg(screen)

        # Calculer les badges
        badges = _compute_badges(save)

        # HUD (header + nav)
        nav_action = hud.draw(screen, save,
                               active_tab=active_tab,
                               badges=badges,
                               mx=mx, my=my, clicked=clicked)
        if nav_action:
            active_tab = nav_action

        # Zone de contenu
        content = hud.content_rect(screen)

        # ── Onglet Histoire (spécial : appelle run_histoire) ──
        if active_tab == "histoire":
            result = run_histoire(screen, clock, save)
            if isinstance(result, dict):
                chosen_level = result
                running = False
                continue
            # Retour sans avoir joué → retour accueil
            active_tab = "accueil"
            continue

        # ── Onglets normaux ──
        scr_obj = screens.get(active_tab)
        if scr_obj:
            scr_obj.save = save
            result = scr_obj.draw(screen, content, mx, my, clicked, scroll_dy)
            if result is not None:
                if result == "infini":
                    # Mode infini : difficulte normale, vagues infinies
                    chosen_level = {"infinite": True, "difficulty": 2}
                    running = False
                elif result == "histoire":
                    active_tab = "histoire"
                else:
                    chosen_level = result
                    running = False

        # Overlays (picker icône, etc.) — dessinés EN DERNIER, au-dessus de tout
        hud.draw_overlay(screen, save, mx=mx, my=my, clicked=clicked)

        pygame.display.flip()
        clock.tick(60)

    sd.save(save)
    return chosen_level, save


# ============================================================
def _compute_badges(save: dict) -> dict:
    """Calcule les badges de notification pour la nav bar."""
    import quetes as qm
    badges = {}
    # Quêtes disponibles à réclamer
    available = qm.get_available_quests(save)
    if available:
        badges["quetes"] = len(available)
    # Skill points disponibles
    sp = save.get("skill_points", 0)
    if sp > 0:
        badges["talents"] = sp
    return badges