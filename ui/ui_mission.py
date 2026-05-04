"""
ui_mission.py
-------------
Panneau d'objectifs en jeu et ecrans de mission complete / failed.
Extrait de ui.py.
"""
import os
import pygame
from core.config import GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH
from ui.ui import (
    COLORS, get_font, _draw_panel, _draw_progress_bar, draw_star, _load_objectif_bg,
)

# ============================================================
# OBJECTIFS DE MISSION (panneau droit, en jeu)
# ============================================================

def draw_mission_objectives(screen, offset_x, offset_y, objectives):
    """
    Affiche les objectifs de la mission en cours à droite de la grille.
    Le fond utilise assets/sprites/objectif.png si présent.
    Titre en noir, objectifs en gris foncé, étoiles à gauche du texte.
    Les textes longs sont retournés à la ligne automatiquement.
    """
    if not objectives:
        return

    panel_x = offset_x + GRID_WIDTH + 8
    panel_w = INTERFACE_WIDTH - 16
    pad     = 10
    fnt_title = get_font("sm", bold=True)
    fnt_obj   = get_font("xs")
    max_text_w = panel_w - pad * 2 - 18  # largeur dispo après étoile

    # Fonction de découpage en lignes
    def _wrap(text, font, max_w):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.render(test, True, (0, 0, 0)).get_width() <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines if lines else [text]

    obj_line_h = fnt_obj.get_height() + 2
    title_h    = fnt_title.get_height() + 6

    # Calculer la hauteur totale du panneau selon le contenu réel
    total_content_h = title_h
    wrapped_cache = []
    for obj in objectives:
        lines = _wrap(obj.get("text", ""), fnt_obj, max_text_w)
        wrapped_cache.append(lines)
        total_content_h += max(1, len(lines)) * obj_line_h + 4

    panel_h = pad * 2 + total_content_h

    # ── Fond : objectif.png redimensionné avec coins arrondis ──
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

    _obj_bg = _load_objectif_bg(panel_w, panel_h)
    if _obj_bg is not None:
        mask = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, panel_w, panel_h), border_radius=12)
        _obj_bg_rounded = _obj_bg.copy()
        _obj_bg_rounded.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        panel.blit(_obj_bg_rounded, (0, 0))
    else:
        panel.fill((20, 24, 40, 200))
        pygame.draw.rect(panel, COLORS["border"],
                         pygame.Rect(0, 0, panel_w, panel_h), 1, border_radius=12)

    # Titre en noir
    title = fnt_title.render("Objectifs", True, (0, 0, 0))
    panel.blit(title, (pad, pad))

    ty = pad + title_h
    for i, obj in enumerate(objectives):
        done  = obj.get("done", False)
        lines = wrapped_cache[i]
        # Étoile à gauche, centrée sur la hauteur du bloc de texte
        block_h = len(lines) * obj_line_h
        star_y_c = ty + (block_h - 14) // 2
        draw_star(panel, pad, star_y_c, 14, done)

        txt_col = (40, 40, 40) if done else (70, 70, 70)
        for li, line in enumerate(lines):
            lt = fnt_obj.render(line, True, txt_col)
            panel.blit(lt, (pad + 18, ty + li * obj_line_h))
        ty += block_h + 4

    panel_y = offset_y
    screen.blit(panel, (panel_x, panel_y))


# ============================================================
# ÉCRAN DE FIN DE MISSION (mode histoire)
# ============================================================

def draw_mission_complete_screen(screen, big_font, font, objectives,
                                  reward_coins, has_next_mission,
                                  mouse_pos, clicked):
    """
    Popup de fin de mission mode histoire.
    Affiche les étoiles obtenues, la récompense, et propose :
      - Rejouer      → "restart"
      - Mission suiv → "next"   (si has_next_mission)
      - Carte        → "histoire"

    Retourne l'action choisie ou None.
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    stars_done = sum(1 for o in objectives if o.get("done", False))
    n_obj      = len(objectives)

    # Carte centrale
    card_w, card_h = 420, 360 if has_next_mission else 310
    cx = (w - card_w) // 2
    cy = (h - card_h) // 2
    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    card.fill((20, 26, 42, 240))
    pygame.draw.rect(card, (100, 120, 200), pygame.Rect(0, 0, card_w, card_h), 2, border_radius=14)
    screen.blit(card, (cx, cy))

    # Titre
    title = big_font.render("MISSION TERMINÉE", True, (255, 220, 60))
    screen.blit(title, (cx + card_w // 2 - title.get_width() // 2, cy + 18))

    # Étoiles image
    star_size = 42
    star_y    = cy + 72
    total_star_w = n_obj * (star_size + 6)
    star_start   = cx + card_w // 2 - total_star_w // 2
    for i in range(n_obj):
        done = i < stars_done
        draw_star(screen, star_start + i * (star_size + 6), star_y, star_size, done)

    # Résumé étoiles
    summary_fnt = get_font("sm")
    summary = summary_fnt.render(f"{stars_done} / {n_obj} objectifs accomplis", True, (200, 210, 230))
    screen.blit(summary, (cx + card_w // 2 - summary.get_width() // 2, star_y + 48))

    # Objectifs détaillés
    obj_fnt = get_font("xs")
    for i, obj in enumerate(objectives):
        done   = obj.get("done", False)
        draw_star(screen, cx + 24, star_y + 80 + i * 20, 14, done)
        col    = (160, 230, 160) if done else (200, 100, 100)
        t      = obj_fnt.render(obj.get("text", ""), True, col)
        screen.blit(t, (cx + 24 + 18, star_y + 80 + i * 20 + 1))

    # Récompense
    reward_y = star_y + 80 + n_obj * 18 + 10
    if reward_coins > 0:
        rw = summary_fnt.render(f"+{reward_coins} pièces", True, (255, 205, 92))
        screen.blit(rw, (cx + card_w // 2 - rw.get_width() // 2, reward_y))
        btn_base_y = reward_y + 34
    else:
        btn_base_y = reward_y + 6

    # Boutons
    mx, my = mouse_pos
    btn_w, btn_h = 160, 42
    gap = 12
    action = None

    buttons = []
    if has_next_mission:
        buttons.append(("Mission suivante →", "next",    (50, 140, 80),  (120, 255, 150)))
    buttons.append(    ("Rejouer",             "restart", (50, 80,  160), (120, 160, 255)))
    buttons.append(    ("← Carte",             "histoire",(80, 50,  80),  (180, 120, 180)))

    total_btn_w = len(buttons) * btn_w + (len(buttons) - 1) * gap
    btn_start_x = cx + card_w // 2 - total_btn_w // 2

    for i, (label, key, col_n, col_h) in enumerate(buttons):
        bx   = btn_start_x + i * (btn_w + gap)
        by   = cy + btn_base_y
        rect = pygame.Rect(bx, by, btn_w, btn_h)
        hov  = rect.collidepoint(mx, my)
        pygame.draw.rect(screen, col_h if hov else col_n, rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 255) if hov else (120, 130, 160), rect, 2, border_radius=10)
        lbl = font.render(label, True, (255, 255, 255))
        screen.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                           by + (btn_h - lbl.get_height()) // 2))
        if clicked and hov:
            action = key

    return action

# ============================================================
# ÉCRAN DE DÉFAITE — MODE HISTOIRE
# ============================================================

def draw_mission_failed_screen(screen, big_font, font, objectives, mouse_pos, clicked):
    """
    Popup de défaite en mode histoire.
    Propose : Rejouer → "restart" | ← Carte → "histoire"
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    stars_done = sum(1 for o in objectives if o.get("done", False))
    n_obj = len(objectives)

    card_w, card_h = 420, 310
    cx = (w - card_w) // 2
    cy = (h - card_h) // 2
    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    card.fill((30, 12, 12, 240))
    pygame.draw.rect(card, (180, 60, 60), pygame.Rect(0, 0, card_w, card_h), 2, border_radius=14)
    screen.blit(card, (cx, cy))

    title = big_font.render("MISSION ECHOUEE", True, (255, 80, 80))
    screen.blit(title, (cx + card_w // 2 - title.get_width() // 2, cy + 16))

    star_size = 36
    star_y    = cy + 72
    total_star_w = n_obj * (star_size + 6)
    star_start   = cx + card_w // 2 - total_star_w // 2
    for i in range(n_obj):
        done = i < stars_done
        draw_star(screen, star_start + i * (star_size + 6), star_y, star_size, done)

    obj_fnt = get_font("xs")
    for i, obj in enumerate(objectives):
        done = obj.get("done", False)
        draw_star(screen, cx + 24, star_y + 50 + i * 20, 14, done)
        col = (160, 230, 160) if done else (200, 100, 100)
        t   = obj_fnt.render(obj.get("text", ""), True, col)
        screen.blit(t, (cx + 24 + 18, star_y + 50 + i * 20 + 1))

    mx, my = mouse_pos
    btn_w, btn_h = 160, 42
    gap = 14
    buttons = [
        ("Rejouer",  "restart",  (50, 80, 160),  (120, 160, 255)),
        ("<- Carte", "histoire", (80, 50, 80),   (180, 120, 180)),
    ]
    total_btn_w = len(buttons) * btn_w + (len(buttons) - 1) * gap
    btn_start_x = cx + card_w // 2 - total_btn_w // 2
    btn_y = cy + card_h - btn_h - 18
    action = None
    for i, (label, key, col_n, col_h) in enumerate(buttons):
        bx   = btn_start_x + i * (btn_w + gap)
        rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
        hov  = rect.collidepoint(mx, my)
        pygame.draw.rect(screen, col_h if hov else col_n, rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 255) if hov else (120, 130, 160), rect, 2, border_radius=10)
        lbl = font.render(label, True, (255, 255, 255))
        screen.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                          btn_y + (btn_h - lbl.get_height()) // 2))
        if clicked and hov:
            action = key
    return action

