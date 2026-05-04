"""
ui.py
-----
Fonctions de rendu de l'interface : HUD, ghost, inventaire, pause, game over,
et LEVEL-UP BANNER (choix de tour en pause).
"""

import os
import random
import pygame
from core.config import ALL_TOWER_TYPES, GRID_WIDTH, GRID_HEIGHT, GRID_SIZE, COLS, ROWS, INTERFACE_WIDTH

# ============================================================
# STAR SPRITE HELPER
# ============================================================

_star_cache = {}
_objectif_bg_cache = {}

def _load_objectif_bg(w, h):
    """
    Charge assets/sprites/objectif.png redimensionné à (w, h).
    Résultat mis en cache par taille. Retourne None si absent.
    """
    key = (w, h)
    if key in _objectif_bg_cache:
        return _objectif_bg_cache[key]
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "objectif.png")
    result = None
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            result = pygame.transform.smoothscale(img, (w, h))
        except Exception:
            result = None
    _objectif_bg_cache[key] = result
    return result

def draw_star(screen, x, y, size, done):
    """
    Dessine une étoile à la position (x, y) en utilisant assets/sprites/etoiles.png.
    Si done=True → couleur normale. Si done=False → image grisée.
    Fallback sur le caractère ★ si le fichier est absent.
    """
    key = (size, done)
    if key not in _star_cache:
        path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "etoiles.png")
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (size, size))
                if not done:
                    # Appliquer un filtre gris : désaturer + assombrir
                    grey = img.copy()
                    grey.fill((0, 0, 0, 0))  # reset
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
    # Fallback texte ★
    fnt = pygame.font.SysFont("arial", size, bold=True)
    col = (255, 210, 40) if done else (60, 60, 80)
    lbl = fnt.render("★", True, col)
    screen.blit(lbl, (x, y))
    return False

# ============================================================
# COLORS & UI CONSTANTS
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

def _draw_panel(screen, rect, alt=False):
    """Dessine un panneau stylisé."""
    bg = COLORS["panel_alt"] if alt else COLORS["panel"]
    pygame.draw.rect(screen, bg, rect, border_radius=RADIUS["md"])
    pygame.draw.rect(screen, COLORS["border"], rect, 1, border_radius=RADIUS["md"])

def _draw_progress_bar(screen, rect, value, max_value, fg, bg=(40, 40, 50)):
    """Dessine une barre de progression."""
    pygame.draw.rect(screen, bg, rect, border_radius=RADIUS["sm"])
    ratio = 0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    fill = pygame.Rect(rect.x, rect.y, int(rect.w * ratio), rect.h)
    pygame.draw.rect(screen, fg, fill, border_radius=RADIUS["sm"])
    pygame.draw.rect(screen, COLORS["border"], rect, 1, border_radius=RADIUS["sm"])

def _get_icon(name, size=18, color=(255, 255, 255)):
    """Crée une petite icône vectorielle."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    if name == "coin":
        pygame.draw.circle(surf, color, (cx, cy), size // 2 - 1)
        pygame.draw.circle(surf, (40, 30, 0), (cx, cy), size // 2 - 1, 1)
    elif name == "hp":
        pygame.draw.polygon(surf, color, [(cx, 2), (size - 2, cy), (cx, size - 2), (2, cy)])
    elif name == "speed":
        pygame.draw.polygon(surf, color, [(2, cy), (cx + 1, 2), (cx - 1, cy - 1), (size - 2, cy), (cx - 1, size - 2), (cx + 1, cy + 1)])
    else:
        pygame.draw.circle(surf, color, (cx, cy), size // 2 - 2, 2)
    return surf


# ============================================================
# CONSTANTES D'INVENTAIRE
# ============================================================

INV_SLOT_SIZE    = 64
INV_SLOT_GAP     = 10
INV_BAR_HEIGHT   = 90
INV_BG_COLOR     = (101, 67, 33)
INV_BORDER_COLOR = (160, 110, 60)
INV_SEL_COLOR    = (255, 220, 80)
INV_EMPTY_COLOR  = (70, 45, 20)

ITEM_LABELS = {
    "small":        "Tour Rapide",
    "big":          "Tour Lourde",
    "sniper":       "Sniper",
    "mortar":       "Mortier",
    "frost":        "Gèleuse",
    "poison":       "Venimeuse",
    "beam":         "Laser",
    "tesla":        "Tesla",
    "rocket":       "Roquette",
    "storm":        "Tempête",
    "arcane":       "Arcane",
    "crystal":      "Cristal",
    "swarm":        "Essaim",
    "burst":        "Fusée",
    "cannon":       "Canon",
    "flamethrower": "Flammes",
    "shock":        "Éclair",
    "mine":         "Mine",
    "laser":        "Laser",
    "trap":         "Piège",
    "tower_damage": "Boost Dégâts",
    "tower_cooldown": "Boost Vitesse",
}
ITEM_COLORS = {
    "small":        (0, 150, 200),
    "big":          (0, 100, 180),
    "sniper":       (230, 180, 60),
    "mortar":       (180, 90, 50),
    "frost":        (120, 200, 255),
    "poison":       (80, 180, 80),
    "beam":         (180, 60, 220),
    "tesla":        (120, 180, 250),
    "rocket":       (200, 100, 40),
    "storm":        (90, 130, 240),
    "arcane":       (150, 60, 220),
    "crystal":      (80, 220, 220),
    "swarm":        (220, 140, 50),
    "burst":        (200, 70, 70),
    "cannon":       (140, 90, 30),
    "flamethrower": (220, 120, 40),
    "shock":        (255, 180, 60),
    "mine":         (120, 80, 50),
    "laser":        (180, 60, 180),
    "trap":         (100, 100, 100),
    "tower_damage": (240, 120, 40),
    "tower_cooldown": (90, 200, 180),
}

# ============================================================
# ICONE PAUSE
# ============================================================

PAUSE_BTN_SIZE = 36   # taille du bouton en pixels

_pause_icon_cache = None

def get_pause_icon():
    """Charge assets/sprites/pause.png une seule fois, ou retourne None."""
    global _pause_icon_cache
    if _pause_icon_cache is not None:
        return _pause_icon_cache
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "pause.png")
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _pause_icon_cache = pygame.transform.smoothscale(img, (PAUSE_BTN_SIZE, PAUSE_BTN_SIZE))
            return _pause_icon_cache
        except Exception as e:
            print(f"[ui] Impossible de charger pause.png : {e}")
    _pause_icon_cache = False   # marquer "tenté mais absent"
    return None


def draw_pause_button(screen, offset_x, offset_y, mx, my):
    """
    Dessine le bouton pause en haut à droite de la grille.
    Retourne le pygame.Rect du bouton (pour détecter les clics).
    """
    btn_x = offset_x + GRID_WIDTH + INTERFACE_WIDTH - PAUSE_BTN_SIZE - 6
    btn_y = offset_y - PAUSE_BTN_SIZE - 6
    btn_rect = pygame.Rect(btn_x, btn_y, PAUSE_BTN_SIZE, PAUSE_BTN_SIZE)
    hov = btn_rect.collidepoint(mx, my)

    icon = get_pause_icon()
    if icon:
        if hov:
            bright = pygame.Surface((PAUSE_BTN_SIZE, PAUSE_BTN_SIZE), pygame.SRCALPHA)
            bright.fill((255, 255, 255, 40))
            screen.blit(icon, btn_rect.topleft)
            screen.blit(bright, btn_rect.topleft)
        else:
            screen.blit(icon, btn_rect.topleft)
    else:
        # Fallback vectoriel : deux barres verticales (▐▐)
        col = (255, 230, 100) if hov else (200, 200, 220)
        pygame.draw.rect(screen, (30, 36, 54, 180), btn_rect, border_radius=8)
        pygame.draw.rect(screen, col, btn_rect, 2, border_radius=8)
        bw, bh = 7, 18
        bx = btn_x + PAUSE_BTN_SIZE // 2 - bw - 3
        by = btn_y + (PAUSE_BTN_SIZE - bh) // 2
        pygame.draw.rect(screen, col, (bx, by, bw, bh), border_radius=2)
        pygame.draw.rect(screen, col, (bx + bw + 5, by, bw, bh), border_radius=2)

    return btn_rect


TOWER_CHOICES = ALL_TOWER_TYPES
TOWER_DESCS   = {
    "small":        "Tour rapide\nDégâts corrects\nPortée courte",
    "big":          "Tour lourde\nDégâts puissants\nPortée moyenne",
    "sniper":       "Tir longue portée\nCritique précis\nDommages élevés",
    "mortar":       "Mortier\nImpact AoE\nPlacement stratégique",
    "frost":        "Gèleuse\nRalentit les ennemis\nContrôle de zone",
    "poison":       "Venimeuse\nDégâts sur le temps\nAffaiblit la cible",
    "beam":         "Laser continu\nDégâts rapides\nPénétration",
    "tesla":        "Tesla\nChocs électriques\nChaines ennemis",
    "rocket":       "Roquette\nExplosion AoE\nPortée moyenne",
    "storm":        "Tempête\nFoudre aléatoire\nZone étendue",
    "arcane":       "Arcane\nMagie pure\nDommages bruts",
    "crystal":      "Cristal\nZone gelée\nRenforce le champ",
    "swarm":        "Essaim\nTir rapide\nFaible dégâts",
    "burst":        "Fusée\nSalve lourde\nCooldown long",
    "cannon":       "Canon\nDégâts lourds\nImpact de zone",
    "flamethrower": "Flammes\nZone de feu\nDégâts continus",
    "shock":        "Éclair\nDégâts électriques\nLenteur ciblée",
    "mine":         "Mine\nDétonation surprise\nDégâts massifs",
    "laser":        "Laser\nPortée maximale\nTir précis",
    "trap":         "Piège\nDégâts au contact\nDéfense statique",
    "tower_damage": "Augmente les dégâts\nDe toutes les tours\nIdéal pour burst",
    "tower_cooldown": "Réduit le cooldown\nDes tours\nForte cadence de tir",
}


# ============================================================
# HUD
# ============================================================

def draw_hud(screen, font, big_font, level, xp, xp_to_next,
             wave_number, max_waves, mobs_killed, max_enemies,
             boss_active, boss_timer, wave_timer,
             offset_x, offset_y,
             player_hp=None, player_max_hp=None):
    """
    HUD affiché sur le fond à gauche de la grille (hors grille).
    Infos en haut à gauche du fond, grandes polices, hiérarchisées.
    """

    PAD     = 12
    panel_w = 160  # largeur fixe du panneau
    gx      = offset_x - panel_w  # collé au bord gauche de la grille
    gy      = offset_y + PAD
    bar_w   = 100

    f_xl  = pygame.font.SysFont("arial", 26, bold=True)
    f_lg  = pygame.font.SysFont("arial", 20, bold=True)
    f_md  = pygame.font.SysFont("arial", 16)
    f_sm  = pygame.font.SysFont("arial", 13)

    def _shadow(surf, fnt, txt, color, x, y):
        sh = fnt.render(txt, True, (0, 0, 0))
        surf.blit(sh, (x + 1, y + 1))
        t = fnt.render(txt, True, color)
        surf.blit(t, (x, y))
        return t.get_height()

    def _bar(surf, x, y, w, h, val, maxv, color, bg=(30, 10, 10)):
        pygame.draw.rect(surf, bg,    (x, y, w, h), border_radius=3)
        pygame.draw.rect(surf, (60,60,60), (x, y, w, h), 1, border_radius=3)
        if maxv > 0 and val > 0:
            fw = int(w * min(val / maxv, 1.0))
            pygame.draw.rect(surf, color, (x, y, fw, h), border_radius=3)

    # ── Surface overlay transparente sur la zone gauche ───────────
    overlay = pygame.Surface((panel_w, GRID_HEIGHT), pygame.SRCALPHA)

    lx = PAD  # coordonnées locales dans overlay

    # ① VAGUE — info la plus importante, très grande
    wave_max_str = "∞" if max_waves >= 9999 else str(max_waves)
    if boss_active:
        tc = (255, 70, 70) if boss_timer < 10 else (255, 160, 60)
        _shadow(overlay, f_xl, f"⚔ BOSS  {boss_timer:.0f}s", tc, lx, PAD)
        ly = PAD + 32
    else:
        _shadow(overlay, f_xl, f"Vague  {wave_number} / {wave_max_str}", (255, 240, 120), lx, PAD)
        ly = PAD + 32
        _shadow(overlay, f_md, f"{wave_timer:.0f}s", (160, 210, 255), lx, ly)
        ly += 22

    ly += 6

    # ② ENNEMIS tués cette vague
    _shadow(overlay, f_lg, f"Ennemis  {mobs_killed} / {max_enemies}", (220, 200, 160), lx, ly)
    ly += 26

    ly += 8
    # ── Ligne séparatrice ──
    pygame.draw.line(overlay, (200, 170, 60, 120), (lx, ly), (lx + bar_w, ly), 1)
    ly += 8

    # ③ HP joueur
    if player_hp is not None and player_max_hp:
        _shadow(overlay, f_lg, "Vie", (100, 220, 100), lx, ly)
        ly += 24
        _bar(overlay, lx, ly, bar_w, 12, player_hp, player_max_hp, (80, 200, 80))
        ly += 16
        _shadow(overlay, f_sm, f"{player_hp} / {player_max_hp}", (180, 230, 180), lx, ly)
        ly += 20

        ly += 8
        pygame.draw.line(overlay, (200, 170, 60, 120), (lx, ly), (lx + bar_w, ly), 1)
        ly += 8

    # ④ Niveau & XP — infos secondaires, plus petites
    _shadow(overlay, f_md, f"Niv. {level}", (200, 160, 255), lx, ly)
    ly += 20
    _bar(overlay, lx, ly, bar_w, 8, xp, xp_to_next, (160, 100, 255), bg=(20, 10, 40))
    ly += 12
    _shadow(overlay, f_sm, f"XP  {xp} / {xp_to_next}", (170, 140, 220), lx, ly)

    screen.blit(overlay, (gx, gy))


# ============================================================
# GHOST DE PLACEMENT
# ============================================================

def draw_ghost(screen, cells, gx, gy, item_type, towers, can_place_fn, offset_x, offset_y):

    is_upgrade = any(
        (
            (getattr(t, "tower_type", getattr(t, "trap_type", None)) == item_type)
            or (item_type == "trap" and getattr(t, "trap_type", None) == "spikes")
        )
        and any(cell in t.cells for cell in cells)
        for t in towers
    )
    valid = is_upgrade or can_place_fn(cells)
    tint  = (0, 255, 0, 80) if valid else (255, 0, 0, 80)

    valid_cells = [(cx, cy) for cx, cy in cells if 0 <= cx < COLS and 0 <= cy < ROWS]
    ghost_surf  = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)

    # Sprite de la tour si disponible
    if valid_cells:
        min_cx = min(c[0] for c in valid_cells)
        min_cy = min(c[1] for c in valid_cells)
        max_cx = max(c[0] for c in valid_cells)
        max_cy = max(c[1] for c in valid_cells)
        fw = (max_cx - min_cx + 1) * GRID_SIZE
        fh = (max_cy - min_cy + 1) * GRID_SIZE

        preview = get_tower_preview(item_type, fw, fh)
        if preview:
            tmp = preview.copy()
            # Réduit l'opacité de chaque pixel à 75 %
            tmp.fill((255, 255, 255, 190), special_flags=pygame.BLEND_RGBA_MULT)
            ghost_surf.blit(tmp, (min_cx * GRID_SIZE, min_cy * GRID_SIZE))

    # Teinte verte/rouge par-dessus
    for cx, cy in valid_cells:
        pygame.draw.rect(ghost_surf, tint,
                         pygame.Rect(cx * GRID_SIZE, cy * GRID_SIZE, GRID_SIZE, GRID_SIZE))

    screen.blit(ghost_surf, (offset_x, offset_y))

    if is_upgrade:
        f2 = get_font("sm", bold=True)
        lbl = f2.render("UPGRADE", True, (255, 255, 100))
        if valid_cells:
            mx_ = sum(c[0] for c in valid_cells) / len(valid_cells) * GRID_SIZE + offset_x
            my_ = sum(c[1] for c in valid_cells) / len(valid_cells) * GRID_SIZE + offset_y
            screen.blit(lbl, (int(mx_) - lbl.get_width() // 2, int(my_) - 10))


# ============================================================
# INVENTAIRE BAS-ECRAN
# ============================================================

def draw_inventory(screen, font, inventory, selected_item, win_w, win_h):
    bar_rect = pygame.Rect(0, win_h - INV_BAR_HEIGHT, win_w, INV_BAR_HEIGHT)
    _draw_panel(screen, bar_rect, alt=True)

    inv_lbl = font.render("Inventaire", True, (220, 190, 130))
    screen.blit(inv_lbl, (12, win_h - INV_BAR_HEIGHT + 8))

    present = [(k, v) for k, v in inventory.items() if v > 0]
    rects   = {}

    if not present:
        hint = font.render("Achetez des tours dans la boutique ->", True, (180, 150, 100))
        screen.blit(hint, (
            win_w // 2 - hint.get_width() // 2,
            win_h - INV_BAR_HEIGHT // 2 - hint.get_height() // 2,
        ))
        return rects

    total_w = len(present) * INV_SLOT_SIZE + (len(present) - 1) * INV_SLOT_GAP
    start_x = (win_w - total_w) // 2
    slot_y  = win_h - INV_BAR_HEIGHT + (INV_BAR_HEIGHT - INV_SLOT_SIZE) // 2

    badge_font = get_font("sm", bold=True)

    for i, (item_type, qty) in enumerate(present):
        sx        = start_x + i * (INV_SLOT_SIZE + INV_SLOT_GAP)
        slot_rect = pygame.Rect(sx, slot_y, INV_SLOT_SIZE, INV_SLOT_SIZE)
        is_sel    = (item_type == selected_item)

        base_col = ITEM_COLORS.get(item_type, (80, 80, 80))
        slot_col = tuple(min(255, c + 45) for c in base_col) if is_sel else base_col
        pygame.draw.rect(screen, slot_col, slot_rect, border_radius=6)

        b_color = INV_SEL_COLOR if is_sel else INV_BORDER_COLOR
        b_width = 3 if is_sel else 1
        pygame.draw.rect(screen, b_color, slot_rect, b_width, border_radius=6)

        lbl_text = ITEM_LABELS.get(item_type, item_type)
        lbl = font.render(lbl_text, True, (255, 255, 255))
        screen.blit(lbl, (
            sx + (INV_SLOT_SIZE - lbl.get_width())  // 2,
            slot_y + (INV_SLOT_SIZE - lbl.get_height()) // 2,
        ))

        if qty > 1:
            b_txt  = badge_font.render(str(qty), True, (255, 255, 255))
            b_w    = b_txt.get_width() + 6
            b_h    = b_txt.get_height() + 2
            b_x    = sx + INV_SLOT_SIZE - b_w - 2
            b_y    = slot_y + INV_SLOT_SIZE - b_h - 2
            pygame.draw.rect(screen, (180, 30, 30), (b_x, b_y, b_w, b_h), border_radius=4)
            screen.blit(b_txt, (b_x + 3, b_y + 1))

        rects[item_type] = slot_rect

    return rects


def draw_toasts(screen, toasts):
    if not toasts:
        return
    w, _ = screen.get_size()
    y = 20
    font = get_font("sm", bold=True)
    for toast in toasts[-4:]:
        ttl = max(1, toast.get("ttl", 1))
        alpha = min(230, max(70, int(255 * (ttl / toast.get("max_ttl", ttl)))))
        text = toast.get("text", "")
        color = toast.get("color", COLORS["text"])
        lbl = font.render(text, True, color)
        pad = 10
        rect = pygame.Rect(w - lbl.get_width() - 24 - pad * 2, y, lbl.get_width() + pad * 2, lbl.get_height() + pad * 2)
        box = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        box.fill((20, 24, 34, alpha))
        screen.blit(box, rect.topleft)
        pygame.draw.rect(screen, COLORS["border"], rect, 1, border_radius=8)
        screen.blit(lbl, (rect.x + pad, rect.y + pad))
        y += rect.h + 8


# ============================================================
# ANIMATION SKILL POINT GAGNE
# ============================================================

def draw_skillpoint_anim(screen, timer, total=180):
    """
    Affiche une animation skill point AU-DESSUS de tout le reste.
    Composée sur une surface SRCALPHA unique blittée en dernier.
    timer : 180 -> 0
    """
    w, h = screen.get_size()

    # Calcul alpha (fade in / fade out)
    FADE = 30
    if timer > total - FADE:
        alpha = int(255 * (total - timer) / FADE)
    elif timer < FADE:
        alpha = int(255 * timer / FADE)
    else:
        alpha = 255
    alpha = max(0, min(255, alpha))

    # Position : glisse vers le haut depuis le bas de la zone haut d'écran
    progress  = (total - timer) / total          # 0 → 1
    target_y  = 24                               # position finale (haut)
    start_y   = -100                             # position de départ (hors écran)
    if progress < 0.15:
        t     = progress / 0.15
        anim_y = int(start_y + (target_y - start_y) * t)
    elif progress > 0.85:
        t     = (progress - 0.85) / 0.15
        anim_y = int(target_y - target_y * t * 0.5)
    else:
        anim_y = target_y

    card_w, card_h = 320, 72
    card_x = w // 2 - card_w // 2

    # ── Tout sur une surface SRCALPHA ──────────────────────────
    overlay = pygame.Surface((card_w, card_h), pygame.SRCALPHA)

    # Fond + bordure
    overlay.fill((20, 10, 40, min(230, alpha)))
    pygame.draw.rect(overlay, (255, 205, 92, min(255, alpha)),
                     pygame.Rect(0, 0, card_w, card_h), 3, border_radius=16)

    # Ligne décorative gauche (dorée)
    pygame.draw.rect(overlay, (255, 205, 92, min(255, alpha)),
                     pygame.Rect(0, 0, 5, card_h), border_radius=4)

    fnt_big = get_font("md", bold=True)   # 22px — rentre bien dans le cadre
    fnt_sm  = get_font("xs")              # 14px — sous-titre

    # Titre
    title_surf = fnt_big.render("NIVEAU SUPERIEUR !", True, COLORS["accent"])
    title_surf.set_alpha(alpha)
    overlay.blit(title_surf, (card_w // 2 - title_surf.get_width() // 2, 10))

    # Sous-titre
    sub_surf = fnt_sm.render("+1 point de talent disponible", True, COLORS["muted"])
    sub_surf.set_alpha(alpha)
    overlay.blit(sub_surf, (card_w // 2 - sub_surf.get_width() // 2, 38))

    # Blit final — au-dessus de tout (appelé juste avant display.flip)
    screen.blit(overlay, (card_x, anim_y))
# Modules freres : re-export pour preserver l'API publique
from ui.ui_screens import *
from ui.ui_screens import _pause_confirm_pending, _draw_confirm_popup
from ui.ui_mission import *

# Imports remontes en haut du fichier
from core.config import GRID_WIDTH, GRID_HEIGHT
from core.entities import get_tower_preview
