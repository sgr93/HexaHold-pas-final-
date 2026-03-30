"""
menu_screen.py
--------------
Système de menu principal avec 4 onglets :
  - Menu Principal (choix du niveau)
  - Gacha (coffres)
  - Équipement
  - Skill Tree
"""

import pygame
import save_data as sd
from config import (
    DIFFICULTY_LEVELS, CHEST_COSTS, RARITIES, RARITY_COLORS,
    EQUIPMENT_SLOTS, EQUIPMENT_STATS, ALL_TOWER_TYPES, TOWER_SLOT_COUNT,
)
from ui import ITEM_LABELS, ITEM_COLORS

# ── Couleurs ──────────────────────────────────────────────────────────────
C_BG        = (18, 18, 28)
C_PANEL     = (30, 32, 48)
C_PANEL2    = (38, 40, 58)
C_ACCENT    = (255, 200, 60)
C_ACCENT2   = (80, 180, 255)
C_TEXT      = (230, 230, 240)
C_SUBTEXT   = (150, 155, 175)
C_BTN       = (50, 55, 80)
C_BTN_HOV   = (70, 75, 110)
C_BTN_BOR   = (90, 95, 130)
C_TAB_ACT   = (60, 65, 100)
C_TAB_INACT = (35, 38, 55)
C_GREEN     = (60, 200, 100)
C_RED       = (220, 60, 60)

DIFF_COLORS = {
    1: (80,  200, 100),
    2: (140, 220, 80 ),
    3: (255, 200, 40 ),
    4: (255, 120, 40 ),
    5: (255, 60,  60 ),
}

CHEST_INFO = {
    "wood":   {"label": "Coffre en Bois",   "color": (139, 90,  43 ), "cost": CHEST_COSTS["wood"]  },
    "silver": {"label": "Coffre en Argent", "color": (170, 180, 200), "cost": CHEST_COSTS["silver"]},
    "gold":   {"label": "Coffre en Or",     "color": (220, 180, 30 ), "cost": CHEST_COSTS["gold"]  },
}

SLOT_ICONS = {
    "casque":   "⛨",
    "armure":   "🛡",
    "pantalon": "👖",
    "arme":     "⚔",
    "tour":     "🗼",
}
SLOT_LABELS = {
    "casque":   "Casque",
    "armure":   "Armure",
    "pantalon": "Pantalon",
    "arme":     "Arme",
    "tour":     "Tour",
}


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
    font_big   = pygame.font.SysFont("arial", 56, bold=True)
    font_med   = pygame.font.SysFont("arial", 28, bold=True)
    font_sm    = pygame.font.SysFont("arial", 20)
    font_xs    = pygame.font.SysFont("arial", 14)

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
    font_med   = pygame.font.SysFont("arial", 24, bold=True)
    font_sm    = pygame.font.SysFont("arial", 18)
    font_xs    = pygame.font.SysFont("arial", 14)

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
    font_big   = pygame.font.SysFont("arial", 36, bold=True)
    font_med   = pygame.font.SysFont("arial", 24, bold=True)
    font_sm    = pygame.font.SysFont("arial", 18)
    font_xs    = pygame.font.SysFont("arial", 14)

    tabs       = ["Menu Principal", "Gacha", "Équipement", "Skill Tree"]
    active_tab = 0

    # État gacha
    last_item_obtained = None
    gacha_msg          = ""
    gacha_msg_timer    = 0

    # État équipement
    selected_inv_idx       = None    # index dans save["inventory_equipment"]
    selected_loadout_slot  = 0
    selected_equip_category = 0
    dragging_item          = None
    drag_offset            = (0, 0)
    save.setdefault("tower_loadout", ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
    if len(save["tower_loadout"]) < TOWER_SLOT_COUNT:
        save["tower_loadout"] = (save["tower_loadout"] + ALL_TOWER_TYPES)[:TOWER_SLOT_COUNT]

    running = True
    chosen_level = None

    while running:
        w, h = screen.get_size()
        screen.fill(C_BG)

        mx, my = pygame.mouse.get_pos()
        clicked = False
        mouse_released = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, save
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None, save
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_released = True

        # ── Header / Title ────────────────────────────────────────────────
        title = font_big.render("HEXAHOLD", True, C_ACCENT)
        screen.blit(title, (w // 2 - title.get_width() // 2, 16))

        # Pièces
        coins_lbl = font_med.render(f"💰 {save['coins']} pièces", True, C_ACCENT)
        screen.blit(coins_lbl, (w - coins_lbl.get_width() - 20, 20))

        # ── Onglets ────────────────────────────────────────────────────────
        tab_h   = 40
        tab_y   = 65
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
            panel = pygame.Rect(20, content_y + 20, w - 40, content_h - 40)
            _draw_rounded_rect(screen, C_PANEL, panel, radius=12)

            subtitle = font_med.render("Choisissez un niveau", True, C_TEXT)
            screen.blit(subtitle, (panel.x + (panel.w - subtitle.get_width()) // 2, panel.y + 18))

            btn_h = 70
            btn_gap = 14
            start_y = panel.y + 70
            for lvl, info in DIFFICULTY_LEVELS.items():
                btn = pygame.Rect(panel.x + 30, start_y, panel.w - 60, btn_h)
                hov = btn.collidepoint(mx, my)
                col = C_BTN_HOV if hov else C_BTN
                _draw_rounded_rect(screen, col, btn, radius=10,
                                   border=2, border_color=DIFF_COLORS[lvl])

                name_lbl = font_med.render(f"Niveau {lvl} — {info['name']}", True, DIFF_COLORS[lvl])
                screen.blit(name_lbl, (btn.x + 18, btn.y + 8))

                detail = font_xs.render(
                    f"{info['waves']} vagues  |  Mult. ennemis ×{info['enemy_hp_mult']}  |  Récompense : {info['coins_reward']} pièces",
                    True, C_SUBTEXT
                )
                screen.blit(detail, (btn.x + 18, btn.y + 38))

                if clicked and hov:
                    chosen_level = lvl
                    running = False

                start_y += btn_h + btn_gap

            note = font_xs.render("Sélectionnez vos tours dans l'onglet Équipement avant de jouer.", True, C_SUBTEXT)
            screen.blit(note, (panel.x + 30, panel.y + panel.h - 40))

        # ────────────────────────────────────────────────────────────────────
        # TAB 1 : GACHA
        # ────────────────────────────────────────────────────────────────────
        elif active_tab == 1:
            # Panneau coffres
            panel_w = min(700, w - 40)
            panel   = pygame.Rect(w // 2 - panel_w // 2, content_y + 10, panel_w, 200)
            _draw_rounded_rect(screen, C_PANEL, panel, radius=12)
            sub = font_med.render("Ouvrir un coffre", True, C_TEXT)
            screen.blit(sub, (panel.x + (panel.w - sub.get_width()) // 2, panel.y + 12))

            chest_btn_w = (panel.w - 80) // 3
            chest_y     = panel.y + 50
            chest_btn_rects = {}
            for ci, (ctype, cinfo) in enumerate(CHEST_INFO.items()):
                cx   = panel.x + 30 + ci * (chest_btn_w + 20)
                cbtn = pygame.Rect(cx, chest_y, chest_btn_w, 110)
                hov  = cbtn.collidepoint(mx, my)
                can  = save["coins"] >= cinfo["cost"]
                col  = (min(cinfo["color"][0]+20, 255),
                         min(cinfo["color"][1]+20, 255),
                         min(cinfo["color"][2]+20, 255)) if hov and can else cinfo["color"]
                bdr  = (255, 220, 80) if can else (80, 80, 80)
                _draw_rounded_rect(screen, col, cbtn, radius=10, border=2, border_color=bdr)
                chest_btn_rects[ctype] = cbtn

                lbl = font_sm.render(cinfo["label"], True, (255,255,255))
                screen.blit(lbl, (cbtn.x + (cbtn.w - lbl.get_width()) // 2, cbtn.y + 12))

                cost_lbl = font_sm.render(f"{cinfo['cost']} 💰", True,
                                          C_ACCENT if can else C_RED)
                screen.blit(cost_lbl, (cbtn.x + (cbtn.w - cost_lbl.get_width()) // 2,
                                        cbtn.y + 45))

                if not can:
                    nl = font_xs.render("Insuffisant", True, C_RED)
                    screen.blit(nl, (cbtn.x + (cbtn.w - nl.get_width()) // 2, cbtn.y + 75))

                if clicked and hov and can:
                    ok, result = sd.open_chest(save, ctype)
                    if ok:
                        last_item_obtained = result
                        gacha_msg         = f"Obtenu : {result['name']} (+{result['value']} {result['label']})"
                        gacha_msg_timer   = 240
                    else:
                        gacha_msg       = result
                        gacha_msg_timer = 120

            # Message résultat
            if gacha_msg_timer > 0:
                gacha_msg_timer -= 1
                alpha = min(255, gacha_msg_timer * 3)
                if last_item_obtained and gacha_msg_timer > 0:
                    rc = tuple(last_item_obtained["color"])
                    msg_lbl = font_med.render(gacha_msg, True, rc)
                else:
                    msg_lbl = font_med.render(gacha_msg, True, C_RED)
                screen.blit(msg_lbl, (w // 2 - msg_lbl.get_width() // 2, panel.y + panel.h + 14))

                # Affichage de l'item obtenu
                if last_item_obtained and gacha_msg_timer > 0:
                    _draw_item_card(screen, font_med, font_sm, font_xs,
                                    last_item_obtained,
                                    pygame.Rect(w // 2 - 160, panel.y + panel.h + 48, 320, 110))

            # Inventaire équipement scrollable
            inv_panel = pygame.Rect(w // 2 - panel_w // 2, content_y + 230,
                                     panel_w, content_h - 240)
            _draw_rounded_rect(screen, C_PANEL, inv_panel, radius=12)
            inv_title = font_sm.render(f"Équipements obtenus ({len(save['inventory_equipment'])})",
                                       True, C_TEXT)
            screen.blit(inv_title, (inv_panel.x + 16, inv_panel.y + 10))

            _draw_equipment_list(screen, font_sm, font_xs, save,
                                  pygame.Rect(inv_panel.x + 10, inv_panel.y + 38,
                                               inv_panel.w - 20, inv_panel.h - 50),
                                  None, mx, my, clicked,
                                  select_callback=None, show_equip_btn=False)

        # ────────────────────────────────────────────────────────────────────
        # TAB 2 : ÉQUIPEMENT
        # ────────────────────────────────────────────────────────────────────
        elif active_tab == 2:
            categories = ["casque", "armure", "pantalon", "arme", "tour"]
            category_labels = ["Casque", "Armure", "Pantalon", "Arme", "Tour"]
            category_slot = categories[selected_equip_category]
            slot_titles = {"casque": "Casque", "armure": "Armure", "pantalon": "Pantalon", "arme": "Arme", "tour": "Tour"}

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
            pygame.draw.circle(screen, (120, 120, 120), (center_x, head_y), 34)
            body_rect = pygame.Rect(center_x - 36, body_y, 72, 120)
            pygame.draw.rect(screen, (140, 140, 140), body_rect, border_radius=24)
            pygame.draw.line(screen, (140, 140, 140), (center_x, body_y + 45), (center_x - 45, body_y + 90), 10)
            pygame.draw.line(screen, (140, 140, 140), (center_x, body_y + 45), (center_x + 45, body_y + 90), 10)
            pygame.draw.line(screen, (140, 140, 140), (center_x - 20, body_y + 115), (center_x - 20, body_y + 170), 10)
            pygame.draw.line(screen, (140, 140, 140), (center_x + 20, body_y + 115), (center_x + 20, body_y + 170), 10)

            def _draw_arrow(start, end):
                pygame.draw.line(screen, C_ACCENT2, start, end, 2)
                pygame.draw.circle(screen, C_ACCENT2, end, 4)

            slot_boxes = {
                "casque": pygame.Rect(center_x - 75, head_y - 140, 150, 40),
                "armure": pygame.Rect(left_panel.x + 18, body_y + 20, 140, 40),
                "arme": pygame.Rect(left_panel.right - 158, body_y + 10, 140, 40),
                "pantalon": pygame.Rect(left_panel.right - 158, body_y + 100, 140, 40),
                "tour": pygame.Rect(center_x - 75, left_panel.y + left_panel.h - 90, 150, 40),
            }

            _draw_arrow((center_x, head_y - 30), (slot_boxes["casque"].centerx, slot_boxes["casque"].bottom))
            _draw_arrow((center_x - 30, body_y + 35), (slot_boxes["armure"].right, slot_boxes["armure"].centery))
            _draw_arrow((center_x + 30, body_y + 35), (slot_boxes["arme"].left, slot_boxes["arme"].centery))
            _draw_arrow((center_x + 20, body_y + 120), (slot_boxes["pantalon"].left, slot_boxes["pantalon"].centery))
            _draw_arrow((center_x, body_y + 140), (slot_boxes["tour"].centerx, slot_boxes["tour"].top))

            equip_ref = save["equipped"]
            inv_items = save["inventory_equipment"]
            drag_item_data = None
            if dragging_item is not None and 0 <= dragging_item < len(inv_items):
                drag_item_data = inv_items[dragging_item]

            def _label_for_slot(slot_key):
                idx = equip_ref.get(slot_key)
                if idx is not None and 0 <= idx < len(inv_items):
                    return inv_items[idx]["name"]
                return "Aucun"

            labels = {key: _label_for_slot(key) for key in slot_boxes}

            for slot_key, rect in slot_boxes.items():
                item_name = labels[slot_key]
                is_filled = equip_ref.get(slot_key) is not None
                hovered = rect.collidepoint(mx, my)
                valid_drop = drag_item_data is not None and drag_item_data["slot"] == slot_key
                if hovered and drag_item_data is not None:
                    border_color = C_GREEN if valid_drop else C_RED
                elif is_filled:
                    border_color = C_GREEN
                else:
                    border_color = C_BTN_BOR
                _draw_rounded_rect(screen, C_PANEL2, rect, radius=14, border=2, border_color=border_color)
                label_text = f"{slot_titles[slot_key]} : {item_name}"
                lbl = font_xs.render(label_text, True, C_TEXT if is_filled else C_SUBTEXT)
                screen.blit(lbl, (rect.x + 12, rect.y + (rect.h - lbl.get_height()) // 2))
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
            if len(tower_loadout) < TOWER_SLOT_COUNT:
                tower_loadout = (tower_loadout + ALL_TOWER_TYPES)[:TOWER_SLOT_COUNT]
                save["tower_loadout"] = tower_loadout

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
                tower_label = ITEM_LABELS.get(tower_loadout[i], tower_loadout[i])
                lbl = font_xs.render(tower_label, True, C_TEXT)
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
                assigned = tower_type in tower_loadout
                is_selected = tower_type == tower_loadout[selected_loadout_slot]
                cell_color = C_BTN_HOV if is_selected else (C_PANEL if assigned else C_BTN)
                _draw_rounded_rect(screen, cell_color, cell, radius=8,
                                   border=2, border_color=C_ACCENT2 if is_selected else C_BTN_BOR)
                tlabel = ITEM_LABELS.get(tower_type, tower_type)
                text = font_xs.render(tlabel, True, C_TEXT)
                screen.blit(text, (cell.x + (cell.w - text.get_width()) // 2,
                                   cell.y + (cell.h - text.get_height()) // 2))
                if clicked and cell.collidepoint(mx, my):
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

            category_items = [
                (idx, item) for idx, item in enumerate(inv_items)
                if item["slot"] == category_slot
            ]
            if not category_items:
                none_lbl = font_sm.render(f"Aucun {category_labels[selected_equip_category].lower()} trouvé.", True, C_SUBTEXT)
                screen.blit(none_lbl, (item_area.x + 16, item_area.y + 40))
            else:
                row_h = 64
                row_gap = 8
                for li, (item_idx, item) in enumerate(category_items):
                    row_y = item_area.y + 44 + li * (row_h + row_gap)
                    row = pygame.Rect(item_area.x + 8, row_y, item_area.w - 16, row_h)
                    is_sel = (selected_inv_idx == li)
                    _draw_rounded_rect(screen, C_PANEL if is_sel else C_BTN, row,
                                       radius=8, border=2,
                                       border_color=C_ACCENT2 if is_sel else C_BTN_BOR)

                    name_lbl = font_sm.render(item["name"], True, tuple(item["color"]))
                    screen.blit(name_lbl, (row.x + 12, row.y + 10))
                    stat_lbl = font_xs.render(f"+{item['value']} {item['label']}", True, C_SUBTEXT)
                    screen.blit(stat_lbl, (row.x + 12, row.y + 34))

                    eq_btn = pygame.Rect(row.right - 90, row.y + 16, 76, 32)
                    already = save["equipped"].get(category_slot) == item_idx
                    btn_color = C_BTN_HOV if eq_btn.collidepoint(mx, my) and not already else C_BTN
                    _draw_rounded_rect(screen, btn_color, eq_btn, radius=8,
                                       border=1, border_color=C_ACCENT2)
                    btn_lbl = font_xs.render("Équipé" if already else "Équiper", True, C_TEXT)
                    screen.blit(btn_lbl, (eq_btn.x + (eq_btn.w - btn_lbl.get_width()) // 2,
                                           eq_btn.y + (eq_btn.h - btn_lbl.get_height()) // 2))

                    if clicked and eq_btn.collidepoint(mx, my) and not already:
                        save["equipped"][category_slot] = item_idx
                        sd.save(save)
                    elif clicked and row.collidepoint(mx, my):
                        selected_inv_idx = li
                        dragging_item = item_idx
                        drag_offset = (row.x - mx, row.y - my)

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
                dname = font_sm.render(drag_item_data["name"], True, tuple(drag_item_data["color"]))
                screen.blit(dname, (drag_rect.x + 10, drag_rect.y + 6))
                dstat = font_xs.render(f"+{drag_item_data['value']} {drag_item_data['label']}", True, C_SUBTEXT)
                screen.blit(dstat, (drag_rect.x + 10, drag_rect.y + 28))

            selected_info = font_sm.render("Sélection : " + category_labels[selected_equip_category], True, C_TEXT)
            screen.blit(selected_info, (right_panel.x + 14, right_panel.y + right_panel.h - 24))

        # ────────────────────────────────────────────────────────────────────
        # TAB 3 : SKILL TREE (placeholder)
        # ────────────────────────────────────────────────────────────────────
        elif active_tab == 3:
            panel = pygame.Rect(w // 2 - 300, content_y + 20, 600, content_h - 30)
            _draw_rounded_rect(screen, C_PANEL, panel, radius=12)

            st = font_med.render("Arbre de Compétences", True, C_ACCENT)
            screen.blit(st, (panel.x + (panel.w - st.get_width()) // 2, panel.y + 18))

            note = font_sm.render("(Fonctionnalité à venir — en cours de développement)", True, C_SUBTEXT)
            screen.blit(note, (panel.x + (panel.w - note.get_width()) // 2, panel.y + 62))

            # Quelques nœuds décoratifs
            nodes = [
                {"name": "Force",      "x": panel.x + 100, "y": panel.y + 140, "unlocked": True },
                {"name": "Rapidité",   "x": panel.x + 300, "y": panel.y + 140, "unlocked": True },
                {"name": "Résistance", "x": panel.x + 500, "y": panel.y + 140, "unlocked": False},
                {"name": "Maîtrise",   "x": panel.x + 200, "y": panel.y + 240, "unlocked": False},
                {"name": "Puissance",  "x": panel.x + 400, "y": panel.y + 240, "unlocked": False},
                {"name": "Légende",    "x": panel.x + 300, "y": panel.y + 340, "unlocked": False},
            ]
            # Connexions
            edges = [(0,1),(1,2),(0,3),(1,3),(1,4),(2,4),(3,5),(4,5)]
            for a, b in edges:
                pygame.draw.line(screen, C_BTN_BOR,
                                 (nodes[a]["x"], nodes[a]["y"]),
                                 (nodes[b]["x"], nodes[b]["y"]), 2)
            for nd in nodes:
                col  = C_ACCENT if nd["unlocked"] else C_BTN
                bord = C_GREEN  if nd["unlocked"] else C_SUBTEXT
                pygame.draw.circle(screen, col, (nd["x"], nd["y"]), 28)
                pygame.draw.circle(screen, bord, (nd["x"], nd["y"]), 28, 2)
                nlbl = font_xs.render(nd["name"], True, C_TEXT)
                screen.blit(nlbl, (nd["x"] - nlbl.get_width() // 2, nd["y"] - nlbl.get_height() // 2))

            info_lbl = font_xs.render("(Les compétences s'achèteront avec des points de skill obtenus en jouant)",
                                       True, C_SUBTEXT)
            screen.blit(info_lbl, (panel.x + (panel.w - info_lbl.get_width()) // 2,
                                    panel.y + panel.h - 30))

        pygame.display.flip()
        clock.tick(60)

    if chosen_level is not None:
        return chosen_level, save
    return None, save


def _draw_item_card(screen, font_med, font_sm, font_xs, item, rect):
    rc = tuple(item["color"])
    _draw_rounded_rect(screen, C_PANEL2, rect, radius=10, border=2, border_color=rc)
    n = font_sm.render(item["name"], True, rc)
    screen.blit(n, (rect.x + (rect.w - n.get_width()) // 2, rect.y + 10))
    v = font_sm.render(f"+{item['value']} {item['label']}", True, C_TEXT)
    screen.blit(v, (rect.x + (rect.w - v.get_width()) // 2, rect.y + 40))
    s = font_xs.render(f"Slot : {SLOT_LABELS.get(item['slot'], item['slot'])}", True, C_SUBTEXT)
    screen.blit(s, (rect.x + (rect.w - s.get_width()) // 2, rect.y + 72))


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

        name_lbl = font_sm.render(item["name"], True, rc)
        screen.blit(name_lbl, (row.x + 10, row.y + 6))

        val_lbl = font_xs.render(f"+{item['value']} {item['label']}", True, C_SUBTEXT)
        screen.blit(val_lbl, (row.x + 10, row.y + 26))

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
