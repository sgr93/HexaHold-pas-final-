"""
hud.py
------
Header et barre de navigation communes à tous les écrans in-game.

Usage dans chaque écran :
    import hud
    hud.init()   # une fois après pygame.init()
    action = hud.draw(screen, save, active_tab="quetes",
                      badges={"quetes": 2}, mx=mx, my=my, clicked=clicked)
    content = hud.content_rect(screen)   # zone utilisable entre header et nav
"""

import os
import math
import pygame
import theme

# ============================================================
# ONGLETS
# ============================================================
TABS = [
    {"key": "accueil",    "label": "Accueil"},
    {"key": "histoire",   "label": "Histoire"},
    {"key": "quetes",     "label": "Quêtes"},
    {"key": "equipement", "label": "Équipement"},
    {"key": "gacha",      "label": "Gacha"},
    {"key": "talents",    "label": "Talents"},
    {"key": "parametres", "label": "Paramètres"},
]

_inited  = False
_blason  = None
_icons   = {}   # {key: Surface|None}
_fonts   = {}

# État du popup icône
_icon_picker_open = False
_avatar_rect      = None   # mis à jour à chaque frame


def init():
    """Charge les assets du HUD. À appeler une fois après pygame.init()."""
    global _inited, _blason
    blason_raw = theme.load_img(theme.IMG_BLASON)
    if blason_raw:
        bh = theme.HEADER_H - 16
        ratio = blason_raw.get_width() / blason_raw.get_height()
        _blason = pygame.transform.smoothscale(blason_raw, (int(bh*ratio), bh))
    for tab in TABS:
        _icons[tab["key"]] = theme.load_icon(f"nav_{tab['key']}", 28)
    _inited = True


def _f(key, body=False):
    if (key, body) not in _fonts:
        sizes = {"title": theme.SZ_SECTION, "label": theme.SZ_LABEL,
                 "small": theme.SZ_SMALL,   "tiny":  theme.SZ_TINY}
        _fonts[(key, body)] = theme.font(sizes.get(key, theme.SZ_LABEL), body=body)
    return _fonts[(key, body)]



# ============================================================
# POPUP SÉLECTION D'ICÔNE
# ============================================================

def _scan_available_icons():
    import os as _os
    folder = _os.path.join(_os.path.dirname(__file__), "assets", "sprites")
    if not _os.path.isdir(folder):
        return []
    all_pngs = [f for f in _os.listdir(folder) if f.lower().endswith(".png")]
    icone_pngs = sorted([f for f in all_pngs if f.lower().startswith("icone")])
    return icone_pngs if icone_pngs else sorted(all_pngs)


def draw_overlay(screen: pygame.Surface, save: dict,
                 mx: int = 0, my: int = 0, clicked: bool = False):
    """
    À appeler dans main_ui APRÈS tout le reste, juste avant display.flip().
    Dessine les overlays qui doivent être au-dessus de tout (picker d'icône...).
    """
    global _icon_picker_open
    if _icon_picker_open:
        close = _draw_icon_picker(screen, save, mx, my, clicked)
        if close:
            _icon_picker_open = False


def _draw_icon_picker(screen, save, mx, my, clicked):
    """Popup sélection d'icône — style theme. Retourne True pour fermer."""
    icons = _scan_available_icons()
    if not icons:
        return True

    CELL   = 64
    COLS_P = 5
    PAD    = 14
    TITLE_H = 38
    rows   = (len(icons) + COLS_P - 1) // COLS_P
    pop_w  = COLS_P * (CELL + PAD) + PAD
    pop_h  = TITLE_H + rows * (CELL + PAD) + PAD

    w_scr, _ = screen.get_size()
    pop_x = max(10, min(80, w_scr - pop_w - 10))
    pop_y = theme.HEADER_H + 8
    pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

    # Fond opaque + bordure
    theme.draw_rect_alpha(screen, (*theme.DARK_2, 252), pop_rect)
    pygame.draw.rect(screen, theme.GOLD, pop_rect, 2, border_radius=theme.RADIUS_LG)
    theme.draw_corner_ornaments(screen, pop_rect, size=8)

    f_lbl = _f("label")
    f_ti  = _f("tiny", body=True)

    # Titre
    title = f_lbl.render("Choisir une icône", True, theme.GOLD_LIGHT)
    screen.blit(title, (pop_rect.x + PAD, pop_rect.y + (TITLE_H - title.get_height()) // 2))

    # Ligne dorée
    theme.draw_gold_rule(screen, pop_rect.x + 8, pop_rect.y + TITLE_H, pop_w - 16)

    # Bouton ✕
    close_r  = 11
    close_cx = pop_rect.right - close_r - 8
    close_cy = pop_rect.y + TITLE_H // 2
    close_rect = pygame.Rect(close_cx - close_r, close_cy - close_r, close_r * 2, close_r * 2)
    close_hov  = close_rect.collidepoint(mx, my)
    pygame.draw.circle(screen, theme.RED_BADGE if close_hov else (60, 20, 20), (close_cx, close_cy), close_r)
    pygame.draw.circle(screen, theme.GOLD_DIM, (close_cx, close_cy), close_r, 1)
    x_lbl = f_ti.render("✕", True, theme.CREAM)
    screen.blit(x_lbl, (close_cx - x_lbl.get_width() // 2, close_cy - x_lbl.get_height() // 2))
    if clicked and close_rect.collidepoint(mx, my):
        return True

    # Grille d'icônes
    current_icon = save.get("player_icon", "icone0.png")
    for idx, fname in enumerate(icons):
        col_i = idx % COLS_P
        row_i = idx // COLS_P
        cx = pop_rect.x + PAD + col_i * (CELL + PAD)
        cy = pop_rect.y + TITLE_H + PAD // 2 + row_i * (CELL + PAD)
        cell_rect = pygame.Rect(cx, cy, CELL, CELL)

        is_sel = (fname == current_icon)
        is_hov = cell_rect.collidepoint(mx, my)
        bg_col  = (20, 35, 20) if is_sel else (theme.DARK_3 if is_hov else theme.DARK_2)
        brd_col = theme.GREEN_OK if is_sel else (theme.GOLD_LIGHT if is_hov else theme.GOLD_DIM)
        theme.draw_panel(screen, cell_rect, color=bg_col, border_color=brd_col,
                         radius=theme.RADIUS_MD, border_w=2 if (is_sel or is_hov) else 1)

        icon_name = fname[:-4] if fname.endswith(".png") else fname
        img = theme.load_sprite(icon_name + ".png", (CELL - 8, CELL - 8))
        if img:
            screen.blit(img, (cx + 4, cy + 4))
        else:
            lbl = f_ti.render(icon_name[:7], True, theme.CREAM_DIM)
            screen.blit(lbl, (cx + CELL//2 - lbl.get_width()//2, cy + CELL//2 - lbl.get_height()//2))

        if clicked and cell_rect.collidepoint(mx, my):
            save["player_icon"] = fname
            import save_data as _sd
            _sd.save(save)

    return False


def draw(screen: pygame.Surface, save: dict,
         active_tab: str = "accueil", badges: dict = None,
         mx: int = 0, my: int = 0, clicked: bool = False) -> str | None:
    """
    Dessine header + barre de navigation.
    Retourne la clé de l'onglet cliqué ou None.
    """
    global _icon_picker_open
    if not _inited:
        init()
    badges = badges or {}
    avatar_clicked = _draw_header(screen, save, mx, my, clicked)
    if avatar_clicked:
        _icon_picker_open = not _icon_picker_open
    action = _draw_nav(screen, active_tab, badges, mx, my, clicked)
    return action


def content_rect(screen: pygame.Surface) -> pygame.Rect:
    """Zone disponible entre header et nav bar."""
    w, h = screen.get_size()
    return pygame.Rect(0, theme.HEADER_H, w, h - theme.HEADER_H - theme.BOTTOM_NAV_H)


# ============================================================
# HEADER
# ============================================================
def _draw_header(screen, save, mx, my, clicked):
    w = screen.get_width()
    H = theme.HEADER_H
    rect = pygame.Rect(0, 0, w, H)

    # Fond dégradé
    surf = pygame.Surface((w, H), pygame.SRCALPHA)
    for y in range(H):
        alpha = int(235 * (1 - (y/H)*0.25))
        pygame.draw.line(surf, (*theme.DARK, alpha), (0, y), (w, y))
    screen.blit(surf, (0, 0))
    pygame.draw.line(screen, theme.GOLD_DIM, (0, H-1), (w, H-1), 1)

    pad = 14

    # ── Avatar + infos joueur ────────────────────────────────
    hex_s  = 52
    hex_r  = pygame.Rect(pad, (H-hex_s)//2, hex_s, hex_s)
    _draw_hex_avatar(screen, hex_r, save)
    if hex_r.collidepoint(mx, my):
        pygame.draw.rect(screen, theme.GOLD_LIGHT, hex_r.inflate(4, 4), 1, border_radius=4)

    tx = pad + hex_s + 10
    ty = H//2 - 20

    fn  = _f("label")
    fls = _f("small", body=True)
    fti = _f("tiny",  body=True)

    name = save.get("player_name", "Soldat")
    screen.blit(fn.render(name, True, theme.CREAM), (tx, ty))
    ty += fn.get_height() + 1

    lvl = save.get("level", 1)
    screen.blit(fls.render(f"Niveau {lvl}", True, theme.GOLD), (tx, ty))
    ty += fls.get_height() + 2

    xp, xp_nxt = save.get("xp", 0), max(1, save.get("xp_next", 30))
    xp_bar = pygame.Rect(tx, ty, 120, 7)
    theme.draw_xp_bar(screen, xp_bar, xp, xp_nxt)
    ty += 10
    screen.blit(fls.render(f"{xp}/{xp_nxt} xp", True, theme.GOLD_LIGHT), (tx, ty))

    # ── Titre centré ─────────────────────────────────────────
    ft = _f("title")
    hexa = ft.render("Hexa", True, theme.CREAM)
    hold = ft.render("Hold", True, theme.GOLD_LIGHT)
    tw   = hexa.get_width() + hold.get_width()
    cx   = w // 2
    title_y = (H - hexa.get_height()) // 2

    if _blason:
        bx = cx - _blason.get_width() // 2
        by = title_y - _blason.get_height() - 2
        if by >= 2:
            screen.blit(_blason, (bx, by))

    screen.blit(hexa, (cx - tw//2, title_y))
    screen.blit(hold, (cx - tw//2 + hexa.get_width(), title_y))

    # ── Monnaies droite ──────────────────────────────────────
    coins = save.get("coins", 0)
    gems  = save.get("gems", 0)

    fn_num = pygame.font.SysFont("arial", 22)  # ← 20 → 28

    # Gemmes (tout à droite)
    gt = fn_num.render(str(gems), True, theme.PURPLE_GEM)
    gx2 = w - pad - gt.get_width()
    gy = H//2 - gt.get_height()//2
    screen.blit(gt, (gx2, gy))
    theme.draw_gem_icon(screen, gx2 - 28, gy + 1, 22)  # ← 26→34, 20→28

    # Pièces (à gauche des gemmes)
    ct = fn_num.render(str(coins), True, theme.GOLD_LIGHT)
    cx2 = gx2 - 34 - 24 - ct.get_width()  # ← 26→34, 20→24
    cy = H//2 - ct.get_height()//2
    screen.blit(ct, (cx2, cy))
    theme.draw_coin_icon(screen, cx2 - 28, cy + 1, 22)  # ← 26→34, 20→28

    if clicked and hex_r.collidepoint(mx, my):
        return True
    return None


def _draw_hex_avatar(screen, rect, save):
    """Avatar hexagonal du joueur."""
    import math as _m
    s  = rect.width
    cx, cy = rect.centerx, rect.centery
    r  = s//2 - 1
    pts = [(int(cx + r*_m.cos(_m.radians(60*i-30))),
            int(cy + r*_m.sin(_m.radians(60*i-30)))) for i in range(6)]
    pygame.draw.polygon(screen, theme.DARK_2, pts)

    icon_name = save.get("player_icon", "icone0")
    if icon_name.endswith(".png"):
        icon_name = icon_name[:-4]
    icon = theme.load_sprite(icon_name + ".png", (s-6, s-6))
    if icon:
        screen.blit(icon, (rect.x+3, rect.y+3))

    pygame.draw.polygon(screen, theme.GOLD, pts, 2)


# ============================================================
# BARRE DE NAVIGATION BAS
# ============================================================
def _draw_nav(screen, active_tab, badges, mx, my, clicked):
    w, h  = screen.get_size()
    NAV_H = theme.BOTTOM_NAV_H
    ny    = h - NAV_H

    # Fond
    surf = pygame.Surface((w, NAV_H), pygame.SRCALPHA)
    for y in range(NAV_H):
        alpha = int(245 * (0.85 + 0.15*(1-y/NAV_H)))
        pygame.draw.line(surf, (*theme.DARK, alpha), (0, y), (w, y))
    screen.blit(surf, (0, ny))
    pygame.draw.line(screen, theme.GOLD_DIM, (0, ny), (w, ny), 1)

    fti   = _f("tiny", body=True)
    tab_w = w // len(TABS)
    action = None

    for i, tab in enumerate(TABS):
        tx     = i * tab_w
        trect  = pygame.Rect(tx, ny, tab_w, NAV_H)
        is_act = tab["key"] == active_tab
        is_hov = trect.collidepoint(mx, my)

        if is_act:
            theme.draw_rect_alpha(screen, (*theme.GOLD, 18), trect)
            pygame.draw.line(screen, theme.GOLD_LIGHT, (tx, ny), (tx+tab_w, ny), 2)
        elif is_hov:
            theme.draw_rect_alpha(screen, (*theme.GOLD, 8), trect)

        # Icône ou placeholder
        icon   = _icons.get(tab["key"])
        icon_cx = tx + tab_w // 2
        icon_y  = ny + 8

        if icon:
            screen.blit(icon, (icon_cx - icon.get_width()//2, icon_y))
        else:
            ph = pygame.Rect(icon_cx - 14, icon_y, 28, 28)
            theme.draw_panel(screen, ph, color=theme.DARK_3,
                             border_color=theme.GOLD_DIM, radius=4)

        # Label
        lbl_col = theme.GOLD_LIGHT if is_act else theme.GOLD_DIM
        lbl = fti.render(tab["label"], True, lbl_col)
        screen.blit(lbl, (icon_cx - lbl.get_width()//2, ny + NAV_H - 18))

        # Badge
        bv = badges.get(tab["key"], 0)
        if bv:
            bx = icon_cx + 10
            by = icon_y - 2
            pygame.draw.circle(screen, theme.RED_BADGE, (bx, by), 8)
            bl = fti.render(str(bv), True, (240, 200, 200))
            screen.blit(bl, (bx - bl.get_width()//2, by - bl.get_height()//2))

        # Séparateur
        if i > 0:
            sep_surf = pygame.Surface((1, NAV_H-16), pygame.SRCALPHA)
            sep_surf.fill((*theme.GOLD_DIM, 60))
            screen.blit(sep_surf, (tx, ny+8))

        if clicked and is_hov and not is_act:
            action = tab["key"]

    return action