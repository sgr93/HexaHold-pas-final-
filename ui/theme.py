"""
theme.py
--------
Thème visuel global de HexaHold — DA SNK médiévale.
TOUT passe par ici : couleurs, polices, images, helpers de dessin.
Changez une variable ici et tout le jeu suit.
"""

import os
import math
import pygame

# ============================================================
# CHEMINS ASSETS  (relatifs au dossier du jeu)
# ============================================================
_BASE       = os.path.join(os.path.dirname(__file__), "..")
_FONTS_DIR  = os.path.join(_BASE, "assets", "fonts")
_IMG_DIR    = os.path.join(_BASE, "assets", "images")
_SPR_DIR    = os.path.join(_BASE, "assets", "sprites")
_ICON_DIR   = os.path.join(_BASE, "assets", "icons")

# ── Polices ──────────────────────────────────────────────────
FONT_TITLE = os.path.join(_FONTS_DIR, "PixelCrash.otf")   # titres & menus
FONT_BODY  = os.path.join(_FONTS_DIR, "Georgia.ttf")      # corps de texte
# Fallback automatique sur SysFont si fichier absent

# ── Images principales ───────────────────────────────────────
IMG_TITLE_BG = os.path.join(_IMG_DIR, "best_snk.png")
IMG_BLASON   = os.path.join(_IMG_DIR, "ailes.png")

# ── Icônes navigation (placeholders tant que tu ne les envoies pas) ──
ICON_NAV = {k: os.path.join(_ICON_DIR, f"nav_{k}.png") for k in
            ("accueil","histoire","quetes","equipement","gacha","talents","parametres")}

# ── Icônes monnaie ───────────────────────────────────────────
ICON_COINS = os.path.join(_SPR_DIR, "pieces.png")
ICON_GEMS  = os.path.join(_SPR_DIR, "gemmes.png")

# ============================================================
# PALETTE
# ============================================================
GOLD         = (200, 146,  10)
GOLD_LIGHT   = (232, 168,  32)
GOLD_DIM     = (107,  93,  63)
CREAM        = (237, 224, 190)
CREAM_DIM    = (180, 165, 130)
DARK         = ( 13,  11,   9)
DARK_2       = ( 20,  16,  10)
DARK_3       = ( 28,  22,  14)
RED_BADGE    = (122,  21,  21)
GREEN_OK     = ( 74, 154,  74)
BLUE_XP      = (100, 180, 255)
PURPLE_GEM   = (170, 136, 255)

# Alias sémantiques utilisés dans les écrans
C_BG        = DARK
C_PANEL     = DARK_2
C_PANEL_ALT = DARK_3
C_BORDER    = GOLD_DIM
C_BORDER_H  = GOLD
C_TEXT      = CREAM
C_TEXT_DIM  = CREAM_DIM
C_ACCENT    = GOLD_LIGHT
C_SUCCESS   = GREEN_OK
C_DANGER    = RED_BADGE

# ============================================================
# TAILLES DE POLICES
# ============================================================
SZ_TITLE   = 48
SZ_MENU    = 28
SZ_MENU_A  = 40   # item actif écran titre
SZ_SECTION = 20
SZ_LABEL   = 16
SZ_SMALL   = 13
SZ_TINY    = 11

# ============================================================
# DIMENSIONS UI
# ============================================================
HEADER_H     = 74
BOTTOM_NAV_H = 68
RADIUS_SM    = 4
RADIUS_MD    = 8
RADIUS_LG    = 12
BORDER_W     = 1
BORDER_ACC   = 2
RULE_W       = 200   # largeur ligne dorée sous le titre

# ============================================================
# CACHES INTERNES
# ============================================================
_font_cache: dict = {}
_img_cache:  dict = {}

# ============================================================
# POLICES
# ============================================================
def font(size: int, bold: bool = False, body: bool = False) -> pygame.font.Font:
    """
    Retourne une police mise en cache.
    body=True  → Georgia (corps de texte)
    body=False → PixelCrash (titres/menus)
    Fallback sur SysFont si le fichier est absent.
    """
    path = FONT_BODY if body else FONT_TITLE
    key  = (path, size, bold)
    if key not in _font_cache:
        if os.path.isfile(path):
            try:
                _font_cache[key] = pygame.font.Font(path, size)
            except Exception as e:
                print(f"[theme] Police inaccessible {path}: {e}")
                _font_cache[key] = pygame.font.SysFont("georgia", size, bold=bold)
        else:
            _font_cache[key] = pygame.font.SysFont("georgia", size, bold=bold)
    return _font_cache[key]

# ============================================================
# IMAGES
# ============================================================
def load_img(path: str, size: tuple = None) -> pygame.Surface | None:
    """Charge et met en cache une image. size=(w,h) pour redimensionner."""
    key = (path, size)
    if key in _img_cache:
        return _img_cache[key]
    if path is None or not os.path.isfile(path):
        _img_cache[key] = None
        return None
    try:
        surf = pygame.image.load(path).convert_alpha()
        if size:
            surf = pygame.transform.smoothscale(surf, size)
        _img_cache[key] = surf
    except Exception as e:
        print(f"[theme] Image inaccessible {path}: {e}")
        _img_cache[key] = None
    return _img_cache[key]

def load_icon(name: str, size: int) -> pygame.Surface | None:
    """Charge assets/icons/<name>.png redimensionnée à size×size."""
    path = os.path.join(_ICON_DIR, f"{name}.png")
    return load_img(path, (size, size))

def load_sprite(name: str, size: tuple = None) -> pygame.Surface | None:
    """Charge assets/sprites/<name>.png"""
    path = os.path.join(_SPR_DIR, name if name.endswith(".png") else f"{name}.png")
    return load_img(path, size)

# ============================================================
# HELPERS DE DESSIN
# ============================================================
def draw_panel(screen: pygame.Surface, rect: pygame.Rect,
               color: tuple = None, border_color: tuple = None,
               radius: int = RADIUS_MD, border_w: int = BORDER_W):
    """Panneau sombre avec bordure."""
    pygame.draw.rect(screen, color or C_PANEL, rect, border_radius=radius)
    if border_w:
        pygame.draw.rect(screen, border_color or C_BORDER, rect, border_w, border_radius=radius)

def draw_rect_alpha(screen: pygame.Surface, color_rgba: tuple, rect: pygame.Rect, radius: int = 0):
    """Rectangle avec transparence."""
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surf, color_rgba, surf.get_rect(), border_radius=radius)
    screen.blit(surf, rect.topleft)

def draw_gold_rule(screen: pygame.Surface, x: int, y: int, width: int = RULE_W):
    """Ligne dorée dégradée (ornement)."""
    surf = pygame.Surface((width, 1), pygame.SRCALPHA)
    for i in range(width):
        t = i / max(width - 1, 1)
        alpha = int(220 * (1 - abs(t - 0.5) * 2))
        surf.set_at((i, 0), (*GOLD, alpha))
    screen.blit(surf, (x, y))

def draw_corner_ornaments(screen: pygame.Surface, rect: pygame.Rect,
                          size: int = 8, color: tuple = GOLD, width: int = 2):
    """Ornements dorés aux 4 coins."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    for pts in [
        [(x, y + size), (x, y), (x + size, y)],
        [(x + w - size, y), (x + w, y), (x + w, y + size)],
        [(x, y + h - size), (x, y + h), (x + size, y + h)],
        [(x + w - size, y + h), (x + w, y + h), (x + w, y + h - size)],
    ]:
        pygame.draw.lines(screen, color, False, pts, width)

def draw_xp_bar(screen: pygame.Surface, rect: pygame.Rect,
                current: int, maximum: int,
                color: tuple = GOLD_LIGHT, bg: tuple = DARK_2):
    """Barre XP."""
    pygame.draw.rect(screen, bg, rect, border_radius=2)
    pygame.draw.rect(screen, GOLD_DIM, rect, 1, border_radius=2)
    if maximum > 0 and current > 0:
        fw = int(rect.width * min(current / maximum, 1.0))
        if fw > 0:
            pygame.draw.rect(screen, color, pygame.Rect(rect.x, rect.y, fw, rect.height), border_radius=2)

def draw_progress_bar(screen: pygame.Surface, rect: pygame.Rect,
                      current: int, maximum: int,
                      color: tuple = GOLD_LIGHT, green_when_full: bool = True):
    """Barre de progression (quêtes)."""
    full = maximum > 0 and current >= maximum
    draw_xp_bar(screen, rect, current, maximum, GREEN_OK if (full and green_when_full) else color)

def render_text(screen: pygame.Surface, text: str, fnt: pygame.font.Font,
                color: tuple, x: int, y: int,
                center: bool = False, shadow: bool = True) -> pygame.Surface:
    """Affiche du texte avec ombre optionnelle. Retourne la surface."""
    if shadow:
        sh = fnt.render(text, True, (0, 0, 0))
        ox = x - sh.get_width() // 2 + 1 if center else x + 1
        screen.blit(sh, (ox, y + 1))
    surf = fnt.render(text, True, color)
    ox = x - surf.get_width() // 2 if center else x
    screen.blit(surf, (ox, y))
    return surf

def draw_coin_icon(screen: pygame.Surface, x: int, y: int, size: int = 18):
    """Icône pièce (sprite ou fallback cercle doré)."""
    icon = load_img(ICON_COINS, (size, size))
    if icon:
        screen.blit(icon, (x, y))
    else:
        pygame.draw.circle(screen, GOLD_LIGHT, (x + size//2, y + size//2), size//2)
        pygame.draw.circle(screen, DARK, (x + size//2, y + size//2), size//2, 1)

def draw_gem_icon(screen: pygame.Surface, x: int, y: int, size: int = 18):
    """Icône gemme (sprite ou fallback losange violet)."""
    icon = load_img(ICON_GEMS, (size, size))
    if icon:
        screen.blit(icon, (x, y))
    else:
        cx, cy = x + size//2, y + size//2
        pts = [(cx, y), (x + size, cy), (cx, y + size), (x, cy)]
        pygame.draw.polygon(screen, PURPLE_GEM, pts)
        pygame.draw.polygon(screen, DARK, pts, 1)

# ============================================================
# FOND PIERRE (tous les écrans in-game)
# ============================================================
_stone_cache: dict = {}

def draw_stone_bg(screen: pygame.Surface, rect: pygame.Rect = None):
    """Fond sombre avec texture de joints de pierre subtils."""
    if rect is None:
        rect = screen.get_rect()
    w, h = rect.width, rect.height
    key  = (w, h)
    if key not in _stone_cache:
        surf = pygame.Surface((w, h))
        surf.fill(DARK)
        # Joints horizontaux
        joint = pygame.Surface((w, 1), pygame.SRCALPHA)
        joint.fill((0, 0, 0, 20))
        for y in range(0, h, 48):
            surf.blit(joint, (0, y))
        # Filets dorés très subtils
        gold_line = pygame.Surface((w, 1), pygame.SRCALPHA)
        gold_line.fill((*GOLD, 8))
        for y in range(48, h, 96):
            surf.blit(gold_line, (0, y))
        # Coins sombres
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for corner in [(0,0),(w,0),(0,h),(w,h)]:
            for r, a in [(min(w,h)//2, 30),(min(w,h)//4, 20)]:
                pygame.draw.circle(overlay, (0,0,0,a), corner, r*2)
        surf.blit(overlay, (0,0))
        _stone_cache[key] = surf
    screen.blit(_stone_cache[key], rect.topleft)

# ============================================================
# VIGNETTE (écran titre)
# ============================================================
_vignette_cache: dict = {}

def make_vignette(w: int, h: int) -> pygame.Surface:
    """Vignette qui assombrit le côté gauche et les bords haut/bas."""
    key = (w, h)
    if key in _vignette_cache:
        return _vignette_cache[key]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # Gauche
    for i in range(w // 3):
        t = 1.0 - i / (w // 3)
        alpha = int(190 * t * t)
        pygame.draw.line(surf, (5, 3, 2, alpha), (i, 0), (i, h))
    # Haut/bas
    for i in range(h // 5):
        t = 1.0 - i / (h // 5)
        alpha = int(130 * t * t)
        pygame.draw.line(surf, (5, 3, 2, alpha), (0, i), (w, i))
        pygame.draw.line(surf, (5, 3, 2, alpha), (0, h-1-i), (w, h-1-i))
    _vignette_cache[key] = surf
    return surf