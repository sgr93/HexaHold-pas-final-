"""
ui.py
-----
Fonctions de rendu de l'interface : HUD, ghost, inventaire, pause, game over,
et LEVEL-UP BANNER (choix de tour en pause).
"""

import random
import pygame
from config import ALL_TOWER_TYPES, GRID_WIDTH, GRID_HEIGHT, GRID_SIZE, COLS, ROWS

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
    "laser":        "Laser lourd",
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
    "laser":        "Laser lourd\nPortée maximale\nTir précis",
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
    info_y = offset_y - 38
    panel = pygame.Rect(offset_x - 8, info_y - 10, GRID_WIDTH + 16, 34)
    _draw_panel(screen, panel, alt=True)
    lvl_txt = font.render(f"Niv.{level}  XP:{xp}/{xp_to_next}", True, COLORS["text"])
    screen.blit(_get_icon("hp", 14, COLORS["accent_alt"]), (offset_x + 4, info_y + 4))
    screen.blit(lvl_txt, (offset_x + 22, info_y))

    wave_txt = font.render(
        f"Vague {wave_number}/{max_waves}  Tués:{mobs_killed}/{max_enemies}",
        True, (255, 255, 180)
    )
    screen.blit(wave_txt, (offset_x + GRID_WIDTH // 2 - wave_txt.get_width() // 2, info_y))

    if boss_active:
        t_color = (255, 80, 80) if boss_timer < 10 else (255, 180, 80)
        t_txt   = font.render(f"BOSS  {boss_timer:.0f}s", True, t_color)
    else:
        t_txt = font.render(f"Vague  {wave_timer:.0f}s", True, (180, 220, 255))
    screen.blit(t_txt, (offset_x + GRID_WIDTH - t_txt.get_width(), info_y))

    if player_hp is not None and player_max_hp:
        bar_w, bar_h = 150, 12
        bx, by = offset_x, info_y - 18
        _draw_progress_bar(screen, pygame.Rect(bx, by, bar_w, bar_h), player_hp, player_max_hp, COLORS["success"], bg=(110, 25, 25))
        hp_lbl = font.render(f"HP {player_hp}/{player_max_hp}", True, (220, 220, 220))
        screen.blit(hp_lbl, (bx + bar_w + 6, by - 1))


# ============================================================
# GHOST DE PLACEMENT
# ============================================================

def draw_ghost(screen, cells, gx, gy, item_type, towers, can_place_fn, offset_x, offset_y):
    from entities import get_tower_preview

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


# ============================================================
# ECRAN DE PAUSE
# ============================================================

def draw_pause_screen(screen, big_font, font):
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))
    pt = big_font.render("PAUSE", True, COLORS["accent"])
    screen.blit(pt, ((w - pt.get_width()) // 2, (h - pt.get_height()) // 2 - 30))
    hint = font.render("Appuyez sur P pour reprendre", True, (200, 200, 200))
    screen.blit(hint, ((w - hint.get_width()) // 2, (h - hint.get_height()) // 2 + 30))


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
    title_surf = big_font.render("✦  CHOIX DE TOUR  ✦", True, (255, 220, 60))
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
