"""
ui/ui_mission.py

Panneau d'objectifs en jeu et ecrans de mission complete / echec.
Extrait de ui.py pour garder ce fichier lisible.
"""

import os
import pygame
from core.config import GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH

# get_font, COLORS et les helpers definis ici pour eviter l'import circulaire
# ui.py importe ui_mission.py, donc ui_mission.py ne peut pas reimporter ui.py
def get_font(size_key="md", bold=False):
    sizes = {"xs": 14, "sm": 18, "md": 22, "lg": 30, "xl": 48}
    return pygame.font.SysFont("arial", sizes.get(size_key, 22), bold=bold)

COLORS = {
    "border": (88, 103, 138),
    "accent": (255, 205, 92),
    "text":   (236, 240, 250),
    "muted":  (163, 173, 196),
}

_objectif_bg_cache = {}

def _load_objectif_bg(w, h):
    key = (w, h)
    if key in _objectif_bg_cache:
        return _objectif_bg_cache[key]
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "objectif.png")
    result = None
    if os.path.isfile(path):
        try:
            img    = pygame.image.load(path).convert_alpha()
            result = pygame.transform.smoothscale(img, (w, h))
        except Exception:
            result = None
    _objectif_bg_cache[key] = result
    return result

_star_cache = {}

def draw_star(screen, x, y, size, done):
    key = (size, done)
    if key not in _star_cache:
        path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "etoiles.png")
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (size, size))
                if not done:
                    grey = img.copy()
                    grey.fill((0, 0, 0, 0))
                    for px in range(size):
                        for py in range(size):
                            r, g, b, a = img.get_at((px, py))
                            lum = int(0.3 * r + 0.59 * g + 0.11 * b)
                            grey.set_at((px, py), (lum // 2, lum // 2, lum // 2, a))
                    _star_cache[key] = grey
                else:
                    _star_cache[key] = img
            except Exception:
                _star_cache[key] = None
        else:
            _star_cache[key] = None
    surf = _star_cache[key]
    if surf is not None:
        screen.blit(surf, (x, y))
        return True
    fnt = pygame.font.SysFont("arial", size, bold=True)
    col = (255, 210, 40) if done else (60, 60, 80)
    screen.blit(fnt.render("*", True, col), (x, y))
    return False

def _draw_panel(screen, rect, alt=False):
    bg = (36, 44, 64) if alt else (29, 35, 51)
    pygame.draw.rect(screen, bg,               rect, border_radius=10)
    pygame.draw.rect(screen, COLORS["border"], rect, 1, border_radius=10)

def _draw_progress_bar(screen, rect, value, max_value, fg, bg=(40, 40, 50)):
    pygame.draw.rect(screen, bg, rect, border_radius=6)
    ratio = 0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    fill  = pygame.Rect(rect.x, rect.y, int(rect.w * ratio), rect.h)
    pygame.draw.rect(screen, fg,               fill, border_radius=6)
    pygame.draw.rect(screen, COLORS["border"], rect, 1, border_radius=6)


# OBJECTIFS EN JEU

def draw_mission_objectives(screen, offset_x, offset_y, objectives):
    """
    Affiche le panneau d'objectifs a droite de la grille.
    Fond objectif.png si present, fallback couleur sinon.
    Les textes longs passent a la ligne automatiquement.
    """
    if not objectives:
        return

    panel_x    = offset_x + GRID_WIDTH + 8
    panel_w    = INTERFACE_WIDTH - 16
    pad        = 10
    fnt_title  = get_font("sm", bold=True)
    fnt_obj    = get_font("xs")
    max_text_w = panel_w - pad * 2 - 18  # largeur dispo apres l'etoile

    def _wrap(text, font, max_w):
        """Decoupe un texte en lignes qui tiennent dans max_w pixels."""
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

    # Hauteur calculee selon le contenu reel — pas de hauteur fixe
    total_content_h = title_h
    wrapped_cache   = []
    for obj in objectives:
        lines = _wrap(obj.get("text", ""), fnt_obj, max_text_w)
        wrapped_cache.append(lines)
        total_content_h += max(1, len(lines)) * obj_line_h + 4

    panel_h = pad * 2 + total_content_h
    panel   = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

    # Fond : objectif.png avec coins arrondis, fallback couleur
    obj_bg = _load_objectif_bg(panel_w, panel_h)
    if obj_bg is not None:
        mask = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, panel_w, panel_h), border_radius=12)
        obj_bg_rounded = obj_bg.copy()
        obj_bg_rounded.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        panel.blit(obj_bg_rounded, (0, 0))
    else:
        panel.fill((20, 24, 40, 200))
        pygame.draw.rect(panel, COLORS["border"],
                         pygame.Rect(0, 0, panel_w, panel_h), 1, border_radius=12)

    # Titre en noir pour contraster avec le fond clair du panneau
    title = fnt_title.render("Objectifs", True, (0, 0, 0))
    panel.blit(title, (pad, pad))

    ty = pad + title_h
    for i, obj in enumerate(objectives):
        done    = obj.get("done", False)
        lines   = wrapped_cache[i]
        block_h = len(lines) * obj_line_h
        # Etoile centree verticalement sur le bloc de texte de cet objectif
        draw_star(panel, pad, ty + (block_h - 14) // 2, 14, done)
        txt_col = (40, 40, 40) if done else (70, 70, 70)
        for li, line in enumerate(lines):
            lt = fnt_obj.render(line, True, txt_col)
            panel.blit(lt, (pad + 18, ty + li * obj_line_h))
        ty += block_h + 4

    screen.blit(panel, (panel_x, offset_y))


# ECRAN DE VICTOIRE

def draw_mission_complete_screen(screen, big_font, font, objectives,
                                  reward_coins, has_next_mission,
                                  mouse_pos, clicked):
    """
    Popup de fin de mission reussie.
    Affiche les etoiles obtenues, la recompense et les boutons d'action.
    Retourne l'action choisie : "next", "restart", "histoire", ou None.
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    stars_done = sum(1 for o in objectives if o.get("done", False))
    n_obj      = len(objectives)

    # Carte plus haute si on a un bouton "mission suivante"
    card_w = 420
    card_h = 360 if has_next_mission else 310
    cx     = (w - card_w) // 2
    cy     = (h - card_h) // 2

    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    card.fill((20, 26, 42, 240))
    pygame.draw.rect(card, (100, 120, 200), pygame.Rect(0, 0, card_w, card_h), 2, border_radius=14)
    screen.blit(card, (cx, cy))

    title = big_font.render("MISSION TERMINEE", True, (255, 220, 60))
    screen.blit(title, (cx + card_w // 2 - title.get_width() // 2, cy + 18))

    # Etoiles grand format
    star_size    = 42
    star_y       = cy + 72
    total_star_w = n_obj * (star_size + 6)
    star_start   = cx + card_w // 2 - total_star_w // 2
    for i in range(n_obj):
        draw_star(screen, star_start + i * (star_size + 6), star_y, star_size, i < stars_done)

    summary_fnt = get_font("sm")
    summary = summary_fnt.render(f"{stars_done} / {n_obj} objectifs accomplis", True, (200, 210, 230))
    screen.blit(summary, (cx + card_w // 2 - summary.get_width() // 2, star_y + 48))

    # Detail des objectifs avec etoile et couleur selon l'etat
    obj_fnt = get_font("xs")
    for i, obj in enumerate(objectives):
        done = obj.get("done", False)
        draw_star(screen, cx + 24, star_y + 80 + i * 20, 14, done)
        col = (160, 230, 160) if done else (200, 100, 100)
        t   = obj_fnt.render(obj.get("text", ""), True, col)
        screen.blit(t, (cx + 42, star_y + 80 + i * 20 + 1))

    reward_y = star_y + 80 + n_obj * 18 + 10
    if reward_coins > 0:
        rw = summary_fnt.render(f"+{reward_coins} pieces", True, (255, 205, 92))
        screen.blit(rw, (cx + card_w // 2 - rw.get_width() // 2, reward_y))
        btn_base_y = reward_y + 34
    else:
        btn_base_y = reward_y + 6

    mx, my  = mouse_pos
    btn_w   = 160
    btn_h   = 42
    gap     = 12
    action  = None

    # "Mission suivante" uniquement si elle existe — pas de bouton mort
    buttons = []
    if has_next_mission:
        buttons.append(("Mission suivante", "next",     (50, 140, 80),  (120, 255, 150)))
    buttons.append(    ("Rejouer",           "restart",  (50, 80,  160), (120, 160, 255)))
    buttons.append(    ("Carte",             "histoire", (80, 50,  80),  (180, 120, 180)))

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


# ECRAN DE DEFAITE

def draw_mission_failed_screen(screen, big_font, font, objectives, mouse_pos, clicked):
    """
    Popup de defaite en mode histoire.
    Plus sobre que l'ecran de victoire — fond rouge sombre, pas de recompense.
    Retourne "restart", "histoire", ou None.
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    stars_done = sum(1 for o in objectives if o.get("done", False))
    n_obj      = len(objectives)

    card_w = 420
    card_h = 310
    cx     = (w - card_w) // 2
    cy     = (h - card_h) // 2

    card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    card.fill((30, 12, 12, 240))
    pygame.draw.rect(card, (180, 60, 60), pygame.Rect(0, 0, card_w, card_h), 2, border_radius=14)
    screen.blit(card, (cx, cy))

    title = big_font.render("MISSION ECHOUEE", True, (255, 80, 80))
    screen.blit(title, (cx + card_w // 2 - title.get_width() // 2, cy + 16))

    star_size    = 36
    star_y       = cy + 72
    total_star_w = n_obj * (star_size + 6)
    star_start   = cx + card_w // 2 - total_star_w // 2
    for i in range(n_obj):
        draw_star(screen, star_start + i * (star_size + 6), star_y, star_size, i < stars_done)

    # Objectifs avec leur etat meme en cas d'echec — utile pour savoir ce qui a marche
    obj_fnt = get_font("xs")
    for i, obj in enumerate(objectives):
        done = obj.get("done", False)
        draw_star(screen, cx + 24, star_y + 50 + i * 20, 14, done)
        col = (160, 230, 160) if done else (200, 100, 100)
        t   = obj_fnt.render(obj.get("text", ""), True, col)
        screen.blit(t, (cx + 42, star_y + 50 + i * 20 + 1))

    mx, my  = mouse_pos
    btn_w   = 160
    btn_h   = 42
    gap     = 14
    buttons = [
        ("Rejouer", "restart",  (50, 80, 160),  (120, 160, 255)),
        ("Carte",   "histoire", (80, 50, 80),   (180, 120, 180)),
    ]
    total_btn_w = len(buttons) * btn_w + (len(buttons) - 1) * gap
    btn_start_x = cx + card_w // 2 - total_btn_w // 2
    btn_y       = cy + card_h - btn_h - 18
    action      = None

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