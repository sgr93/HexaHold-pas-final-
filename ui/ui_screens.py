"""
ui_screens.py
-------------
Ecrans en overlay : pause, game over, choix de level-up.
Extrait de ui.py.
"""
import random
import pygame
from core.config import ALL_TOWER_TYPES, GRID_WIDTH, GRID_HEIGHT
from ui.ui import (
    COLORS, ITEM_COLORS, ITEM_LABELS, TOWER_DESCS, get_font,
)

# ============================================================
# ECRAN DE PAUSE
# ============================================================

_pause_confirm_pending = None  # None | "restart" | "menu"


def draw_pause_screen(screen, big_font, font, mouse_pos=(0,0), clicked=False):
    """
    Overlay de pause avec 3 boutons : Continuer / Recommencer / Menu.
    Retourne : "resume" | "restart" | "menu" | None
    """
    global _pause_confirm_pending

    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    pt = big_font.render("PAUSE", True, COLORS["accent"])
    screen.blit(pt, ((w - pt.get_width()) // 2, h // 2 - 130))

    mx, my = mouse_pos
    btn_w, btn_h = 240, 54
    gap = 16
    total_h = 3 * btn_h + 2 * gap
    start_y = h // 2 - total_h // 2 + 20

    buttons = [
        ("Continuer",   "resume",  (60, 160, 80),  (150, 255, 160)),
        ("Recommencer", "restart", (60, 80,  160), (150, 160, 255)),
        ("Menu",        "menu",    (120, 50, 50),  (255, 130, 130)),
    ]

    action = None
    confirm_open = _pause_confirm_pending is not None
    for i, (label, key, col_n, col_h) in enumerate(buttons):
        bx = (w - btn_w) // 2
        by = start_y + i * (btn_h + gap)
        rect = pygame.Rect(bx, by, btn_w, btn_h)
        hov  = rect.collidepoint(mx, my) and not confirm_open
        pygame.draw.rect(screen, col_h if hov else col_n, rect, border_radius=12)
        border_col = (255, 255, 255) if hov else (180, 180, 200)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=12)
        lbl = font.render(label, True, (255, 255, 255))
        screen.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                           by + (btn_h - lbl.get_height()) // 2))
        if clicked and hov:
            if key == "resume":
                action = key
            else:
                _pause_confirm_pending = key

    # ── Popup de confirmation pour Recommencer / Menu ──
    if _pause_confirm_pending is not None:
        result = _draw_confirm_popup(screen, font, big_font, mouse_pos, clicked,
                                     _pause_confirm_pending)
        if result == "ok":
            action = _pause_confirm_pending
            _pause_confirm_pending = None
        elif result == "cancel":
            _pause_confirm_pending = None

    return action


def _draw_confirm_popup(screen, font, big_font, mouse_pos, clicked, pending_key):
    """Popup modale de confirmation. Retourne 'ok', 'cancel' ou None."""
    w, h = screen.get_size()
    veil = pygame.Surface((w, h), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 180))
    screen.blit(veil, (0, 0))

    title_txt = "Recommencer la partie ?" if pending_key == "restart" else "Retour au menu ?"
    sub_txt   = "La progression de cette partie sera perdue."
    t  = big_font.render(title_txt, True, (255, 230, 150))
    st = font.render(sub_txt, True, (220, 200, 150))

    bw, bh = 170, 46
    gap = 20
    pad_x = 36
    pad_y = 22
    btn_total_w = bw * 2 + gap
    pop_w = max(t.get_width(), st.get_width(), btn_total_w) + pad_x * 2
    pop_h = pad_y + t.get_height() + 12 + st.get_height() + 22 + bh + pad_y
    pop = pygame.Rect((w - pop_w) // 2, (h - pop_h) // 2, pop_w, pop_h)
    pygame.draw.rect(screen, (28, 22, 14), pop, border_radius=12)
    pygame.draw.rect(screen, (200, 170, 60), pop, 2, border_radius=12)

    screen.blit(t,  (pop.centerx - t.get_width()  // 2, pop.y + pad_y))
    screen.blit(st, (pop.centerx - st.get_width() // 2, pop.y + pad_y + t.get_height() + 12))

    mx, my = mouse_pos
    total_w = btn_total_w
    by = pop.bottom - bh - pad_y
    bx_ok     = pop.centerx - total_w // 2
    bx_cancel = bx_ok + bw + gap

    ok_rect     = pygame.Rect(bx_ok,     by, bw, bh)
    cancel_rect = pygame.Rect(bx_cancel, by, bw, bh)

    ok_hov  = ok_rect.collidepoint(mx, my)
    can_hov = cancel_rect.collidepoint(mx, my)

    pygame.draw.rect(screen, (160, 60, 60) if ok_hov else (110, 40, 40), ok_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 180, 180), ok_rect, 2, border_radius=10)
    ok_lbl = font.render("Confirmer", True, (255, 255, 255))
    screen.blit(ok_lbl, (ok_rect.centerx - ok_lbl.get_width() // 2,
                         ok_rect.centery - ok_lbl.get_height() // 2))

    pygame.draw.rect(screen, (60, 100, 60) if can_hov else (40, 70, 40), cancel_rect, border_radius=10)
    pygame.draw.rect(screen, (180, 230, 180), cancel_rect, 2, border_radius=10)
    can_lbl = font.render("Annuler", True, (255, 255, 255))
    screen.blit(can_lbl, (cancel_rect.centerx - can_lbl.get_width() // 2,
                          cancel_rect.centery - can_lbl.get_height() // 2))

    if clicked:
        if ok_hov:
            return "ok"
        if can_hov:
            return "cancel"
    return None


# ============================================================
# ECRAN GAME OVER / VICTOIRE
# ============================================================

def draw_gameover_screen(screen, big_font, font, win, mouse_pos, clicked, reward_coins=0):
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    msg, color = ("VICTOIRE !", (80, 255, 80)) if win else ("DÉFAITE", (255, 60, 60))
    title = big_font.render(msg, True, color)
    screen.blit(title, ((w - title.get_width()) // 2, h // 2 - 100))

    if win:
        subtitle = font.render(f"+{reward_coins} pièces gagnées", True, (240, 220, 140))
    else:
        subtitle = font.render("Essayez encore !", True, (240, 220, 140))
    screen.blit(subtitle, ((w - subtitle.get_width()) // 2, h // 2 - 40))

    btn_w, btn_h = 220, 52
    btn_x, btn_y = (w - btn_w) // 2, h // 2 + 20
    btn_rect  = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    hovered   = btn_rect.collidepoint(mouse_pos)
    btn_color = (100, 180, 100) if hovered else (60, 120, 60)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=10)
    pygame.draw.rect(screen, (200, 255, 200), btn_rect, 2, border_radius=10)
    lbl = font.render("Rejouer", True, (255, 255, 255))
    screen.blit(lbl, (btn_x + (btn_w - lbl.get_width()) // 2,
                       btn_y + (btn_h - lbl.get_height()) // 2))

    menu_btn = pygame.Rect((w - btn_w) // 2, h // 2 + 90, btn_w, btn_h)
    mhov     = menu_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (60, 80, 160) if mhov else (40, 55, 110), menu_btn, border_radius=10)
    pygame.draw.rect(screen, (150, 180, 255), menu_btn, 2, border_radius=10)
    mlbl = font.render("Menu Principal", True, (255, 255, 255))
    screen.blit(mlbl, (menu_btn.x + (menu_btn.w - mlbl.get_width()) // 2,
                        menu_btn.y + (menu_btn.h - mlbl.get_height()) // 2))

    if clicked:
        if hovered:
            return "restart"
        if mhov:
            return "menu"
    return None


# ============================================================
# MESSAGE DE DEMARRAGE
# ============================================================

def draw_start_hint(screen, font, offset_x, offset_y):
    hint = font.render("Placez une tour pour démarrer", True, (220, 220, 100))
    screen.blit(hint, (
        offset_x + (GRID_WIDTH  - hint.get_width())  // 2,
        offset_y + (GRID_HEIGHT - hint.get_height()) // 2,
    ))


# ============================================================
# LEVEL-UP BANNER  (choix de 3 tours à ajouter à l'inventaire)
# ============================================================

def pick_three_towers():
    """Retourne 3 types de tours (avec répétition possible si nécessaire)."""
    pool = list(ALL_TOWER_TYPES) * 2
    random.shuffle(pool)
    seen = []
    for t in pool:
        if t not in seen:
            seen.append(t)
        if len(seen) == 3:
            break
    while len(seen) < 3:
        seen.append(random.choice(ALL_TOWER_TYPES))
    return seen[:3]


def draw_levelup_banner(screen, big_font, font, choices, mouse_pos, clicked):
    """
    Affiche la bannière de level-up avec overlay gris + 3 cartes de tours.
    Retourne le type de tour choisi (str) ou None si pas encore choisi.
    """
    w, h = screen.get_size()

    # Overlay gris semi-transparent
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((20, 20, 30, 190))
    screen.blit(overlay, (0, 0))

    # Titre
    title_surf = big_font.render(" CHOIX DE TOUR ", True, (255, 220, 60))
    screen.blit(title_surf, (w // 2 - title_surf.get_width() // 2, h // 5 - 20))

    sub = font.render("Choisissez la tour que vous voulez ajouter à votre inventaire", True, (200, 200, 200))
    screen.blit(sub, (w // 2 - sub.get_width() // 2, h // 5 + 32))

    # Cartes
    card_w, card_h = 160, 200
    gap            = 30
    total_w        = 3 * card_w + 2 * gap
    start_x        = (w - total_w) // 2
    card_y         = h // 2 - card_h // 2

    chosen = None
    mx, my = mouse_pos

    for i, tower_type in enumerate(choices):
        cx   = start_x + i * (card_w + gap)
        rect = pygame.Rect(cx, card_y, card_w, card_h)
        hov  = rect.collidepoint(mx, my)

        base = ITEM_COLORS.get(tower_type, (80, 80, 80))
        col  = tuple(min(255, c + 40) for c in base) if hov else base
        pygame.draw.rect(screen, col, rect, border_radius=14)
        bdr  = (255, 220, 60) if hov else (150, 150, 180)
        pygame.draw.rect(screen, bdr, rect, 3 if hov else 1, border_radius=14)

        # Icône (cercle)
        icon_r = 36
        pygame.draw.circle(screen, (255, 255, 255, 180),
                           (cx + card_w // 2, card_y + 60), icon_r, 0)
        pygame.draw.circle(screen, bdr, (cx + card_w // 2, card_y + 60), icon_r, 2)
        ilbl = big_font.render(tower_type[0].upper(), True, col)
        screen.blit(ilbl, (cx + card_w // 2 - ilbl.get_width() // 2,
                            card_y + 60 - ilbl.get_height() // 2))

        # Nom
        nlbl = font.render(ITEM_LABELS.get(tower_type, tower_type), True, (255, 255, 255))
        screen.blit(nlbl, (cx + (card_w - nlbl.get_width()) // 2, card_y + 108))

        # Description
        desc_font = get_font("sm")
        desc_lines = TOWER_DESCS.get(tower_type, "").split("\n")
        for li, line in enumerate(desc_lines):
            dl = desc_font.render(line, True, (200, 220, 255))
            screen.blit(dl, (cx + (card_w - dl.get_width()) // 2,
                              card_y + 136 + li * 18))

        if clicked and hov:
            chosen = tower_type

    return chosen
