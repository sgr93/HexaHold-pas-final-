"""
screens/talents_screen.py

Skill Tree SNK — Eren, Mikasa, Erwin
- Débloqué au niveau 2 (skill_points >= 1)
- Popup de confirmation au premier accès
- Coût croissant par nœud
- Reset en bas à droite
- Icônes par skill
- Premier nœud brillant, dernier mis en valeur
"""

import os
import math
import pygame
import ui.theme as theme
import core.save_data as sd


# COÛTS CROISSANTS — 15 points pour finir un arbre
NODE_COSTS = [1, 1, 1, 1, 1, 1, 2, 2, 2, 3]

RESET_COST_PER_PT = 10

# Icônes spritesheet 16×16, grille 8 cols
ICON_SHEET = "AbilityIcons0.png"
ICON_CELL  = 16
ICON_COLS  = 8

# Index dans le spritesheet pour chaque skill (par perso)
SKILL_ICONS = {
    "eren":   [16, 43, 41, 60, 39, 18, 49, 23, 17, 32],
    "mikasa": [8, 15, 51, 37, 35, 11, 13, 12, 14, 47],
    "erwin":  [0, 2, 36, 7, 6, 52, 4, 30, 3, 59],
}

CHARS = {
    "eren": {
        "name":        "Eren Jäger",
        "color":       (213, 90, 48),
        "style":       "DEGATS BRUTS / RAGE",
        "style_color": (255, 120, 60),
        "final":       "Titan Assaillant",
        "sprite":      "eren_normal.png",
        "nodes": [
            {"name": "Rage",      "desc": "+3 dégâts",                        "s": "sm", "x": .12, "y": .50},
            {"name": "Instinct",  "desc": "+20% chance crit",                 "s": "sm", "x": .22, "y": .28},
            {"name": "Furie",     "desc": "+20% dégâts critiques",            "s": "md", "x": .32, "y": .65},
            {"name": "Endurance", "desc": "+15 HP  +0.2 regen/s",            "s": "sm", "x": .42, "y": .32},
            {"name": "Tranche",   "desc": "+20% dégâts critiques",            "s": "sm", "x": .51, "y": .68},
            {"name": "Berserker", "desc": "+7 degats  +8% crit  -5 cd",    "s": "lg", "x": .60, "y": .30},
            {"name": "Esquive",   "desc": "+0.5 vitesse",                     "s": "sm", "x": .69, "y": .65},
            {"name": "Percee",    "desc": "+4 degats  +2 vitesse d'attaque", "s": "md", "x": .77, "y": .35},
            {"name": "Acier",     "desc": "+8% defense  +20 HP",             "s": "sm", "x": .85, "y": .65},
            {"name": "ULTIME - Titan Assaillant",
             "desc": "Burst x3 degats pendant 8s\nChaque coup ralentit les ennemis\nCooldown : 45s",
             "s": "lg", "x": .93, "y": .45},
        ],
        "edges": [[0,1],[0,2],[1,3],[2,3],[3,4],[3,5],[4,6],[5,6],[6,7],[5,7],[7,8],[7,9],[8,9]],
    },
    "mikasa": {
        "name":        "Mikasa Ackerman",
        "color":       (127, 119, 221),
        "style":       "VITESSE & VITESSE D'ATTAQUE",
        "style_color": (160, 150, 255),
        "final":       "Lame d'Ackerman",
        "sprite":      "mikasa_normal.png",
        "nodes": [
            {"name": "Rapidité",   "desc": "+0.5 vitesse",                             "s": "sm", "x": .12, "y": .50},
            {"name": "Précision",  "desc": "+10% chance crit",                         "s": "sm", "x": .22, "y": .28},
            {"name": "Acrobatie",  "desc": "+2 vitesse",                               "s": "sm", "x": .32, "y": .68},
            {"name": "Tranchant",  "desc": "+4 degats  +3% degats critiques",        "s": "md", "x": .42, "y": .32},
            {"name": "Asiatique",  "desc": "+10% dégâts critiques",                   "s": "sm", "x": .51, "y": .68},
            {"name": "Ackerman",   "desc": "+1 vit. attaque  +1.0 vitesse\n+25% degats critiques", "s": "lg", "x": .60, "y": .30},
            {"name": "Fulgurance", "desc": "+3 degats  +1 vitesse",                  "s": "sm", "x": .69, "y": .65},
            {"name": "Ombre",      "desc": "+2 vitesse d'attaque  +2 degats",        "s": "md", "x": .77, "y": .35},
            {"name": "Resistance", "desc": "+20 HP  +5% defense",                    "s": "sm", "x": .85, "y": .65},
            {"name": "ULTIME - Lame d'Ackerman",
             "desc": "Vitesse x2  Vit. attaque x2\npendant 10s\nCooldown : 40s",
             "s": "lg", "x": .93, "y": .45},
        ],
        "edges": [[0,1],[0,2],[1,3],[2,3],[3,4],[3,5],[4,6],[5,6],[6,7],[5,7],[7,8],[7,9],[8,9]],
    },
    "erwin": {
        "name":        "Erwin Smith",
        "color":       (29, 158, 117),
        "style":       "SUPPORT & STRATEGIE",
        "style_color": (80, 200, 160),
        "final":       "Charge du Bataillon",
        "sprite":      "erwin_normal.png",
        "nodes": [
            {"name": "Tactique",   "desc": "+6% dégâts tours",                       "s": "sm", "x": .12, "y": .50},
            {"name": "Logistique", "desc": "+8% pièces/partie",                      "s": "sm", "x": .22, "y": .28},
            {"name": "Formation",  "desc": "+8% dmg tours  +5% portee",             "s": "md", "x": .32, "y": .65},
            {"name": "Embuscade",  "desc": "+12% degats pieges",                     "s": "sm", "x": .42, "y": .32},
            {"name": "Ravitail.",  "desc": "+12% pieces  +1 gemme/5 vagues",        "s": "sm", "x": .51, "y": .68},
            {"name": "Commandant", "desc": "+12% dmg tours  -8% cd\n+10% portee",   "s": "lg", "x": .60, "y": .30},
            {"name": "Piege++",    "desc": "-10% cd pieges  +8% dmg pieges",        "s": "sm", "x": .69, "y": .65},
            {"name": "XP+",        "desc": "+15% XP en jeu",                         "s": "md", "x": .77, "y": .35},
            {"name": "Forteresse", "desc": "+25 HP  +8% defense",                   "s": "sm", "x": .85, "y": .65},
            {"name": "ULTIME - Charge du Bataillon",
             "desc": "Tours tirent 2x plus vite\npendant 12s  +50% XP en jeu\nCooldown : 50s",
             "s": "lg", "x": .93, "y": .45},
        ],
        "edges": [[0,1],[0,2],[1,3],[2,3],[3,4],[3,5],[4,6],[5,6],[5,7],[6,8],[7,8],[7,9],[8,9]],
    },
}

NODE_R   = {"sm": 13, "md": 18, "lg": 24}
RECT_H   = 152
RECT_GAP = 10

_bg_cache    = {}
_spr_cache   = {}
_sheet_cache = {}


def _load_bg_full(name, target_w, target_h):
    key = (name, target_w, target_h)
    if key not in _bg_cache:
        path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", name)
        try:
            img = pygame.image.load(path).convert_alpha()
            iw, ih = img.get_size()
            scale = max(target_w / iw, target_h / ih)
            sw, sh = int(iw * scale), int(ih * scale)
            scaled = pygame.transform.smoothscale(img, (sw, sh))
            cx = (sw - target_w) // 2
            cy = (sh - target_h) // 2
            crop = scaled.subsurface(pygame.Rect(cx, cy, target_w, target_h)).copy()
            _bg_cache[key] = crop
        except Exception:
            _bg_cache[key] = None
    return _bg_cache[key]


def _load_spr(name, size):
    key = (name, size)
    if key not in _spr_cache:
        path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", name)
        try:
            img = pygame.image.load(path).convert_alpha()
            _spr_cache[key] = pygame.transform.smoothscale(img, size)
        except Exception:
            _spr_cache[key] = None
    return _spr_cache[key]

def _make_circle_icon(icon, size):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # cercle masque
    pygame.draw.circle(surf, (255, 255, 255, 255), (size//2, size//2), size//2)

    # copie icône
    icon = pygame.transform.smoothscale(icon, (size, size))

    # appliquer masque
    surf.blit(icon, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    return surf


def _load_skill_icon(cid, skill_idx, size=24):
    key = (cid, skill_idx, size)
    if key not in _sheet_cache:
        path = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", ICON_SHEET)
        try:
            if "sheet" not in _sheet_cache:
                _sheet_cache["sheet"] = pygame.image.load(path).convert_alpha()
            sheet = _sheet_cache["sheet"]
            idx   = SKILL_ICONS[cid][skill_idx]
            row   = idx // ICON_COLS
            col   = idx % ICON_COLS
            x, y  = col * ICON_CELL, row * ICON_CELL
            icon  = sheet.subsurface(pygame.Rect(x, y, ICON_CELL, ICON_CELL))
            scaled = pygame.transform.smoothscale(icon, (size, size))
            _sheet_cache[key] = _make_circle_icon(scaled, size)
        except Exception:
            _sheet_cache[key] = None
    return _sheet_cache[key]


def _node_cost(node_idx):
    return NODE_COSTS[min(node_idx, len(NODE_COSTS) - 1)]


def _total_cost_to_node(node_idx):
    return sum(NODE_COSTS[:node_idx + 1])


class TalentsScreen:
    def __init__(self, save):
        self.save         = save
        self.popup        = None
        self.show_confirm = None  # None ou "pending"

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save  = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        sp = save.get("skill_points", 0)

        # Verrouillé si pas encore niveau 2 
        if sp == 0 and not save.get("skill_tree_nodes"):
            return None

        # Popup confirmation premier accès 
        if self.show_confirm == "pending":
            self._draw_confirm(screen, area, mx, my, clicked, f_lbl, f_sm, f_ti)
            return None

        if not save.get("skill_tree_seen") and self.show_confirm is None:
            self.show_confirm = "pending"
            return None

        pad = 16
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad * 2

        # Titre
        theme.render_text(screen, "Skill Tree", f_sec, theme.GOLD_LIGHT, x, y)
        spl = f_lbl.render(f"Points disponibles : {sp}", True, theme.GOLD_LIGHT)
        screen.blit(spl, (area.right - pad - spl.get_width(),
                          y + (f_sec.get_height() - spl.get_height()) // 2))
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, w)
        y += f_sec.get_height() + 12

        locked_char = save.get("skill_tree_locked", None)
        self.popup  = None

        # Fond unique
        total_h = len(CHARS) * RECT_H + (len(CHARS) - 1) * RECT_GAP
        bg_area = pygame.Rect(x, y, w, total_h)
        bg_full = _load_bg_full("bg_skilltree.png", w, total_h)
        if bg_full:
            screen.blit(bg_full, (x, y))
            theme.draw_rect_alpha(screen, (0, 0, 0, 130), bg_area)
        else:
            theme.draw_rect_alpha(screen, (*theme.DARK_2, 220), bg_area)

        rect_y = y
        for cid, ch in CHARS.items():
            is_locked = locked_char is not None and locked_char != cid
            rect = pygame.Rect(x, rect_y, w, RECT_H)
            self._draw_char_rect(screen, rect, cid, ch, is_locked,
                                 save, mx, my, clicked, f_sm, f_ti)
            rect_y += RECT_H + RECT_GAP

        # Bouton Reset en bas à droite 
        spent      = self._total_spent(save)
        reset_cost = spent * RESET_COST_PER_PT
        coins      = save.get("coins", 0)
        can_reset  = spent > 0 and coins >= reset_cost

        btn_w = 320
        rbtn  = pygame.Rect(area.right - pad - btn_w, rect_y + 6, btn_w, 36)
        hov_r = rbtn.collidepoint(mx, my) and can_reset
        theme.draw_panel(screen, rbtn,
                         color=(50, 12, 12) if hov_r else theme.DARK_2,
                         border_color=theme.RED_BADGE if can_reset else (50, 35, 30),
                         radius=theme.RADIUS_MD, border_w=2 if can_reset else 1)

        if can_reset:
            rl = f_sm.render(f"Reset  --  {reset_cost} pieces  ({spent} pts x {RESET_COST_PER_PT})",
                             True, theme.RED_BADGE if hov_r else (200, 80, 80))
        else:
            rl = f_sm.render(f"Reset  --  {reset_cost} pieces necessaires  (vous avez {coins})",
                             True, theme.GOLD_DIM)
        screen.blit(rl, (rbtn.centerx - rl.get_width() // 2,
                         rbtn.centery - rl.get_height() // 2))
        if clicked and hov_r:
            self._do_reset(save)
            sd.save(save)

        # Popup nœud (en dernier)
        if self.popup:
            self._draw_popup(screen, *self.popup, f_sm, f_ti)

        return None

    # ──────────────────────────────────────────────────────────
    def _draw_confirm(self, screen, area, mx, my, clicked, f_lbl, f_sm, f_ti):
        """Popup de confirmation : choix irréversible."""
        W, H = 420, 180
        bx = area.centerx - W // 2
        by = area.centery - H // 2
        pop = pygame.Rect(bx, by, W, H)

        theme.draw_rect_alpha(screen, (0, 0, 0, 180), area)
        theme.draw_panel(screen, pop, color=theme.DARK_2,
                         border_color=theme.GOLD, radius=theme.RADIUS_LG, border_w=2)
        theme.draw_corner_ornaments(screen, pop)

        t = f_lbl.render("Choisir votre Skill Tree", True, theme.GOLD_LIGHT)
        screen.blit(t, (pop.centerx - t.get_width() // 2, by + 16))

        w1 = f_sm.render("Attention - ce choix est irreversible.", True, (220, 160, 60))
        screen.blit(w1, (pop.centerx - w1.get_width() // 2, by + 44))

        w2 = f_ti.render("Investir dans un arbre bloquera définitivement les deux autres.", True, theme.CREAM_DIM)
        screen.blit(w2, (pop.centerx - w2.get_width() // 2, by + 68))

        w3 = f_ti.render("Un reset est possible contre des pièces.", True, theme.GOLD_DIM)
        screen.blit(w3, (pop.centerx - w3.get_width() // 2, by + 86))

        btn = pygame.Rect(pop.centerx - 80, by + H - 48, 160, 34)
        hov = btn.collidepoint(mx, my)
        theme.draw_panel(screen, btn,
                         color=(25, 18, 5) if hov else theme.DARK_3,
                         border_color=theme.GOLD if hov else theme.GOLD_DIM,
                         radius=theme.RADIUS_MD, border_w=2)
        bl = f_sm.render("J'ai compris", True, theme.GOLD_LIGHT if hov else theme.CREAM)
        screen.blit(bl, (btn.centerx - bl.get_width() // 2,
                         btn.centery - bl.get_height() // 2))
        if clicked and hov:
            self.save["skill_tree_seen"] = True
            self.show_confirm = None
            sd.save(self.save)

    # ──────────────────────────────────────────────────────────
    def _draw_char_rect(self, screen, rect, cid, ch, is_locked,
                        save, mx, my, clicked, f_sm, f_ti):
        color          = ch["color"]
        nodes          = ch["nodes"]
        edges          = ch["edges"]
        unlocked_nodes = save.get("skill_tree_nodes", {}).get(cid, [])
        sp             = save.get("skill_points", 0)
        tick           = pygame.time.get_ticks()

        # Overlay si verrouillé
        if is_locked:
            theme.draw_rect_alpha(screen, (0, 0, 0, 140), rect)

        # Bordure rectangle
        pygame.draw.rect(screen,
                         (45, 38, 30) if is_locked else color,
                         rect, 2 if not is_locked else 1,
                         border_radius=theme.RADIUS_MD)

        # Sprite perso
        spr_w = rect.width // 6
        spr_h = rect.height
        spr = _load_spr(ch["sprite"], (spr_w, spr_h))
        if spr:
            tmp = spr.copy()
            if is_locked:
                tmp.set_alpha(60)
            screen.blit(tmp, (rect.x, rect.y))

        # Nom
        f_name = theme.font(theme.SZ_LABEL)
        nc = (70, 60, 50) if is_locked else color
        ns = f_name.render(ch["name"], True, nc)
        screen.blit(ns, (rect.x + 8, rect.y + 5))

        # Style du personnage (dégâts bruts / vitesse / support)
        f_style = theme.font(theme.SZ_TINY, body=True)
        style_col = (60, 50, 40) if is_locked else ch.get("style_color", color)
        sl = f_style.render(ch.get("style", ""), True, style_col)
        screen.blit(sl, (rect.x + 8, rect.y + 5 + ns.get_height() + 2))

        if is_locked:
            lk = f_ti.render("Verrouillé", True, (80, 65, 55))
            screen.blit(lk, (rect.right - lk.get_width() - 8, rect.y + 6))

        # Liaisons
        for a, b in edges:
            na, nb = nodes[a], nodes[b]
            x1 = rect.x + int(na["x"] * rect.width)
            y1 = rect.y + int(na["y"] * rect.height)
            x2 = rect.x + int(nb["x"] * rect.width)
            y2 = rect.y + int(nb["y"] * rect.height)
            both = a in unlocked_nodes and b in unlocked_nodes
            pygame.draw.line(screen,
                             color if both else (90, 80, 65),
                             (x1, y1), (x2, y2),
                             5 if both else 2)

        # Nœuds
        for i, node in enumerate(nodes):
            nx  = rect.x + int(node["x"] * rect.width)
            ny_ = rect.y + int(node["y"] * rect.height)
            r   = NODE_R[node["s"]]
            is_final  = (i == len(nodes) - 1)
            is_first  = (i == 0)
            node_on   = i in unlocked_nodes
            cost      = _node_cost(i)

            if is_first:
                adj = len(unlocked_nodes) == 0
            else:
                adj = any(
                    (a == i and b in unlocked_nodes) or (b == i and a in unlocked_nodes)
                    for a, b in edges
                )
            can_buy = not node_on and adj and sp >= cost and not is_locked

            # Nœud final : double anneau doré 
            if is_final:
                pulse = int(20 + 15 * math.sin(tick * 0.003)) if node_on else 0
                pygame.draw.circle(screen,
                                   (*color, 80 + pulse) if node_on else (50, 42, 32),
                                   (nx, ny_), r + 10, 2)
                pygame.draw.circle(screen,
                                   color if node_on else (40, 33, 26),
                                   (nx, ny_), r + 6, 1)

            # Premier nœud : halo pulsant
            if is_first and not node_on and not is_locked:
                pulse = int(40 + 30 * math.sin(tick * 0.004))
                theme.draw_rect_alpha(screen,
                                      (*color, pulse),
                                      pygame.Rect(nx - r - 6, ny_ - r - 6,
                                                  (r + 6) * 2, (r + 6) * 2))

            # Fond nœud
            fill_a = 90 if node_on else (30 if can_buy else 10)
            theme.draw_rect_alpha(screen,
                                  (*color, fill_a),
                                  pygame.Rect(nx - r, ny_ - r, r * 2, r * 2))
            pygame.draw.circle(screen,
                               color if (node_on or can_buy) else (80, 70, 55),
                               (nx, ny_), r,
                               3 if (node_on or can_buy) else 2)

            # Icône skill
            icon_size = max(12, r * 2 - 6)
            icon = _load_skill_icon(cid, i, icon_size)
            if icon:
                screen.blit(icon, (nx - icon_size // 2, ny_ - icon_size // 2))
            elif node_on:
                ic = f_ti.render("U" if is_final else "V", True, color)
                screen.blit(ic, (nx - ic.get_width() // 2, ny_ - ic.get_height() // 2))

            # Hover
            if ((mx - nx) ** 2 + (my - ny_) ** 2) ** .5 <= r + 5:
                pygame.draw.circle(screen, theme.GOLD_LIGHT, (nx, ny_), r + 3, 1)
                self.popup = (node, color, nx, ny_ + r + 8,
                              node_on, can_buy, is_locked, is_final, i)
                if clicked and can_buy:
                    self._buy_node(save, cid, i)
                    sd.save(save)

        # Barre de progression
        bar = pygame.Rect(rect.x + 8, rect.bottom - 7, rect.width - 16, 3)
        pygame.draw.rect(screen, (25, 20, 15), bar, border_radius=2)
        prog = len(unlocked_nodes)
        if prog:
            fw = int(bar.width * prog / len(nodes))
            pygame.draw.rect(screen, color,
                             pygame.Rect(bar.x, bar.y, fw, bar.height),
                             border_radius=2)

    # ──────────────────────────────────────────────────────────
    def _draw_popup(self, screen, node, color, px, py,
                    node_on, can_buy, is_locked, is_final, node_idx, f_sm, f_ti):
        lines    = node["desc"].split("\n")
        cost     = _node_cost(node_idx)
        total_cost = _total_cost_to_node(node_idx)
        W = 240
        H = 20 + 16 + 14 + 14 + len(lines) * 14 + 20 + 16
        sw, sh = screen.get_size()
        bx = max(8, min(px - W // 2, sw - W - 8))
        by = max(8, min(py + 4, sh - H - 8))
        pop = pygame.Rect(bx, by, W, H)

        theme.draw_panel(screen, pop, color=theme.DARK_2,
                         border_color=color, radius=theme.RADIUS_MD, border_w=2)

        dy = by + 8
        ns = f_sm.render(node["name"], True, color)
        screen.blit(ns, (bx + 10, dy)); dy += ns.get_height() + 4

        c1 = f_ti.render(f"Coût : {cost} point{'s' if cost > 1 else ''} de skill", True, theme.GOLD_LIGHT)
        screen.blit(c1, (bx + 10, dy)); dy += c1.get_height() + 2

        c2 = f_ti.render(f"Total depuis le début : {total_cost} pts", True, theme.GOLD_DIM)
        screen.blit(c2, (bx + 10, dy)); dy += c2.get_height() + 6

        for line in lines:
            ls = f_ti.render(line, True, theme.CREAM_DIM)
            screen.blit(ls, (bx + 10, dy)); dy += ls.get_height() + 2

        dy += 4
        if node_on:
            st = f_ti.render("Debloque", True, theme.GREEN_OK)
        elif is_locked:
            st = f_ti.render("Arbre verrouillé", True, (100, 80, 60))
        elif can_buy:
            st = f_ti.render("Cliquer pour débloquer", True, theme.GOLD_DIM)
        else:
            st = f_ti.render("Points ou nœud adjacent manquant", True, (70, 60, 50))
        screen.blit(st, (bx + 10, dy))

    # ──────────────────────────────────────────────────────────
    def _buy_node(self, save, cid, node_idx):
        cost = _node_cost(node_idx)
        if save.get("skill_points", 0) < cost:
            return
        if "skill_tree_nodes" not in save:
            save["skill_tree_nodes"] = {}
        if cid not in save["skill_tree_nodes"]:
            save["skill_tree_nodes"][cid] = []
        if node_idx not in save["skill_tree_nodes"][cid]:
            save["skill_tree_nodes"][cid].append(node_idx)
        save["skill_points"]      = max(0, save.get("skill_points", 0) - cost)
        save["skill_tree_locked"] = cid

    def _total_spent(self, save):
        total = 0
        for cid, nodes in save.get("skill_tree_nodes", {}).items():
            for i in nodes:
                total += _node_cost(i)
        return total

    def _do_reset(self, save):
        spent = self._total_spent(save)
        cost  = spent * RESET_COST_PER_PT
        if save.get("coins", 0) < cost:
            return
        save["coins"]             = save.get("coins", 0) - cost
        save["skill_points"]      = save.get("skill_points", 0) + spent
        save["skill_tree_nodes"]  = {}
        save["skill_tree_locked"] = None