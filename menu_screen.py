"""
menu_screen.py
--------------
Système de menu principal avec 4 onglets :
  - Menu Principal (choix du niveau)
  - Gacha (coffres)
  - Équipement
  - Skill Tree
"""
import os
import pygame
import save_data as sd
from config import (
    DIFFICULTY_LEVELS, CHEST_COSTS, RARITIES, RARITY_COLORS, RARITY_WEIGHTS,
    EQUIPMENT_SLOTS, EQUIPMENT_STATS, ALL_TOWER_TYPES, TOWER_SLOT_COUNT,
    LEVEL_START, XP_START, XP_TO_NEXT_LVL_START, XP_GROWTH_FACTOR,
)
from ui import ITEM_LABELS, ITEM_COLORS
import quetes as quetes_module
from histoire import run_histoire
# ============================================================
# COLORS FROM THEME (INLINED)
# ============================================================
COLORS = {
    "bg": (15, 18, 28),
    "panel": (29, 35, 51),
    "panel_alt": (36, 44, 64),
    "border": (88, 103, 138),
    "text": (236, 240, 250),
    "muted": (163, 173, 196),
    "accent": (255, 205, 92),
    "accent_alt": (111, 205, 255),
    "success": (96, 224, 138),
    "danger": (240, 99, 99),
}
RADIUS = {"sm": 6, "md": 10, "lg": 14}

def get_font(size_key="md", bold=False):
    """Retourne une font simple."""
    sizes = {"xs": 14, "sm": 18, "md": 22, "lg": 30, "xl": 48}
    size = sizes.get(size_key, 22)
    return pygame.font.SysFont("arial", size, bold=bold)

def calculate_level_info(total_xp):
    """Calcule le niveau actuel et l'XP nécessaire pour le niveau suivant."""
    level = LEVEL_START
    xp_to_next = XP_TO_NEXT_LVL_START
    remaining_xp = total_xp

    while remaining_xp >= xp_to_next:
        remaining_xp -= xp_to_next
        level += 1
        xp_to_next = int(xp_to_next * XP_GROWTH_FACTOR)

    return level, remaining_xp, xp_to_next

ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "sprites")
_icon_cache = {}

def load_icon(name, size=None):
    key = (name, size)
    if key in _icon_cache:
        return _icon_cache[key]

    # Cherche d'abord dans assets/sprites/, puis assets/ en fallback
    for folder in [
        os.path.join(os.path.dirname(__file__), "assets", "sprites"),
        os.path.join(os.path.dirname(__file__), "assets"),
    ]:
        path = os.path.join(folder, f"{name}.png")
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, (size, size))
            _icon_cache[key] = img
            return _icon_cache[key]
        except Exception:
            pass

    print(f"[WARN] Icon not found: {name}.png")
    _icon_cache[key] = None
    return None

def add_xp(player, amount):
    player["xp"] += amount

    # Level up en boucle (si gros gain d'XP)
    while player["xp"] >= player["xp_next"]:
        player["xp"] -= player["xp_next"]
        player["level"] += 1

        # Scaling du level (tu peux ajuster)
        player["xp_next"] = int(player["xp_next"] * 1.25)

        print(f"Level UP ! Niveau {player['level']}")
        
def draw_panel(screen, rect, alt=False):
    """Dessine un panneau stylisé."""
    bg = COLORS["panel_alt"] if alt else COLORS["panel"]
    pygame.draw.rect(screen, bg, rect, border_radius=RADIUS["md"])
    pygame.draw.rect(screen, COLORS["border"], rect, 1, border_radius=RADIUS["md"])

def draw_button(screen, rect, hovered=False, active=False):
    """Dessine un bouton."""
    if active:
        color = COLORS["accent_alt"]
    elif hovered:
        color = (min(255, COLORS["panel_alt"][0] + 20), min(255, COLORS["panel_alt"][1] + 20), min(255, COLORS["panel_alt"][2] + 20))
    else:
        color = COLORS["panel_alt"]
    pygame.draw.rect(screen, color, rect, border_radius=RADIUS["md"])
    pygame.draw.rect(screen, COLORS["accent"] if hovered else COLORS["border"], rect, 2, border_radius=RADIUS["md"])

# ── Cache des sprites d'icônes (pieces.png / gemmes.png) ─────────────────────
_ICON_SPRITE_CACHE: dict = {}
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "sprites")

def _load_icon_sprite(filename, size):
    """Charge et met en cache un sprite PNG redimensionné à (size, size). Retourne None si absent."""
    key = (filename, size)
    if key in _ICON_SPRITE_CACHE:
        return _ICON_SPRITE_CACHE[key]
    path = os.path.join(_ASSETS_DIR, filename)
    surf = None
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            surf = pygame.transform.smoothscale(img, (size, size))
        except Exception as e:
            print(f"[menu_screen] Impossible de charger {filename}: {e}")
    _ICON_SPRITE_CACHE[key] = surf
    return surf


def _get_icon(name, size=18, color=(255, 255, 255)):
    """
    Retourne une surface icône.
    Pour 'coin' -> tente pieces.png, fallback vectoriel.
    Pour 'gem'  -> tente gemmes.png, fallback vectoriel.
    """
    if name == "coin":
        img = _load_icon_sprite("pieces.png", size)
        if img is not None:
            return img
    elif name == "gem":
        img = _load_icon_sprite("gemmes.png", size)
        if img is not None:
            return img

    # Fallback vectoriel
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    if name == "coin":
        pygame.draw.circle(surf, color, (cx, cy), size // 2 - 1)
        pygame.draw.circle(surf, (40, 30, 0), (cx, cy), size // 2 - 1, 1)
    elif name == "gem":
        points = [(cx, 1), (size-2, cy//2), (cx, size-2), (2, cy//2)]
        pygame.draw.polygon(surf, color, points)
        pygame.draw.polygon(surf, (color[0]//2, color[1]//2, color[2]//2), points, 1)
    elif name == "hp":
        pygame.draw.polygon(surf, color, [(cx, 2), (size - 2, cy), (cx, size - 2), (2, cy)])
    elif name == "speed":
        pygame.draw.polygon(surf, color, [(2, cy), (cx + 1, 2), (cx - 1, cy - 1), (size - 2, cy), (cx - 1, size - 2), (cx + 1, cy + 1)])
    else:
        pygame.draw.circle(surf, color, (cx, cy), size // 2 - 2, 2)
    return surf

def draw_player_info(screen, font, small_font, player, x=20, y=20):
    """
    player doit contenir :
    {
        "level":       int,
        "xp":          int,
        "xp_next":     int,
        "player_icon": str (optionnel, ex: "icone0.png")
    }
    Retourne le pygame.Rect de l'icône joueur (pour détecter le clic).
    """
    ICON_SIZE = 48
    BAR_WIDTH = 160
    BAR_HEIGHT = 10

    # === Icône joueur ===
    icon_name = player.get("player_icon", "icone0")
    if icon_name.endswith(".png"):
        icon_name = icon_name[:-4]
    icon = load_icon(icon_name, ICON_SIZE)
    icon_rect = pygame.Rect(x, y, ICON_SIZE, ICON_SIZE)
    if icon:
        screen.blit(icon, (x, y))
    else:
        pygame.draw.rect(screen, (80, 80, 80), icon_rect)

    # Bordure dorée au survol pour indiquer que c'est cliquable
    mx_cur, my_cur = pygame.mouse.get_pos()
    if icon_rect.collidepoint(mx_cur, my_cur):
        pygame.draw.rect(screen, (255, 205, 92), icon_rect, 2, border_radius=6)
    else:
        pygame.draw.rect(screen, (100, 100, 120), icon_rect, 1, border_radius=6)

    # === Texte niveau ===
    lvl_text = font.render(f"Niv. {player['level']}", True, (255, 255, 255))
    text_x = x + ICON_SIZE + 10
    text_y = y + 4
    screen.blit(lvl_text, (text_x, text_y))

    # === Barre XP ===
    xp = player["xp"]
    xp_next = max(1, player["xp_next"])
    ratio = max(0, min(1, xp / xp_next))

    bar_x = text_x
    bar_y = text_y + lvl_text.get_height() + 6

    pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, BAR_WIDTH, BAR_HEIGHT), border_radius=4)
    pygame.draw.rect(screen, (100, 200, 255),
                     (bar_x, bar_y, int(BAR_WIDTH * ratio), BAR_HEIGHT), border_radius=4)
    pygame.draw.rect(screen, (255, 255, 255),
                     (bar_x, bar_y, BAR_WIDTH, BAR_HEIGHT), 1, border_radius=4)

    xp_text = small_font.render(f"{xp}/{xp_next}", True, (200, 200, 200))
    screen.blit(xp_text, (bar_x, bar_y + BAR_HEIGHT + 4))

    return icon_rect


def _scan_available_icons():
    """
    Scanne assets/sprites/ et retourne la liste des PNG dont le nom
    commence par 'icone'. Si aucun trouvé, retourne tous les PNG du dossier.
    """
    folder = os.path.join(os.path.dirname(__file__), "assets", "sprites")
    if not os.path.isdir(folder):
        return []
    all_pngs = [f for f in os.listdir(folder) if f.lower().endswith(".png")]
    icone_pngs = sorted([f for f in all_pngs if f.lower().startswith("icone")])
    return icone_pngs if icone_pngs else sorted(all_pngs)


def draw_icon_picker(screen, font_sm, font_xs, save, mx, my, clicked):
    """
    Dessine le popup de sélection d'icône joueur.
    Retourne True quand le popup doit se fermer (bouton ✕ cliqué ou icône sélectionnée).
    Modifie save["player_icon"] directement si une icône est choisie.
    """
    icons = _scan_available_icons()
    if not icons:
        return True

    CELL = 64
    COLS_PICKER = 5
    PAD = 14
    TITLE_H = 36

    rows = (len(icons) + COLS_PICKER - 1) // COLS_PICKER
    pop_w = COLS_PICKER * (CELL + PAD) + PAD
    pop_h = TITLE_H + rows * (CELL + PAD) + PAD

    w_scr, _ = screen.get_size()
    pop_x = max(10, min(20, w_scr - pop_w - 10))
    pop_y = 95
    pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

    # Fond du popup
    _draw_rounded_rect(screen, (20, 24, 40), pop_rect, radius=12,
                       border=2, border_color=(88, 103, 138))

    # Titre
    title_lbl = font_sm.render("Choisir une icône", True, (236, 240, 250))
    screen.blit(title_lbl, (pop_rect.x + PAD, pop_rect.y + (TITLE_H - title_lbl.get_height()) // 2))

    # Bouton ✕ en haut à droite
    close_r = 12
    close_cx = pop_rect.right - close_r - 8
    close_cy = pop_rect.y + TITLE_H // 2
    close_rect = pygame.Rect(close_cx - close_r, close_cy - close_r, close_r * 2, close_r * 2)
    close_hov = close_rect.collidepoint(mx, my)
    pygame.draw.circle(screen, (200, 60, 60) if close_hov else (140, 50, 50), (close_cx, close_cy), close_r)
    pygame.draw.circle(screen, (255, 100, 100), (close_cx, close_cy), close_r, 1)
    x_lbl = font_xs.render("✕", True, (255, 220, 220))
    screen.blit(x_lbl, (close_cx - x_lbl.get_width() // 2, close_cy - x_lbl.get_height() // 2))

    if clicked and close_rect.collidepoint(mx, my):
        return True  # fermeture demandée

    # Séparateur sous le titre
    pygame.draw.line(screen, (60, 70, 100),
                     (pop_rect.x + 8, pop_rect.y + TITLE_H),
                     (pop_rect.right - 8, pop_rect.y + TITLE_H), 1)

    current_icon = save.get("player_icon", "icone0.png")

    for idx, fname in enumerate(icons):
        col_i = idx % COLS_PICKER
        row_i = idx // COLS_PICKER
        cx = pop_rect.x + PAD + col_i * (CELL + PAD)
        cy = pop_rect.y + TITLE_H + PAD // 2 + row_i * (CELL + PAD)
        cell_rect = pygame.Rect(cx, cy, CELL, CELL)

        is_selected = (fname == current_icon)
        is_hovered  = cell_rect.collidepoint(mx, my)

        bg_col     = (60, 80, 60)   if is_selected else ((50, 60, 80) if is_hovered else (29, 35, 51))
        border_col = (96, 224, 138) if is_selected else ((255, 205, 92) if is_hovered else (60, 70, 95))
        _draw_rounded_rect(screen, bg_col, cell_rect, radius=8, border=2, border_color=border_col)

        icon_name = fname[:-4] if fname.endswith(".png") else fname
        img = load_icon(icon_name, CELL - 8)
        if img:
            screen.blit(img, (cx + 4, cy + 4))
        else:
            lbl = font_xs.render(icon_name[:7], True, (180, 180, 180))
            screen.blit(lbl, (cx + CELL // 2 - lbl.get_width() // 2,
                               cy + CELL // 2 - lbl.get_height() // 2))

        if clicked and cell_rect.collidepoint(mx, my):
            save["player_icon"] = fname
            import save_data as _sd
            _sd.save(save)
            # On ne ferme PAS automatiquement, le joueur peut continuer à changer

    return False  # rester ouvert


def _inline_currency(screen, font, value, currency, x, y, color=None, icon_size=18):
    """
    Affiche l'icône currency (pieces.png ou gemmes.png) suivie du texte value.
    currency = 'coins' ou 'gems'.
    Retourne la largeur totale rendue.
    """
    icon_name = "coin" if currency == "coins" else "gem"
    default_color = (255, 205, 92) if currency == "coins" else (255, 100, 255)
    text_color = color or default_color
    icon = _get_icon(icon_name, icon_size)
    text_surf = font.render(str(value), True, text_color)
    screen.blit(icon, (x, y + (text_surf.get_height() - icon_size) // 2))
    screen.blit(text_surf, (x + icon_size + 4, y))
    return icon_size + 4 + text_surf.get_width()


# ── Couleurs ──────────────────────────────────────────────────────────────
C_BG = COLORS["bg"]
C_PANEL = COLORS["panel"]
C_PANEL2 = COLORS["panel_alt"]
C_ACCENT = COLORS["accent"]
C_ACCENT2 = COLORS["accent_alt"]
C_TEXT = COLORS["text"]
C_SUBTEXT = COLORS["muted"]
C_BTN = COLORS["panel_alt"]
C_BTN_HOV = (64, 79, 114)
C_BTN_BOR = COLORS["border"]
C_TAB_ACT = (52, 64, 95)
C_TAB_INACT = (31, 38, 57)
C_GREEN = COLORS["success"]
C_RED = COLORS["danger"]

font = pygame.font.SysFont("arial", 24)
small_font = pygame.font.SysFont("arial", 16)

DIFF_COLORS = {
    1: (80,  200, 100),
    2: (140, 220, 80 ),
    3: (255, 200, 40 ),
    4: (255, 120, 40 ),
    5: (255, 60,  60 ),
}

CHEST_INFO = {
    "wood":   {"label": "Coffre en Bois",   "color": (139, 90,  43 ), "cost": CHEST_COSTS["wood"],  "currency": "coins"},
    "silver": {"label": "Coffre en Argent", "color": (170, 180, 200), "cost": CHEST_COSTS["silver"],"currency": "coins"},
    "gold":   {"label": "Coffre en Or",     "color": (220, 180, 30 ), "cost": CHEST_COSTS["gold"],  "currency": "coins"},
    "gem_common": {"label": "Coffre Gemme Commun",   "color": (200, 100, 200), "cost": CHEST_COSTS["gem_common"],      "currency": "gems"},
    "gem_epic": {"label": "Coffre Gemme Épique",     "color": (255, 150, 255), "cost": CHEST_COSTS["gem_epic"],        "currency": "gems"},
    "gem_legendary": {"label": "Coffre Gemme Légendaire", "color": (255, 0, 255), "cost": CHEST_COSTS["gem_legendary"], "currency": "gems"},
}

SLOT_ICONS = {
    "cape":   "",
    "veste":   "",
    "bottes": "",
    "arme":     "",
    "tour":     "",
}

SLOT_LABELS = {
    "cape":   "Cape",
    "veste":   "Veste",
    "bottes": "Bottes",
    "arme":     "Arme",
    "tour":     "Tour",
}

RARITY_SLOT_COLORS = {
    "Commun": (120, 120, 128),
    "Rare": (70, 130, 235),
    "Epique": (150, 90, 220),
    "Legendaire": (230, 190, 60),
}
EQUIPMENT_SLOT_IMAGE_FILES = {
    "cape": "cape.png",
    "veste": "veste.png",
    "bottes": "bottes.png",
    "arme": "lames.png",
    "tour": "tour.png",
}
EQUIPMENT_DEFAULT_NAMES = {
    "cape": "Cape du bataillon",
    "veste": "Veste de garnison",
    "bottes": "Bottes tactique",
    "arme": "Lames jumelles",
    "tour": "Insigne de commandement",
}

_equipment_character_sprite = None
_equipment_background_sprite = None
_equipment_icon_cache = {}


def _get_equipment_character_sprite():
    """Charge le sprite du personnage de l'écran d'équipement une seule fois."""
    global _equipment_character_sprite
    if _equipment_character_sprite is not None:
        return _equipment_character_sprite

    path = os.path.join(os.path.dirname(__file__), "assets", "sprites", "eren.png")
    try:
        _equipment_character_sprite = pygame.image.load(path).convert_alpha()
    except Exception:
        _equipment_character_sprite = False
    return _equipment_character_sprite


def _get_equipment_background_sprite():
    """Charge le fond du panneau d'équipement une seule fois."""
    global _equipment_background_sprite
    if _equipment_background_sprite is not None:
        return _equipment_background_sprite

    path = os.path.join(os.path.dirname(__file__), "assets", "sprites", "maison1.png")
    try:
        _equipment_background_sprite = pygame.image.load(path).convert_alpha()
    except Exception:
        _equipment_background_sprite = False
    return _equipment_background_sprite


def _get_equipment_rarity_color(rarity):
    return RARITY_SLOT_COLORS.get(rarity, tuple(RARITY_COLORS.get(rarity, (120, 120, 128))))


def _get_equipment_name(item):
    default_name = EQUIPMENT_DEFAULT_NAMES.get(item.get("slot"), "Equipement")
    return item.get("name") or default_name


def _get_equipment_icon_surface(item):
    slot_key = item.get("slot")
    filename = item.get("image") or EQUIPMENT_SLOT_IMAGE_FILES.get(slot_key)
    if not filename:
        return None
    path = os.path.join(os.path.dirname(__file__), "assets", "sprites", filename)
    if path in _equipment_icon_cache:
        return _equipment_icon_cache[path]
    try:
        _equipment_icon_cache[path] = pygame.image.load(path).convert_alpha()
    except Exception:
        _equipment_icon_cache[path] = False
    return _equipment_icon_cache[path]


def _fit_surface(image, max_w, max_h):
    if not image or max_w <= 0 or max_h <= 0:
        return None
    scale = min(max_w / image.get_width(), max_h / image.get_height())
    new_w = max(1, int(image.get_width() * scale))
    new_h = max(1, int(image.get_height() * scale))
    return pygame.transform.smoothscale(image, (new_w, new_h))


def _draw_equipment_icon(screen, item, rect, show_label=False):
    rarity_color = _get_equipment_rarity_color(item.get("rarity"))
    _draw_rounded_rect(screen, C_PANEL2, rect, radius=min(rect.w, rect.h) // 4, border=2, border_color=rarity_color)

    fill_rect = rect.inflate(-6, -6)
    inner = pygame.Surface((fill_rect.w, fill_rect.h), pygame.SRCALPHA)
    inner.fill((*rarity_color, 70))
    screen.blit(inner, fill_rect.topleft)

    icon = _get_equipment_icon_surface(item)
    if icon:
        top_padding = 18 if show_label else 4
        fitted = _fit_surface(icon, fill_rect.w - 2, fill_rect.h - top_padding - 2)
        if fitted:
            icon_x = fill_rect.centerx - fitted.get_width() // 2
            icon_y = fill_rect.y + top_padding + max(0, (fill_rect.h - top_padding - fitted.get_height()) // 2)
            screen.blit(fitted, (icon_x, icon_y))

    if show_label:
        name_lbl = get_font("xs", bold=True).render(_get_equipment_name(item), True, C_TEXT)
        screen.blit(name_lbl, (rect.centerx - name_lbl.get_width() // 2, rect.y + 6))

# État global du menu (plus utilisé depuis la refonte skilltree radial)


def _draw_rounded_rect(surf, color, rect, radius=10, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def _center_text(surf, font, text, color, rect):
    lbl = font.render(text, True, color)
    surf.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2,
                    rect.y + (rect.h - lbl.get_height()) // 2))
    return lbl


def run_title_screen(screen, clock, save):
    font_big = get_font("xl", bold=True)
    font_med = get_font("lg", bold=True)
    font_sm = get_font("sm")
    font_xs = get_font("xs")

    buttons = ["Jouer", "Options", "Quitter"]
    selected = None

    while True:
        w, h = screen.get_size()
        screen.fill(C_BG)

        title = font_big.render("HEXAHOLD", True, C_ACCENT)
        screen.blit(title, (w // 2 - title.get_width() // 2, 100))

        subtitle = font_sm.render("Défendez vos tours dans un mode TD intense.", True, C_SUBTEXT)
        screen.blit(subtitle, (w // 2 - subtitle.get_width() // 2, 180))

        mx, my = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, save
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None, save
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        btn_h = 70
        gap = 20
        total_h = len(buttons) * btn_h + (len(buttons) - 1) * gap
        start_y = h // 2 - total_h // 2
        for i, label in enumerate(buttons):
            btn = pygame.Rect(w // 2 - 140, start_y + i * (btn_h + gap), 280, btn_h)
            hov = btn.collidepoint(mx, my)
            _draw_rounded_rect(screen, C_BTN_HOV if hov else C_BTN, btn, radius=14,
                               border=2, border_color=C_ACCENT if hov else C_BTN_BOR)
            txt = font_med.render(label, True, C_TEXT)
            screen.blit(txt, (btn.x + (btn.w - txt.get_width()) // 2,
                              btn.y + (btn.h - txt.get_height()) // 2))
            if clicked and hov:
                if label == "Jouer":
                    return "play", save
                if label == "Options":
                    save = run_options_screen(screen, clock, save)
                if label == "Quitter":
                    return None, save

        footer = font_xs.render("Utilisez le menu Options pour régler le volume et l'affichage.", True, C_SUBTEXT)
        screen.blit(footer, (w // 2 - footer.get_width() // 2, h - 60))

        pygame.display.flip()
        clock.tick(60)


def run_options_screen(screen, clock, save):
    font_med = get_font("md", bold=True)
    font_sm = get_font("sm")
    font_xs = get_font("xs")

    option_items = [
        {"label": "Volume musique", "key": "music_volume", "type": "slider"},
        {"label": "Volume sons", "key": "sound_volume", "type": "slider"},
        {"label": "Plein écran", "key": "fullscreen",   "type": "toggle"},
    ]

    def _update_music_volume():
        if not pygame.mixer.get_init():
            return
        try:
            pygame.mixer.music.set_volume(save.get("music_volume", 0.8))
        except Exception:
            pass

    _update_music_volume()

    while True:
        w, h = screen.get_size()
        screen.fill(C_BG)

        title = font_med.render("Options", True, C_ACCENT)
        screen.blit(title, (w // 2 - title.get_width() // 2, 40))

        mx, my = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sd.save(save)
                return save
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                sd.save(save)
                return save
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        slider_width = 300
        option_y = 110
        for opt in option_items:
            label = font_sm.render(opt["label"], True, C_TEXT)
            screen.blit(label, (w // 2 - slider_width // 2, option_y))
            if opt["type"] == "slider":
                rect = pygame.Rect(w // 2 - slider_width // 2, option_y + 28, slider_width, 18)
                pygame.draw.rect(screen, C_BTN, rect, border_radius=9)
                value = save.get(opt["key"], 0.8)
                fill = pygame.Rect(rect.x, rect.y, int(rect.w * value), rect.h)
                pygame.draw.rect(screen, C_ACCENT, fill, border_radius=9)
                pygame.draw.rect(screen, C_BTN_BOR, rect, 2, border_radius=9)
                if clicked and rect.collidepoint(mx, my):
                    save[opt["key"]] = min(1.0, max(0.0, (mx - rect.x) / rect.w))
                    if opt["key"] == "music_volume":
                        _update_music_volume()
            else:
                rect = pygame.Rect(w // 2 - slider_width // 2, option_y + 28, 120, 32)
                label_val = "ON" if save.get(opt["key"], False) else "OFF"
                pygame.draw.rect(screen, C_BTN_HOV if rect.collidepoint(mx, my) else C_BTN, rect, border_radius=9)
                pygame.draw.rect(screen, C_BTN_BOR, rect, 2, border_radius=9)
                txt = font_sm.render(label_val, True, C_TEXT)
                screen.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2,
                                  rect.y + (rect.h - txt.get_height()) // 2))
                if clicked and rect.collidepoint(mx, my):
                    save[opt["key"]] = not save.get(opt["key"], False)
            option_y += 80

        back_btn = pygame.Rect(w // 2 - 90, h - 90, 180, 50)
        hov = back_btn.collidepoint(mx, my)
        _draw_rounded_rect(screen, C_BTN_HOV if hov else C_BTN, back_btn, radius=12,
                           border=2, border_color=C_ACCENT if hov else C_BTN_BOR)
        back_txt = font_med.render("Retour", True, C_TEXT)
        screen.blit(back_txt, (back_btn.x + (back_btn.w - back_txt.get_width()) // 2,
                                back_btn.y + (back_btn.h - back_txt.get_height()) // 2))
        if clicked and hov:
            sd.save(save)
            return save

        pygame.display.flip()
        clock.tick(60)


def run_menu(screen, clock, save=None):
    """
    Lance le menu principal.
    Retourne (difficulty_level: int, save) quand le joueur choisit un niveau,
    ou (None, save) si le joueur quitte.
    """
    if save is None:
        save = sd.load()
    font_big = get_font("xl", bold=True)
    font_med = get_font("md", bold=True)
    font_sm = get_font("sm")
    font_xs = get_font("xs")

    tabs       = ["Menu Principal", "Gacha", "Équipement", "Skill Tree", "Quêtes"]
    active_tab = 0

    # État gacha
    last_item_obtained = None
    gacha_msg          = ""
    gacha_msg_timer    = 0
    gacha_info_popup   = None   # None ou ctype du coffre dont on affiche les taux
    # Nouveau système gacha tours
    gacha_tower_results    = []
    gacha_tower_anim       = 0
    gacha_tower_result_idx = 0
    gacha_show_rates       = False
    gacha_tower_scroll     = 0
    # Overlay coffre pièces (fullscreen)
    chest_overlay_item    = None   # item dict affiché en overlay
    chest_overlay_timer   = 0      # frames restantes (240 = 4s)
    sd._ensure_tower_data(save)

    # État équipement
    selected_inv_idx       = None    # index dans save["inventory_equipment"]
    selected_loadout_slot  = 0
    selected_equip_category = 0
    equip_scroll_by_cat    = [0, 0, 0, 0, 0]  # scroll indépendant par onglet équipement
    dragging_item          = None
    drag_offset            = (0, 0)
    save.setdefault("tower_loadout", ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
    if len(save["tower_loadout"]) < TOWER_SLOT_COUNT:
        save["tower_loadout"] = (save["tower_loadout"] + ALL_TOWER_TYPES)[:TOWER_SLOT_COUNT]

    quest_section_active = "quotidiennes"
    event_type_scroll = 0
    available_quests_clicked = None
    icon_picker_open = False

    running = True
    chosen_level = None

    while running:
        w, h = screen.get_size()
        screen.fill(C_BG)

        mx, my = pygame.mouse.get_pos()
        clicked = False
        mouse_released = False
        scroll_dy = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, save
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None, save
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_released = True
            if event.type == pygame.MOUSEWHEEL:
                scroll_dy = event.y

        # ── Header / Title ────────────────────────────────────────────────
        title = font_big.render("HEXAHOLD", True, C_ACCENT)
        screen.blit(title, (w // 2 - title.get_width() // 2, 16))

        # Pièces (icône + valeur)
        _hdr_coins_txt = font_med.render(str(save['coins']), True, C_ACCENT)
        _hdr_coin_ico  = _get_icon("coin", 22)
        _hdr_cx = w - _hdr_coins_txt.get_width() - 22 - 8 - 12
        screen.blit(_hdr_coin_ico,  (_hdr_cx, 18))
        screen.blit(_hdr_coins_txt, (_hdr_cx + 26, 18))

        # Gemmes (icône + valeur)
        _hdr_gems_txt = font_med.render(str(save.get('gems', 0)), True, (255, 100, 255))
        _hdr_gem_ico  = _get_icon("gem", 22)
        _hdr_gx = _hdr_cx - _hdr_gems_txt.get_width() - 22 - 8 - 20
        screen.blit(_hdr_gem_ico,  (_hdr_gx, 18))
        screen.blit(_hdr_gems_txt, (_hdr_gx + 26, 18))
        
        # Icône et progression du joueur (données réelles depuis la sauvegarde)
        _player_display = {
            "level":       save.get("level", 1),
            "xp":          save.get("xp", 0),
            "xp_next":     save.get("xp_next", 30),
            "player_icon": save.get("player_icon", "icone0.png"),
        }
        _icon_rect = draw_player_info(screen, font, small_font, _player_display)
        if clicked and _icon_rect.collidepoint(mx, my):
            icon_picker_open = True
            _icon_picker_just_opened = True
        else:
            _icon_picker_just_opened = False
        # ── Onglets ────────────────────────────────────────────────────────
        tab_h   = 40
        tab_y   = 95
        tab_w   = w // len(tabs)
        tab_rects = []
        for i, tab in enumerate(tabs):
            tr = pygame.Rect(i * tab_w, tab_y, tab_w, tab_h)
            tab_rects.append(tr)
            col = C_TAB_ACT if i == active_tab else C_TAB_INACT
            _draw_rounded_rect(screen, col, tr, radius=0)
            if i == active_tab:
                pygame.draw.rect(screen, C_ACCENT, (tr.x, tr.y + tr.h - 3, tr.w, 3))
            _center_text(screen, font_sm, tab, C_ACCENT if i == active_tab else C_SUBTEXT, tr)
            if clicked and tr.collidepoint(mx, my):
                active_tab = i

        content_y = tab_y + tab_h + 10
        content_h = h - content_y - 10

        # ── CONTENU SELON ONGLET ───────────────────────────────────────────

        # ────────────────────────────────────────────────────────────────────
        # TAB 0 : MENU PRINCIPAL — choix du niveau
        # ────────────────────────────────────────────────────────────────────
        if active_tab == 0:
            panel = pygame.Rect(20, content_y + 10, w - 40, content_h - 20)
            _draw_rounded_rect(screen, C_PANEL, panel, radius=12)

            subtitle = font_med.render("Choisissez un mode de jeu", True, C_TEXT)
            screen.blit(subtitle, (panel.x + (panel.w - subtitle.get_width()) // 2, panel.y + 16))

            # ── Trois boutons de mode ──
            mode_buttons = [
                ("◈  Mode Histoire",  (138, 106, 30), (196, 154, 46)),
                ("∞  Mode Infini",    (30,  90, 130), (60, 160, 220)),
                ("⚔  Mode Guerre",   (110,  30,  30), (200,  60,  60)),
            ]
            btn_h   = 64
            btn_gap = 14
            btn_w   = panel.w - 60
            start_y = panel.y + 60

            for i, (label, col_n, col_h) in enumerate(mode_buttons):
                btn = pygame.Rect(panel.x + 30, start_y + i * (btn_h + btn_gap), btn_w, btn_h)
                hov = btn.collidepoint(mx, my)
                border_col = col_h if hov else col_n
                _draw_rounded_rect(screen, C_BTN_HOV if hov else C_BTN, btn,
                                radius=10, border=2, border_color=border_col)
                lbl = font_med.render(label, True, col_h if hov else C_TEXT)
                screen.blit(lbl, (btn.x + 22, btn.y + (btn_h - lbl.get_height()) // 2))

                if clicked and hov:
                    if i == 0:   # Mode Histoire
                        result = run_histoire(screen, clock, save)
                        if isinstance(result, dict):
                            chosen_level = result.get("difficulty", 1)
                            running = False
                    elif i == 1: # Mode Infini — à implémenter
                        pass
                    elif i == 2: # Mode Guerre — à implémenter
                        pass

            # ── Sélection rapide de difficulté (toujours accessible) ──
            diff_y = start_y + len(mode_buttons) * (btn_h + btn_gap) + 16
            diff_lbl = font_sm.render("— Partie rapide : choisissez une difficulté —", True, C_SUBTEXT)
            screen.blit(diff_lbl, (panel.x + panel.w//2 - diff_lbl.get_width()//2, diff_y))
            diff_y += diff_lbl.get_height() + 8

            for lvl, info in DIFFICULTY_LEVELS.items():
                if diff_y + 46 > panel.bottom - 10:
                    break
                btn = pygame.Rect(panel.x + 30, diff_y, btn_w, 46)
                hov = btn.collidepoint(mx, my)
                _draw_rounded_rect(screen, C_BTN_HOV if hov else C_BTN, btn,
                                   radius=8, border=2, border_color=DIFF_COLORS[lvl])
                name_lbl = font_sm.render(f"Niv. {lvl} — {info['name']}", True, DIFF_COLORS[lvl])
                screen.blit(name_lbl, (btn.x + 14, btn.y + 6))
                detail = font_xs.render(
                    f"{info['waves']} vagues  |  x{info['enemy_hp_mult']} HP  |  {info['coins_reward']} pièces",
                    True, C_SUBTEXT)
                screen.blit(detail, (btn.x + 14, btn.y + 26))
                if clicked and hov:
                    chosen_level = lvl
                    running = False
                diff_y += 46 + 8

        # ────────────────────────────────────────────────────────────────────
        # TAB 1 : GACHA (refonte complète avec 2 coffres + système tours)
        # ────────────────────────────────────────────────────────────────────
        elif active_tab == 1:
            # ── Palette locale gacha ─────────────────────────────────────────
            G_BG      = (18, 20, 30)
            G_CARD    = (28, 32, 48)
            G_CARD2   = (38, 44, 64)
            G_BORDER  = (60, 70, 100)
            G_GOLD    = (220, 170, 40)
            G_GEM     = (140, 80, 240)
            G_RED_LBL = (230, 80, 80)
            RARITY_COL = {
                "Commun":    (160, 160, 165),
                "Rare":      (60,  130, 255),
                "Épique":    (155,  60, 255),
                "Légendaire":(240, 175,  20),
            }

            def _gacha_rounded(surf, col, r, radius=10, bw=0, bc=None):
                pygame.draw.rect(surf, col, r, border_radius=radius)
                if bw and bc:
                    pygame.draw.rect(surf, bc, r, bw, border_radius=radius)

            # Layout : 2 colonnes côte à côte
            pad  = 14
            full_w = min(w - 2*pad, 860)
            left_x = w//2 - full_w//2
            col_w  = (full_w - pad) // 2  # largeur de chaque carte coffre

            # ── COFFRE PIÈCES (gauche) ───────────────────────────────────────
            coin_card = pygame.Rect(left_x, content_y + 8, col_w, 310)
            _gacha_rounded(screen, G_CARD, coin_card, radius=14, bw=2, bc=(100, 85, 40))

            # Niveau réel du coffre pièces
            chest_level_coin = sd.get_coin_chest_level(save)
            coin_pulls_in, coin_pulls_needed, _ = sd.get_coin_chest_progress(save)

            # Badge Lv
            lv_badge = pygame.Rect(coin_card.x + 10, coin_card.y + 10, 46, 24)
            _gacha_rounded(screen, G_GOLD, lv_badge, radius=6)
            lv_txt = font_xs.render(f"Lv {chest_level_coin}", True, (30, 20, 0))
            screen.blit(lv_txt, (lv_badge.x + (lv_badge.w - lv_txt.get_width())//2,
                                  lv_badge.y + (lv_badge.h - lv_txt.get_height())//2))

            # Titre
            coin_title = font_med.render("Boîte à objets", True, C_TEXT)
            screen.blit(coin_title, (coin_card.x + 62, coin_card.y + 12))

            # Barre de progression
            prog_bar_rect = pygame.Rect(coin_card.x + 10, coin_card.y + 44, col_w - 20, 14)
            _gacha_rounded(screen, (40, 40, 55), prog_bar_rect, radius=7)
            if chest_level_coin < 10:
                coin_prog = min(1.0, coin_pulls_in / max(1, coin_pulls_needed))
                prog_label_txt = f"{coin_pulls_in}/{coin_pulls_needed}"
            else:
                coin_prog = 1.0
                prog_label_txt = "MAX"
            prog_fill = pygame.Rect(prog_bar_rect.x, prog_bar_rect.y,
                                     int(prog_bar_rect.w * coin_prog), 14)
            _gacha_rounded(screen, G_GOLD, prog_fill, radius=7)
            prog_lbl = font_xs.render(prog_label_txt, True, C_TEXT)
            screen.blit(prog_lbl, (prog_bar_rect.x + (prog_bar_rect.w - prog_lbl.get_width())//2,
                                    prog_bar_rect.y + (prog_bar_rect.h - prog_lbl.get_height())//2))

            # Image coffre (boite_a_objet.png en priorité)
            chest_img_rect = pygame.Rect(coin_card.x + col_w//2 - 60, coin_card.y + 68, 120, 100)
            chest_img = _load_icon_sprite("boite_a_objet.png", 120)
            if chest_img is None:
                chest_img = _load_icon_sprite("coffre_pieces.png", 120)
            if chest_img is None:
                chest_img = _load_icon_sprite("coffre.png", 120)
            if chest_img:
                screen.blit(chest_img, chest_img_rect.topleft)
            else:
                _gacha_rounded(screen, (80, 60, 20), chest_img_rect, radius=12, bw=2, bc=G_GOLD)
                chest_ico = font_big.render("📦", True, G_GOLD)
                screen.blit(chest_ico, (chest_img_rect.centerx - chest_ico.get_width()//2,
                                         chest_img_rect.centery - chest_ico.get_height()//2))

            # Texte pitié — affiche le nombre de tirages restants pour la garantie
            coin_lvl_now = sd.get_coin_chest_level(save)
            epic_thr_c, legend_thr_c = sd.COIN_CHEST_PITY.get(coin_lvl_now, (30, 100))
            cur_pity_epic_c   = save.get("coin_chest_pity_epic", 0)
            cur_pity_legend_c = save.get("coin_chest_pity_legend", 0)
            remaining_epic_c   = max(0, epic_thr_c - cur_pity_epic_c)
            remaining_legend_c = max(0, legend_thr_c - cur_pity_legend_c)

            pe_lbl = font_xs.render(f"{remaining_epic_c} tirages restants avant objet garanti ", True, (220, 80, 80))
            screen.blit(pe_lbl, (coin_card.x + 10, coin_card.y + 178))
            epic_col_lbl = font_xs.render("Épique", True, RARITY_COL["Épique"])
            screen.blit(epic_col_lbl, (coin_card.x + 10 + pe_lbl.get_width(), coin_card.y + 178))

            pl_lbl = font_xs.render(f"{remaining_legend_c} tirages restants avant objet garanti ", True, (220, 80, 80))
            screen.blit(pl_lbl, (coin_card.x + 10, coin_card.y + 200))
            leg_col_lbl = font_xs.render("Légendaire", True, RARITY_COL["Légendaire"])
            screen.blit(leg_col_lbl, (coin_card.x + 10 + pl_lbl.get_width(), coin_card.y + 200))

            # Boutons 1× et 5×
            coin_btn1 = pygame.Rect(coin_card.x + 10, coin_card.y + 230, (col_w - 30)//2, 52)
            coin_btn5 = pygame.Rect(coin_btn1.right + 10, coin_card.y + 230, (col_w - 30)//2, 52)
            can_coin1 = save.get("coins", 0) >= CHEST_COSTS["wood"]
            can_coin5 = save.get("coins", 0) >= CHEST_COSTS["wood"] * 5
            cost_default = CHEST_COSTS["wood"]

            for btn, count_b, can_b, cost_b in [
                (coin_btn1, 1, can_coin1, cost_default),
                (coin_btn5, 5, can_coin5, cost_default * 5),
            ]:
                hov_b = btn.collidepoint(mx, my)
                bc_b  = G_GOLD if can_b else G_BORDER
                bg_b  = (55, 50, 20) if (hov_b and can_b) else (38, 34, 14)
                _gacha_rounded(screen, bg_b, btn, radius=10, bw=2, bc=bc_b)
                count_lbl = font_sm.render(f"{count_b} Achats", True, C_TEXT)
                screen.blit(count_lbl, (btn.x + (btn.w - count_lbl.get_width())//2, btn.y + 6))
                cost_ico = _get_icon("coin", 16)
                cost_lbl = font_xs.render(str(cost_b), True, G_GOLD if can_b else C_RED)
                cw = 16 + 4 + cost_lbl.get_width()
                cx_ = btn.x + (btn.w - cw)//2
                screen.blit(cost_ico, (cx_, btn.y + 30))
                screen.blit(cost_lbl, (cx_ + 20, btn.y + 30))
                if clicked and hov_b and can_b:
                    for _ in range(count_b):
                        ok, result = sd.open_chest(save, "wood")
                        if ok:
                            last_item_obtained = result
                            chest_overlay_item  = result
                            chest_overlay_timer = 240
                            gacha_msg       = f"Obtenu : {result['name']} (+{result['value']} {result['label']})"
                            gacha_msg_timer = 240
                    if not ok:
                        gacha_msg = result; gacha_msg_timer = 120

            # Bouton % taux
            pct_btn_c = pygame.Rect(coin_card.right - 36, coin_card.y + 10, 28, 28)
            hov_pct_c = pct_btn_c.collidepoint(mx, my)
            _gacha_rounded(screen, (50, 50, 70) if hov_pct_c else (35, 35, 52), pct_btn_c, radius=6, bw=1, bc=G_BORDER)
            pct_c_lbl = font_xs.render("%", True, C_TEXT)
            screen.blit(pct_c_lbl, (pct_btn_c.x + (pct_btn_c.w - pct_c_lbl.get_width())//2,
                                     pct_btn_c.y + (pct_btn_c.h - pct_c_lbl.get_height())//2))
            if clicked and hov_pct_c:
                gacha_info_popup = None if gacha_info_popup == "wood" else "wood"

            # ── COFFRE TOURS (droite) ────────────────────────────────────────
            gem_card = pygame.Rect(left_x + col_w + pad, content_y + 8, col_w, 310)
            _gacha_rounded(screen, G_CARD, gem_card, radius=14, bw=2, bc=(100, 50, 160))

            tower_level_val = sd._get_tower_chest_level(save)
            pulls_in, pulls_needed, _ = sd._get_tower_chest_progress(save)
            cost_per_gem = sd.TOWER_CHEST_COSTS.get(tower_level_val, 5)
            pity_e, pity_l = sd.TOWER_CHEST_PITY.get(tower_level_val, (22, 100))

            # Badge Lv
            lv_badge_g = pygame.Rect(gem_card.x + 10, gem_card.y + 10, 38, 24)
            _gacha_rounded(screen, G_GEM, lv_badge_g, radius=6)
            lv_g_txt = font_xs.render(f"Lv {tower_level_val}", True, (240, 220, 255))
            screen.blit(lv_g_txt, (lv_badge_g.x + (lv_badge_g.w - lv_g_txt.get_width())//2,
                                    lv_badge_g.y + (lv_badge_g.h - lv_g_txt.get_height())//2))
            gem_title = font_med.render("Contrat Héros / Tour", True, C_TEXT)
            screen.blit(gem_title, (gem_card.x + 56, gem_card.y + 12))

            # Barre progression coffre tours
            prog_bar_g = pygame.Rect(gem_card.x + 10, gem_card.y + 44, col_w - 20, 14)
            _gacha_rounded(screen, (40, 30, 60), prog_bar_g, radius=7)
            prog_g = min(1.0, pulls_in / max(1, pulls_needed)) if tower_level_val < 10 else 1.0
            prog_fill_g = pygame.Rect(prog_bar_g.x, prog_bar_g.y, int(prog_bar_g.w * prog_g), 14)
            _gacha_rounded(screen, G_GEM, prog_fill_g, radius=7)
            prog_g_lbl = font_xs.render(f"{pulls_in}/{pulls_needed}" if tower_level_val < 10 else "MAX", True, C_TEXT)
            screen.blit(prog_g_lbl, (prog_bar_g.x + (prog_bar_g.w - prog_g_lbl.get_width())//2,
                                      prog_bar_g.y + (prog_bar_g.h - prog_g_lbl.get_height())//2))

            # Image coffre gemmes (contrat.png en priorité)
            chest_img_rect_g = pygame.Rect(gem_card.x + col_w//2 - 50, gem_card.y + 68, 100, 100)
            chest_img_g = _load_icon_sprite("contrat.png", 100)
            if chest_img_g is None:
                chest_img_g = _load_icon_sprite("coffre_tours.png", 100)
            if chest_img_g is None:
                chest_img_g = _load_icon_sprite("coffre_gemmes.png", 100)
            if chest_img_g:
                screen.blit(chest_img_g, chest_img_rect_g.topleft)
            else:
                _gacha_rounded(screen, (50, 20, 80), chest_img_rect_g, radius=12, bw=2, bc=G_GEM)
                q_ico = font_big.render("?", True, G_GEM)
                screen.blit(q_ico, (chest_img_rect_g.centerx - q_ico.get_width()//2,
                                     chest_img_rect_g.centery - q_ico.get_height()//2))

            # Pitié tours — affiche le nombre de tirages restants
            cur_pity_epic_g   = save.get("tower_chest_pity_epic", 0)
            cur_pity_legend_g = save.get("tower_chest_pity_legend", 0)
            remaining_epic_g   = max(0, pity_e - cur_pity_epic_g)
            remaining_legend_g = max(0, pity_l - cur_pity_legend_g)

            pe_g_lbl = font_xs.render(f"{remaining_epic_g} tirages restants avant tour garantie ", True, (220, 80, 80))
            screen.blit(pe_g_lbl, (gem_card.x + 10, gem_card.y + 178))
            epic_g_lbl = font_xs.render("Épique", True, RARITY_COL["Épique"])
            screen.blit(epic_g_lbl, (gem_card.x + 10 + pe_g_lbl.get_width(), gem_card.y + 178))

            pl_g_lbl = font_xs.render(f"{remaining_legend_g} tirages restants avant tour garantie ", True, (220, 80, 80))
            screen.blit(pl_g_lbl, (gem_card.x + 10, gem_card.y + 200))
            leg_g_lbl = font_xs.render("Légendaire", True, RARITY_COL["Légendaire"])
            screen.blit(leg_g_lbl, (gem_card.x + 10 + pl_g_lbl.get_width(), gem_card.y + 200))

            # Boutons 1× et 5×
            gem_btn1 = pygame.Rect(gem_card.x + 10, gem_card.y + 230, (col_w - 30)//2, 52)
            gem_btn5 = pygame.Rect(gem_btn1.right + 10, gem_card.y + 230, (col_w - 30)//2, 52)
            can_gem1 = save.get("gems", 0) >= cost_per_gem
            can_gem5 = save.get("gems", 0) >= cost_per_gem * 5

            for btn_g, cnt_g, can_g, cost_g in [
                (gem_btn1, 1, can_gem1, cost_per_gem),
                (gem_btn5, 5, can_gem5, cost_per_gem * 5),
            ]:
                hov_g  = btn_g.collidepoint(mx, my)
                bc_g   = G_GEM if can_g else G_BORDER
                bg_g   = (45, 20, 70) if (hov_g and can_g) else (28, 14, 48)
                _gacha_rounded(screen, bg_g, btn_g, radius=10, bw=2, bc=bc_g)
                cnt_lbl = font_sm.render(f"{cnt_g} Achats", True, C_TEXT)
                screen.blit(cnt_lbl, (btn_g.x + (btn_g.w - cnt_lbl.get_width())//2, btn_g.y + 6))
                gem_ico = _get_icon("gem", 16)
                cost_g_lbl = font_xs.render(str(cost_g), True, (200, 130, 255) if can_g else C_RED)
                gw = 16 + 4 + cost_g_lbl.get_width()
                gx_ = btn_g.x + (btn_g.w - gw)//2
                screen.blit(gem_ico, (gx_, btn_g.y + 30))
                screen.blit(cost_g_lbl, (gx_ + 20, btn_g.y + 30))
                if clicked and hov_g and can_g:
                    ok_g, res_g = sd.open_tower_chest(save, cnt_g)
                    if ok_g:
                        gacha_tower_results   = res_g
                        gacha_tower_anim      = 300
                        gacha_tower_result_idx = 0
                    else:
                        gacha_msg = res_g; gacha_msg_timer = 120

            # Bouton % taux tours
            pct_btn_g = pygame.Rect(gem_card.right - 36, gem_card.y + 10, 28, 28)
            hov_pct_g = pct_btn_g.collidepoint(mx, my)
            _gacha_rounded(screen, (50, 30, 70) if hov_pct_g else (35, 20, 55), pct_btn_g, radius=6, bw=1, bc=G_BORDER)
            pct_g_lbl = font_xs.render("%", True, C_TEXT)
            screen.blit(pct_g_lbl, (pct_btn_g.x + (pct_btn_g.w - pct_g_lbl.get_width())//2,
                                     pct_btn_g.y + (pct_btn_g.h - pct_g_lbl.get_height())//2))
            if clicked and hov_pct_g:
                gacha_show_rates = not gacha_show_rates

            # ── RÉSULTATS TIRAGE TOURS ────────────────────────────────────────
            if gacha_tower_anim > 0:
                gacha_tower_anim -= 1
                if len(gacha_tower_results) > 1:
                    idx_show = min(len(gacha_tower_results) - 1,
                                   (300 - gacha_tower_anim) // (300 // max(1, len(gacha_tower_results))))
                else:
                    idx_show = 0
                if gacha_tower_results:
                    res = gacha_tower_results[idx_show]
                    rc  = tuple(res["rarity_color"])
                    # Carte plus haute si doublon (jauge + bouton)
                    card_h = 130 if not res["is_new"] and res.get("needed") else 90
                    rcard = pygame.Rect(w//2 - 200, content_y + 322, 400, card_h)
                    _gacha_rounded(screen, (20, 15, 35), rcard, radius=12, bw=2, bc=rc)

                    # Badge nouvelle/doublon
                    badge_txt = "✨ NOUVELLE TOUR !" if res["is_new"] else "🔁 Doublon"
                    badge_col = (100, 255, 150) if res["is_new"] else (180, 150, 255)
                    new_lbl = font_sm.render(badge_txt, True, badge_col)
                    screen.blit(new_lbl, (rcard.x + 14, rcard.y + 8))

                    if len(gacha_tower_results) > 1:
                        nav_lbl = font_xs.render(f"{idx_show+1}/{len(gacha_tower_results)}", True, C_SUBTEXT)
                        screen.blit(nav_lbl, (rcard.right - nav_lbl.get_width() - 10, rcard.y + 8))

                    tower_name = font_med.render(res["label"], True, rc)
                    screen.blit(tower_name, (rcard.x + 14, rcard.y + 32))
                    rar_lbl = font_xs.render(f"{res['rarity']}  |  Niv. {res['level']}", True, rc)
                    screen.blit(rar_lbl, (rcard.x + 14, rcard.y + 58))
                    desc_lbl = font_xs.render(res["desc"], True, C_SUBTEXT)
                    screen.blit(desc_lbl, (rcard.right - desc_lbl.get_width() - 14, rcard.y + 58))

                    # Si doublon : jauge de copies + bouton upgrade manuel
                    if not res["is_new"] and res.get("needed") is not None:
                        copies_now = res.get("copies", 0)
                        needed_up  = res["needed"]
                        can_up     = res.get("can_upgrade", False)

                        # Jauge copies
                        gauge_rect = pygame.Rect(rcard.x + 14, rcard.y + 80, rcard.w - 28, 12)
                        _gacha_rounded(screen, (40, 35, 60), gauge_rect, radius=6)
                        fill_ratio = min(1.0, copies_now / max(1, needed_up))
                        fill_col   = (100, 255, 150) if can_up else (140, 100, 220)
                        fill_w     = int(gauge_rect.w * fill_ratio)
                        if fill_w > 0:
                            _gacha_rounded(screen, fill_col,
                                           pygame.Rect(gauge_rect.x, gauge_rect.y, fill_w, 12), radius=6)
                        gauge_lbl = font_xs.render(f"{copies_now}/{needed_up}", True, C_TEXT)
                        screen.blit(gauge_lbl, (gauge_rect.x + (gauge_rect.w - gauge_lbl.get_width())//2,
                                                 gauge_rect.y + (gauge_rect.h - gauge_lbl.get_height())//2))

                        # Bouton "Niveau supérieur" si prêt
                        if can_up:
                            up_btn = pygame.Rect(rcard.x + 14, rcard.y + 100, rcard.w - 28, 24)
                            hov_up = up_btn.collidepoint(mx, my)
                            _gacha_rounded(screen, (50, 180, 70) if hov_up else (35, 130, 50),
                                           up_btn, radius=8, bw=2, bc=(100, 255, 130))
                            up_lbl = font_xs.render("▲ Niveau supérieur", True, (220, 255, 220))
                            screen.blit(up_lbl, (up_btn.x + (up_btn.w - up_lbl.get_width())//2,
                                                  up_btn.y + (up_btn.h - up_lbl.get_height())//2))
                            if clicked and hov_up:
                                ok_up, _ = sd.upgrade_tower(save, res["tower_id"])
                                if ok_up:
                                    # Mettre à jour le résultat affiché
                                    new_lv = save["towers_level"].get(res["tower_id"], 1)
                                    new_cp = save["towers_copies"].get(res["tower_id"], 0)
                                    new_need = sd.TOWER_UPGRADE_COST[new_lv - 1] if new_lv <= len(sd.TOWER_UPGRADE_COST) else None
                                    res["level"]       = new_lv
                                    res["copies"]      = new_cp
                                    res["needed"]      = new_need
                                    res["can_upgrade"] = (new_need is not None) and (new_cp >= new_need)
                        else:
                            # Indiquer combien il manque
                            missing = needed_up - copies_now
                            miss_lbl = font_xs.render(f"Encore {missing} doublon{'s' if missing > 1 else ''} pour monter de niveau", True, C_SUBTEXT)
                            screen.blit(miss_lbl, (rcard.x + 14, rcard.y + 100))

            # ── MESSAGE COFFRE PIÈCES ──────────────────────────────────────────
            if gacha_msg_timer > 0:
                gacha_msg_timer -= 1
                if last_item_obtained:
                    rc2 = tuple(last_item_obtained["color"])
                    msg_lbl = font_sm.render(gacha_msg, True, rc2)
                else:
                    msg_lbl = font_sm.render(gacha_msg, True, C_RED)
                screen.blit(msg_lbl, (w//2 - msg_lbl.get_width()//2, content_y + 328))
                if last_item_obtained and gacha_msg_timer > 0:
                    _draw_item_card(screen, font_med, font_sm, font_xs,
                                    last_item_obtained,
                                    pygame.Rect(w//2 - 160, content_y + 356, 320, 90))

            # ── POPUP TAUX RARITÉS COFFRE TOURS (tableau visuel tous niveaux) ──
            if gacha_show_rates:
                RARITIES_SHOW = ["Commun", "Rare", "Épique", "Légendaire"]
                ROW_H   = 20   # hauteur d'une ligne de niveau
                BAR_W   = 90   # largeur de la barre de pourcentage
                PAD     = 10
                COL_LV  = 28   # colonne "Lv X"
                COL_GAP = 6
                COL_RAR = 52   # largeur colonne rareté (label)
                # Largeur totale : pad + Lv + gap + (label+bar)*4 + pad
                pr_w = PAD*2 + COL_LV + COL_GAP + len(RARITIES_SHOW) * (COL_RAR + BAR_W + COL_GAP)
                pr_w = min(pr_w, w - 20)
                # Hauteur : titre + en-tête + 10 lignes + pitié
                HEADER_H = 28
                PITY_H   = 40
                pr_h = PAD*2 + HEADER_H + 10 * (ROW_H + 2) + PITY_H
                pr_x = max(10, min(pct_btn_g.right - pr_w, w - pr_w - 10))
                pr_y = max(content_y + 4, pct_btn_g.top - pr_h - 6)
                pr_rect = pygame.Rect(pr_x, pr_y, pr_w, pr_h)

                # Fond
                _gacha_rounded(screen, (14, 10, 28), pr_rect, radius=12, bw=2, bc=G_GEM)

                # Titre
                t_lbl = font_sm.render("Taux par niveau de coffre", True, (210, 170, 255))
                screen.blit(t_lbl, (pr_x + (pr_w - t_lbl.get_width())//2, pr_y + PAD))

                # En-tête colonnes
                hdr_y = pr_y + PAD + HEADER_H - 4
                lv_hdr = font_xs.render("Lv", True, C_SUBTEXT)
                screen.blit(lv_hdr, (pr_x + PAD, hdr_y))
                col_xs_starts = []
                cx_hdr = pr_x + PAD + COL_LV + COL_GAP
                for rar in RARITIES_SHOW:
                    rc_h = RARITY_COL[rar]
                    rar_hdr = font_xs.render(rar[:4], True, rc_h)
                    screen.blit(rar_hdr, (cx_hdr, hdr_y))
                    col_xs_starts.append(cx_hdr)
                    cx_hdr += COL_RAR + BAR_W + COL_GAP

                # Ligne séparatrice
                sep_y = hdr_y + 18
                pygame.draw.line(screen, (50, 40, 80), (pr_x + 6, sep_y), (pr_x + pr_w - 6, sep_y))

                # 10 lignes de niveaux
                for lv in range(1, 11):
                    row_y = sep_y + 2 + (lv - 1) * (ROW_H + 2)
                    # Surligner le niveau actuel
                    if lv == tower_level_val:
                        hl = pygame.Rect(pr_x + 4, row_y, pr_w - 8, ROW_H)
                        _gacha_rounded(screen, (40, 28, 70), hl, radius=4, bw=1, bc=(130, 80, 210))

                    # Numéro de niveau
                    lv_col = (255, 215, 0) if lv == tower_level_val else C_SUBTEXT
                    lv_t = font_xs.render(f"{'▶' if lv == tower_level_val else ' '}{lv}", True, lv_col)
                    screen.blit(lv_t, (pr_x + PAD, row_y + 2))

                    weights_lv = sd.TOWER_CHEST_WEIGHTS_BY_LEVEL[lv]
                    total_lv   = sum(weights_lv.values()) or 1

                    for ri, rar in enumerate(RARITIES_SHOW):
                        pct_val = weights_lv.get(rar, 0) / total_lv * 100
                        cx_r    = col_xs_starts[ri]
                        rc_r    = RARITY_COL[rar]

                        # Barre de progression
                        bar_bg = pygame.Rect(cx_r, row_y + 5, BAR_W, 8)
                        _gacha_rounded(screen, (30, 25, 45), bar_bg, radius=4)
                        fill_pix = int(BAR_W * pct_val / 100)
                        if fill_pix > 0:
                            _gacha_rounded(screen, rc_r,
                                           pygame.Rect(bar_bg.x, bar_bg.y, fill_pix, 8), radius=4)
                        # Pourcentage à droite de la barre
                        pct_str  = f"{pct_val:.0f}%" if pct_val > 0 else "—"
                        pct_surf = font_xs.render(pct_str, True, rc_r if pct_val > 0 else (50, 50, 60))
                        screen.blit(pct_surf, (cx_r + BAR_W + 2, row_y + 2))

                # Pitié du niveau actuel
                pity_y = sep_y + 2 + 10 * (ROW_H + 2) + 4
                pygame.draw.line(screen, (50, 40, 80), (pr_x + 6, pity_y), (pr_x + pr_w - 6, pity_y))
                pe_s = font_xs.render(f"Pitié Épique Lv{tower_level_val} : {pity_e} pulls garantis", True, RARITY_COL["Épique"])
                pl_s = font_xs.render(f"Pitié Légend. Lv{tower_level_val} : {pity_l} pulls garantis", True, RARITY_COL["Légendaire"])
                screen.blit(pe_s, (pr_x + PAD, pity_y + 4))
                screen.blit(pl_s, (pr_x + PAD, pity_y + 20))

                if clicked and not pr_rect.collidepoint(mx, my):
                    gacha_show_rates = False

            # ── POPUP TAUX COFFRE PIÈCES (tableau tous niveaux) ──────────────
            if gacha_info_popup == "wood":
                RARITIES_COIN = ["Commun", "Rare", "Épique", "Légendaire", "Mythique"]
                RARITY_COL_COIN = {
                    "Commun":    (160, 160, 165),
                    "Rare":      (60,  130, 255),
                    "Épique":    (155,  60, 255),
                    "Légendaire":(240, 175,  20),
                    "Mythique":  (255,  60, 220),
                }
                ROW_HC  = 20
                BAR_WC  = 70
                PAD_C   = 10
                COL_LVC = 28
                COL_GAPC = 4
                COL_RARC = 44
                pi_w = PAD_C*2 + COL_LVC + COL_GAPC + len(RARITIES_COIN) * (COL_RARC + BAR_WC + COL_GAPC)
                pi_w = min(pi_w, w - 20)
                HEADER_HC = 28
                pi_h = PAD_C*2 + HEADER_HC + 10 * (ROW_HC + 2)
                pi_x = max(10, min(pct_btn_c.right - pi_w, w - pi_w - 10))
                pi_y = max(content_y + 4, pct_btn_c.top - pi_h - 6)
                pi_rect = pygame.Rect(pi_x, pi_y, pi_w, pi_h)

                _gacha_rounded(screen, (20, 17, 8), pi_rect, radius=12, bw=2, bc=G_GOLD)

                t_lbl_c = font_sm.render("Taux par niveau de coffre", True, G_GOLD)
                screen.blit(t_lbl_c, (pi_x + (pi_w - t_lbl_c.get_width())//2, pi_y + PAD_C))

                hdr_yc = pi_y + PAD_C + HEADER_HC - 4
                lv_hdr_c = font_xs.render("Lv", True, C_SUBTEXT)
                screen.blit(lv_hdr_c, (pi_x + PAD_C, hdr_yc))
                col_xs_c = []
                cx_hdr_c = pi_x + PAD_C + COL_LVC + COL_GAPC
                for rar_c2 in RARITIES_COIN:
                    rc_h2 = RARITY_COL_COIN[rar_c2]
                    rar_hdr2 = font_xs.render(rar_c2[:4], True, rc_h2)
                    screen.blit(rar_hdr2, (cx_hdr_c, hdr_yc))
                    col_xs_c.append(cx_hdr_c)
                    cx_hdr_c += COL_RARC + BAR_WC + COL_GAPC

                sep_yc = hdr_yc + 18
                pygame.draw.line(screen, (80, 65, 20), (pi_x + 6, sep_yc), (pi_x + pi_w - 6, sep_yc))

                for lv_c2 in range(1, 11):
                    row_yc = sep_yc + 2 + (lv_c2 - 1) * (ROW_HC + 2)
                    if lv_c2 == chest_level_coin:
                        hl_c = pygame.Rect(pi_x + 4, row_yc, pi_w - 8, ROW_HC)
                        _gacha_rounded(screen, (55, 42, 10), hl_c, radius=4, bw=1, bc=G_GOLD)

                    lv_col_c = G_GOLD if lv_c2 == chest_level_coin else C_SUBTEXT
                    lv_t_c = font_xs.render(f"{'▶' if lv_c2 == chest_level_coin else ' '}{lv_c2}", True, lv_col_c)
                    screen.blit(lv_t_c, (pi_x + PAD_C, row_yc + 2))

                    weights_lv_c = sd.COIN_CHEST_WEIGHTS_BY_LEVEL[lv_c2]
                    total_lv_c   = sum(weights_lv_c.values()) or 1

                    for ri_c, rar_c3 in enumerate(RARITIES_COIN):
                        pct_c3  = weights_lv_c.get(rar_c3, 0) / total_lv_c * 100
                        cx_rc   = col_xs_c[ri_c]
                        rc_r3   = RARITY_COL_COIN[rar_c3]

                        bar_bg_c = pygame.Rect(cx_rc, row_yc + 5, BAR_WC, 8)
                        _gacha_rounded(screen, (35, 28, 10), bar_bg_c, radius=4)
                        fill_pc = int(BAR_WC * pct_c3 / 100)
                        if fill_pc > 0:
                            _gacha_rounded(screen, rc_r3,
                                           pygame.Rect(bar_bg_c.x, bar_bg_c.y, fill_pc, 8), radius=4)
                        pct_str_c  = f"{pct_c3:.0f}%" if pct_c3 > 0 else "—"
                        pct_surf_c = font_xs.render(pct_str_c, True, rc_r3 if pct_c3 > 0 else (50, 50, 60))
                        screen.blit(pct_surf_c, (cx_rc + BAR_WC + 2, row_yc + 2))

                if clicked and not pi_rect.collidepoint(mx, my) and not pct_btn_c.collidepoint(mx, my):
                    gacha_info_popup = None

            # ── COLLECTION TOURS (en bas) ─────────────────────────────────────
            coll_y  = content_y + 332 if (gacha_tower_anim <= 0 and gacha_msg_timer <= 0) else content_y + 438
            coll_h  = h - coll_y - 12
            if coll_h > 60:
                coll_panel = pygame.Rect(left_x, coll_y, full_w, coll_h)
                _gacha_rounded(screen, G_CARD, coll_panel, radius=12, bw=1, bc=G_BORDER)
                coll_title = font_sm.render("Ma Collection de Tours", True, C_TEXT)
                screen.blit(coll_title, (coll_panel.x + 14, coll_panel.y + 10))

                towers_unlocked = save.get("towers_unlocked", {})
                towers_level    = save.get("towers_level", {})
                towers_copies   = save.get("towers_copies", {})

                cell_size = 80
                cell_gap  = 8
                cells_per_row = max(1, (full_w - 20) // (cell_size + cell_gap))
                all_tower_ids = list(sd.TOWER_POOL.keys())

                clip_area = pygame.Rect(coll_panel.x + 6, coll_panel.y + 36,
                                         coll_panel.w - 12, coll_panel.h - 42)
                old_clip = screen.get_clip()
                screen.set_clip(clip_area)

                # Scroll avec molette
                if scroll_dy and coll_panel.collidepoint(mx, my):
                    gacha_tower_scroll = max(0, gacha_tower_scroll - scroll_dy * (cell_size + cell_gap))

                for ti, tid in enumerate(all_tower_ids):
                    row_i = ti // cells_per_row
                    col_i = ti % cells_per_row
                    cx_c  = clip_area.x + col_i * (cell_size + cell_gap)
                    cy_c  = clip_area.y + row_i * (cell_size + cell_gap) - gacha_tower_scroll
                    if cy_c + cell_size < clip_area.y or cy_c > clip_area.bottom:
                        continue
                    cell_r = pygame.Rect(cx_c, cy_c, cell_size, cell_size)
                    tinfo  = sd.TOWER_POOL[tid]
                    is_unl = towers_unlocked.get(tid, False)
                    rar_c  = RARITY_COL.get(tinfo["rarity"], C_SUBTEXT) if is_unl else (40, 40, 50)
                    bg_cc  = G_CARD2 if is_unl else (22, 22, 32)
                    _gacha_rounded(screen, bg_cc, cell_r, radius=8, bw=2, bc=rar_c)

                    if is_unl:
                        # Nom tour
                        tn_lbl = font_xs.render(tinfo["label"][:9], True, rar_c)
                        screen.blit(tn_lbl, (cell_r.x + (cell_r.w - tn_lbl.get_width())//2, cell_r.y + 5))
                        # Niveau
                        lv_c  = towers_level.get(tid, 1)
                        lv_lbl = font_xs.render(f"Niv.{lv_c}", True, C_TEXT)
                        screen.blit(lv_lbl, (cell_r.x + (cell_r.w - lv_lbl.get_width())//2, cell_r.y + 22))
                        # Badge rareté (petit cercle coin haut-gauche)
                        pygame.draw.circle(screen, rar_c, (cell_r.x + 6, cell_r.y + 6), 4)

                        cur_lv     = towers_level.get(tid, 1)
                        copies_now = towers_copies.get(tid, 0)
                        if cur_lv <= len(sd.TOWER_UPGRADE_COST):
                            needed_up = sd.TOWER_UPGRADE_COST[cur_lv - 1]
                            can_up    = copies_now >= needed_up

                            # Jauge copies (barre fine)
                            gauge = pygame.Rect(cell_r.x + 6, cell_r.y + 40, cell_r.w - 12, 8)
                            _gacha_rounded(screen, (40, 35, 60), gauge, radius=4)
                            fill_ratio = min(1.0, copies_now / max(1, needed_up))
                            fill_col_g = (100, 255, 140) if can_up else (130, 90, 210)
                            fw = max(0, int(gauge.w * fill_ratio))
                            if fw > 0:
                                _gacha_rounded(screen, fill_col_g,
                                               pygame.Rect(gauge.x, gauge.y, fw, 8), radius=4)
                            # Texte copies centré sur la barre
                            cop_lbl = font_xs.render(f"{copies_now}/{needed_up}", True, C_TEXT)
                            screen.blit(cop_lbl, (gauge.x + (gauge.w - cop_lbl.get_width())//2,
                                                   gauge.bottom + 2))

                            # Bouton "▲ Niv. sup." si prêt
                            if can_up:
                                up_btn = pygame.Rect(cell_r.x + 5, cell_r.y + 62, cell_r.w - 10, 14)
                                hov_up_c = up_btn.collidepoint(mx, my)
                                _gacha_rounded(screen,
                                               (60, 210, 85) if hov_up_c else (40, 160, 60),
                                               up_btn, radius=4, bw=1, bc=(100, 255, 130))
                                up_lbl = font_xs.render("▲ Niv. sup.", True, (10, 10, 10) if hov_up_c else (200, 255, 200))
                                screen.blit(up_lbl, (up_btn.x + (up_btn.w - up_lbl.get_width())//2,
                                                      up_btn.y + (up_btn.h - up_lbl.get_height())//2))
                                if clicked and hov_up_c:
                                    sd.upgrade_tower(save, tid)
                        else:
                            # Niveau max
                            max_lbl = font_xs.render("✦ MAX", True, G_GOLD)
                            screen.blit(max_lbl, (cell_r.x + (cell_r.w - max_lbl.get_width())//2, cell_r.y + 44))
                    else:
                        # Verrou
                        lock_lbl = font_med.render("🔒", True, (60, 60, 70))
                        screen.blit(lock_lbl, (cell_r.x + (cell_r.w - lock_lbl.get_width())//2,
                                                cell_r.y + (cell_r.h - lock_lbl.get_height())//2))
                        rar_sm = font_xs.render(tinfo["rarity"][0], True, RARITY_COL.get(tinfo["rarity"], C_SUBTEXT))
                        screen.blit(rar_sm, (cell_r.x + 4, cell_r.y + 4))

                screen.set_clip(old_clip)

            # ── OVERLAY PLEIN ÉCRAN — résultat de l'ouverture du coffre ─────
            if chest_overlay_timer > 0:
                chest_overlay_timer -= 1
                _ov_total = 240
                # Alpha : fondu entrant 20f, plein, fondu sortant 40f
                if chest_overlay_timer > _ov_total - 20:
                    _ov_alpha = int(200 * ((_ov_total - chest_overlay_timer) / 20))
                elif chest_overlay_timer < 40:
                    _ov_alpha = int(200 * (chest_overlay_timer / 40))
                else:
                    _ov_alpha = 200

                # Fond grisé sur tout l'écran
                _ov_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                _ov_surf.fill((0, 0, 0, _ov_alpha))
                screen.blit(_ov_surf, (0, 0))

                if chest_overlay_item:
                    _it = chest_overlay_item
                    _rar = _it.get("rarity", "Commun")
                    _rar_col = tuple(RARITY_COL.get(_rar, (160, 160, 160)))
                    _card_w, _card_h = 380, 220
                    _cx = w // 2 - _card_w // 2
                    _cy = h // 2 - _card_h // 2

                    _card = pygame.Surface((_card_w, _card_h), pygame.SRCALPHA)
                    _card.fill((18, 14, 32, min(240, _ov_alpha + 30)))
                    _card_rect = pygame.Rect(0, 0, _card_w, _card_h)
                    pygame.draw.rect(_card, (*_rar_col, min(255, _ov_alpha + 55)),
                                     _card_rect, 3, border_radius=18)
                    screen.blit(_card, (_cx, _cy))

                    # Rareté badge
                    _rbadge = font_sm.render(f"✦ {_rar} ✦", True, _rar_col)
                    screen.blit(_rbadge, (w // 2 - _rbadge.get_width() // 2, _cy + 16))

                    # Nom de l'objet
                    _name_lbl = font_med.render(_it.get("name", "Objet"), True, (255, 255, 255))
                    screen.blit(_name_lbl, (w // 2 - _name_lbl.get_width() // 2, _cy + 52))

                    # Stat
                    _stat_lbl = font_sm.render(
                        f"+{_it['value']} {_it['label']}", True, _rar_col)
                    screen.blit(_stat_lbl, (w // 2 - _stat_lbl.get_width() // 2, _cy + 92))

                    # Icône équipement
                    _eq_icon = _get_equipment_icon_surface(_it) if hasattr(pygame, '_eq_icon_fn') else None
                    try:
                        from menu_screen import _get_equipment_icon_surface as _eif
                        _eq_icon = _eif(_it)
                    except Exception:
                        _eq_icon = None
                    if _eq_icon and _eq_icon is not False:
                        _fitted = _fit_surface(_eq_icon, 80, 80)
                        if _fitted:
                            screen.blit(_fitted, (w // 2 - _fitted.get_width() // 2, _cy + 120))

                    # Instruction
                    _hint = font_xs.render("Cliquez pour continuer", True, C_SUBTEXT)
                    screen.blit(_hint, (w // 2 - _hint.get_width() // 2, _cy + _card_h - 30))

                # Fermer l'overlay au clic
                if clicked:
                    chest_overlay_timer = 0
                    chest_overlay_item  = None

        # ────────────────────────────────────────────────────────────────────
        # TAB 2 : ÉQUIPEMENT
        # ────────────────────────────────────────────────────────────────────
        elif active_tab == 2:
            categories = ["cape", "veste", "bottes", "arme", "tour"]
            category_labels = ["Cape", "Veste", "Bottes", "Arme", "Tour"]
            category_slot = categories[selected_equip_category]
            slot_titles = {"cape": "Cape", "veste": "Veste", "bottes": "Bottes", "arme": "Arme", "tour": "Tour"}

            left_w = int((w - 40) * 0.55)
            right_w = (w - 40) - left_w - 10

            left_panel = pygame.Rect(20, content_y + 10, left_w, content_h - 10)
            _draw_rounded_rect(screen, C_PANEL, left_panel, radius=12)
            lp_title = font_med.render("Personnalisez votre soldat", True, C_ACCENT)
            screen.blit(lp_title, (left_panel.x + (left_panel.w - lp_title.get_width()) // 2,
                                    left_panel.y + 12))

            center_x = left_panel.x + left_panel.w // 2
            head_y = left_panel.y + 90
            body_y = head_y + 60

            preview_area = pygame.Rect(left_panel.x + 20, left_panel.y + 56, left_panel.w - 40, left_panel.h - 128)
            background_sprite = _get_equipment_background_sprite()
            if background_sprite:
                bg_scaled = pygame.transform.smoothscale(background_sprite, (preview_area.w, preview_area.h))
                screen.blit(bg_scaled, preview_area.topleft)
                overlay = pygame.Surface((preview_area.w, preview_area.h), pygame.SRCALPHA)
                overlay.fill((12, 16, 24, 82))
                screen.blit(overlay, preview_area.topleft)
                pygame.draw.rect(screen, C_BTN_BOR, preview_area, 2, border_radius=18)
            else:
                _draw_rounded_rect(screen, C_PANEL2, preview_area, radius=18, border=2, border_color=C_BTN_BOR)

            character_sprite = _get_equipment_character_sprite()
            if character_sprite:
                max_sprite_h = min(preview_area.h - 70, 420)
                scale = max_sprite_h / character_sprite.get_height()
                sprite_w = max(1, int(character_sprite.get_width() * scale))
                sprite_h = max(1, int(character_sprite.get_height() * scale))
                scaled_sprite = pygame.transform.smoothscale(character_sprite, (sprite_w, sprite_h))
                sprite_x = center_x - sprite_w // 2
                sprite_y = preview_area.bottom - sprite_h - 12
                screen.blit(scaled_sprite, (sprite_x, sprite_y))
            else:
                pygame.draw.circle(screen, (120, 120, 120), (center_x, head_y), 34)
                body_rect = pygame.Rect(center_x - 36, body_y, 72, 120)
                pygame.draw.rect(screen, (140, 140, 140), body_rect, border_radius=24)
                pygame.draw.line(screen, (140, 140, 140), (center_x, body_y + 45), (center_x - 45, body_y + 90), 10)
                pygame.draw.line(screen, (140, 140, 140), (center_x, body_y + 45), (center_x + 45, body_y + 90), 10)
                pygame.draw.line(screen, (140, 140, 140), (center_x - 20, body_y + 115), (center_x - 20, body_y + 170), 10)
                pygame.draw.line(screen, (140, 140, 140), (center_x + 20, body_y + 115), (center_x + 20, body_y + 170), 10)

            slot_boxes = {
                "cape": pygame.Rect(preview_area.right - 112, preview_area.y + 24, 92, 92),
                "veste": pygame.Rect(preview_area.right - 112, preview_area.y + 142, 92, 92),
                "bottes": pygame.Rect(preview_area.right - 112, preview_area.y + 260, 92, 92),
                "arme": pygame.Rect(preview_area.x + 20, preview_area.y + preview_area.h // 2 - 46, 92, 92),
                "tour": pygame.Rect(center_x - 72, preview_area.bottom - 72, 144, 54),
            }

            equip_ref = save["equipped"]
            inv_items = save["inventory_equipment"]
            drag_item_data = None
            if dragging_item is not None and 0 <= dragging_item < len(inv_items):
                drag_item_data = inv_items[dragging_item]

            for slot_key, rect in slot_boxes.items():
                equipped_idx = equip_ref.get(slot_key)
                equipped_item = inv_items[equipped_idx] if equipped_idx is not None and 0 <= equipped_idx < len(inv_items) else None
                is_filled = equipped_item is not None
                hovered = rect.collidepoint(mx, my)
                valid_drop = drag_item_data is not None and drag_item_data["slot"] == slot_key
                if hovered and drag_item_data is not None:
                    border_color = C_GREEN if valid_drop else C_RED
                elif is_filled:
                    border_color = C_GREEN
                else:
                    border_color = C_BTN_BOR
                if slot_key == "tour":
                    if equipped_item:
                        _draw_equipment_icon(screen, equipped_item, rect, show_label=False)
                        pygame.draw.rect(screen, border_color, rect, 2, border_radius=18)
                    else:
                        _draw_rounded_rect(screen, C_PANEL2, rect, radius=18, border=2, border_color=border_color)
                        title_lbl = font_xs.render("Boost tour", True, C_ACCENT2)
                        screen.blit(title_lbl, (rect.centerx - title_lbl.get_width() // 2, rect.y + 18))
                else:
                    if equipped_item:
                        _draw_equipment_icon(screen, equipped_item, rect, show_label=False)
                        pygame.draw.rect(screen, border_color, rect, 3, border_radius=18)
                    else:
                        _draw_rounded_rect(screen, C_PANEL2, rect, radius=18, border=3, border_color=border_color)
                        title_lbl = font_xs.render(slot_titles[slot_key], True, C_ACCENT2)
                        screen.blit(title_lbl, (rect.centerx - title_lbl.get_width() // 2, rect.y + 36))
                if clicked and rect.collidepoint(mx, my) and is_filled:
                    save["equipped"][slot_key] = None
                    sd.save(save)

            hint = font_xs.render("Glissez un équipement vers le slot au bout de la flèche ou cliquez pour déséquiper.", True, C_SUBTEXT)
            screen.blit(hint, (left_panel.x + 16, left_panel.y + left_panel.h - 34))

            right_panel = pygame.Rect(20 + left_w + 10, content_y + 10, right_w, content_h - 10)
            _draw_rounded_rect(screen, C_PANEL, right_panel, radius=12)
            rp_title = font_med.render("Loadout et équipement", True, C_TEXT)
            screen.blit(rp_title, (right_panel.x + 14, right_panel.y + 12))

            loadout_area = pygame.Rect(right_panel.x + 10, right_panel.y + 50, right_panel.w - 20, 200)
            _draw_rounded_rect(screen, C_PANEL2, loadout_area, radius=12)
            lo_title = font_sm.render("Loadout de tours", True, C_TEXT)
            screen.blit(lo_title, (loadout_area.x + 12, loadout_area.y + 12))

            tower_loadout = save.get("tower_loadout")
            if not isinstance(tower_loadout, list):
                tower_loadout = list(tower_loadout or [])
            # Seules les tours débloquées sont disponibles
            towers_unlocked_eq = save.get("towers_unlocked", {t: True for t in ["small", "big", "trap"]})
            unlocked_tower_types = [t for t in ALL_TOWER_TYPES if towers_unlocked_eq.get(t, False)]
            if not unlocked_tower_types:
                unlocked_tower_types = ["small", "big", "trap"]
            cleaned_loadout = []
            for tower_type in tower_loadout:
                if tower_type in unlocked_tower_types and tower_type not in cleaned_loadout:
                    cleaned_loadout.append(tower_type)
            for tower_type in unlocked_tower_types:
                if len(cleaned_loadout) >= TOWER_SLOT_COUNT:
                    break
                if tower_type not in cleaned_loadout:
                    cleaned_loadout.append(tower_type)
            tower_loadout = cleaned_loadout[:TOWER_SLOT_COUNT]
            # Garantir exactement TOWER_SLOT_COUNT éléments (None = slot vide)
            while len(tower_loadout) < TOWER_SLOT_COUNT:
                tower_loadout.append(None)
            if save.get("tower_loadout") != tower_loadout:
                save["tower_loadout"] = tower_loadout
                sd.save(save)

            slot_width = (loadout_area.w - 28) // TOWER_SLOT_COUNT
            loadout_slot_rects = []
            for i in range(TOWER_SLOT_COUNT):
                slot_rect = pygame.Rect(
                    loadout_area.x + 14 + i * slot_width,
                    loadout_area.y + 42,
                    slot_width - 8,
                    38,
                )
                loadout_slot_rects.append(slot_rect)
                is_selected = (i == selected_loadout_slot)
                _draw_rounded_rect(screen, C_BTN_HOV if is_selected else C_BTN, slot_rect, radius=10,
                                   border=2, border_color=C_ACCENT2 if is_selected else C_BTN_BOR)
                slot_val = tower_loadout[i] if i < len(tower_loadout) else None
                if slot_val:
                    tower_label = ITEM_LABELS.get(slot_val, slot_val)
                    lbl = font_xs.render(tower_label, True, C_TEXT)
                else:
                    lbl = font_xs.render("— vide —", True, C_SUBTEXT)
                screen.blit(lbl, (slot_rect.x + (slot_rect.w - lbl.get_width()) // 2,
                                  slot_rect.y + (slot_rect.h - lbl.get_height()) // 2))
                if clicked and slot_rect.collidepoint(mx, my):
                    selected_loadout_slot = i

            grid_top = loadout_area.y + 92
            cols = 5
            cell_w = (loadout_area.w - 14 - cols * 10) // cols
            cell_h = 28
            for ti, tower_type in enumerate(ALL_TOWER_TYPES):
                row = ti // cols
                col = ti % cols
                cell = pygame.Rect(
                    loadout_area.x + 10 + col * (cell_w + 10),
                    grid_top + row * (cell_h + 8),
                    cell_w,
                    cell_h,
                )
                is_unlocked_lt = towers_unlocked_eq.get(tower_type, False)
                assigned = tower_type in tower_loadout
                cur_slot_val = tower_loadout[selected_loadout_slot] if selected_loadout_slot < len(tower_loadout) else None
                is_selected = tower_type == cur_slot_val
                assigned_elsewhere = assigned and not is_selected
                if not is_unlocked_lt:
                    cell_color = (22, 22, 30)
                    bdr_col = (45, 45, 55)
                elif is_selected:
                    cell_color = C_BTN_HOV
                    bdr_col = C_ACCENT2
                elif assigned_elsewhere:
                    cell_color = (70, 70, 78)
                    bdr_col = C_BTN_BOR
                else:
                    cell_color = C_BTN
                    bdr_col = C_BTN_BOR
                _draw_rounded_rect(screen, cell_color, cell, radius=8, border=2, border_color=bdr_col)
                tlabel = ITEM_LABELS.get(tower_type, tower_type)
                if not is_unlocked_lt:
                    # Tour verrouillée : afficher le nom grisé + cadenas
                    lock_lbl = font_xs.render(f"🔒 {tlabel[:6]}", True, (55, 55, 65))
                    screen.blit(lock_lbl, (cell.x + (cell.w - lock_lbl.get_width()) // 2,
                                           cell.y + (cell.h - lock_lbl.get_height()) // 2))
                else:
                    text = font_xs.render(tlabel, True, C_SUBTEXT if assigned_elsewhere else C_TEXT)
                    screen.blit(text, (cell.x + (cell.w - text.get_width()) // 2,
                                       cell.y + (cell.h - text.get_height()) // 2))
                if clicked and cell.collidepoint(mx, my) and not assigned_elsewhere and is_unlocked_lt:
                    tower_loadout[selected_loadout_slot] = tower_type
                    save["tower_loadout"] = tower_loadout
                    sd.save(save)

            equip_panel = pygame.Rect(right_panel.x + 10, loadout_area.y + loadout_area.h + 14,
                                      right_panel.w - 20, right_panel.h - loadout_area.h - 28)
            _draw_rounded_rect(screen, C_PANEL2, equip_panel, radius=12)
            eq_title = font_sm.render("Équipement disponible", True, C_TEXT)
            screen.blit(eq_title, (equip_panel.x + 12, equip_panel.y + 12))

            tab_w = (equip_panel.w - 20) // len(category_labels)
            tab_y = equip_panel.y + 46
            for i, label in enumerate(category_labels):
                tab_rect = pygame.Rect(equip_panel.x + 10 + i * tab_w, tab_y, tab_w, 34)
                selected = (i == selected_equip_category)
                _draw_rounded_rect(screen, C_BTN_HOV if selected else C_BTN, tab_rect,
                                   radius=8, border=2,
                                   border_color=C_ACCENT2 if selected else C_BTN_BOR)
                txt = font_sm.render(label, True, C_TEXT)
                screen.blit(txt, (tab_rect.x + (tab_rect.w - txt.get_width()) // 2,
                                  tab_rect.y + (tab_rect.h - txt.get_height()) // 2))
                if clicked and tab_rect.collidepoint(mx, my):
                    selected_equip_category = i
                    selected_inv_idx = None

            item_area = pygame.Rect(equip_panel.x + 10, tab_y + 46,
                                     equip_panel.w - 20, equip_panel.h - 62)
            _draw_rounded_rect(screen, C_PANEL, item_area, radius=10)
            item_hint = font_xs.render("Cliquez sur une ligne pour commencer à glisser", True, C_SUBTEXT)
            screen.blit(item_hint, (item_area.x + 12, item_area.y + 12))

            # Tri par rareté décroissante (Mythique > Légendaire > Épique > Rare > Commun)
            RARITY_ORDER = {"Mythique": 0, "Légendaire": 1, "Épique": 2, "Rare": 3, "Commun": 4}
            category_items = sorted(
                [(idx, item) for idx, item in enumerate(inv_items) if item["slot"] == category_slot],
                key=lambda x: RARITY_ORDER.get(x[1].get("rarity", "Commun"), 5)
            )

            if not category_items:
                none_lbl = font_sm.render(f"Aucun {category_labels[selected_equip_category].lower()} trouvé.", True, C_SUBTEXT)
                screen.blit(none_lbl, (item_area.x + 16, item_area.y + 40))
            else:
                row_h   = 64
                row_gap = 8
                scroll_area = pygame.Rect(item_area.x + 4, item_area.y + 38,
                                          item_area.w - 8, item_area.h - 42)
                # Scroll molette
                if scroll_dy and item_area.collidepoint(mx, my):
                    equip_scroll_by_cat[selected_equip_category] = max(
                        0, equip_scroll_by_cat[selected_equip_category] - scroll_dy * (row_h + row_gap)
                    )
                equip_scroll = equip_scroll_by_cat[selected_equip_category]
                total_content_h = len(category_items) * (row_h + row_gap)
                max_scroll = max(0, total_content_h - scroll_area.h)
                equip_scroll_by_cat[selected_equip_category] = min(equip_scroll, max_scroll)
                equip_scroll = equip_scroll_by_cat[selected_equip_category]

                # Scrollbar visuelle
                if total_content_h > scroll_area.h:
                    sb_w    = 4
                    sb_x    = scroll_area.right - sb_w - 2
                    sb_h    = max(20, int(scroll_area.h * scroll_area.h / total_content_h))
                    sb_y    = scroll_area.y + int(equip_scroll / total_content_h * scroll_area.h)
                    pygame.draw.rect(screen, (50, 55, 75),
                                     pygame.Rect(sb_x, scroll_area.y, sb_w, scroll_area.h), border_radius=2)
                    pygame.draw.rect(screen, C_BTN_BOR,
                                     pygame.Rect(sb_x, sb_y, sb_w, sb_h), border_radius=2)

                old_clip_eq = screen.get_clip()
                screen.set_clip(scroll_area)

                for li, (item_idx, item) in enumerate(category_items):
                    row_y = scroll_area.y + li * (row_h + row_gap) - equip_scroll
                    if row_y + row_h < scroll_area.y or row_y > scroll_area.bottom:
                        continue
                    row = pygame.Rect(scroll_area.x + 4, row_y, scroll_area.w - 12, row_h)
                    is_sel = (selected_inv_idx == li)
                    _draw_rounded_rect(screen, C_PANEL if is_sel else C_BTN, row,
                                       radius=8, border=2,
                                       border_color=C_ACCENT2 if is_sel else C_BTN_BOR)

                    icon_rect = pygame.Rect(row.x + 8, row.y + 8, 48, 48)
                    _draw_equipment_icon(screen, item, icon_rect, show_label=False)
                    name_lbl = font_sm.render(_get_equipment_name(item), True, tuple(item["color"]))
                    screen.blit(name_lbl, (row.x + 66, row.y + 10))
                    stat_lbl = font_xs.render(f"+{item['value']} {item['label']}  |  {item['rarity']}", True, C_SUBTEXT)
                    screen.blit(stat_lbl, (row.x + 66, row.y + 34))

                    eq_btn = pygame.Rect(row.right - 90, row.y + 16, 76, 32)
                    already = save["equipped"].get(category_slot) == item_idx
                    btn_color = C_BTN_HOV if eq_btn.collidepoint(mx, my) and not already else C_BTN
                    _draw_rounded_rect(screen, btn_color, eq_btn, radius=8, border=1, border_color=C_ACCENT2)
                    btn_lbl = font_xs.render("Équipé" if already else "Équiper", True, C_TEXT)
                    screen.blit(btn_lbl, (eq_btn.x + (eq_btn.w - btn_lbl.get_width()) // 2,
                                           eq_btn.y + (eq_btn.h - btn_lbl.get_height()) // 2))

                    # Bouton Vendre
                    sell_btn = pygame.Rect(row.right - 174, row.y + 16, 76, 32)
                    _rarity = item.get("rarity", "Commun")
                    _sell_val = sd.EQUIPMENT_SELL_VALUES.get(_rarity, 20)
                    sell_col = (200, 60, 60) if sell_btn.collidepoint(mx, my) else (140, 40, 40)
                    _draw_rounded_rect(screen, sell_col, sell_btn, radius=8, border=1, border_color=(255, 100, 100))
                    sell_txt = font_xs.render(f"Vendre {_sell_val}", True, (255, 210, 210))
                    screen.blit(sell_txt, (sell_btn.x + (sell_btn.w - sell_txt.get_width()) // 2,
                                           sell_btn.y + (sell_btn.h - sell_txt.get_height()) // 2))

                    if clicked and eq_btn.collidepoint(mx, my) and not already:
                        save["equipped"][category_slot] = item_idx
                        sd.save(save)
                    elif clicked and sell_btn.collidepoint(mx, my):
                        ok_sell, coins_got, err = sd.sell_equipment(save, item_idx)
                        if ok_sell:
                            gacha_msg = f"Vendu ! +{coins_got} pièces"
                            gacha_msg_timer = 180
                            # reset scroll/selection car l'inventaire a changé
                            selected_inv_idx = None
                        else:
                            gacha_msg = err
                            gacha_msg_timer = 120
                    elif clicked and row.collidepoint(mx, my) and not eq_btn.collidepoint(mx, my) and not sell_btn.collidepoint(mx, my):
                        selected_inv_idx = li
                        dragging_item = item_idx
                        drag_offset = (row.x - mx, row.y - my)

                screen.set_clip(old_clip_eq)

            if mouse_released and dragging_item is not None:
                if drag_item_data is not None:
                    for slot_key, rect in slot_boxes.items():
                        if rect.collidepoint(mx, my) and drag_item_data["slot"] == slot_key:
                            save["equipped"][slot_key] = dragging_item
                            sd.save(save)
                            break
                dragging_item = None

            if dragging_item is not None and drag_item_data is not None:
                drag_rect = pygame.Rect(mx + 12, my + 12, 180, 52)
                _draw_rounded_rect(screen, C_PANEL2, drag_rect, radius=8, border=2,
                                   border_color=tuple(drag_item_data["color"]))
                icon_rect = pygame.Rect(drag_rect.x + 8, drag_rect.y + 6, 40, 40)
                _draw_equipment_icon(screen, drag_item_data, icon_rect, show_label=False)
                dname = font_sm.render(_get_equipment_name(drag_item_data), True, tuple(drag_item_data["color"]))
                screen.blit(dname, (drag_rect.x + 56, drag_rect.y + 6))
                dstat = font_xs.render(f"+{drag_item_data['value']} {drag_item_data['label']}", True, C_SUBTEXT)
                screen.blit(dstat, (drag_rect.x + 56, drag_rect.y + 28))

            selected_info = font_sm.render("Sélection : " + category_labels[selected_equip_category], True, C_TEXT)
            screen.blit(selected_info, (right_panel.x + 14, right_panel.y + right_panel.h - 24))

        # ────────────────────────────────────────────────────────────────────
        # TAB 3 : SKILL TREE (ARBRE RADIAL)
        # ────────────────────────────────────────────────────────────────────
        elif active_tab == 3:
            import math
            from save_data import SKILLS, can_unlock_skill, unlock_skill
            
            # Panneau de fond
            tree_panel = pygame.Rect(10, content_y, w - 20, content_h)
            _draw_rounded_rect(screen, C_PANEL, tree_panel, radius=14)
            
            # Titre et points de skill
            tree_title = font_med.render("Arbre de Compétences", True, C_ACCENT)
            screen.blit(tree_title, (w // 2 - tree_title.get_width() // 2, content_y + 8))
            
            skill_pts_text = f"⭐ {save.get('skill_points', 0)} pts"
            sp_label = font_sm.render(skill_pts_text, True, C_GREEN)
            screen.blit(sp_label, (w // 2 - sp_label.get_width() // 2, content_y + 36))
            
            # ── Configuration des 5 branches ──
            cats = ["force", "speed", "resist", "tower", "power"]
            cat_names = {
                "force": "FORCE",
                "speed": "RAPIDITÉ",
                "resist": "RÉSISTANCE",
                "tower": "TOURS",
                "power": "PUISSANCE",
            }
            cat_icons = {
                "force": "💪",
                "speed": "⚡",
                "resist": "🛡",
                "tower": "🗼",
                "power": "✨",
            }
            cat_colors = {
                "force": (220, 60, 60),
                "speed": (100, 200, 255),
                "resist": (100, 200, 150),
                "tower": (200, 160, 60),
                "power": (200, 100, 255),
            }
            
            # Centre de l'arbre (le personnage)
            cx = w // 2
            cy = content_y + content_h // 2 + 20
            
            # Dessin du personnage central
            pygame.draw.circle(screen, (180, 180, 200), (cx, cy), 28)
            pygame.draw.circle(screen, C_ACCENT, (cx, cy), 28, 3)
            char_lbl = font_sm.render("🧑", True, C_TEXT)
            screen.blit(char_lbl, (cx - char_lbl.get_width() // 2, cy - char_lbl.get_height() // 2))
            
            # ── Calcul des positions des nœuds ──
            # 5 branches réparties uniformément : angles en partant du haut
            # -90° = haut, puis 72° entre chaque branche
            branch_angles = {}
            for bi, cat in enumerate(cats):
                angle_deg = -90 + bi * 72  # 360 / 5 = 72°
                branch_angles[cat] = math.radians(angle_deg)
            
            # Distance du centre pour chaque niveau de skill
            available_radius = min(content_h // 2 - 60, (w - 80) // 2 - 30)
            level_distances = {
                1: available_radius * 0.3,
                2: available_radius * 0.55,
                3: available_radius * 0.78,
                4: available_radius * 0.98,
            }
            
            node_radius = 22
            hovered_skill = None
            
            # Collecter toutes les positions des nœuds
            skill_positions = {}  # skill_id -> (x, y)
            
            # Positionner les skills des 5 branches principales
            for cat in cats:
                base_angle = branch_angles[cat]
                cat_skills = [(sid, SKILLS[sid]) for sid in SKILLS.keys()
                              if SKILLS[sid]["category"] == cat]
                
                # Trier par niveau
                cat_skills.sort(key=lambda x: x[1]["level"])
                
                # Grouper par niveau pour gérer les branches qui se divisent
                levels = {}
                for sid, skill in cat_skills:
                    lv = skill["level"]
                    if lv not in levels:
                        levels[lv] = []
                    levels[lv].append((sid, skill))
                
                for lv, skills_at_level in levels.items():
                    dist = level_distances.get(lv, available_radius * 0.3 * lv)
                    n = len(skills_at_level)
                    # Spread within the branch
                    spread_angle = 0.25 if n > 1 else 0
                    for si, (sid, skill) in enumerate(skills_at_level):
                        if n == 1:
                            angle = base_angle
                        else:
                            offset = (si - (n - 1) / 2) * spread_angle
                            angle = base_angle + offset
                        sx = int(cx + math.cos(angle) * dist)
                        sy = int(cy + math.sin(angle) * dist)
                        skill_positions[sid] = (sx, sy)
            
            # Positionner les skills HYBRIDES (entre 2 branches)
            hybrid_skills = [(sid, SKILLS[sid]) for sid in SKILLS.keys()
                             if SKILLS[sid]["category"] == "hybrid"]
            for sid, skill in hybrid_skills:
                branches = skill.get("branches", [])
                if len(branches) == 2 and branches[0] in branch_angles and branches[1] in branch_angles:
                    a1 = branch_angles[branches[0]]
                    a2 = branch_angles[branches[1]]
                    # Calcul de l'angle moyen (gestion du wraparound)
                    diff = a2 - a1
                    if diff > math.pi:
                        diff -= 2 * math.pi
                    elif diff < -math.pi:
                        diff += 2 * math.pi
                    mid_angle = a1 + diff / 2
                    dist = available_radius * 0.55
                    sx = int(cx + math.cos(mid_angle) * dist)
                    sy = int(cy + math.sin(mid_angle) * dist)
                    skill_positions[sid] = (sx, sy)
            
            # ── Dessiner les lignes de connexion ──
            def _get_skill_color(sk):
                """Get the display color for a skill (handles hybrid blend)."""
                cat = sk["category"]
                if cat == "hybrid":
                    br = sk.get("branches", [])
                    if len(br) == 2:
                        c1 = cat_colors.get(br[0], C_SUBTEXT)
                        c2 = cat_colors.get(br[1], C_SUBTEXT)
                        return ((c1[0]+c2[0])//2, (c1[1]+c2[1])//2, (c1[2]+c2[2])//2)
                return cat_colors.get(cat, C_SUBTEXT)
            
            for sid, skill in SKILLS.items():
                if sid not in skill_positions:
                    continue
                sx, sy = skill_positions[sid]
                
                is_unlocked = save.get("skills_unlocked", {}).get(sid, False)
                line_col = _get_skill_color(skill)
                
                # Ligne vers les prérequis
                requires = skill.get("requires", [])
                if not requires:
                    # Connecté au centre (personnage)
                    if is_unlocked:
                        alpha_col = line_col
                    else:
                        alpha_col = (line_col[0] // 3, line_col[1] // 3, line_col[2] // 3)
                    pygame.draw.line(screen, alpha_col, (cx, cy), (sx, sy), 2)
                else:
                    for req_id in requires:
                        if req_id in skill_positions:
                            rx, ry = skill_positions[req_id]
                            req_unlocked = save.get("skills_unlocked", {}).get(req_id, False)
                            if is_unlocked and req_unlocked:
                                alpha_col = line_col
                            elif req_unlocked:
                                alpha_col = (line_col[0] // 2, line_col[1] // 2, line_col[2] // 2)
                            else:
                                alpha_col = (line_col[0] // 4, line_col[1] // 4, line_col[2] // 4)
                            pygame.draw.line(screen, alpha_col, (rx, ry), (sx, sy), 2)
            
            # ── Dessiner les labels de branche ──
            for cat in cats:
                angle = branch_angles[cat]
                label_dist = available_radius + 20
                lx = int(cx + math.cos(angle) * label_dist)
                ly = int(cy + math.sin(angle) * label_dist)
                clbl = font_xs.render(f"{cat_icons[cat]} {cat_names[cat]}", True, cat_colors[cat])
                screen.blit(clbl, (lx - clbl.get_width() // 2, ly - clbl.get_height() // 2))
            
            # ── Dessiner les nœuds de compétences ──
            for sid, skill in SKILLS.items():
                if sid not in skill_positions:
                    continue
                sx, sy = skill_positions[sid]
                
                is_unlocked = save.get("skills_unlocked", {}).get(sid, False)
                can_buy, err_msg = can_unlock_skill(save, sid)
                base_col = _get_skill_color(skill)
                
                # Vérifier survol
                dist_to_mouse = math.sqrt((mx - sx) ** 2 + (my - sy) ** 2)
                is_hovered = dist_to_mouse <= node_radius + 4
                
                if is_hovered:
                    hovered_skill = (sid, skill, sx, sy)
                
                # Couleur du nœud
                if is_unlocked:
                    node_col = base_col
                    border_c = (min(base_col[0] + 60, 255), min(base_col[1] + 60, 255), min(base_col[2] + 60, 255))
                elif can_buy:
                    node_col = (base_col[0] // 2, base_col[1] // 2, base_col[2] // 2)
                    border_c = (200, 180, 80)
                else:
                    node_col = (40, 40, 50)
                    border_c = (70, 70, 80)
                
                # Effet hover
                if is_hovered:
                    pygame.draw.circle(screen, (255, 255, 255, 80), (sx, sy), node_radius + 6, 2)
                
                # Cercle du nœud
                pygame.draw.circle(screen, node_col, (sx, sy), node_radius)
                pygame.draw.circle(screen, border_c, (sx, sy), node_radius, 3)
                
                # Icône / texte dans le nœud
                if is_unlocked:
                    icon_text = "✓"
                    icon_col = (255, 255, 255)
                else:
                    icon_text = str(skill["cost"])
                    icon_col = C_TEXT if can_buy else C_SUBTEXT
                
                icon_lbl = font_sm.render(icon_text, True, icon_col)
                screen.blit(icon_lbl, (sx - icon_lbl.get_width() // 2, sy - icon_lbl.get_height() // 2))
                
                # Clic pour acheter
                if clicked and is_hovered and not is_unlocked and can_buy:
                    unlock_skill(save, sid)
            
            # ── Tooltip au survol ──
            if hovered_skill:
                hsid, hskill, hx, hy = hovered_skill
                h_unlocked = save.get("skills_unlocked", {}).get(hsid, False)
                h_can, h_err = can_unlock_skill(save, hsid)
                h_col = _get_skill_color(hskill)
                
                # Construction du tooltip
                tt_lines = [
                    hskill["name"],
                    hskill["description"],
                    f"Coût: {hskill['cost']} pts",
                ]
                if h_unlocked:
                    tt_lines.append("✓ ACQUISE")
                elif h_can:
                    tt_lines.append("Cliquez pour acheter")
                else:
                    tt_lines.append(f"⛔ {h_err}")
                
                # Prérequis
                if hskill.get("requires"):
                    req_names = []
                    for rid in hskill["requires"]:
                        r = SKILLS.get(rid)
                        if r:
                            is_r_done = save.get("skills_unlocked", {}).get(rid, False)
                            prefix = "✓" if is_r_done else "✗"
                            req_names.append(f"{prefix} {r['name']}")
                    if req_names:
                        tt_lines.append("Requis: " + ", ".join(req_names))
                
                # Dimensions du tooltip
                tt_font = font_xs
                tt_padding = 10
                tt_line_h = 18
                tt_w = max(tt_font.size(line)[0] for line in tt_lines) + tt_padding * 2
                tt_h = len(tt_lines) * tt_line_h + tt_padding * 2
                
                # Position du tooltip (éviter de sortir de l'écran)
                tt_x = min(hx + node_radius + 10, w - tt_w - 10)
                tt_y = min(hy - tt_h // 2, h - tt_h - 10)
                tt_x = max(10, tt_x)
                tt_y = max(content_y + 5, tt_y)
                
                tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
                _draw_rounded_rect(screen, (20, 22, 35), tt_rect, radius=8, border=2,
                                   border_color=h_col)
                
                for li, line in enumerate(tt_lines):
                    if li == 0:
                        col = h_col
                    elif li == len(tt_lines) - 1 and not h_unlocked:
                        col = C_GREEN if h_can else C_RED
                    elif "✓ ACQUISE" in line:
                        col = C_GREEN
                    else:
                        col = C_SUBTEXT
                    
                    lt = tt_font.render(line, True, col)
                    screen.blit(lt, (tt_x + tt_padding, tt_y + tt_padding + li * tt_line_h))

        elif active_tab == 4:
            quest_panel = pygame.Rect(20, content_y + 10, w - 40, content_h - 10)
            _draw_rounded_rect(screen, C_PANEL, quest_panel, radius=12)

            quest_title = font_med.render("Quêtes et Missions", True, C_ACCENT)
            screen.blit(quest_title, (quest_panel.x + (quest_panel.w - quest_title.get_width()) // 2, quest_panel.y + 12))

            section_names = ["Quotidiennes", "Missions", "Événements"]
            section_ids = ["quotidiennes", "missions", "evenements"]
            section_tab_h = 36
            section_tab_y = quest_panel.y + 50
            section_tab_w = (quest_panel.w - 40) // 3

            for si, (sname, sid) in enumerate(zip(section_names, section_ids)):
                sr = pygame.Rect(quest_panel.x + 20 + si * (section_tab_w + 10), section_tab_y, section_tab_w, section_tab_h)
                is_active = (quest_section_active == sid)
                scol = C_TAB_ACT if is_active else C_TAB_INACT
                _draw_rounded_rect(screen, scol, sr, radius=8, border=2,
                                   border_color=C_ACCENT if is_active else C_BTN_BOR)
                stxt = font_sm.render(sname, True, C_ACCENT if is_active else C_SUBTEXT)
                screen.blit(stxt, (sr.x + (sr.w - stxt.get_width()) // 2, sr.y + (sr.h - stxt.get_height()) // 2))
                if clicked and sr.collidepoint(mx, my):
                    quest_section_active = sid

            content_rect = pygame.Rect(quest_panel.x + 20, section_tab_y + section_tab_h + 12,
                                        quest_panel.w - 40, quest_panel.h - section_tab_h - 90)
            _draw_rounded_rect(screen, C_PANEL2, content_rect, radius=10)

            if quest_section_active == "evenements":
                event_types = quetes_module.get_all_event_types()
                if event_types:
                    event_names = {"histoire": "📖 Histoire", "guerre": "⚔️ Guerre", "infini": "♾️ Infini"}
                    left_btn = pygame.Rect(content_rect.x + 10, content_rect.y + 10, 40, 30)
                    right_btn = pygame.Rect(content_rect.right - 50, content_rect.y + 10, 40, 30)
                    left_hov = left_btn.collidepoint(mx, my)
                    right_hov = right_btn.collidepoint(mx, my)
                    _draw_rounded_rect(screen, C_BTN_HOV if left_hov else C_BTN, left_btn, radius=6)
                    _draw_rounded_rect(screen, C_BTN_HOV if right_hov else C_BTN, right_btn, radius=6)
                    lt = font_sm.render("<", True, C_TEXT)
                    rt = font_sm.render(">", True, C_TEXT)
                    screen.blit(lt, (left_btn.x + (left_btn.w - lt.get_width()) // 2, left_btn.y + (left_btn.h - lt.get_height()) // 2))
                    screen.blit(rt, (right_btn.x + (right_btn.w - rt.get_width()) // 2, right_btn.y + (right_btn.h - rt.get_height()) // 2))
                    if clicked and left_hov:
                        event_type_scroll = (event_type_scroll - 1) % len(event_types)
                    if clicked and right_hov:
                        event_type_scroll = (event_type_scroll + 1) % len(event_types)
                    current_event_type = event_types[event_type_scroll % len(event_types)] if event_types else None
                    if current_event_type:
                        event_title = font_sm.render(event_names.get(current_event_type, current_event_type), True, C_ACCENT)
                        screen.blit(event_title, (content_rect.centerx - event_title.get_width() // 2, content_rect.y + 15))
                        quest_dicts = quetes_module.get_event_quests_by_type(current_event_type)
                        quest_list = list(quest_dicts.items())
                    else:
                        quest_list = []
                else:
                    quest_list = []
            else:
                quest_dicts = quetes_module.get_quests_by_section(quest_section_active)
                quest_list = list(quest_dicts.items())

            quest_display_area = pygame.Rect(content_rect.x + 10, content_rect.y + 50,
                                              content_rect.w - 20, content_rect.h - 60)
            if not quest_list:
                no_quest_lbl = font_sm.render("Aucune quête disponible.", True, C_SUBTEXT)
                screen.blit(no_quest_lbl, (quest_display_area.centerx - no_quest_lbl.get_width() // 2,
                                            quest_display_area.centery - no_quest_lbl.get_height() // 2))
            else:
                q_row_h = 64
                q_row_gap = 8
                for qi, (q_id, quest) in enumerate(quest_list):
                    qy = quest_display_area.y + qi * (q_row_h + q_row_gap)
                    if qy + q_row_h < quest_display_area.y or qy > quest_display_area.bottom:
                        continue
                    q_row = pygame.Rect(quest_display_area.x, qy, quest_display_area.w, q_row_h)
                    is_completed = quetes_module.check_quest_completion(q_id, save)
                    is_claimed = quetes_module.has_quest_been_completed(save, q_id)
                    can_claim = is_completed and not is_claimed
                    if is_claimed:
                        q_bg_col = (50, 70, 50)
                        q_border_col = C_GREEN
                    elif can_claim:
                        q_bg_col = (70, 70, 50)
                        q_border_col = (255, 220, 80)
                    else:
                        q_bg_col = C_BTN
                        q_border_col = C_BTN_BOR
                    _draw_rounded_rect(screen, q_bg_col, q_row, radius=10, border=2, border_color=q_border_col)
                    quest_name_col = C_GREEN if is_claimed else (C_ACCENT if can_claim else C_TEXT)
                    q_name = font_sm.render(quest["nom"], True, quest_name_col)
                    screen.blit(q_name, (q_row.x + 14, q_row.y + 8))
                    q_desc = font_xs.render(quest["description"], True, C_SUBTEXT)
                    screen.blit(q_desc, (q_row.x + 14, q_row.y + 30))
                    # Affichage des récompenses avec icônes
                    _rw_x = q_row.right - 14
                    _rw_y = q_row.y + 50
                    if quest.get("gemmes"):
                        _gem_txt = font_xs.render(f"+{quest['gemmes']}", True, (255, 100, 255))
                        _gem_ico = _get_icon("gem", 14)
                        _rw_x -= _gem_txt.get_width()
                        screen.blit(_gem_txt, (_rw_x, _rw_y))
                        _rw_x -= 16
                        screen.blit(_gem_ico, (_rw_x, _rw_y))
                        _rw_x -= 6
                    if quest.get("pieces"):
                        _coin_txt = font_xs.render(f"+{quest['pieces']}", True, (255, 205, 92))
                        _coin_ico = _get_icon("coin", 14)
                        _rw_x -= _coin_txt.get_width()
                        screen.blit(_coin_txt, (_rw_x, _rw_y))
                        _rw_x -= 16
                        screen.blit(_coin_ico, (_rw_x, _rw_y))
                        _rw_x -= 6
                    if quest.get("xp"):
                        _xp_txt = font_xs.render(f"+{quest['xp']} XP", True, (200, 200, 100))
                        _rw_x -= _xp_txt.get_width()
                        screen.blit(_xp_txt, (_rw_x, _rw_y))
                    if not is_claimed:
                        claim_btn = pygame.Rect(q_row.right - 100, q_row.y + 14, 86, 30)
                        claim_hov = claim_btn.collidepoint(mx, my)
                        if can_claim:
                            claim_col = C_BTN_HOV if claim_hov else (100, 200, 100)
                            claim_txt = "Réclamer"
                            if clicked and claim_btn.collidepoint(mx, my):
                                ok, reward_quest = quetes_module.claim_quest_reward(save, q_id)
                                if ok:
                                    sd.save(save)
                        else:
                            claim_col = (80, 80, 80)
                            claim_txt = "En cours..."
                        _draw_rounded_rect(screen, claim_col, claim_btn, radius=6, border=1, border_color=C_BTN_BOR)
                        btn_lbl = font_xs.render(claim_txt, True, C_TEXT)
                        screen.blit(btn_lbl, (claim_btn.x + (claim_btn.w - btn_lbl.get_width()) // 2,
                                               claim_btn.y + (claim_btn.h - btn_lbl.get_height()) // 2))
                    else:
                        status_lbl = font_xs.render("? Complétée", True, C_GREEN)
                        screen.blit(status_lbl, (q_row.right - status_lbl.get_width() - 14, q_row.y + 22))

        # ── Popup sélection icône joueur (par-dessus tout) ───────────────
        if icon_picker_open:
            should_close = draw_icon_picker(
                screen, font_sm, font_xs, save, mx, my,
                clicked and not _icon_picker_just_opened
            )
            if should_close:
                icon_picker_open = False

        # ── Toast messages globaux (vente, erreurs, etc.) ────────────────
        if gacha_msg_timer > 0:
            gacha_msg_timer -= 1
            _alpha_t = min(255, gacha_msg_timer * 4)
            _t_surf = font_sm.render(gacha_msg, True, (255, 220, 100))
            _t_bg = pygame.Surface((_t_surf.get_width() + 24, _t_surf.get_height() + 12), pygame.SRCALPHA)
            _t_bg.fill((20, 20, 30, _alpha_t))
            pygame.draw.rect(_t_bg, (100, 100, 140, _alpha_t),
                             _t_bg.get_rect(), 1, border_radius=8)
            _t_x = w // 2 - _t_bg.get_width() // 2
            _t_y = h - 80
            screen.blit(_t_bg, (_t_x, _t_y))
            _t_surf.set_alpha(_alpha_t)
            screen.blit(_t_surf, (_t_x + 12, _t_y + 6))

        pygame.display.flip()
        clock.tick(60)

    if chosen_level is not None:
        return chosen_level, save
    return None, save


def _draw_item_card(screen, font_med, font_sm, font_xs, item, rect):
    rc = tuple(item["color"])
    _draw_rounded_rect(screen, C_PANEL2, rect, radius=10, border=2, border_color=rc)
    icon_rect = pygame.Rect(rect.x + 14, rect.y + 16, 72, 72)
    _draw_equipment_icon(screen, item, icon_rect, show_label=False)
    n = font_sm.render(_get_equipment_name(item), True, rc)
    screen.blit(n, (rect.x + 100, rect.y + 14))
    v = font_sm.render(f"+{item['value']} {item['label']}", True, C_TEXT)
    screen.blit(v, (rect.x + 100, rect.y + 42))
    s = font_xs.render(f"Slot : {SLOT_LABELS.get(item['slot'], item['slot'])}  |  {item['rarity']}", True, C_SUBTEXT)
    screen.blit(s, (rect.x + 100, rect.y + 72))


def _draw_equipment_list(screen, font_sm, font_xs, save, area,
                          selected_idx, mx, my, clicked,
                          select_callback, show_equip_btn=False,
                          equip_callback=None):
    """
    Affiche la liste des équipements dans 'area'.
    Retourne le nouvel index sélectionné.
    """
    items  = save["inventory_equipment"]
    row_h  = 46
    row_gap = 4
    new_sel = selected_idx

    if not items:
        no_lbl = font_xs.render("Aucun équipement. Ouvrez des coffres !", True, C_SUBTEXT)
        screen.blit(no_lbl, (area.x + (area.w - no_lbl.get_width()) // 2,
                              area.y + 20))
        return new_sel

    clip = screen.get_clip()
    screen.set_clip(area)

    for i, item in enumerate(items):
        ry    = area.y + i * (row_h + row_gap)
        if ry + row_h < area.y or ry > area.y + area.h:
            continue
        row   = pygame.Rect(area.x, ry, area.w, row_h)
        is_sel = (i == selected_idx)
        rc    = tuple(item["color"])
        col   = C_PANEL2 if is_sel else C_BTN
        _draw_rounded_rect(screen, col, row, radius=7, border=2,
                           border_color=rc if is_sel else C_BTN_BOR)

        icon_rect = pygame.Rect(row.x + 6, row.y + 5, 36, 36)
        _draw_equipment_icon(screen, item, icon_rect, show_label=False)

        name_lbl = font_sm.render(_get_equipment_name(item), True, rc)
        screen.blit(name_lbl, (row.x + 50, row.y + 6))

        val_lbl = font_xs.render(f"+{item['value']} {item['label']}  |  {item['rarity']}", True, C_SUBTEXT)
        screen.blit(val_lbl, (row.x + 50, row.y + 26))

        # Bouton Équiper
        if show_equip_btn and equip_callback:
            eq_btn = pygame.Rect(row.right - 90, row.y + 8, 80, 30)
            # Vérifie si déjà équipé
            already = save["equipped"].get(item["slot"]) == i
            ecol    = C_SUBTEXT if already else (C_BTN_HOV if eq_btn.collidepoint(mx, my) else C_BTN)
            _draw_rounded_rect(screen, ecol, eq_btn, radius=5, border=1, border_color=C_ACCENT2)
            etxt = font_xs.render("Équipé" if already else "Équiper", True, C_TEXT)
            screen.blit(etxt, (eq_btn.x + (eq_btn.w - etxt.get_width()) // 2,
                                eq_btn.y + (eq_btn.h - etxt.get_height()) // 2))
            if clicked and eq_btn.collidepoint(mx, my) and not already:
                equip_callback(i)

        if clicked and row.collidepoint(mx, my):
            new_sel = i if new_sel != i else None

    screen.set_clip(clip)
    return new_sel