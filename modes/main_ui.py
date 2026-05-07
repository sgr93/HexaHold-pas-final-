"""
modes/main_ui.py

Interface principale de HexaHold.
Gère la navigation entre tous les onglets via la barre du bas.
Retourne (chosen_level, save) où chosen_level est None si le joueur quitte
sans choisir de partie.
"""

import pygame
import core.save_data as sd
import core.quetes as qm
import ui.theme as theme
import ui.hud as hud
from modes.histoire import run_histoire
from ui.ui import draw_skillpoint_anim
from screens.accueil_screen import AccueilScreen
from screens.quetes_screen import QuetesScreen
from screens.equipement_screen import EquipementScreen
from screens.gacha_screen import GachaScreen
from screens.talents_screen import TalentsScreen
from screens.parametres_screen import ParametresScreen


def run_main_ui(screen: pygame.Surface, clock: pygame.time.Clock, save: dict):
    """
    Boucle de l'interface principale.
    Retourne (chosen_level, save) ou (None, save) si le joueur quitte.
    """
    hud.init()

    active_tab   = "accueil"
    chosen_level = None
    skillpoint_anim_timer = 0

    # Chaque onglet a son propre objet screen — ils gardent leur état entre les visites
    screens = {
        "accueil":    AccueilScreen(save),
        "quetes":     QuetesScreen(save),
        "equipement": EquipementScreen(save),
        "gacha":      GachaScreen(save),
        "talents":    TalentsScreen(save),
        "parametres": ParametresScreen(save),
    }

    while True:
        w, h      = screen.get_size()
        mx, my    = pygame.mouse.get_pos()
        clicked   = False
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

        theme.draw_stone_bg(screen)

        # Badges calculés à chaque frame — léger, pas besoin de cache
        nav_action = hud.draw(
            screen, save,
            active_tab=active_tab,
            badges=_compute_badges(save),
            mx=mx, my=my, clicked=clicked
        )
        if nav_action:
            active_tab = nav_action

        content = hud.content_rect(screen)

        # Histoire est un cas spécial — elle lance sa propre boucle et bloque jusqu'au retour
        if active_tab == "histoire":
            result = run_histoire(screen, clock, save)
            if isinstance(result, dict):
                # Niveau choisi depuis l'écran histoire — on sort directement
                chosen_level = result
                break
            # Retour sans avoir joué — on revient à l'accueil plutôt que de rester bloqué sur "histoire"
            active_tab = "accueil"
            continue

        # Onglets normaux — on passe la save à jour au cas où elle a changé entre les visites
        scr_obj = screens.get(active_tab)
        if scr_obj:
            scr_obj.save = save
            result = scr_obj.draw(screen, content, mx, my, clicked, scroll_dy)
            if result == "infini":
                # Mode infini : difficulté normale, vagues sans fin
                chosen_level = {"infinite": True, "difficulty": 2}
                break
            elif result == "histoire":
                active_tab = "histoire"
            elif result is not None:
                chosen_level = result
                break

        # Overlays (picker icône, etc.) — dessinés en dernier pour passer par-dessus tout
        hud.draw_overlay(screen, save, mx=mx, my=my, clicked=clicked)

        # Animation skill point — se déclenche dès qu'un level-up est en attente
        if skillpoint_anim_timer > 0:
            draw_skillpoint_anim(screen, skillpoint_anim_timer)
            skillpoint_anim_timer -= 1
        elif save.get("pending_skillpoint_anim"):
            skillpoint_anim_timer = 180
            save["pending_skillpoint_anim"] = False

        pygame.display.flip()
        clock.tick(60)

    sd.save(save)
    return chosen_level, save


def _compute_badges(save: dict) -> dict:
    """
    Calcule les badges de notification pour la nav bar.
    Quêtes réclamables et skill points dispo — les deux choses que le joueur
    doit voir en un coup d'œil sans rentrer dans chaque onglet.
    """
    badges = {}
    available = qm.get_available_quests(save)
    if available:
        badges["quetes"] = len(available)
    sp = save.get("skill_points", 0)
    if sp > 0:
        badges["talents"] = sp
    return badges