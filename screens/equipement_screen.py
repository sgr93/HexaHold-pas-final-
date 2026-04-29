"""
screens/equipement_screen.py
-----------------------------
Écran Équipement — version modernisée :
- Slots gauche/droite autour d'Eren
- Loadout de tours en bas
- Inventaire avec onglets
- Popup d’info détaillée (stats, niveau, vente, équiper)
- Tri des équipements par rareté
"""

import os
import pygame
import theme
import save_data as sd
from config import ALL_TOWER_TYPES, TOWER_SLOT_COUNT, EQUIPMENT_STATS

# Slots autour du perso
SLOTS_LEFT  = ["cape", "veste"]
SLOTS_RIGHT = ["arme", "bottes"]
SLOT_LABELS = {
    "cape":   "Cape",
    "veste":  "Veste",
    "bottes": "Bottes",
    "arme":   "Arme",
    "tour":   "Tour",
}

EQUIPMENT_IMAGE_FILES = {
    "cape":   "cape.png",
    "veste":  "veste.png",
    "bottes": "bottes.png",
    "arme":   "lames.png",
    "tour":   "tour.png",
}

RARITY_COLORS = {
    "Commun":     (120, 120, 128),
    "Rare":       (70, 130, 235),
    "Épique":     (150, 90, 220),
    "Légendaire": (230, 190, 60),
    "Mythique":   (255, 60, 220),
    # Aliases sans accents (ancienne sauvegarde)
    "Epique":     (150, 90, 220),
    "Legendaire": (230, 190, 60),
}

# Valeur de vente par rareté
SELL_VALUES = {
    "Commun":     25,
    "Rare":       75,
    "Épique":     200,
    "Légendaire": 500,
    "Mythique":   1200,
    # Aliases sans accents
    "Epique":     200,
    "Legendaire": 500,
}

# Ordre de tri par rareté (du plus rare au plus commun)
RARITY_ORDER = {
    "Mythique":   5,
    "Légendaire": 4,
    "Épique":     3,
    "Rare":       2,
    "Commun":     1,
    # Aliases sans accents
    "Legendaire": 4,
    "Epique":     3,
}

TOWER_DESCRIPTIONS = {
    "small":   "Tour légère à tir rapide. Idéale en début de partie pour harceler les ennemis à faible portée.",
    "big":     "Tour lourde au tir lent mais très puissant. Excellente contre les ennemis blindés.",
    "trap":    "Piège au sol qui s'active au passage des ennemis. Invisible jusqu'au contact.",
    "sniper":  "Tour longue portée à dégâts élevés. Cible en priorité l'ennemi le plus avancé.",
    "mortar":  "Lance des obus en zone. Efficace contre les groupes mais lente à recharger.",
    "frost":   "Ralentit les ennemis dans sa zone. Ne tue pas mais facilite le travail des autres tours.",
    "tesla":   "Décharge électrique qui se propage entre ennemis proches. Dévastatrice en groupe.",
    "cannon":  "Canon à forte cadence avec bonne portée. Bon équilibre entre vitesse et puissance.",
    "laser":   "Rayon continu infligeant des dégâts par seconde. Très efficace sur les boss.",
}

_sprite_cache = {}


def _load_sprite(filename, size=None):
    if not filename:
        return None
    key = (filename, size)
    if key in _sprite_cache:
        return _sprite_cache[key]
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", filename)
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        _sprite_cache[key] = img
    except Exception:
        _sprite_cache[key] = None
    return _sprite_cache[key]


def _rarity_color(item):
    return RARITY_COLORS.get(item.get("rarity", "Commun"), (120, 120, 128))


def _draw_eq_slot(screen, rect, item, label, f_label, f_lvl):
    """Slot d'équipement (90x90) avec couleur de rareté."""
    if item:
        col = _rarity_color(item)
        border_w = 2
    else:
        col = (80, 68, 46)
        border_w = 1

    pygame.draw.rect(screen, (6, 4, 2), rect)
    pygame.draw.rect(screen, col, rect, border_w)

    # Image ou placeholder
    img_name = item.get("image") or EQUIPMENT_IMAGE_FILES.get(item.get("slot", "")) if item else None
    img = _load_sprite(img_name) if img_name else None
    inner = pygame.Rect(rect.x + 4, rect.y + 4, rect.w - 8, rect.h - 24)
    if img:
        scaled = pygame.transform.smoothscale(img, (inner.w, inner.h))
        screen.blit(scaled, inner.topleft)
    else:
        pygame.draw.rect(screen, (20, 15, 8), inner)
        pygame.draw.rect(screen, (60, 48, 28), inner, 1)
        lbl_s = f_label.render(label, True, theme.GOLD_DIM)
        screen.blit(lbl_s, (rect.centerx - lbl_s.get_width() // 2,
                            inner.centery - lbl_s.get_height() // 2))

    # Niveau sous l'image
    if item:
        lvl_s = f_lvl.render(f"Niv.{item.get('level', 1)}", True, theme.GOLD_LIGHT)
    else:
        lvl_s = f_lvl.render(label, True, theme.GOLD_DIM)
    screen.blit(lvl_s, (rect.centerx - lvl_s.get_width() // 2,
                        rect.bottom - lvl_s.get_height() - 2))


def _draw_tour_slot(screen, rect, tower_type, f_lvl):
    """Slot de tour dans le loadout."""
    if tower_type:
        col = (107, 93, 63)
        border_w = 2
    else:
        col = (50, 42, 28)
        border_w = 1

    pygame.draw.rect(screen, (6, 4, 2), rect)
    pygame.draw.rect(screen, col, rect, border_w)

    img = _load_sprite(f"{tower_type}.png") if tower_type else None
    inner = pygame.Rect(rect.x + 4, rect.y + 4, rect.w - 8, rect.h - 20)
    if img:
        scaled = pygame.transform.smoothscale(img, (inner.w, inner.h))
        screen.blit(scaled, inner.topleft)
    else:
        pygame.draw.rect(screen, (20, 15, 8), inner)
        pygame.draw.rect(screen, (50, 42, 28), inner, 1)

    from ui import ITEM_LABELS
    name = ITEM_LABELS.get(tower_type, tower_type or "—")[:8] if tower_type else "—"
    ns = f_lvl.render(name, True, theme.GOLD_LIGHT if tower_type else theme.GOLD_DIM)
    screen.blit(ns, (rect.centerx - ns.get_width() // 2,
                     rect.bottom - ns.get_height() - 2))


def _draw_panel_popup(screen, rect):
    pygame.draw.rect(screen, (18, 14, 8), rect, border_radius=10)
    pygame.draw.rect(screen, theme.GOLD, rect, 2, border_radius=10)


class EquipementScreen:
    def __init__(self, save):
        self.save = save
        self.inv_tab = "cape"    # cape/veste/bottes/arme/tour
        self.selected_loadout_slot = 0

        # Scroll par onglet
        self.scroll_by_tab = {
            "cape": 0, "veste": 0, "bottes": 0,
            "arme": 0, "tour": 0
        }

        # Popup
        self.popup_open = False
        self.popup_item_idx = None
        self.popup_item_source = None  # "inv" ou "tour"
        self.pending_equip_from_popup = False
        self.pending_sell_idx = None

    # ─────────────────────────────────────────────
    # UTILITAIRES
    # ─────────────────────────────────────────────
    def _get_inventory_item(self, idx):
        inv = self.save.get("inventory_equipment", [])
        if 0 <= idx < len(inv):
            return inv[idx]
        return None

    def _get_item_stats(self, item):
        """Récupère les stats depuis EQUIPMENT_STATS.
        Format config : {"stat": str, "label": str, "values": {"Commun": int, ...}}
        """
        slot      = item.get("slot")
        stats_key = item.get("stats_key") or slot
        entry     = EQUIPMENT_STATS.get(stats_key)
        if not entry:
            return {}
        rarity = item.get("rarity", "Commun")
        level  = item.get("level", 1)
        mult   = 1.0 + 0.1 * (level - 1)
        values = entry.get("values", {})
        base   = values.get(rarity, values.get("Commun", 0))
        label  = entry.get("label", stats_key)
        try:
            val = int(float(base) * mult)
        except Exception:
            val = 0
        return {label: val}

    def _draw_item_popup(self, screen, item, mx, my, clicked):
        """Popup compact avec nom, image, stats, boutons Équiper / Vendre."""
        W, H = 260, 320
        sw, sh = screen.get_size()
        px = sw // 2 - W // 2
        py = sh // 2 - H // 2
        rect = pygame.Rect(px, py, W, H)

        _draw_panel_popup(screen, rect)

        f_title = theme.font(theme.SZ_LABEL, body=True)
        f_txt   = theme.font(theme.SZ_SMALL, body=True)
        f_tiny  = theme.font(theme.SZ_TINY, body=True)

        # Nom
        name = item.get("name") or SLOT_LABELS.get(item.get("slot"), "Équipement")
        lbl = f_title.render(name, True, theme.CREAM)
        screen.blit(lbl, (px + W // 2 - lbl.get_width() // 2, py + 6))

        # Rareté
        rarity = item.get("rarity", "Commun")
        r_col = RARITY_COLORS.get(rarity, theme.CREAM_DIM)
        r_lbl = f_tiny.render(rarity, True, r_col)
        screen.blit(r_lbl, (px + W // 2 - r_lbl.get_width() // 2, py + 6 + lbl.get_height()))

        # Image
        if item.get("tower_type"):
            img_name = f"{item['tower_type']}.png"
        else:
            img_name = item.get("image") or EQUIPMENT_IMAGE_FILES.get(item.get("slot", ""), "")
        img = _load_sprite(img_name)
        if img:
            img_s = pygame.transform.smoothscale(img, (80, 80))
            screen.blit(img_s, (px + W // 2 - 40, py + 40))

        # Niveau
        lvl = item.get("level", 1)
        lvl_lbl = f_tiny.render(f"Niveau {lvl}", True, theme.GOLD_LIGHT)
        screen.blit(lvl_lbl, (px + 12, py + 40))

        # Description (tours) ou Stats (équipements)
        sy = py + 130
        if item.get("tower_type"):
            tower_desc = TOWER_DESCRIPTIONS.get(item["tower_type"], "Aucune description disponible.")
            title_s = f_txt.render("Description :", True, theme.CREAM)
            screen.blit(title_s, (px + 12, sy))
            sy += title_s.get_height() + 6
            words = tower_desc.split()
            line_buf, max_w = [], W - 28
            for word in words:
                test = " ".join(line_buf + [word])
                if f_tiny.size(test)[0] <= max_w:
                    line_buf.append(word)
                else:
                    if line_buf:
                        ls = f_tiny.render(" ".join(line_buf), True, theme.CREAM_DIM)
                        screen.blit(ls, (px + 14, sy))
                        sy += ls.get_height() + 2
                    line_buf = [word]
            if line_buf:
                ls = f_tiny.render(" ".join(line_buf), True, theme.CREAM_DIM)
                screen.blit(ls, (px + 14, sy))
        else:
            stats = self._get_item_stats(item)
            if stats:
                title_s = f_txt.render("Statistiques :", True, theme.CREAM)
                screen.blit(title_s, (px + 12, sy))
                sy += title_s.get_height() + 2
                for k, v in stats.items():
                    line = f_tiny.render(f"{k.capitalize()} : {v}", True, theme.CREAM)
                    screen.blit(line, (px + 18, sy))
                    sy += line.get_height() + 1

        # Valeur de vente
        sell_val = SELL_VALUES.get(rarity, 10)
        sell_txt = f_tiny.render(f"Valeur de vente : {sell_val} pièces", True, theme.CREAM_DIM)
        screen.blit(sell_txt, (px + 12, rect.bottom - 70))

        # Boutons
        btn_w, btn_h = 90, 28
        btn_equip = pygame.Rect(px + 15, rect.bottom - 40, btn_w, btn_h)
        btn_sell  = pygame.Rect(px + W - btn_w - 15, rect.bottom - 40, btn_w, btn_h)

        pygame.draw.rect(screen, (40, 70, 40), btn_equip, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD, btn_equip, 1, border_radius=6)
        e_lbl = f_tiny.render("Équiper", True, theme.CREAM)
        screen.blit(e_lbl, (btn_equip.centerx - e_lbl.get_width() // 2,
                            btn_equip.centery - e_lbl.get_height() // 2))

        pygame.draw.rect(screen, (80, 40, 40), btn_sell, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD, btn_sell, 1, border_radius=6)
        s_lbl = f_tiny.render("Vendre", True, theme.CREAM)
        screen.blit(s_lbl, (btn_sell.centerx - s_lbl.get_width() // 2,
                            btn_sell.centery - s_lbl.get_height() // 2))

        # Fermer (croix)
        close_rect = pygame.Rect(rect.right - 24, rect.top + 6, 18, 18)
        pygame.draw.rect(screen, (40, 40, 40), close_rect, border_radius=4)
        pygame.draw.rect(screen, theme.GOLD_DIM, close_rect, 1, border_radius=4)
        x_lbl = f_tiny.render("X", True, theme.CREAM)
        screen.blit(x_lbl, (close_rect.centerx - x_lbl.get_width() // 2,
                            close_rect.centery - x_lbl.get_height() // 2))

        if clicked:
            if close_rect.collidepoint(mx, my):
                self.popup_open = False
                self.popup_item_idx = None
                self.popup_item_source = None
            elif btn_equip.collidepoint(mx, my):
                self.pending_equip_from_popup = True
            elif btn_sell.collidepoint(mx, my):
                self.pending_sell_idx = self.popup_item_idx

    def _sell_item(self, idx):
        """Vendre un équipement de l'inventaire."""
        inv = self.save.get("inventory_equipment", [])
        if not (0 <= idx < len(inv)):
            return
        item = inv[idx]
        rarity = item.get("rarity", "Commun")
        value = SELL_VALUES.get(rarity, 10)
        self.save["coins"] = self.save.get("coins", 0) + value

        # Retirer des slots équipés
        eqp = self.save.get("equipped", {})
        for k, v in list(eqp.items()):
            if v == idx:
                eqp[k] = None
        # Décaler les index supérieurs
        for k, v in list(eqp.items()):
            if isinstance(v, int) and v > idx:
                eqp[k] = v - 1

        inv.pop(idx)
        self.save["inventory_equipment"] = inv
        self.save["equipped"] = eqp
        sd.save(self.save)

    def _auto_equip_item(self, idx):
        """Équipe l'objet dans son slot naturel."""
        inv = self.save.get("inventory_equipment", [])
        if not (0 <= idx < len(inv)):
            return
        item = inv[idx]
        slot = item.get("slot")
        if not slot:
            return
        eqp = self.save.get("equipped", {})
        eqp[slot] = idx
        self.save["equipped"] = eqp
        sd.save(self.save)

    # ─────────────────────────────────────────────
    # DESSIN PRINCIPAL
    # ─────────────────────────────────────────────
    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save  = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        # Bloquer les clics sur le fond quand le popup est ouvert
        clicked_bg = clicked and not self.popup_open

        pad = 10
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad * 2

        # Titre
        theme.render_text(screen, "Équipement", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, w)
        y += f_sec.get_height() + 10

        # ── PANNEAU PERSO ─────────────────────────
        panel_h = 370
        panel   = pygame.Rect(x, y, w, panel_h)

        bg = _load_sprite("maison1.png")
        if bg:
            bg_s = pygame.transform.smoothscale(bg, (panel.w, panel.h))
            screen.blit(bg_s, panel.topleft)
            ov = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
            ov.fill((10, 7, 4, 70))
            screen.blit(ov, panel.topleft)
        else:
            pygame.draw.rect(screen, theme.DARK_2, panel)
        pygame.draw.rect(screen, theme.GOLD, panel, 2)

        # Eren centré
        eren = _load_sprite("eren.png")
        eren_w, eren_h = 160, 280
        if eren:
            scale  = eren_h / eren.get_height()
            eren_w = int(eren.get_width() * scale)
            eren_s = pygame.transform.smoothscale(eren, (eren_w, eren_h))
            ex     = panel.centerx - eren_w // 2
            ey     = panel.y + 8
            screen.blit(eren_s, (ex, ey))
        else:
            ex = panel.centerx - 55
            ey = panel.y + 8
            ph = pygame.Rect(ex, ey, 110, 170)
            pygame.draw.rect(screen, theme.DARK_3, ph)
            pygame.draw.rect(screen, theme.GOLD_DIM, ph, 1)

        # ── Slots équipement ──────────────────────
        inv = save.get("inventory_equipment", [])
        eqp = save.get("equipped", {})

        SLOT_W, SLOT_H = 90, 90
        GAP = 6

        # On écarte un peu plus les slots d'Eren
        offset = 80  # plus grand qu'avant

        # Gauche : Cape, Veste, Bottes
        left_x = panel.centerx - eren_w // 2 - SLOT_W - offset
        for i, slot in enumerate(SLOTS_LEFT):
            sy = panel.y + 8 + i * (SLOT_H + GAP)
            sr = pygame.Rect(left_x, sy, SLOT_W, SLOT_H)
            idx = eqp.get(slot)
            item = inv[idx] if isinstance(idx, int) and 0 <= idx < len(inv) else None
            _draw_eq_slot(screen, sr, item, SLOT_LABELS[slot], f_ti, f_ti)
            if clicked_bg and sr.collidepoint(mx, my) and item:
                self.popup_open = True
                self.popup_item_idx = idx
                self.popup_item_source = "inv"

        # Droite : Arme, Tour
        right_x = panel.centerx + eren_w // 2 + offset
        for i, slot in enumerate(SLOTS_RIGHT):
            sy = panel.y + 8 + i * (SLOT_H + GAP)
            sr = pygame.Rect(right_x, sy, SLOT_W, SLOT_H)
            idx = eqp.get(slot)
            item = inv[idx] if isinstance(idx, int) and 0 <= idx < len(inv) else None
            _draw_eq_slot(screen, sr, item, SLOT_LABELS[slot], f_ti, f_ti)
            if clicked_bg and sr.collidepoint(mx, my) and item:
                self.popup_open = True
                self.popup_item_idx = idx
                self.popup_item_source = "inv"

        # ── Tours (loadout) en bas ────────────────
        tower_loadout = save.get("tower_loadout", ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
        if not isinstance(tower_loadout, list):
            tower_loadout = list(ALL_TOWER_TYPES[:TOWER_SLOT_COUNT])
        while len(tower_loadout) < TOWER_SLOT_COUNT:
            tower_loadout.append(None)
        tower_loadout = tower_loadout[:TOWER_SLOT_COUNT]

        T_W, T_H = 80, 80
        T_GAP    = 14
        total_tours_w = TOWER_SLOT_COUNT * T_W + (TOWER_SLOT_COUNT - 1) * T_GAP
        tx_start = panel.centerx - total_tours_w // 2
        ty       = panel.bottom - T_H - 10

        tl = f_sm.render("Tours", True, theme.CREAM)
        screen.blit(tl, (panel.centerx - tl.get_width() // 2, ty - tl.get_height() - 4))

        for i, tt in enumerate(tower_loadout):
            tr = pygame.Rect(tx_start + i * (T_W + T_GAP), ty, T_W, T_H)
            is_sel = (i == self.selected_loadout_slot)
            _draw_tour_slot(screen, tr, tt, f_ti)
            if is_sel:
                pygame.draw.rect(screen, theme.GOLD_LIGHT, tr, 2)
            if clicked_bg and tr.collidepoint(mx, my):
                self.selected_loadout_slot = i
                if tt:
                    self.popup_open = True
                    self.popup_item_idx = i
                    self.popup_item_source = "tour"

        y += panel_h + 8

        # ── INVENTAIRE ────────────────────────────
        tab_labels = [
            ("cape",   "Cape"),
            ("veste",  "Veste"),
            ("bottes", "Bottes"),
            ("arme",   "Arme"),
            ("tour",   "Tours"),
        ]
        tab_w_each = (w - (len(tab_labels) - 1) * 4) // len(tab_labels)
        ty0 = y
        cx2 = x
        for key, label in tab_labels:
            tr2    = pygame.Rect(cx2, ty0, tab_w_each, 30)
            is_act = self.inv_tab == key
            theme.draw_panel(screen, tr2,
                             color=(30, 22, 8) if is_act else theme.DARK_2,
                             border_color=theme.GOLD if is_act else theme.GOLD_DIM,
                             radius=theme.RADIUS_SM, border_w=2 if is_act else 1)
            theme.render_text(screen, label, f_ti,
                              theme.GOLD_LIGHT if is_act else theme.CREAM_DIM,
                              tr2.centerx, tr2.centery - f_ti.get_height() // 2,
                              center=True, shadow=False)
            if clicked_bg and tr2.collidepoint(mx, my):
                self.inv_tab = key
                self.scroll_by_tab.setdefault(key, 0)
            cx2 += tab_w_each + 4

        y += 36

        # Filtrage selon onglet
        if self.inv_tab == "tour":
            tu   = save.get("towers_unlocked", {})
            tl_s = save.get("towers_level", {})
            items = [(i, {"slot": "tour",
                          "rarity": sd.TOWER_POOL.get(tt, {}).get("rarity", "Commun"),
                          "tower_type": tt, "level": tl_s.get(tt, 1)})
                     for i, tt in enumerate(ALL_TOWER_TYPES) if tu.get(tt, False)]
        else:
            items = [(i, it) for i, it in enumerate(inv)
                     if it.get("slot") == self.inv_tab]

        # Tri par rareté (du plus rare au plus commun)
        def _rarity_key(entry):
            it = entry[1]
            r = it.get("rarity", "Commun")
            return RARITY_ORDER.get(r, 1)
        items.sort(key=_rarity_key, reverse=True)

        # Grille
        COLS = 10
        CELL = w // COLS
        clip = pygame.Rect(x, y, w, area.bottom - y)
        screen.set_clip(clip)

        self.scroll_by_tab[self.inv_tab] = max(0, self.scroll_by_tab.get(self.inv_tab, 0) - scroll_dy * 20)
        cur_scroll = self.scroll_by_tab[self.inv_tab]

        for idx, (orig_idx, item) in enumerate(items):
            col = idx % COLS
            row = idx // COLS
            cx3 = x + col * CELL
            cy3 = y + row * CELL - cur_scroll
            cr  = pygame.Rect(cx3 + 1, cy3 + 1, CELL - 3, CELL - 3)
            if cr.bottom < clip.top or cr.top > clip.bottom:
                continue

            rc = _rarity_color(item)
            pygame.draw.rect(screen, (14, 10, 6), cr)
            pygame.draw.rect(screen, rc, cr, 2)

            if self.inv_tab == "tour":
                img_name = f"{item.get('tower_type', '')}.png"
            else:
                img_name = item.get("image") or EQUIPMENT_IMAGE_FILES.get(item.get("slot", ""))
            img = _load_sprite(img_name) if img_name else None
            inner2 = pygame.Rect(cr.x + 3, cr.y + 3, cr.w - 6, cr.h - 16)
            if img:
                screen.blit(pygame.transform.smoothscale(img, (inner2.w, inner2.h)), inner2.topleft)
            else:
                pygame.draw.rect(screen, (20, 15, 8), inner2)

            lvl_s = f_ti.render(f"Nv.{item.get('level', 1)}", True, theme.CREAM)
            screen.blit(lvl_s, (cr.centerx - lvl_s.get_width() // 2,
                                cr.bottom - lvl_s.get_height() - 1))

            if self.inv_tab != "tour":
                if orig_idx in list(eqp.values()):
                    es = f_ti.render("E", True, theme.DARK)
                    eb = pygame.Rect(cr.x + 1, cr.y + 1, es.get_width() + 3, es.get_height() + 1)
                    pygame.draw.rect(screen, theme.GOLD_LIGHT, eb)
                    screen.blit(es, (eb.x + 1, eb.y))

            if clicked_bg and cr.collidepoint(mx, my):
                if self.inv_tab == "tour":
                    self.popup_open = True
                    self.popup_item_idx = orig_idx
                    self.popup_item_source = "tour"
                else:
                    self.popup_open = True
                    self.popup_item_idx = orig_idx
                    self.popup_item_source = "inv"

        screen.set_clip(None)

        rows   = (len(items) + COLS - 1) // COLS
        max_sc = max(0, rows * CELL - (area.bottom - y))
        self.scroll_by_tab[self.inv_tab] = min(self.scroll_by_tab[self.inv_tab], max_sc)

        # ── POPUP ─────────────────────────────────
        if self.popup_open and self.popup_item_idx is not None:
            if self.popup_item_source == "inv":
                item = self._get_inventory_item(self.popup_item_idx)
            elif self.popup_item_source == "tour":
                tt = ALL_TOWER_TYPES[self.popup_item_idx]
                lvl = save.get("towers_level", {}).get(tt, 1)
                item = {"slot": "tour", "tower_type": tt, "rarity": "Commun",
                        "level": lvl, "name": tt}
            else:
                item = None

            if item:
                self._draw_item_popup(screen, item, mx, my, clicked)

        # Actions après popup
        if self.pending_equip_from_popup and self.popup_item_source == "inv" and self.popup_item_idx is not None:
            self._auto_equip_item(self.popup_item_idx)
            self.pending_equip_from_popup = False
            self.popup_open = False
            self.popup_item_idx = None
            self.popup_item_source = None

        if self.pending_sell_idx is not None and self.popup_item_source == "inv":
            self._sell_item(self.pending_sell_idx)
            self.pending_sell_idx = None
            self.popup_open = False
            self.popup_item_idx = None
            self.popup_item_source = None

        return None