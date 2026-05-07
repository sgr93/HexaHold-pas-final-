"""
ui/hud.py

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
import ui.theme as theme
import core.save_data as sd


# ONGLETS — dans l'ordre d'affichage dans la nav bar
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
_icons   = {}  # {key: Surface|None} — chargé une fois dans init()
_fonts   = {}

# État global du picker d'icône — partagé entre draw() et draw_overlay()
_icon_picker_open       = False
_avatar_rect            = None  # mis à jour à chaque frame dans _draw_header
_talent_popup_timer     = 0     # frames restantes avant de masquer le tooltip talent
_talent_tab_rect_global = None  # rect de l'onglet talent, mémorisé pour draw_overlay


def init():
    """Charge les assets du HUD. À appeler une fois après pygame.init()."""
    global _inited, _blason
    blason_raw = theme.load_img(theme.IMG_BLASON)
    if blason_raw:
        bh    = theme.HEADER_H - 16
        ratio = blason_raw.get_width() / blason_raw.get_height()
        _blason = pygame.transform.smoothscale(blason_raw, (int(bh * ratio), bh))
    for tab in TABS:
        _icons[tab["key"]] = theme.load_icon(f"nav_{tab['key']}", 28)
    _inited = True


def _f(key, body=False):
    """Cache de polices — évite de recréer les objets font à chaque frame."""
    if (key, body) not in _fonts:
        sizes = {
            "title": theme.SZ_SECTION,
            "label": theme.SZ_LABEL,
            "small": theme.SZ_SMALL,
            "tiny":  theme.SZ_TINY,
        }
        _fonts[(key, body)] = theme.font(sizes.get(key, theme.SZ_LABEL), body=body)
    return _fonts[(key, body)]


# POPUP SÉLECTION D'ICÔNE

def _scan_available_icons():
    """
    Scanne le dossier sprites pour trouver les icônes disponibles.
    Priorité aux fichiers "icone*.png", fallback sur tous les PNG si aucun trouvé.
    """
    folder = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")
    if not os.path.isdir(folder):
        return []
    all_pngs    = [f for f in os.listdir(folder) if f.lower().endswith(".png")]
    icone_pngs  = sorted([f for f in all_pngs if f.lower().startswith("icone")])
    return icone_pngs if icone_pngs else sorted(all_pngs)


def draw_overlay(screen: pygame.Surface, save: dict,
                 mx: int = 0, my: int = 0, clicked: bool = False):
    """
    Dessine les overlays au-dessus de tout — à appeler en dernier dans la boucle,
    juste avant display.flip(). Gère le picker d'icône et le tooltip talent.
    """
    global _icon_picker_open
    if _icon_picker_open:
        if _draw_icon_picker(screen, save, mx, my, clicked):
            _icon_picker_open = False
    if _talent_tab_rect_global is not None:
        _draw_talent_locked_tooltip(screen, _talent_tab_rect_global, mx, my)


def _draw_icon_picker(screen, save, mx, my, clicked):
    """
    Popup de sélection d'icône. Retourne True pour se fermer.
    La fermeture se fait soit par le bouton ✕, soit en cliquant une icône.
    """
    icons = _scan_available_icons()
    if not icons:
        return True

    CELL    = 64
    COLS_P  = 5
    PAD     = 14
    TITLE_H = 38
    rows    = (len(icons) + COLS_P - 1) // COLS_P
    pop_w   = COLS_P * (CELL + PAD) + PAD
    pop_h   = TITLE_H + rows * (CELL + PAD) + PAD

    w_scr, _ = screen.get_size()
    pop_x    = max(10, min(80, w_scr - pop_w - 10))
    pop_y    = theme.HEADER_H + 8
    pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

    theme.draw_rect_alpha(screen, (*theme.DARK_2, 252), pop_rect)
    pygame.draw.rect(screen, theme.GOLD, pop_rect, 2, border_radius=theme.RADIUS_LG)
    theme.draw_corner_ornaments(screen, pop_rect, size=8)

    f_lbl = _f("label")
    f_ti  = _f("tiny", body=True)

    title = f_lbl.render("Choisir une icône", True, theme.GOLD_LIGHT)
    screen.blit(title, (pop_rect.x + PAD, pop_rect.y + (TITLE_H - title.get_height()) // 2))
    theme.draw_gold_rule(screen, pop_rect.x + 8, pop_rect.y + TITLE_H, pop_w - 16)

    # Bouton ✕ rouge, légèrement en dehors du popup pour ne pas masquer les icônes
    close_r   = 13
    close_cx  = pop_rect.right - close_r + 4
    close_cy  = pop_rect.top   - close_r + 4
    close_rect = pygame.Rect(close_cx - close_r, close_cy - close_r, close_r * 2, close_r * 2)
    close_hov  = close_rect.collidepoint(mx, my)
    pygame.draw.circle(screen, (200, 30, 30) if close_hov else (160, 20, 20), (close_cx, close_cy), close_r)
    pygame.draw.circle(screen, (255, 80, 80) if close_hov else (220, 60, 60), (close_cx, close_cy), close_r, 2)
    x_lbl = pygame.font.SysFont("arial", 15, bold=True).render("X", True, (255, 220, 220))
    screen.blit(x_lbl, (close_cx - x_lbl.get_width() // 2, close_cy - x_lbl.get_height() // 2))
    if clicked and close_rect.collidepoint(mx, my):
        return True

    # Grille d'icônes avec highlight sur la sélection actuelle
    current_icon = save.get("player_icon", "icone0.png")
    for idx, fname in enumerate(icons):
        col_i     = idx % COLS_P
        row_i     = idx // COLS_P
        cx        = pop_rect.x + PAD + col_i * (CELL + PAD)
        cy        = pop_rect.y + TITLE_H + PAD // 2 + row_i * (CELL + PAD)
        cell_rect = pygame.Rect(cx, cy, CELL, CELL)
        is_sel    = fname == current_icon
        is_hov    = cell_rect.collidepoint(mx, my)
        bg_col    = (20, 35, 20) if is_sel else (theme.DARK_3 if is_hov else theme.DARK_2)
        brd_col   = theme.GREEN_OK if is_sel else (theme.GOLD_LIGHT if is_hov else theme.GOLD_DIM)
        theme.draw_panel(screen, cell_rect, color=bg_col, border_color=brd_col,
                         radius=theme.RADIUS_MD, border_w=2 if (is_sel or is_hov) else 1)
        icon_name = fname[:-4] if fname.endswith(".png") else fname
        img = theme.load_sprite(icon_name + ".png", (CELL - 8, CELL - 8))
        if img:
            screen.blit(img, (cx + 4, cy + 4))
        else:
            lbl = f_ti.render(icon_name[:7], True, theme.CREAM_DIM)
            screen.blit(lbl, (cx + CELL // 2 - lbl.get_width() // 2,
                               cy + CELL // 2 - lbl.get_height() // 2))
        if clicked and cell_rect.collidepoint(mx, my):
            save["player_icon"] = fname
            sd.save(save)
            return True  # on ferme directement après la sélection

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
    return _draw_nav(screen, active_tab, badges, mx, my, clicked, save)


def content_rect(screen: pygame.Surface) -> pygame.Rect:
    """Zone disponible entre header et nav bar — c'est là que les écrans dessinent."""
    w, h = screen.get_size()
    return pygame.Rect(0, theme.HEADER_H, w, h - theme.HEADER_H - theme.BOTTOM_NAV_H)


# HEADER

def _draw_header(screen, save, mx, my, clicked):
    global _icon_picker_open, _avatar_rect

    w = screen.get_width()
    H = theme.HEADER_H

    # Fond dégradé léger — plus opaque en haut, légèrement transparent en bas
    surf = pygame.Surface((w, H), pygame.SRCALPHA)
    for y in range(H):
        alpha = int(235 * (1 - (y / H) * 0.25))
        pygame.draw.line(surf, (*theme.DARK, alpha), (0, y), (w, y))
    screen.blit(surf, (0, 0))
    pygame.draw.line(screen, theme.GOLD_DIM, (0, H - 1), (w, H - 1), 1)

    pad = 14

    # Avatar hexagonal — cliquable pour ouvrir le picker d'icône
    avatar_size = H - 10
    hex_r = pygame.Rect(pad, (H - avatar_size) // 2, avatar_size, avatar_size)
    _avatar_rect = hex_r
    _draw_hex_avatar(screen, hex_r, save)

    # Contour doré plus vif au survol pour signaler que c'est interactif
    if hex_r.collidepoint(mx, my):
        cx_h, cy_h = hex_r.centerx, hex_r.centery
        r_h  = avatar_size // 2 - 1
        pts  = [(int(cx_h + r_h * math.cos(math.radians(60 * i - 30))),
                 int(cy_h + r_h * math.sin(math.radians(60 * i - 30)))) for i in range(6)]
        pygame.draw.polygon(screen, theme.GOLD_LIGHT, pts, 2)

    if clicked and hex_r.collidepoint(mx, my):
        _icon_picker_open = not _icon_picker_open

    tx = hex_r.right + 8
    ty = H // 2 - 20

    fn  = _f("label")
    fls = _f("small", body=True)

    screen.blit(fn.render(save.get("player_name", "Soldat"), True, theme.CREAM), (tx, ty))
    ty += fn.get_height() + 1

    lvl     = save.get("level", 1)
    xp      = save.get("xp", 0)
    xp_nxt  = max(1, save.get("xp_next", 30))
    # % restant plutôt que % accompli — plus motivant de voir "10% restants" que "90%"
    pct_remaining = max(0, min(100, int(round((1 - xp / xp_nxt) * 100))))

    lvl_surf = fls.render(f"Niveau {lvl}", True, theme.GOLD)
    pct_surf = fls.render(f"{pct_remaining}% restants", True, theme.GOLD_LIGHT)
    screen.blit(lvl_surf, (tx, ty))
    screen.blit(pct_surf, (tx + lvl_surf.get_width() + 8, ty))
    ty += fls.get_height() + 2

    theme.draw_xp_bar(screen, pygame.Rect(tx, ty, 120, 7), xp, xp_nxt)

    # Titre centré — bicolore comme sur l'écran titre
    ft   = _f("title")
    hexa = ft.render("Hexa", True, theme.CREAM)
    hold = ft.render("Hold", True, theme.GOLD_LIGHT)
    tw   = hexa.get_width() + hold.get_width()
    cx   = w // 2

    if _blason:
        bx = cx - _blason.get_width() // 2
        by = (H - hexa.get_height()) // 2 - _blason.get_height() - 2
        if by >= 2:
            screen.blit(_blason, (bx, by))

    title_y = (H - hexa.get_height()) // 2
    screen.blit(hexa, (cx - tw // 2, title_y))
    screen.blit(hold, (cx - tw // 2 + hexa.get_width(), title_y))

    # Monnaies à droite — gemmes tout à droite, pièces juste avant
    coins  = save.get("coins", 0)
    gems   = save.get("gems", 0)
    fn_num = pygame.font.SysFont("arial", 22)

    gt  = fn_num.render(str(gems), True, theme.PURPLE_GEM)
    gx2 = w - pad - gt.get_width()
    gy  = H // 2 - gt.get_height() // 2
    screen.blit(gt, (gx2, gy))
    theme.draw_gem_icon(screen, gx2 - 28, gy + 1, 22)

    ct  = fn_num.render(str(coins), True, theme.GOLD_LIGHT)
    cx2 = gx2 - 34 - 24 - ct.get_width()
    cy  = H // 2 - ct.get_height() // 2
    screen.blit(ct, (cx2, cy))
    theme.draw_coin_icon(screen, cx2 - 28, cy + 1, 22)


def _draw_hex_avatar(screen, rect, save):
    """Avatar hexagonal — forme géométrique + icône du joueur par-dessus."""
    s       = rect.width
    cx, cy  = rect.centerx, rect.centery
    r       = s // 2 - 1
    pts     = [(int(cx + r * math.cos(math.radians(60 * i - 30))),
                int(cy + r * math.sin(math.radians(60 * i - 30)))) for i in range(6)]
    pygame.draw.polygon(screen, theme.DARK_2, pts)

    icon_name = save.get("player_icon", "icone0")
    if icon_name.endswith(".png"):
        icon_name = icon_name[:-4]
    icon = theme.load_sprite(icon_name + ".png", (s - 6, s - 6))
    if icon:
        screen.blit(icon, (rect.x + 3, rect.y + 3))

    pygame.draw.polygon(screen, theme.GOLD, pts, 2)


# TOOLTIP TALENT VERROUILLÉ

def _show_talent_locked_popup(screen, tab_rect):
    """Déclenche l'affichage du tooltip pendant 3 secondes (180 frames)."""
    global _talent_popup_timer
    _talent_popup_timer = 180


def _draw_talent_locked_tooltip(screen, tab_rect, mx, my):
    """
    Tooltip affiché au hover ou pendant _talent_popup_timer frames après un clic.
    Explique pourquoi l'onglet est verrouillé et comment le débloquer.
    """
    global _talent_popup_timer
    if _talent_popup_timer > 0:
        _talent_popup_timer -= 1
    if not (tab_rect.collidepoint(mx, my) or _talent_popup_timer > 0):
        return

    f_sm = _f("small", body=True)
    f_ti = _f("tiny",  body=True)

    W, H = 260, 58
    cx   = tab_rect.centerx
    bx   = max(4, min(cx - W // 2, screen.get_width() - W - 4))
    by   = tab_rect.top - H - 8
    pop  = pygame.Rect(bx, by, W, H)

    theme.draw_rect_alpha(screen, (*theme.DARK_2, 240), pop, radius=theme.RADIUS_MD)
    pygame.draw.rect(screen, theme.GOLD_DIM, pop, 1, border_radius=theme.RADIUS_MD)

    # Petite flèche pointant vers l'onglet en dessous
    arrow_x = cx
    arrow_y = pop.bottom
    pygame.draw.polygon(screen, theme.GOLD_DIM, [
        (arrow_x - 6, arrow_y), (arrow_x + 6, arrow_y), (arrow_x, arrow_y + 6)
    ])

    title = f_sm.render("Deblocable au niveau 2", True, theme.GOLD_LIGHT)
    screen.blit(title, (pop.centerx - title.get_width() // 2, pop.y + 8))
    sub = f_ti.render("Gagnez de l'XP en completant des parties.", True, theme.CREAM_DIM)
    screen.blit(sub, (pop.centerx - sub.get_width() // 2, pop.y + 28))
    sub2 = f_ti.render("Chaque victoire rapporte de l'XP de compte.", True, theme.CREAM_DIM)
    screen.blit(sub2, (pop.centerx - sub2.get_width() // 2, pop.y + 42))


# BARRE DE NAVIGATION BAS

def _draw_nav(screen, active_tab, badges, mx, my, clicked, save=None):
    """
    Dessine la nav bar en bas et retourne la clé de l'onglet cliqué.
    L'onglet Talents est verrouillé si le joueur n'a pas encore de skill points.
    """
    global _talent_tab_rect_global

    w, h  = screen.get_size()
    NAV_H = theme.BOTTOM_NAV_H
    ny    = h - NAV_H
    save  = save or {}

    # Fond dégradé inverse du header — plus opaque en bas
    surf = pygame.Surface((w, NAV_H), pygame.SRCALPHA)
    for y in range(NAV_H):
        alpha = int(245 * (0.85 + 0.15 * (1 - y / NAV_H)))
        pygame.draw.line(surf, (*theme.DARK, alpha), (0, y), (w, y))
    screen.blit(surf, (0, ny))
    pygame.draw.line(screen, theme.GOLD_DIM, (0, ny), (w, ny), 1)

    fti    = _f("tiny", body=True)
    tab_w  = w // len(TABS)
    action = None

    for i, tab in enumerate(TABS):
        tx    = i * tab_w
        trect = pygame.Rect(tx, ny, tab_w, NAV_H)
        is_act = tab["key"] == active_tab
        is_hov = trect.collidepoint(mx, my)

        # Talents verrouillé tant que le joueur n'a pas de skill points ni de nœuds achetés
        is_talent_locked = (
            tab["key"] == "talents"
            and save.get("skill_points", 0) == 0
            and not save.get("skill_tree_nodes")
        )

        if is_act:
            theme.draw_rect_alpha(screen, (*theme.GOLD, 18), trect)
            pygame.draw.line(screen, theme.GOLD_LIGHT, (tx, ny), (tx + tab_w, ny), 2)
        elif is_hov and not is_talent_locked:
            theme.draw_rect_alpha(screen, (*theme.GOLD, 8), trect)
        elif is_talent_locked:
            # Overlay sombre pour bien signaler que c'est verrouillé
            theme.draw_rect_alpha(screen, (0, 0, 0, 80), trect)

        icon    = _icons.get(tab["key"])
        icon_cx = tx + tab_w // 2
        icon_y  = ny + 8

        if icon:
            icon_draw = icon.copy() if is_talent_locked else icon
            if is_talent_locked:
                icon_draw.set_alpha(60)  # grisé pour renforcer l'impression de verrouillage
            screen.blit(icon_draw, (icon_cx - icon_draw.get_width() // 2, icon_y))
        else:
            ph = pygame.Rect(icon_cx - 14, icon_y, 28, 28)
            theme.draw_panel(screen, ph, color=theme.DARK_3,
                             border_color=theme.GOLD_DIM, radius=4)

        lbl_col = (60, 55, 45) if is_talent_locked else (theme.GOLD_LIGHT if is_act else theme.GOLD_DIM)
        label   = f"[ ] {tab['label']}" if is_talent_locked else tab["label"]
        lbl     = fti.render(label, True, lbl_col)
        screen.blit(lbl, (icon_cx - lbl.get_width() // 2, ny + NAV_H - 18))

        # Badge de notification — petit cercle rouge avec le nombre
        bv = badges.get(tab["key"], 0)
        if bv:
            bx = icon_cx + 10
            by = icon_y - 2
            pygame.draw.circle(screen, theme.RED_BADGE, (bx, by), 8)
            bl = fti.render(str(bv), True, (240, 200, 200))
            screen.blit(bl, (bx - bl.get_width() // 2, by - bl.get_height() // 2))

        # Séparateur vertical entre les onglets
        if i > 0:
            sep = pygame.Surface((1, NAV_H - 16), pygame.SRCALPHA)
            sep.fill((*theme.GOLD_DIM, 60))
            screen.blit(sep, (tx, ny + 8))

        if clicked and is_hov and not is_act and not is_talent_locked:
            action = tab["key"]

        if clicked and is_hov and is_talent_locked:
            _show_talent_locked_popup(screen, trect)

        if is_talent_locked:
            _talent_tab_rect_global = trect

    return action