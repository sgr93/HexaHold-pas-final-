"""
modes/histoire.py

Mode Histoire — Carte des Murs (Attack on Titan).
Affiche une carte interactive avec des chapitres qui se débloquent
progressivement. Chaque chapitre contient des missions avec objectifs et étoiles.

Appel depuis menu_screen.py :
    from modes.histoire import run_histoire
    result = run_histoire(screen, clock, save)
    # result : None (retour menu) ou dict {chapter, mission, difficulty}
"""

import copy
import math
import pygame
import core.save_data as sd
from modes.histoire_data import (
    CHAPTERS, MAP_LABELS,
    C_BG, C_GOLD, C_GOLD2, C_GOLD3, C_PARCHMENT, C_MUTED,
    is_mission_unlocked, get_mission_best_stars,
)
from modes.histoire_render import (
    _font, _draw_text_centered, _draw_rect_alpha,
    _draw_circle_aa, _lerp_color, _build_map_surface,
)
from modes.histoire_widgets import Popup, ChapterPoint, Cinematic, Notification


def run_histoire(screen, clock, save):
    """
    Lance le mode Histoire et retourne soit None (retour menu) soit un dict
    {chapter, mission, difficulty} pour démarrer une partie.
    """
    save.setdefault("histoire_unlocked",  [0])
    save.setdefault("histoire_completed", [])

    sw, sh     = screen.get_size()
    FONT_PIXEL = "assets/fonts/PIXELCRASH.otf"

    fonts = {
        "xs":       pygame.font.SysFont("georgia", 13),
        "xs_title": pygame.font.Font(FONT_PIXEL, 13),
        "sm":       pygame.font.Font(FONT_PIXEL, 16),
        "md":       pygame.font.Font(FONT_PIXEL, 20),
        "lg":       pygame.font.Font(FONT_PIXEL, 26),
        "cine":     pygame.font.SysFont("georgia", 18),
        "map_sm":   pygame.font.SysFont("georgia", 16),
        "map_xs":   pygame.font.SysFont("georgia", 14),
        "wall":     pygame.font.Font(FONT_PIXEL, 17),
    }

    # Zone carte — carrée et centrée, laisse de la place pour le header
    header_h = 50
    map_size = min(sw, sh - header_h)
    map_x    = (sw - map_size) // 2
    map_y    = header_h + ((sh - header_h) - map_size) // 2
    map_surf = _build_map_surface(map_size, map_size)

    # Points de chapitre positionnés selon les cx/cy en % de la carte
    chapter_points = {
        idx: ChapterPoint(idx,
                          map_x + int(ch["cx"] * map_size),
                          map_y + int(ch["cy"] * map_size))
        for idx, ch in CHAPTERS.items()
    }

    popup    = Popup()
    cine     = Cinematic()
    notif    = Notification()
    back_rect = pygame.Rect(12, 12, 90, 28)
    prev_time = pygame.time.get_ticks()

    # BOUCLE PRINCIPALE
    while True:
        now  = pygame.time.get_ticks()
        dt   = (now - prev_time) / 1000.0
        prev_time = now

        mx, my  = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Escape ferme dans l'ordre : cinématique → popup → écran
                    if cine.active:
                        cine.skip()
                    elif popup.visible:
                        popup.close()
                    else:
                        return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        # Recalcul de la carte si la fenêtre a été redimensionnée
        cur_sw, cur_sh = screen.get_size()
        if cur_sw != sw or cur_sh != sh:
            sw, sh   = cur_sw, cur_sh
            map_size = min(sw, sh - header_h)
            map_x    = (sw - map_size) // 2
            map_y    = header_h + ((sh - header_h) - map_size) // 2
            map_surf = _build_map_surface(map_size, map_size)
            for idx, ch in CHAPTERS.items():
                chapter_points[idx].cx = map_x + int(ch["cx"] * map_size)
                chapter_points[idx].cy = map_y + int(ch["cy"] * map_size)

        unlocked_set  = set(save.get("histoire_unlocked",  [0]))
        completed_set = set(save.get("histoire_completed", []))

        # UPDATE
        popup.update(dt)
        cine.update(dt)
        notif.update(dt)
        for idx, cp in chapter_points.items():
            cp.update(dt, idx in unlocked_set)

        # RENDU
        screen.fill(C_BG)
        screen.blit(map_surf, (map_x, map_y))

        # Labels de la carte — toujours au-dessus de la surface, ombre portée incluse
        for text, pct_x, pct_y, size, color, bold in MAP_LABELS:
            lx   = map_x + int(pct_x * map_size)
            ly   = map_y + int(pct_y * map_size)
            fkey = "wall" if bold else "map_xs"
            f    = fonts.get(fkey) or pygame.font.SysFont("arial", size, bold=bold)
            s    = f.render(text, True, (0, 0, 0))
            screen.blit(s, (lx - s.get_width() // 2 + 1, ly - s.get_height() // 2 + 1))
            t    = f.render(text, True, color)
            screen.blit(t, (lx - t.get_width() // 2, ly - t.get_height() // 2))

        # Points de chapitre avec hover uniquement si la cinématique n'est pas active
        for idx, cp in chapter_points.items():
            hovered = (
                idx in unlocked_set
                and math.dist((mx, my), (cp.cx, cp.cy)) < ChapterPoint.RADIUS + 4
                and not cine.active
            )
            cp.draw(screen, idx in unlocked_set, idx in completed_set, hovered, save)

        # Header fixe en haut
        pygame.draw.rect(screen, (10, 8, 4), (0, 0, sw, header_h))
        pygame.draw.line(screen, C_GOLD, (0, header_h), (sw, header_h), 1)
        title_t = fonts["md"].render("Mode Histoire", True, C_PARCHMENT)
        screen.blit(title_t, (sw // 2 - title_t.get_width() // 2, 15))
        sub_t = fonts["xs"].render("Les Murs - Territoire Humain", True, C_GOLD)
        screen.blit(sub_t, (sw - sub_t.get_width() - 16, 18))

        bh_col = C_GOLD2 if back_rect.collidepoint(mx, my) else C_GOLD
        pygame.draw.rect(screen, (18, 14, 6), back_rect, border_radius=4)
        pygame.draw.rect(screen, bh_col, back_rect, 1, border_radius=4)
        bt = fonts["xs"].render("< Retour", True, bh_col)
        screen.blit(bt, (back_rect.x + back_rect.w // 2 - bt.get_width() // 2,
                         back_rect.y + back_rect.h // 2 - bt.get_height() // 2))

        # Popup, notif et cinématique — dans cet ordre, la cine passe par-dessus tout
        start_btn = popup.draw(screen, sw, sh, save, fonts, False, mx, my)
        notif.draw(screen, sw, fonts)
        cine.draw(screen, sw, sh, fonts)

        # GESTION DES CLICS
        if clicked and not cine.active:
            if back_rect.collidepoint(mx, my):
                sd.save(save)
                return None

            # Zone de fermeture du popup (le petit "x")
            if popup.visible:
                close_zone = pygame.Rect(
                    sw - Popup.WIDTH * popup._anim + Popup.WIDTH - 36,
                    54, 28, 28
                )
                if close_zone.collidepoint(mx, my):
                    popup.close()

            # Bouton commencer — lance la cinématique ou la mission
            if start_btn and start_btn.collidepoint(mx, my) and popup.chapter_idx is not None:
                idx = popup.chapter_idx
                ch  = CHAPTERS[idx]

                if ch.get("type") == "cinematique":
                    cine.start(idx)
                    popup.close()
                    _complete_chapter(idx, save, chapter_points, notif, unlocked_set, completed_set)

                elif not ch.get("special"):
                    mission_idx = popup.selected_mission
                    if is_mission_unlocked(save, idx, mission_idx):
                        sd.save(save)
                        # Difficulté croissante selon le chapitre, +1 pour la dernière mission
                        ch_diff  = {1: 2, 2: 3, 3: 4, 4: 4, 5: 5}
                        diff_val = ch_diff.get(idx, 2)
                        missions = CHAPTERS.get(idx, {}).get("missions", [])
                        if mission_idx == len(missions) - 1:
                            diff_val = min(5, diff_val + 1)
                        return {"chapter": idx, "mission": mission_idx, "difficulty": diff_val}

            # Sélection d'une mission dans le popup au clic
            if popup.visible and popup.chapter_idx is not None:
                ch = CHAPTERS[popup.chapter_idx]
                if ch.get("missions"):
                    pw_p      = Popup.WIDTH
                    px_p      = int(sw - pw_p * popup._anim)
                    row_heights = getattr(popup, "mission_row_heights", None)
                    y_cur     = 50 + 68 - popup.scroll  # py_p + content_y_p
                    for i in range(len(ch["missions"])):
                        rh       = row_heights[i] if row_heights and i < len(row_heights) else 82
                        row_rect = pygame.Rect(px_p + 8, y_cur, pw_p - 16, rh)
                        if row_rect.collidepoint(mx, my):
                            if is_mission_unlocked(save, popup.chapter_idx, i):
                                popup.selected_mission = i
                            break
                        y_cur += rh + 8

            # Clic sur un point de chapitre — ouvre le popup seulement si en dehors du popup
            popup_area = pygame.Rect(sw - int(Popup.WIDTH * popup._anim), 50,
                                     int(Popup.WIDTH * popup._anim), sh - 50)
            if not popup_area.collidepoint(mx, my):
                for idx, cp in chapter_points.items():
                    if idx in unlocked_set and math.dist((mx, my), (cp.cx, cp.cy)) < ChapterPoint.RADIUS + 6:
                        popup.open(idx)
                        break

        elif clicked and cine.active:
            cine.skip()

        pygame.display.flip()
        clock.tick(60)


def _complete_chapter(idx, save, chapter_points, notif, unlocked_set, completed_set):
    """
    Marque un chapitre comme complété et débloque le suivant.
    Déclenche l'animation de ripple sur le nouveau point de chapitre.
    """
    if idx not in completed_set:
        completed_set.add(idx)
        hist_comp = save.setdefault("histoire_completed", [])
        if idx not in hist_comp:
            hist_comp.append(idx)

    ch       = CHAPTERS[idx]
    next_idx = ch.get("unlock_next")
    if next_idx is not None and next_idx not in unlocked_set:
        unlocked_set.add(next_idx)
        hist_unl = save.setdefault("histoire_unlocked", [0])
        if next_idx not in hist_unl:
            hist_unl.append(next_idx)
        chapter_points[next_idx].trigger_unlock()
        notif.show(f"Nouveau chapitre débloqué : {CHAPTERS[next_idx]['label']}")

    sd.save(save)


# API PUBLIQUE — utilisée par game.py

def get_mission_objectives(chapter_idx, mission_idx):
    """
    Retourne les objectifs d'une mission en copies fraîches.
    On deepcopy pour éviter que les modifications en cours de partie
    ne corrompent les données de CHAPTERS.
    """
    ch       = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if 0 <= mission_idx < len(missions):
        return copy.deepcopy(missions[mission_idx].get("objectives", []))
    return []


def get_mission_name(chapter_idx, mission_idx):
    """Retourne le nom d'une mission, 'Mission' par défaut si introuvable."""
    ch       = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if 0 <= mission_idx < len(missions):
        return missions[mission_idx].get("name", "Mission")
    return "Mission"


def has_next_mission(chapter_idx, mission_idx):
    """Retourne True si une mission suivante existe dans le même chapitre ou le suivant."""
    missions = CHAPTERS.get(chapter_idx, {}).get("missions", [])
    if mission_idx + 1 < len(missions):
        return True
    # On regarde si le chapitre suivant a des missions jouables
    return bool(CHAPTERS.get(chapter_idx + 1, {}).get("missions"))


def get_next_mission(chapter_idx, mission_idx):
    """
    Retourne (chapter_idx, mission_idx) de la mission suivante.
    Si on est à la dernière mission du chapitre, on passe au suivant.
    Fallback sur la mission actuelle si vraiment rien derrière.
    """
    missions = CHAPTERS.get(chapter_idx, {}).get("missions", [])
    if mission_idx + 1 < len(missions):
        return chapter_idx, mission_idx + 1
    next_ch_idx = chapter_idx + 1
    while next_ch_idx in CHAPTERS:
        if CHAPTERS[next_ch_idx].get("missions"):
            return next_ch_idx, 0
        next_ch_idx += 1
    return chapter_idx, mission_idx


def save_mission_result(save, chapter_idx, mission_idx, objectives):
    """
    Sauvegarde le résultat d'une mission : étoiles, état des objectifs,
    déblocage de la suite. On ne rétrograde jamais un objectif déjà accompli.
    """
    stars_done = sum(1 for o in objectives if o.get("done", False))

    # Meilleur score en étoiles — on ne rétrograde pas
    key = f"ch{chapter_idx}_m{mission_idx}_stars"
    save[key] = max(save.get(key, 0), stars_done)

    # Fusion des états d'objectifs : une fois True, toujours True
    obj_key         = f"ch{chapter_idx}_m{mission_idx}_objectives"
    prev_obj_states = save.get(obj_key, [])
    save[obj_key]   = [
        obj.get("done", False) or (prev_obj_states[i] if i < len(prev_obj_states) else False)
        for i, obj in enumerate(objectives)
    ]

    save[f"ch{chapter_idx}_m{mission_idx}_done"] = True

    if stars_done >= 1:
        ch            = CHAPTERS.get(chapter_idx, {})
        missions      = ch.get("missions", [])
        next_m_idx    = mission_idx + 1

        if next_m_idx < len(missions):
            # Débloque la mission suivante dans le même chapitre
            save[f"ch{chapter_idx}_m{next_m_idx}_unlocked"] = True
        else:
            # Fin du chapitre — on débloque le suivant
            next_ch_idx = ch.get("unlock_next")
            if next_ch_idx is not None:
                hist_unl = save.setdefault("histoire_unlocked", [0])
                if next_ch_idx not in hist_unl:
                    hist_unl.append(next_ch_idx)
                save[f"ch{next_ch_idx}_m0_unlocked"] = True

            hist_comp = save.setdefault("histoire_completed", [])
            if chapter_idx not in hist_comp:
                hist_comp.append(chapter_idx)

    sd.save(save)
    return stars_done


def get_mission_objective_states(save, chapter_idx, mission_idx):
    """
    Retourne la liste des états d'objectifs sauvegardés.
    Ex : [True, False, True] — aligné sur get_mission_objectives().
    Retourne [] si la mission n'a jamais été jouée.
    """
    return save.get(f"ch{chapter_idx}_m{mission_idx}_objectives", [])


def get_last_mission_index(chapter_idx):
    """
    Retourne l'index de la dernière mission du chapitre.
    Retourne -1 si le chapitre n'existe pas ou n'a pas de missions.
    Utilisé par game_loop_update.py pour identifier le boss de fin de chapitre.
    """
    missions = CHAPTERS.get(chapter_idx, {}).get("missions", [])
    return len(missions) - 1 if missions else -1