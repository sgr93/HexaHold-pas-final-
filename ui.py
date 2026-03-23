"""
ui.py
-----
Fonctions de rendu de l'interface : menu principal, HUD, ghost de placement,
inventaire bas-écran, écran de pause, écran Game Over.

"""

import pygame
from config import GRID_WIDTH, GRID_HEIGHT, GRID_SIZE, COLS, ROWS

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
    "small": "Tour S",
    "big":   "Tour B",
    "trap":  "Piege",
}
ITEM_COLORS = {
    "small": (0, 150, 200),
    "big":   (0, 100, 180),
    "trap":  (100, 100, 100),
}


# ============================================================
# MENU PRINCIPAL
# ============================================================

def main_menu(screen, clock):
    font     = pygame.font.SysFont(None, 64)
    sub_font = pygame.font.SysFont(None, 32)
    running  = True
    while running:
        screen.fill((20, 20, 30))
        w, h = screen.get_size()
        title = font.render("HEXAHOLD", True, (255, 220, 80))
        screen.blit(title, ((w - title.get_width()) // 2, h // 3))
        sub = sub_font.render("Cliquez ou appuyez sur Entree pour jouer", True, (180, 180, 180))
        screen.blit(sub, ((w - sub.get_width()) // 2, h // 2))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False


# ============================================================
# HUD
# ============================================================

def draw_hud(screen, font, big_font, level, xp, xp_to_next,
             wave_number, max_waves, mobs_killed, max_enemies,
             boss_active, boss_timer, wave_timer,
             offset_x, offset_y,
             player_hp=None, player_max_hp=None):
    info_y = offset_y - 30
    lvl_txt = font.render(f"Niv.{level}  XP:{xp}/{xp_to_next}", True, (200, 255, 200))
    screen.blit(lvl_txt, (offset_x, info_y))

    wave_txt = font.render(
        f"Vague {wave_number}/{max_waves}  Tues:{mobs_killed}/{max_enemies}",
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
        bar_w, bar_h = 120, 10
        bx, by = offset_x, info_y - 18
        pygame.draw.rect(screen, (120, 0, 0),     (bx, by, bar_w, bar_h))
        fill_w = int(bar_w * max(0, player_hp) / player_max_hp)
        pygame.draw.rect(screen, (0, 200, 0),     (bx, by, fill_w, bar_h))
        pygame.draw.rect(screen, (200, 200, 200), (bx, by, bar_w, bar_h), 1)
        hp_lbl = font.render(f"HP {player_hp}/{player_max_hp}", True, (220, 220, 220))
        screen.blit(hp_lbl, (bx + bar_w + 6, by - 1))


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
    color = (0, 255, 0, 80) if valid else (255, 0, 0, 80)
    ghost_surf = pygame.Surface((GRID_WIDTH, GRID_HEIGHT), pygame.SRCALPHA)
    for cx, cy in cells:
        # FIX-8 : on ne dessine que les cases dans les limites de la grille
        if 0 <= cx < COLS and 0 <= cy < ROWS:
            pygame.draw.rect(ghost_surf, color,
                             pygame.Rect(cx * GRID_SIZE, cy * GRID_SIZE, GRID_SIZE, GRID_SIZE))
    screen.blit(ghost_surf, (offset_x, offset_y))
    if is_upgrade:
        f2 = pygame.font.SysFont(None, 20)
        lbl = f2.render("UPGRADE", True, (255, 255, 100))
        # Ne calcule le centre que sur les cases valides
        valid_cells = [(cx, cy) for cx, cy in cells if 0 <= cx < COLS and 0 <= cy < ROWS]
        if valid_cells:
            mx_ = sum(c[0] for c in valid_cells) / len(valid_cells) * GRID_SIZE + offset_x
            my_ = sum(c[1] for c in valid_cells) / len(valid_cells) * GRID_SIZE + offset_y
            screen.blit(lbl, (int(mx_) - lbl.get_width() // 2, int(my_) - 10))


# ============================================================
# INVENTAIRE BAS-ECRAN
# ============================================================

def draw_inventory(screen, font, inventory, selected_item, win_w, win_h):
    """
    Dessine la barre d'inventaire en bas de l'ecran.

    inventory     : dict { item_type: quantite }  ex. {"small": 2, "trap": 1}
    selected_item : item_type actuellement selectionne (ou None)

    Retourne un dict { item_type: pygame.Rect } pour la detection de clics.

    Visuellement :
    - Fond marron sur toute la largeur
    - Slots centres avec icone coloree et label
    - Slot selectionne : contour jaune epais + fond plus clair
    - Quantite > 1 : badge rouge en bas-droite du slot
    - Inventaire vide : message d'aide centre
    """
    # Fond marron
    bar_rect = pygame.Rect(0, win_h - INV_BAR_HEIGHT, win_w, INV_BAR_HEIGHT)
    pygame.draw.rect(screen, INV_BG_COLOR, bar_rect)
    pygame.draw.line(screen, INV_BORDER_COLOR,
                     (0, win_h - INV_BAR_HEIGHT), (win_w, win_h - INV_BAR_HEIGHT), 2)

    # Label "Inventaire" a gauche
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

    # Centrage des slots
    total_w = len(present) * INV_SLOT_SIZE + (len(present) - 1) * INV_SLOT_GAP
    start_x = (win_w - total_w) // 2
    slot_y  = win_h - INV_BAR_HEIGHT + (INV_BAR_HEIGHT - INV_SLOT_SIZE) // 2

    badge_font = pygame.font.SysFont(None, 20)

    for i, (item_type, qty) in enumerate(present):
        sx        = start_x + i * (INV_SLOT_SIZE + INV_SLOT_GAP)
        slot_rect = pygame.Rect(sx, slot_y, INV_SLOT_SIZE, INV_SLOT_SIZE)
        is_sel    = (item_type == selected_item)

        # Fond du slot (plus clair si selectionne)
        base_col = ITEM_COLORS.get(item_type, (80, 80, 80))
        slot_col = tuple(min(255, c + 45) for c in base_col) if is_sel else base_col
        pygame.draw.rect(screen, slot_col, slot_rect, border_radius=6)

        # Bordure
        b_color = INV_SEL_COLOR if is_sel else INV_BORDER_COLOR
        b_width = 3 if is_sel else 1
        pygame.draw.rect(screen, b_color, slot_rect, b_width, border_radius=6)

        # Label centre
        lbl_text = ITEM_LABELS.get(item_type, item_type)
        lbl      = font.render(lbl_text, True, (255, 255, 255))
        screen.blit(lbl, (
            sx + (INV_SLOT_SIZE - lbl.get_width())  // 2,
            slot_y + (INV_SLOT_SIZE - lbl.get_height()) // 2,
        ))

        # Badge quantite (si > 1)
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
    pt = big_font.render("PAUSE", True, (255, 255, 255))
    screen.blit(pt, ((w - pt.get_width()) // 2, (h - pt.get_height()) // 2 - 30))
    hint = font.render("Appuyez sur P pour reprendre", True, (200, 200, 200))
    screen.blit(hint, ((w - hint.get_width()) // 2, (h - hint.get_height()) // 2 + 30))


# ============================================================
# ECRAN GAME OVER / VICTOIRE
# ============================================================

def draw_gameover_screen(screen, big_font, font, win, mouse_pos, clicked):
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    msg, color = ("VICTOIRE !", (80, 255, 80)) if win else ("GAME OVER", (255, 60, 60))
    title = big_font.render(msg, True, color)
    screen.blit(title, ((w - title.get_width()) // 2, h // 2 - 80))

    btn_w, btn_h = 200, 50
    btn_x, btn_y = (w - btn_w) // 2, h // 2
    btn_rect  = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    hovered   = btn_rect.collidepoint(mouse_pos)
    btn_color = (100, 180, 100) if hovered else (60, 120, 60)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=8)
    pygame.draw.rect(screen, (200, 255, 200), btn_rect, 2, border_radius=8)
    lbl = font.render("Rejouer", True, (255, 255, 255))
    screen.blit(lbl, (btn_x + (btn_w - lbl.get_width()) // 2,
                       btn_y + (btn_h - lbl.get_height()) // 2))
    return clicked and hovered


# ============================================================
# MESSAGE DE DEMARRAGE
# ============================================================

def draw_start_hint(screen, font, offset_x, offset_y):
    hint = font.render("Placez une tour pour demarrer", True, (220, 220, 100))
    screen.blit(hint, (
        offset_x + (GRID_WIDTH  - hint.get_width())  // 2,
        offset_y + (GRID_HEIGHT - hint.get_height()) // 2,
    ))
