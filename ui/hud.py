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
    folder = _os.path.join(_os.path.dirname(__file__), "..", "assets", "sprites")
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

    # Tooltip talent verrouillé — toujours au-dessus de tout
    if _talent_tab_rect_global is not None:
        _draw_talent_locked_tooltip(screen, _talent_tab_rect_global, mx, my)


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

    # Bouton ✕ — rond rouge en haut à droite, légèrement en dehors du popup
    close_r  = 13
    close_cx = pop_rect.right - close_r + 4
    close_cy = pop_rect.top   - close_r + 4
    close_rect = pygame.Rect(close_cx - close_r, close_cy - close_r, close_r * 2, close_r * 2)
    close_hov  = close_rect.collidepoint(mx, my)
    pygame.draw.circle(screen, (200, 30, 30) if close_hov else (160, 20, 20), (close_cx, close_cy), close_r)
    pygame.draw.circle(screen, (255, 80, 80) if close_hov else (220, 60, 60), (close_cx, close_cy), close_r, 2)
    f_x = pygame.font.SysFont("arial", 15, bold=True)
    x_lbl = f_x.render("X", True, (255, 220, 220))
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
            import core.save_data as _sd
            _sd.save(save)
            return True  # fermer le picker après sélection

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
    _draw_header(screen, save, mx, my, clicked)
    action = _draw_nav(screen, active_tab, badges, mx, my, clicked, save)
    return action


def content_rect(screen: pygame.Surface) -> pygame.Rect:
    """Zone disponible entre header et nav bar."""
    w, h = screen.get_size()
    return pygame.Rect(0, theme.HEADER_H, w, h - theme.HEADER_H - theme.BOTTOM_NAV_H)


# ============================================================
# HEADER
# ============================================================
def _draw_header(screen, save, mx, my, clicked):
    global _icon_picker_open, _avatar_rect

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

    # ── Avatar hexagonal cliquable ───────────────────────────
    avatar_size = H - 10
    hex_r = pygame.Rect(pad, (H - avatar_size) // 2, avatar_size, avatar_size)
    _avatar_rect = hex_r
    _draw_hex_avatar(screen, hex_r, save)

    # Survol : contour doré plus vif pour signaler que c'est cliquable
    if hex_r.collidepoint(mx, my):
        import math as _m
        cx_h, cy_h = hex_r.centerx, hex_r.centery
        r_h = avatar_size // 2 - 1
        pts = [(int(cx_h + r_h * _m.cos(_m.radians(60*i-30))),
                int(cy_h + r_h * _m.sin(_m.radians(60*i-30)))) for i in range(6)]
        pygame.draw.polygon(screen, theme.GOLD_LIGHT, pts, 2)

    # Clic sur l'avatar = ouvrir/fermer le picker
    if clicked and hex_r.collidepoint(mx, my):
        _icon_picker_open = not _icon_picker_open

    tx = hex_r.right + 8
    ty = H//2 - 20

    fn  = _f("label")
    fls = _f("small", body=True)
    fti = _f("tiny",  body=True)

    name = save.get("player_name", "Soldat")
    screen.blit(fn.render(name, True, theme.CREAM), (tx, ty))
    ty += fn.get_height() + 1

    lvl = save.get("level", 1)
    xp, xp_nxt = save.get("xp", 0), max(1, save.get("xp_next", 30))
    pct_remaining = max(0, min(100, int(round((1 - xp / xp_nxt) * 100))))

    lvl_surf = fls.render(f"Niveau {lvl}", True, theme.GOLD)
    pct_surf = fls.render(f"{pct_remaining}% restants", True, theme.GOLD_LIGHT)
    screen.blit(lvl_surf, (tx, ty))
    screen.blit(pct_surf, (tx + lvl_surf.get_width() + 8, ty))
    ty += fls.get_height() + 2

    xp_bar = pygame.Rect(tx, ty, 120, 7)
    theme.draw_xp_bar(screen, xp_bar, xp, xp_nxt)

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

    fn_num = pygame.font.SysFont("arial", 22)

    # Gemmes (tout à droite)
    gt = fn_num.render(str(gems), True, theme.PURPLE_GEM)
    gx2 = w - pad - gt.get_width()
    gy = H//2 - gt.get_height()//2
    screen.blit(gt, (gx2, gy))
    theme.draw_gem_icon(screen, gx2 - 28, gy + 1, 22)

    # Pièces (à gauche des gemmes)
    ct = fn_num.render(str(coins), True, theme.GOLD_LIGHT)
    cx2 = gx2 - 34 - 24 - ct.get_width()
    cy = H//2 - ct.get_height()//2
    screen.blit(ct, (cx2, cy))
    theme.draw_coin_icon(screen, cx2 - 28, cy + 1, 22)

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
# HELPERS TALENT LOCKED
# ============================================================

_talent_popup_timer = 0   # frames restantes d'affichage du popup
_talent_tab_rect_global = None  # rect de l'onglet talent, mis à jour chaque frame

def _show_talent_locked_popup(screen, tab_rect):
    global _talent_popup_timer
    _talent_popup_timer = 180  # 3 secondes à 60fps


def _draw_talent_locked_tooltip(screen, tab_rect, mx, my):
    """Affiche un petit popup au-dessus de l'onglet Talents verrouillé."""
    global _talent_popup_timer

    # Décrémentation du timer (appelé chaque frame si onglet locked)
    if _talent_popup_timer > 0:
        _talent_popup_timer -= 1

    # On affiche si hover OU si timer actif
    show = tab_rect.collidepoint(mx, my) or _talent_popup_timer > 0
    if not show:
        return

    f_sm = _f("small", body=True)
    f_ti = _f("tiny",  body=True)

    W, H = 260, 58
    cx   = tab_rect.centerx
    bx   = max(4, min(cx - W // 2, screen.get_width() - W - 4))
    by   = tab_rect.top - H - 8

    pop = pygame.Rect(bx, by, W, H)

    import theme as _theme
    _theme.draw_rect_alpha(screen, (*_theme.DARK_2, 240), pop, radius=_theme.RADIUS_MD)
    pygame.draw.rect(screen, _theme.GOLD_DIM, pop, 1, border_radius=_theme.RADIUS_MD)

    # Petite flèche vers le bas
    arrow_x = cx
    arrow_y = pop.bottom
    pygame.draw.polygon(screen, _theme.GOLD_DIM, [
        (arrow_x - 6, arrow_y), (arrow_x + 6, arrow_y), (arrow_x, arrow_y + 6)
    ])

    title = f_sm.render("Deblocable au niveau 2", True, _theme.GOLD_LIGHT)
    screen.blit(title, (pop.centerx - title.get_width() // 2, pop.y + 8))

    sub = f_ti.render("Gagnez de l'XP en completant des parties.", True, _theme.CREAM_DIM)
    screen.blit(sub, (pop.centerx - sub.get_width() // 2, pop.y + 28))

    sub2 = f_ti.render("Chaque victoire rapporte de l'XP de compte.", True, _theme.CREAM_DIM)
    screen.blit(sub2, (pop.centerx - sub2.get_width() // 2, pop.y + 42))


# ============================================================
# BARRE DE NAVIGATION BAS
# ============================================================
def _draw_nav(screen, active_tab, badges, mx, my, clicked, save=None):
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
    if save is None:
        save = {}

    for i, tab in enumerate(TABS):
        tx     = i * tab_w
        trect  = pygame.Rect(tx, ny, tab_w, NAV_H)
        is_act = tab["key"] == active_tab
        is_hov = trect.collidepoint(mx, my)

        # Onglet Talents verrouillé si aucun skill point et aucun nœud acheté
        is_talent_locked = (
            tab["key"] == "talents"
            and save.get("skill_points", 0) == 0
            and not save.get("skill_tree_nodes")
        )

        if is_act:
            theme.draw_rect_alpha(screen, (*theme.GOLD, 18), trect)
            pygame.draw.line(screen, theme.GOLD_LIGHT, (tx, ny), (tx+tab_w, ny), 2)
        elif is_hov and not is_talent_locked:
            theme.draw_rect_alpha(screen, (*theme.GOLD, 8), trect)
        elif is_talent_locked:
            # Overlay grisé pour l'onglet verrouillé
            theme.draw_rect_alpha(screen, (0, 0, 0, 80), trect)

        # Icône ou placeholder
        icon   = _icons.get(tab["key"])
        icon_cx = tx + tab_w // 2
        icon_y  = ny + 8

        if icon:
            icon_draw = icon.copy() if is_talent_locked else icon
            if is_talent_locked:
                icon_draw.set_alpha(60)
            screen.blit(icon_draw, (icon_cx - icon_draw.get_width()//2, icon_y))
        else:
            ph = pygame.Rect(icon_cx - 14, icon_y, 28, 28)
            theme.draw_panel(screen, ph, color=theme.DARK_3,
                             border_color=theme.GOLD_DIM, radius=4)

        # Label
        if is_talent_locked:
            lbl_col = (60, 55, 45)
            lbl = fti.render("[ ] " + tab["label"], True, lbl_col)
        else:
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

        if clicked and is_hov and not is_act and not is_talent_locked:
            action = tab["key"]

        # Popup "débloquable niveau 2" si on clique sur l'onglet verrouillé
        if clicked and is_hov and is_talent_locked:
            _show_talent_locked_popup(screen, trect)
        if is_talent_locked:
            _talent_tab_rect = trect  # mémorisé pour dessin après la boucle
            global _talent_tab_rect_global
            _talent_tab_rect_global = trect

    return action