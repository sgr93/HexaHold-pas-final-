"""
ui/theme.py

Theme visuel global de HexaHold - DA SNK medievale.
TOUT passe par ici : couleurs, polices, images, helpers de dessin.
Changer une variable ici et tout le jeu suit.
"""

import os
import math
import pygame


# CHEMINS ASSETS

_BASE      = os.path.join(os.path.dirname(__file__), "..")
_FONTS_DIR = os.path.join(_BASE, "assets", "fonts")
_IMG_DIR   = os.path.join(_BASE, "assets", "images")
_SPR_DIR   = os.path.join(_BASE, "assets", "sprites")
_ICON_DIR  = os.path.join(_BASE, "assets", "icons")

# Deux polices : pixel pour les titres/menus, Georgia pour le corps de texte
FONT_TITLE = os.path.join(_FONTS_DIR, "PixelCrash.otf")
FONT_BODY  = os.path.join(_FONTS_DIR, "Georgia.ttf")

IMG_TITLE_BG = os.path.join(_IMG_DIR, "best_snk.png")
IMG_BLASON   = os.path.join(_IMG_DIR, "ailes.png")

ICON_NAV = {k: os.path.join(_ICON_DIR, f"nav_{k}.png") for k in
            ("accueil", "histoire", "quetes", "equipement", "gacha", "talents", "parametres")}

ICON_COINS = os.path.join(_SPR_DIR, "pieces.png")
ICON_GEMS  = os.path.join(_SPR_DIR, "gemmes.png")


# PALETTE
# On commence sombre et on monte vers le doré — cohérent avec l'ambiance murs/titans

GOLD       = (200, 146,  10)
GOLD_LIGHT = (232, 168,  32)
GOLD_DIM   = (107,  93,  63)
CREAM      = (237, 224, 190)
CREAM_DIM  = (180, 165, 130)
DARK       = ( 13,  11,   9)
DARK_2     = ( 20,  16,  10)
DARK_3     = ( 28,  22,  14)
RED_BADGE  = (122,  21,  21)
GREEN_OK   = ( 74, 154,  74)
BLUE_XP    = (100, 180, 255)
PURPLE_GEM = (170, 136, 255)

# Alias semantiques — utilises dans les ecrans pour ne pas hardcoder les couleurs
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


# TAILLES DE POLICES

SZ_TITLE  = 48
SZ_MENU   = 28
SZ_MENU_A = 40   # item actif sur l'ecran titre — plus grand pour bien le distinguer
SZ_SECTION = 20
SZ_LABEL  = 16
SZ_SMALL  = 13
SZ_TINY   = 11


# DIMENSIONS UI

HEADER_H     = 74
BOTTOM_NAV_H = 68
RADIUS_SM    = 4
RADIUS_MD    = 8
RADIUS_LG    = 12
BORDER_W     = 1
BORDER_ACC   = 2
RULE_W       = 200   # largeur de la ligne doree sous les titres


# CACHES INTERNES — evite de recreer les objets font/image a chaque frame

_font_cache:  dict = {}
_img_cache:   dict = {}
_stone_cache: dict = {}
_vignette_cache: dict = {}


# POLICES

def font(size: int, bold: bool = False, body: bool = False) -> pygame.font.Font:
    """
    Retourne une police mise en cache.
    body=True -> Georgia (texte courant), body=False -> PixelCrash (titres).
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


# IMAGES

def load_img(path: str, size: tuple = None) -> pygame.Surface | None:
    """
    Charge et met en cache une image. size=(w,h) pour redimensionner.
    Retourne None silencieusement si le fichier est absent — pas de crash.
    """
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
    """Charge assets/icons/<name>.png redimensionnee a size x size."""
    return load_img(os.path.join(_ICON_DIR, f"{name}.png"), (size, size))


def load_sprite(name: str, size: tuple = None) -> pygame.Surface | None:
    """Charge assets/sprites/<name>.png — ajoute .png si absent."""
    path = os.path.join(_SPR_DIR, name if name.endswith(".png") else f"{name}.png")
    return load_img(path, size)


# HELPERS DE DESSIN

def draw_panel(screen: pygame.Surface, rect: pygame.Rect,
               color: tuple = None, border_color: tuple = None,
               radius: int = RADIUS_MD, border_w: int = BORDER_W):
    """Panneau sombre avec bordure doree — base de tous les composants UI."""
    pygame.draw.rect(screen, color or C_PANEL, rect, border_radius=radius)
    if border_w:
        pygame.draw.rect(screen, border_color or C_BORDER, rect, border_w, border_radius=radius)


def draw_rect_alpha(screen: pygame.Surface, color_rgba: tuple,
                    rect: pygame.Rect, radius: int = 0):
    """Rectangle avec transparence — pygame ne supporte pas l'alpha sur draw.rect."""
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surf, color_rgba, surf.get_rect(), border_radius=radius)
    screen.blit(surf, rect.topleft)


def draw_gold_rule(screen: pygame.Surface, x: int, y: int, width: int = RULE_W):
    """Ligne doree avec degradee sur les bords — ornement sous les titres."""
    surf = pygame.Surface((width, 1), pygame.SRCALPHA)
    for i in range(width):
        t     = i / max(width - 1, 1)
        alpha = int(220 * (1 - abs(t - 0.5) * 2))
        surf.set_at((i, 0), (*GOLD, alpha))
    screen.blit(surf, (x, y))


def draw_corner_ornaments(screen: pygame.Surface, rect: pygame.Rect,
                          size: int = 8, color: tuple = GOLD, width: int = 2):
    """Crochets dores aux 4 coins d'un panneau — donne le look SNK medievale."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    for pts in [
        [(x,         y + size), (x,         y),     (x + size,     y)],
        [(x + w - size, y),     (x + w,     y),     (x + w,     y + size)],
        [(x,         y + h - size), (x,     y + h), (x + size,     y + h)],
        [(x + w - size, y + h), (x + w,     y + h), (x + w, y + h - size)],
    ]:
        pygame.draw.lines(screen, color, False, pts, width)


def draw_xp_bar(screen: pygame.Surface, rect: pygame.Rect,
                current: int, maximum: int,
                color: tuple = GOLD_LIGHT, bg: tuple = DARK_2):
    """Barre XP avec fond sombre et remplissage dore."""
    pygame.draw.rect(screen, bg,       rect, border_radius=2)
    pygame.draw.rect(screen, GOLD_DIM, rect, 1, border_radius=2)
    if maximum > 0 and current > 0:
        fw = int(rect.width * min(current / maximum, 1.0))
        if fw > 0:
            pygame.draw.rect(screen, color,
                             pygame.Rect(rect.x, rect.y, fw, rect.height), border_radius=2)


def draw_progress_bar(screen: pygame.Surface, rect: pygame.Rect,
                      current: int, maximum: int,
                      color: tuple = GOLD_LIGHT, green_when_full: bool = True):
    """Barre de progression pour les quetes — verte quand completee."""
    full = maximum > 0 and current >= maximum
    draw_xp_bar(screen, rect, current, maximum,
                GREEN_OK if (full and green_when_full) else color)


def render_text(screen: pygame.Surface, text: str, fnt: pygame.font.Font,
                color: tuple, x: int, y: int,
                center: bool = False, shadow: bool = True) -> pygame.Surface:
    """
    Affiche du texte avec ombre portee optionnelle.
    center=True centre horizontalement sur x. Retourne la surface rendue.
    """
    if shadow:
        sh = fnt.render(text, True, (0, 0, 0))
        ox = x - sh.get_width() // 2 + 1 if center else x + 1
        screen.blit(sh, (ox, y + 1))
    surf = fnt.render(text, True, color)
    screen.blit(surf, (x - surf.get_width() // 2 if center else x, y))
    return surf


def draw_coin_icon(screen: pygame.Surface, x: int, y: int, size: int = 18):
    """Icone piece — sprite ou fallback cercle dore si l'asset est absent."""
    icon = load_img(ICON_COINS, (size, size))
    if icon:
        screen.blit(icon, (x, y))
    else:
        pygame.draw.circle(screen, GOLD_LIGHT, (x + size // 2, y + size // 2), size // 2)
        pygame.draw.circle(screen, DARK,       (x + size // 2, y + size // 2), size // 2, 1)


def draw_gem_icon(screen: pygame.Surface, x: int, y: int, size: int = 18):
    """Icone gemme — sprite ou fallback losange violet si l'asset est absent."""
    icon = load_img(ICON_GEMS, (size, size))
    if icon:
        screen.blit(icon, (x, y))
    else:
        cx, cy = x + size // 2, y + size // 2
        pts    = [(cx, y), (x + size, cy), (cx, y + size), (x, cy)]
        pygame.draw.polygon(screen, PURPLE_GEM, pts)
        pygame.draw.polygon(screen, DARK, pts, 1)


# FOND PIERRE

def draw_stone_bg(screen: pygame.Surface, rect: pygame.Rect = None):
    """
    Fond sombre avec texture de joints de pierre subtils.
    Mis en cache par taille — pas de recalcul a chaque frame.
    """
    if rect is None:
        rect = screen.get_rect()
    w, h = rect.width, rect.height
    key  = (w, h)
    if key not in _stone_cache:
        surf = pygame.Surface((w, h))
        surf.fill(DARK)

        # Joints horizontaux toutes les 48px — simule des rangees de pierres
        joint = pygame.Surface((w, 1), pygame.SRCALPHA)
        joint.fill((0, 0, 0, 20))
        for y in range(0, h, 48):
            surf.blit(joint, (0, y))

        # Filets dores tres subtils tous les 96px — juste une touche medievale
        gold_line = pygame.Surface((w, 1), pygame.SRCALPHA)
        gold_line.fill((*GOLD, 8))
        for y in range(48, h, 96):
            surf.blit(gold_line, (0, y))

        # Coins sombres — vignette discrete sur les quatre angles
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        for corner in [(0, 0), (w, 0), (0, h), (w, h)]:
            for r, a in [(min(w, h) // 2, 30), (min(w, h) // 4, 20)]:
                pygame.draw.circle(overlay, (0, 0, 0, a), corner, r * 2)
        surf.blit(overlay, (0, 0))
        _stone_cache[key] = surf

    screen.blit(_stone_cache[key], rect.topleft)


# VIGNETTE

def make_vignette(w: int, h: int) -> pygame.Surface:
    """
    Vignette pour l'ecran titre : assombrit le cote gauche et les bords haut/bas.
    Le cote gauche est plus sombre pour mettre en valeur le texte du menu qui est a gauche.
    Mis en cache par taille.
    """
    key = (w, h)
    if key in _vignette_cache:
        return _vignette_cache[key]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # Degradee gauche — couvre un tiers de la largeur
    for i in range(w // 3):
        t     = 1.0 - i / (w // 3)
        alpha = int(190 * t * t)
        pygame.draw.line(surf, (5, 3, 2, alpha), (i, 0), (i, h))

    # Degradees haut et bas — couvrent un cinquieme de la hauteur
    for i in range(h // 5):
        t     = 1.0 - i / (h // 5)
        alpha = int(130 * t * t)
        pygame.draw.line(surf, (5, 3, 2, alpha), (0, i),         (w, i))
        pygame.draw.line(surf, (5, 3, 2, alpha), (0, h - 1 - i), (w, h - 1 - i))

    _vignette_cache[key] = surf
    return surf