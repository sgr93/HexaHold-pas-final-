"""
histoire.py
-----------
Mode Histoire - Carte des Murs (Attack on Titan)
Affiche une carte interactive avec des chapitres qui se debloquent
progressivement. Chaque chapitre contient des missions avec objectifs et etoiles.

Appel depuis menu_screen.py :
    from histoire import run_histoire
    result = run_histoire(screen, clock, save)
    # result : None (retour menu) ou dict {chapter, mission, difficulty}
"""

import pygame
import math
import core.save_data as sd
from modes.histoire_data import (
    CHAPTERS, MAP_LABELS, C_BG, C_BG2, C_WALL, C_WALL_LT, C_GOLD, C_GOLD2, C_GOLD3, C_PARCHMENT, C_PARCHMENT2, C_RED, C_RED2, C_GREEN_D, C_GREEN_L, C_BROWN_D, C_BROWN_L, C_PURPLE_D, C_PURPLE_L, C_LOCKED, C_LOCKED_B, C_OVERLAY, C_PANEL, C_PANEL_B, C_TEXT, C_MUTED, C_STAR_ON, C_STAR_OFF, C_NOTIF_BG, C_NOTIF_B, is_mission_unlocked, get_mission_best_stars,
)
from modes.histoire_render import (
    _font, _draw_text_centered, _draw_rect_alpha, _draw_circle_aa, _lerp_color, _build_map_surface,
)
from modes.histoire_widgets import Popup, ChapterPoint, Cinematic, Notification
import copy


def run_histoire(screen, clock, save):
    """
    Lance le mode Histoire.
    Retourne :
      None  → retour au menu principal
      dict  → {"chapter": idx, "mission": idx, "difficulty": 1}
               pour lancer une partie
    """
    # ── Initialiser la progression dans save ──
    save.setdefault("histoire_unlocked",  [0])
    save.setdefault("histoire_completed", [])

    sw, sh = screen.get_size()

    # ── Fonts ──
    fonts = {
        "xs":   pygame.font.SysFont("arial", 13),
        "sm":   pygame.font.SysFont("arial", 16),
        "md":   pygame.font.SysFont("arial", 20, bold=True),
        "lg":   pygame.font.SysFont("arial", 26, bold=True),
        "cine": pygame.font.SysFont("arial", 18, italic=True),
        "map_sm": pygame.font.SysFont("arial", 16),
        "map_xs": pygame.font.SysFont("arial", 14),
        "wall":   pygame.font.SysFont("arial", 17, bold=True),
    }

    # ── Zone carte ──
    header_h = 50
    map_w = sw
    map_h = sh - header_h
    # On centre la carte dans l'espace disponible
    map_size = min(map_w, map_h)
    map_x = (sw - map_size) // 2
    map_y = header_h + (map_h - map_size) // 2

    # ── Construire la surface carte ──
    map_surf = _build_map_surface(map_size, map_size)

    # ── Points de chapitre ──
    chapter_points = {}
    for idx, ch in CHAPTERS.items():
        cx_abs = map_x + int(ch["cx"] * map_size)
        cy_abs = map_y + int(ch["cy"] * map_size)
        chapter_points[idx] = ChapterPoint(idx, cx_abs, cy_abs)

    popup  = Popup()
    cine   = Cinematic()
    notif  = Notification()

    # ── Back button ──
    back_rect = pygame.Rect(12, 12, 90, 28)

    prev_time = pygame.time.get_ticks()

    # ── BOUCLE PRINCIPALE ──
    running = True
    while running:
        now = pygame.time.get_ticks()
        dt  = (now - prev_time) / 1000.0
        prev_time = now

        mx, my = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if cine.active:
                        cine.skip()
                    elif popup.visible:
                        popup.close()
                    else:
                        return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        # ── Dimensions adaptatives (si resize) ──
        cur_sw, cur_sh = screen.get_size()
        if cur_sw != sw or cur_sh != sh:
            sw, sh = cur_sw, cur_sh
            map_w  = sw
            map_h  = sh - header_h
            map_size = min(map_w, map_h)
            map_x  = (sw - map_size) // 2
            map_y  = header_h + (map_h - map_size) // 2
            map_surf = _build_map_surface(map_size, map_size)
            for idx, ch in CHAPTERS.items():
                chapter_points[idx].cx = map_x + int(ch["cx"] * map_size)
                chapter_points[idx].cy = map_y + int(ch["cy"] * map_size)

        unlocked_set  = set(save.get("histoire_unlocked", [0]))
        completed_set = set(save.get("histoire_completed", []))

        # ── Update objets ──
        popup.update(dt)
        cine.update(dt)
        notif.update(dt)
        for idx, cp in chapter_points.items():
            cp.update(dt, idx in unlocked_set)

        # ── Dessin fond ──
        screen.fill(C_BG)

        # ── Carte ──
        screen.blit(map_surf, (map_x, map_y))

        # ── Labels carte (toujours au-dessus, sauf popup/cine) ──
        for (text, pct_x, pct_y, size, color, bold) in MAP_LABELS:
            lx = map_x + int(pct_x * map_size)
            ly = map_y + int(pct_y * map_size)
            fkey = "wall" if bold else "map_xs"
            f = fonts.get(fkey) or pygame.font.SysFont("arial", size, bold=bold)
            # Shadow
            s = f.render(text, True, (0, 0, 0))
            screen.blit(s, (lx - s.get_width()//2 + 1, ly - s.get_height()//2 + 1))
            t = f.render(text, True, color)
            screen.blit(t, (lx - t.get_width()//2, ly - t.get_height()//2))

        # ── Points de chapitre ──
        for idx, cp in chapter_points.items():
            unlocked = idx in unlocked_set
            completed = idx in completed_set
            hovered = (
                unlocked
                and math.dist((mx, my), (cp.cx, cp.cy)) < ChapterPoint.RADIUS + 4
                and not cine.active
            )
            cp.draw(screen, unlocked, completed, hovered, save)

        # ── Header ──
        pygame.draw.rect(screen, (10, 8, 4), (0, 0, sw, header_h))
        pygame.draw.line(screen, C_GOLD, (0, header_h), (sw, header_h), 1)
        title_t = fonts["md"].render("Mode Histoire", True, C_PARCHMENT)
        screen.blit(title_t, (sw//2 - title_t.get_width()//2, 15))
        sub_t = fonts["xs"].render("Les Murs - Territoire Humain", True, C_GOLD)
        screen.blit(sub_t, (sw - sub_t.get_width() - 16, 18))

        # Bouton retour
        bh_col = C_GOLD2 if back_rect.collidepoint(mx, my) else C_GOLD
        pygame.draw.rect(screen, (18, 14, 6), back_rect, border_radius=4)
        pygame.draw.rect(screen, bh_col, back_rect, 1, border_radius=4)
        bt = fonts["xs"].render("< Retour", True, bh_col)
        screen.blit(bt, (back_rect.x + back_rect.w//2 - bt.get_width()//2,
                         back_rect.y + back_rect.h//2 - bt.get_height()//2))

        # ── Popup ──
        start_btn = popup.draw(screen, sw, sh, save, fonts, False, mx, my)

        # ── Notification ──
        notif.draw(screen, sw, fonts)

        # ── Cinématique (par-dessus tout) ──
        cine.draw(screen, sw, sh, fonts)

        # ── Gestion des clics ──
        if clicked and not cine.active:
            # Bouton retour
            if back_rect.collidepoint(mx, my):
                sd.save(save)
                return None

            # Bouton fermer popup (zone x)
            if popup.visible:
                close_zone = pygame.Rect(
                    sw - Popup.WIDTH * popup._anim + Popup.WIDTH - 36,
                    50 + 4, 28, 28
                )
                if close_zone.collidepoint(mx, my):
                    popup.close()

            # Bouton commencer
            if start_btn and start_btn.collidepoint(mx, my) and popup.chapter_idx is not None:
                idx = popup.chapter_idx
                ch  = CHAPTERS[idx]

                if ch.get("type") == "cinematique":
                    cine.start(idx)
                    popup.close()
                    # Marquer complété + débloquer suivant
                    _complete_chapter(idx, save, chapter_points, notif, unlocked_set, completed_set)

                elif ch.get("special"):
                    pass  # Rien à lancer

                else:
                    # Vérifier que la mission sélectionnée est bien déverrouillée
                    mission_idx = popup.selected_mission
                    if is_mission_unlocked(save, idx, mission_idx):
                        sd.save(save)
                        # Difficulté croissante selon le chapitre
                        _ch_diff = {1: 2, 2: 3, 3: 4, 4: 4, 5: 5}
                        _diff_val = _ch_diff.get(idx, 2)
                        # Dernier niveau du chapitre = +1 de difficulté
                        _ch_data_tmp = CHAPTERS.get(idx, {})
                        _ch_ms_tmp = _ch_data_tmp.get("missions", [])
                        if mission_idx == len(_ch_ms_tmp) - 1:
                            _diff_val = min(5, _diff_val + 1)
                        return {"chapter": idx, "mission": mission_idx, "difficulty": _diff_val}

            # Clic sur une ligne de mission dans le popup (pour la sélectionner)
            if popup.visible and popup.chapter_idx is not None:
                ch = CHAPTERS[popup.chapter_idx]
                if ch.get("missions"):
                    pw_p = Popup.WIDTH
                    px_p = int(sw - pw_p * popup._anim)
                    py_p = 50
                    content_y_p = 68
                    row_gap_p = 8
                    clip_y = py_p + content_y_p
                    # Utiliser les hauteurs dynamiques si disponibles, sinon fallback 82
                    row_heights = getattr(popup, "mission_row_heights", None)
                    y_cur = clip_y - popup.scroll
                    for i in range(len(ch["missions"])):
                        rh = row_heights[i] if row_heights and i < len(row_heights) else 82
                        row_rect = pygame.Rect(px_p + 8, y_cur, pw_p - 16, rh)
                        if row_rect.collidepoint(mx, my):
                            if is_mission_unlocked(save, popup.chapter_idx, i):
                                popup.selected_mission = i
                            break
                        y_cur += rh + row_gap_p

            # Clic sur un point de chapitre
            if not popup.visible or not pygame.Rect(sw - int(Popup.WIDTH * popup._anim), 50,
                                                     int(Popup.WIDTH * popup._anim),
                                                     sh - 50).collidepoint(mx, my):
                for idx, cp in chapter_points.items():
                    if idx in unlocked_set:
                        if math.dist((mx, my), (cp.cx, cp.cy)) < ChapterPoint.RADIUS + 6:
                            popup.open(idx)
                            break

        # Passer cinématique
        elif clicked and cine.active:
            cine.skip()

        pygame.display.flip()
        clock.tick(60)

    sd.save(save)
    return None


def _complete_chapter(idx, save, chapter_points, notif, unlocked_set, completed_set):
    """Marque un chapitre complété et débloque le suivant."""
    if idx not in completed_set:
        completed_set.add(idx)
        hist_comp = save.get("histoire_completed", [])
        if idx not in hist_comp:
            hist_comp.append(idx)
        save["histoire_completed"] = hist_comp

    ch = CHAPTERS[idx]
    next_idx = ch.get("unlock_next")
    if next_idx is not None and next_idx not in unlocked_set:
        unlocked_set.add(next_idx)
        hist_unl = save.get("histoire_unlocked", [0])
        if next_idx not in hist_unl:
            hist_unl.append(next_idx)
        save["histoire_unlocked"] = hist_unl
        chapter_points[next_idx].trigger_unlock()
        notif.show(f"Nouveau chapitre débloqué : {CHAPTERS[next_idx]['label']}")

    sd.save(save)

# ─────────────────────────────────────────────────────────────────
# API PUBLIQUE — utilisée par game.py
# ─────────────────────────────────────────────────────────────────

def get_mission_objectives(chapter_idx, mission_idx):
    """
    Retourne la liste des objectifs d'une mission (copies fraîches).
    Chaque objectif : {"text": str, "done": bool}
    """
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if 0 <= mission_idx < len(missions):
        return copy.deepcopy(missions[mission_idx].get("objectives", []))
    return []


def get_mission_name(chapter_idx, mission_idx):
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if 0 <= mission_idx < len(missions):
        return missions[mission_idx].get("name", "Mission")
    return "Mission"


def has_next_mission(chapter_idx, mission_idx):
    """Retourne True si une mission suivante existe (même chapitre ou chapitre suivant)."""
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if mission_idx + 1 < len(missions):
        return True
    # Chapitre suivant avec missions
    next_ch = CHAPTERS.get(chapter_idx + 1, {})
    return bool(next_ch.get("missions"))


def get_next_mission(chapter_idx, mission_idx):
    """
    Retourne (chapter_idx, mission_idx) de la mission suivante.
    """
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if mission_idx + 1 < len(missions):
        return chapter_idx, mission_idx + 1
    # Chercher dans le chapitre suivant
    next_ch_idx = chapter_idx + 1
    while next_ch_idx in CHAPTERS:
        next_ch = CHAPTERS[next_ch_idx]
        if next_ch.get("missions"):
            return next_ch_idx, 0
        next_ch_idx += 1
    return chapter_idx, mission_idx  # fallback


def save_mission_result(save, chapter_idx, mission_idx, objectives):
    """
    Sauvegarde le résultat d'une mission :
    - Enregistre les étoiles (objectifs complétés)
    - Sauvegarde l'état de chaque objectif individuellement
    - Déverrouille la mission suivante si ≥1 objectif accompli
    - Marque le chapitre complété si toutes missions faites
    """
    stars_done = sum(1 for o in objectives if o.get("done", False))

    # Stockage des étoiles par mission
    key = f"ch{chapter_idx}_m{mission_idx}_stars"
    prev_best = save.get(key, 0)
    save[key] = max(prev_best, stars_done)

    # Sauvegarder l'état de chaque objectif individuellement
    # On ne rétrograde jamais un objectif déjà accompli (max entre ancien et nouveau)
    obj_key = f"ch{chapter_idx}_m{mission_idx}_objectives"
    prev_obj_states = save.get(obj_key, [])
    new_states = [o.get("done", False) for o in objectives]
    # Fusionner : un objectif déjà accompli reste accompli
    merged = []
    for i, done in enumerate(new_states):
        prev_done = prev_obj_states[i] if i < len(prev_obj_states) else False
        merged.append(done or prev_done)
    save[obj_key] = merged

    # Marquer la mission comme terminée (dans la liste histoire_missions_done)
    done_key = f"ch{chapter_idx}_m{mission_idx}_done"
    save[done_key] = True

    # Déverrouiller la mission suivante si au moins 1 étoile
    if stars_done >= 1:
        ch = CHAPTERS.get(chapter_idx, {})
        missions = ch.get("missions", [])
        next_mission_idx = mission_idx + 1

        if next_mission_idx < len(missions):
            # Mission suivante dans le même chapitre
            unlock_key = f"ch{chapter_idx}_m{next_mission_idx}_unlocked"
            save[unlock_key] = True
        else:
            # Fin du chapitre : débloquer le chapitre suivant
            next_ch_idx = ch.get("unlock_next")
            if next_ch_idx is not None:
                hist_unl = save.get("histoire_unlocked", [0])
                if next_ch_idx not in hist_unl:
                    hist_unl.append(next_ch_idx)
                    save["histoire_unlocked"] = hist_unl
                # Débloquer la première mission du chapitre suivant
                unlock_key = f"ch{next_ch_idx}_m0_unlocked"
                save[unlock_key] = True

            # Marquer le chapitre comme complété
            hist_comp = save.get("histoire_completed", [])
            if chapter_idx not in hist_comp:
                hist_comp.append(chapter_idx)
            save["histoire_completed"] = hist_comp

    sd.save(save)
    return stars_done




def get_mission_objective_states(save, chapter_idx, mission_idx):
    """
    Retourne la liste des états d'objectifs sauvegardés pour une mission.
    Ex : [True, False, True] — index aligné sur les objectifs de get_mission_objectives().
    Retourne [] si aucune donnée sauvegardée.
    """
    key = f"ch{chapter_idx}_m{mission_idx}_objectives"
    return save.get(key, [])


def get_last_mission_index(chapter_idx):
    """
    Retourne l'index (0-basé) de la dernière mission du chapitre donné.
    Retourne -1 si le chapitre n'existe pas ou n'a pas de missions.
    Utilisé par game.py pour détecter le boss de fin de chapitre.
    """
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if not missions:
        return -1
    return len(missions) - 1