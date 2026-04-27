"""
title_screen.py
---------------
Écran titre HexaHold — style SNK / médiéval.
Items : Jouer | Options | Quitter
Retourne ("play", save) ou (None, save).
"""

import math
import pygame
import save_data as sd
import theme

# ============================================================
ITEMS = [
    {"label": "Jouer",    "action": "play"},
    {"label": "Options",  "action": "options"},
    {"label": "Quitter",  "action": "quit"},
]

_bg_cache     = {}
_blason_cache = {}


def run_title_screen(screen: pygame.Surface,
                     clock:  pygame.time.Clock,
                     save:   dict):
    """
    Boucle principale de l'écran titre.
    Retourne ("play", save) ou (None, save).
    """
    w, h = screen.get_size()

    # ── Assets ──────────────────────────────────────────────
    bg = _get_bg(w, h)
    blason = _get_blason(h)

    # ── Polices ─────────────────────────────────────────────
    f_title = theme.font(theme.SZ_TITLE)
    f_item  = theme.font(theme.SZ_MENU)
    f_act   = theme.font(theme.SZ_MENU_A)
    f_slog  = theme.font(theme.SZ_SMALL, body=True)

    # ── État ────────────────────────────────────────────────
    hov_idx = 0
    tick    = 0

    running = True
    while running:
        tick += 1
        w, h = screen.get_size()
        mx, my = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, save
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, save
                elif event.key in (pygame.K_UP, pygame.K_w):
                    hov_idx = (hov_idx - 1) % len(ITEMS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    hov_idx = (hov_idx + 1) % len(ITEMS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    action = ITEMS[hov_idx]["action"]
                    result = _handle_action(action, screen, clock, save, w, h, bg)
                    if result == "play":
                        return "play", save
                    elif result == "quit":
                        return None, save
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.VIDEORESIZE:
                w, h = event.w, event.h
                bg = _get_bg(w, h)
                blason = _get_blason(h)

        # ── Rendu ────────────────────────────────────────────
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill(theme.DARK)
        screen.blit(theme.make_vignette(w, h), (0, 0))

        # ── Zone titre (haut gauche) ─────────────────────────
        tx = int(w * 0.04)
        ty = int(h * 0.05)

        # Blason centré entre Hexa et Hold (au-dessus)
        hexa_s = f_title.render("Hexa", True, theme.CREAM)
        hold_s = f_title.render("Hold", True, theme.GOLD_LIGHT)
        title_w = hexa_s.get_width() + hold_s.get_width()

        if blason:
            bx = tx + (title_w - blason.get_width()) // 2
            by = ty
            screen.blit(blason, (bx, by))
            ty += blason.get_height() + int(h * 0.005)

        theme.draw_gold_rule(screen, tx, ty, theme.RULE_W)
        ty += 4

        # Titre "Hexa" (crème) + "Hold" (doré)
        _sh = f_title.render("HexaHold", True, (0, 0, 0))
        screen.blit(_sh, (tx + 2, ty + 2))
        screen.blit(hexa_s, (tx, ty))
        screen.blit(hold_s, (tx + hexa_s.get_width(), ty))
        ty += f_title.get_height() + 4

        theme.draw_gold_rule(screen, tx, ty, theme.RULE_W)
        ty += 8

        slogan = f_slog.render("Défends les murs · Protège l'humanité",
                               True, theme.GOLD_DIM)
        screen.blit(slogan, (tx, ty))

        # ── Items de menu ────────────────────────────────────
        menu_y = int(h * 0.44)
        gap    = int(h * 0.004)

        for i, item in enumerate(ITEMS):
            is_act = (i == hov_idx)
            fnt    = f_act if is_act else f_item
            col    = theme.GOLD_LIGHT if is_act else theme.CREAM_DIM
            lbl    = fnt.render(item["label"], True, col)

            iy       = menu_y + i * (theme.SZ_MENU_A + gap + 8)
            ix       = tx
            hit_rect = pygame.Rect(ix - 4, iy - 4,
                                   lbl.get_width() + 120,
                                   lbl.get_height() + 8)

            if hit_rect.collidepoint(mx, my):
                hov_idx = i
                if clicked:
                    action = item["action"]
                    result = _handle_action(action, screen, clock, save, w, h, bg)
                    if result == "play":
                        return "play", save
                    elif result == "quit":
                        return None, save

            if is_act:
                _draw_item_bg(screen, hit_rect)
                pygame.draw.rect(screen, theme.GOLD,
                                 pygame.Rect(ix - 4, iy, 2, lbl.get_height()))
                _draw_glow_text(screen, lbl, ix + 10, iy, tick)
            else:
                sh = fnt.render(item["label"], True, (0, 0, 0))
                screen.blit(sh, (ix + 11, iy + 1))
                screen.blit(lbl, (ix + 10, iy))

        pygame.display.flip()
        clock.tick(60)

    return None, save


# ============================================================
# ACTIONS
# ============================================================
def _handle_action(action, screen, clock, save, w, h, bg):
    if action == "options":
        _run_options(screen, clock, save, w, h, bg)
        return None
    return action  # "play" ou "quit"


def _run_options(screen, clock, save, w, h, bg):
    """Popup Options (volume musique / sons / plein écran)."""
    f_title = theme.font(theme.SZ_SECTION)
    f_label = theme.font(theme.SZ_LABEL, body=True)
    f_small = theme.font(theme.SZ_SMALL, body=True)

    pop_w = min(480, w - 80)
    pop_h = 280
    pop   = pygame.Rect((w - pop_w)//2, (h - pop_h)//2, pop_w, pop_h)

    music_vol = save.get("music_volume", 0.8)
    sound_vol = save.get("sound_volume", 0.8)

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        # Fond
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill(theme.DARK)
        screen.blit(theme.make_vignette(w, h), (0, 0))

        # Overlay sombre
        theme.draw_rect_alpha(screen, (0, 0, 0, 160), pygame.Rect(0, 0, w, h))

        # Panel
        theme.draw_panel(screen, pop, color=theme.DARK_2,
                         border_color=theme.GOLD, radius=theme.RADIUS_LG, border_w=2)
        theme.draw_corner_ornaments(screen, pop)

        # Titre
        theme.render_text(screen, "Options", f_title, theme.GOLD_LIGHT,
                          pop.centerx, pop.y + 16, center=True)
        theme.draw_gold_rule(screen, pop.centerx - theme.RULE_W//2,
                             pop.y + 16 + f_title.get_height() + 2, theme.RULE_W)

        by = pop.y + 70

        # Volume musique
        theme.render_text(screen, "Volume Musique", f_label, theme.CREAM, pop.x+24, by, shadow=False)
        bar = pygame.Rect(pop.x+24, by+24, pop_w-48, 14)
        music_vol = _slider(screen, f_small, mx, my, clicked, bar, music_vol)
        by += 80

        # Volume sons
        theme.render_text(screen, "Volume Sons", f_label, theme.CREAM, pop.x+24, by, shadow=False)
        bar2 = pygame.Rect(pop.x+24, by+24, pop_w-48, 14)
        sound_vol = _slider(screen, f_small, mx, my, clicked, bar2, sound_vol)
        by += 80

        # Bouton Fermer
        btn = pygame.Rect(pop.centerx-70, pop.bottom-52, 140, 36)
        hov = btn.collidepoint(mx, my)
        theme.draw_panel(screen, btn,
                         color=theme.DARK_3 if not hov else (40,30,12),
                         border_color=theme.GOLD if hov else theme.GOLD_DIM,
                         radius=theme.RADIUS_SM, border_w=2)
        theme.render_text(screen, "Fermer", f_label,
                          theme.GOLD_LIGHT if hov else theme.CREAM,
                          btn.centerx, btn.centery - f_label.get_height()//2,
                          center=True, shadow=False)
        if clicked and hov:
            running = False

        # Appliquer volumes
        save["music_volume"] = music_vol
        save["sound_volume"] = sound_vol
        try:
            pygame.mixer.music.set_volume(music_vol)
        except Exception:
            pass

        pygame.display.flip()
        clock.tick(60)

    sd.save(save)


def _slider(screen, f_small, mx, my, clicked, rect, value):
    """Slider horizontal. Retourne la nouvelle valeur."""
    pygame.draw.rect(screen, theme.DARK_3, rect, border_radius=3)
    pygame.draw.rect(screen, theme.GOLD_DIM, rect, 1, border_radius=3)
    fw = int(rect.width * value)
    if fw > 0:
        pygame.draw.rect(screen, theme.GOLD, pygame.Rect(rect.x, rect.y, fw, rect.height), border_radius=3)
    cx = rect.x + fw
    pygame.draw.circle(screen, theme.GOLD_LIGHT, (cx, rect.centery), 9)
    pygame.draw.circle(screen, theme.DARK, (cx, rect.centery), 5)
    pct = f_small.render(f"{int(value*100)}%", True, theme.GOLD_DIM)
    screen.blit(pct, (rect.right + 8, rect.centery - pct.get_height()//2))
    if clicked and rect.inflate(0, 24).collidepoint(mx, my):
        value = max(0.0, min(1.0, (mx - rect.x) / rect.width))
    return value


# ============================================================
# HELPERS VISUELS
# ============================================================
def _get_bg(w, h):
    bg = theme.load_img(theme.IMG_TITLE_BG)
    if bg:
        return pygame.transform.smoothscale(bg, (w, h))
    return None

def _get_blason(h):
    blason = theme.load_img(theme.IMG_BLASON)
    if blason:
        bh    = int(h * 0.09)
        ratio = blason.get_width() / blason.get_height()
        return pygame.transform.smoothscale(blason, (int(bh * ratio), bh))
    return None

def _draw_item_bg(screen, rect):
    """Fond parchemin dégradé derrière l'item actif."""
    surf = pygame.Surface((rect.width + 80, rect.height), pygame.SRCALPHA)
    for i in range(surf.get_width()):
        t = i / max(surf.get_width()-1, 1)
        alpha = int(170 * max(0.0, 1.0 - t * 1.3))
        pygame.draw.line(surf, (60, 35, 8, alpha), (i, 0), (i, surf.get_height()-1))
    screen.blit(surf, (rect.x, rect.y))

def _draw_glow_text(screen, lbl, x, y, tick):
    """Texte doré avec lueur pulsante."""
    glow_a = int(70 + 35 * math.sin(tick * 0.05))
    gs = pygame.Surface((lbl.get_width()+40, lbl.get_height()+10), pygame.SRCALPHA)
    pygame.draw.rect(gs, (200, 100, 10, glow_a), gs.get_rect(), border_radius=4)
    screen.blit(gs, (x-10, y-4))
    # Ombre
    sh = pygame.Surface(lbl.get_size(), pygame.SRCALPHA)
    sh.blit(lbl, (0, 0))
    sh.fill((0, 0, 0, 160), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(sh, (x+2, y+2))
    screen.blit(lbl, (x, y))