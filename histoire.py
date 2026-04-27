"""
histoire.py
-----------
Mode Histoire — Carte des Murs (Attack on Titan)
Affiche une carte interactive avec des chapitres qui se débloquent
progressivement. Chaque chapitre contient des missions avec objectifs et étoiles.

Appel depuis menu_screen.py :
    from histoire import run_histoire
    result = run_histoire(screen, clock, save)
    # result : None (retour menu) ou dict {chapter, mission, difficulty}
"""

import pygame
import math
import save_data as sd

# Import des fonctions d'API définies en bas du fichier (forward reference via module)
# Elles sont utilisées dans Popup.draw() — disponibles à l'exécution car Python charge tout
# le module avant d'exécuter les classes.

# ─────────────────────────────────────────────────────────────────
# PALETTE
# ─────────────────────────────────────────────────────────────────
C_BG         = (13,  10,   6)
C_BG2        = (22,  17,   8)
C_WALL       = (60,  48,  20)
C_WALL_LT    = (100, 80,  30)
C_GOLD       = (138, 106, 30)
C_GOLD2      = (196, 154, 46)
C_GOLD3      = (232, 196, 80)
C_PARCHMENT  = (232, 223, 200)
C_PARCHMENT2 = (180, 168, 140)
C_RED        = (139, 26,  26)
C_RED2       = (196, 40,  40)
C_GREEN_D    = (30,  74,  30)
C_GREEN_L    = (58, 138,  58)
C_BROWN_D    = (58,  30,  14)
C_BROWN_L    = (138, 90,  46)
C_PURPLE_D   = (26,  10,  46)
C_PURPLE_L   = (74,  26, 142)
C_LOCKED     = (42,  32,  14)
C_LOCKED_B   = (70,  54,  22)
C_OVERLAY    = (0,    0,   0, 180)
C_PANEL      = (18,  14,   8)
C_PANEL_B    = (196, 154, 46)
C_TEXT       = (232, 223, 200)
C_MUTED      = (160, 148, 118)
C_STAR_ON    = (196, 154, 46)
C_STAR_OFF   = (60,  50,  22)
C_NOTIF_BG   = (18,  14,   8)
C_NOTIF_B    = (196, 154, 46)

# ─────────────────────────────────────────────────────────────────
# DONNÉES DES CHAPITRES
# ─────────────────────────────────────────────────────────────────
# cx, cy : position en % de la surface de carte (0..1)
CHAPTERS = {
    0: {
        "label":      "Ouverture",
        "title":      "Chute du Mur Maria",
        "cx": 0.500, "cy": 0.862,
        "type":       "cinematique",
        "color_out":  C_RED,
        "color_in":   C_RED2,
        "unlock_next": 1,
        "cinematic": [
            "Anno 845.",
            "L'humanité vit depuis cent ans en paix derrière trois immenses murs...",
            "Wall Maria. Wall Rose. Wall Sheena.",
            "Ce jour-là, tout a changé.",
            "Un titan colossal est apparu au-delà de Wall Maria.",
            "Et le mur... a cédé.",
        ],
    },
    1: {
        "label":      "Chapitre 1",
        "title":      "La Bataille de Trost",
        "cx": 0.500, "cy": 0.670,
        "color_out":  C_GREEN_D,
        "color_in":   C_GREEN_L,
        "unlock_next": 2,
        "missions": [
            {
                "name": "Tenir le Fort",
                "locked": False,
                "objectives": [
                    {"text": "Survivre à 3 vagues d'ennemis", "done": False},
                    {"text": "Ne pas perdre plus de 20 PV",   "done": False},
                    {"text": "Placer 3 tours avant la vague 2","done": False},
                ],
            },
            {
                "name": "La Contre-Attaque",
                "locked": True,
                "objectives": [
                    {"text": "Éliminer 30 ennemis",                 "done": False},
                    {"text": "Terminer en moins de 5 minutes",       "done": False},
                    {"text": "Utiliser uniquement des petites tours","done": False},
                ],
            },
            {
                "name": "Le Titan de Trost",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss sans perdre de PV",       "done": False},
                    {"text": "Atteindre la difficulté Difficile",        "done": False},
                    {"text": "Placer 5 types de tours différents",       "done": False},
                ],
            },
        ],
    },
    2: {
        "label":      "Chapitre 2",
        "title":      "La Forêt des Titans",
        "cx": 0.746, "cy": 0.682,
        "color_out":  (30, 58, 14),
        "color_in":   (58, 122, 30),
        "unlock_next": 3,
        "missions": [
            {
                "name": "Dans les Ombres",
                "locked": False,
                "objectives": [
                    {"text": "Survivre 5 vagues en forêt",         "done": False},
                    {"text": "Ne pas dépasser 3 tours détruites",  "done": False},
                    {"text": "Tuer 50 ennemis",                    "done": False},
                ],
            },
            {
                "name": "Embuscade",
                "locked": True,
                "objectives": [
                    {"text": "Défendre sans tours de type sniper",        "done": False},
                    {"text": "Survivre à un assaut nocturne (×1.5)",      "done": False},
                    {"text": "Tuer le mini-boss en 30 secondes",          "done": False},
                ],
            },
            {
                "name": "Le Titan Féminin",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss en Difficile",              "done": False},
                    {"text": "Ne jamais perdre plus de 50% PV",           "done": False},
                    {"text": "3 étoiles sur la mission précédente",       "done": False},
                ],
            },
        ],
    },
    3: {
        "label":      "Chapitre 3",
        "title":      "Siège du Château Utgard",
        "cx": 0.304, "cy": 0.642,
        "color_out":  C_BROWN_D,
        "color_in":   C_BROWN_L,
        "unlock_next": 4,
        "missions": [
            {
                "name": "Nuit Sans Lune",
                "locked": False,
                "objectives": [
                    {"text": "Survivre jusqu'à l'aube (8 vagues)",      "done": False},
                    {"text": "Protéger 3 survivants alliés",             "done": False},
                    {"text": "Ne pas utiliser de murs supplémentaires",  "done": False},
                ],
            },
            {
                "name": "Assaut des Titans 14m",
                "locked": True,
                "objectives": [
                    {"text": "Affronter des titans classe 14m",          "done": False},
                    {"text": "Garder le château à 50% d'intégrité",     "done": False},
                    {"text": "Terminer avec 5 tours actives",            "done": False},
                ],
            },
            {
                "name": "Dernier Rempart",
                "locked": True,
                "objectives": [
                    {"text": "Vaincre le boss en Très Difficile",       "done": False},
                    {"text": "Aucun ennemi ne franchit le seuil",       "done": False},
                    {"text": "Finir avec tous ses PV",                  "done": False},
                ],
            },
        ],
    },
    4: {
        "label":      "Chapitre 4",
        "title":      "???",
        "cx": 0.740, "cy": 0.490,
        "color_out":  C_PURPLE_D,
        "color_in":   C_PURPLE_L,
        "unlock_next": 5,
        "special": "Ce chapitre est mystérieux.\nSon contenu sera révélé en temps voulu...",
    },
    5: {
        "label":      "Chapitre 5",
        "title":      "???",
        "cx": 0.500, "cy": 0.906,
        "color_out":  (46, 10, 10),
        "color_in":   (142, 26, 26),
        "special": "Le dernier chapitre.\nTout mène ici.\nPréparez-vous...",
    },
}

# Labels de la carte (texte, cx%, cy%, taille, couleur, gras)
MAP_LABELS = [
    ("TITAN TERRITORY",    0.50, 0.04, 11, C_GOLD2,     True),
    ("WALL MARIA",         0.50, 0.09, 11, C_GOLD2,     True),
    ("WALL ROSE",          0.50, 0.225,11, C_GOLD2,     True),
    ("WALL SHEENA",        0.50, 0.335,11, C_GOLD2,     True),
    ("Human Territory",    0.50, 0.365, 9, C_GOLD,      False),
    ("Royal Capital",      0.50, 0.508, 9, C_PARCHMENT, False),
    ("Utopia District",    0.50, 0.200, 9, C_PARCHMENT, False),
    ("Orvud District",     0.50, 0.268, 9, C_PARCHMENT, False),
    ("Yarckel District",   0.28, 0.438, 9, C_PARCHMENT, False),
    ("Stohess District",   0.72, 0.438, 9, C_PARCHMENT, False),
    ("Krolva District",    0.10, 0.500, 9, C_PARCHMENT, False),
    ("Karanes District",   0.90, 0.500, 9, C_PARCHMENT, False),
    ("Ehrmich District",   0.50, 0.605, 9, C_PARCHMENT, False),
    ("Dauper Village",     0.32, 0.628, 8, C_PARCHMENT2,False),
    ("Ragako Village",     0.37, 0.708, 8, C_PARCHMENT2,False),
    ("Utgard Castle",      0.27, 0.672, 8, C_PARCHMENT2,False),
    ("Trost District",     0.50, 0.735, 9, C_PARCHMENT, False),
    ("Titan Forest",       0.78, 0.678, 8, C_PARCHMENT2,False),
    ("Shiganshina District",0.50, 0.874, 9, C_PARCHMENT, False),
]

# ─────────────────────────────────────────────────────────────────
# UTILITAIRES DESSIN
# ─────────────────────────────────────────────────────────────────

def _font(size, bold=False):
    return pygame.font.SysFont("arial", size, bold=bold)

def _draw_text_centered(surf, text, font, color, cx, cy, shadow=True):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        surf.blit(s, (cx - s.get_width()//2 + 1, cy - s.get_height()//2 + 1))
    t = font.render(text, True, color)
    surf.blit(t, (cx - t.get_width()//2, cy - t.get_height()//2))

def _draw_rect_alpha(surf, color, rect, radius=0):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)

def _draw_circle_aa(surf, color, cx, cy, r, width=0):
    pygame.draw.circle(surf, color, (int(cx), int(cy)), r, width)

def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))


# ─────────────────────────────────────────────────────────────────
# CONSTRUCTION DE LA SURFACE CARTE (appelée une fois, mise en cache)
# ─────────────────────────────────────────────────────────────────

def _build_map_surface(w, h):
    """
    Dessine la carte des murs (fond, cercles, routes, décorations)
    sans les points de chapitre ni les labels texte.
    Retourne une Surface.
    """
    surf = pygame.Surface((w, h))
    surf.fill(C_BG)

    cx, cy = w // 2, h // 2

    # Légère teinte de fond centrale
    r_outer = int(min(w, h) * 0.44)
    r_rose  = int(min(w, h) * 0.31)
    r_inner = int(min(w, h) * 0.18)

    # Territoire titan (fond)
    pygame.draw.rect(surf, C_BG2, pygame.Rect(0, 0, w, h))
    pygame.draw.circle(surf, (20, 16,  8), (cx, cy), r_outer + 14)

    # ── Wall Maria ──
    pygame.draw.circle(surf, C_WALL,    (cx, cy), r_outer,     16)
    pygame.draw.circle(surf, C_WALL_LT, (cx, cy), r_outer,      2)
    # 4 portes Wall Maria
    for gx, gy, gw, gh in [
        (cx-12, cy-r_outer-10, 24, 14),
        (cx-12, cy+r_outer- 4, 24, 14),
        (cx-r_outer-10, cy-12, 14, 24),
        (cx+r_outer- 4, cy-12, 14, 24),
    ]:
        pygame.draw.rect(surf, C_WALL,   (gx, gy, gw, gh), border_radius=2)
        pygame.draw.rect(surf, C_WALL_LT,(gx, gy, gw, gh), 1, border_radius=2)

    # ── Wall Rose ──
    pygame.draw.circle(surf, C_WALL,    (cx, cy), r_rose,  12)
    pygame.draw.circle(surf, C_WALL_LT, (cx, cy), r_rose,   2)
    for gx, gy, gw, gh in [
        (cx-9, cy-r_rose-8, 18, 12),
        (cx-9, cy+r_rose-4, 18, 12),
        (cx-r_rose-8, cy-9, 12, 18),
        (cx+r_rose-4, cy-9, 12, 18),
    ]:
        pygame.draw.rect(surf, C_WALL,    (gx, gy, gw, gh), border_radius=2)
        pygame.draw.rect(surf, C_WALL_LT, (gx, gy, gw, gh), 1, border_radius=2)

    # ── Wall Sheena ──
    pygame.draw.circle(surf, C_WALL,    (cx, cy), r_inner, 10)
    pygame.draw.circle(surf, C_WALL_LT, (cx, cy), r_inner,  1)
    for gx, gy, gw, gh in [
        (cx-6, cy-r_inner-6, 12, 10),
        (cx-6, cy+r_inner-4, 12, 10),
        (cx-r_inner-6, cy-6, 10, 12),
        (cx+r_inner-4, cy-6, 10, 12),
    ]:
        pygame.draw.rect(surf, C_WALL,    (gx, gy, gw, gh), border_radius=1)
        pygame.draw.rect(surf, C_WALL_LT, (gx, gy, gw, gh), 1, border_radius=1)

    # ── Remplissage intérieur Wall Sheena (capitale) ──
    pygame.draw.circle(surf, (26, 20, 8), (cx, cy), r_inner - 5)

    # ── Routes en croix ──
    road_w = max(12, w // 40)
    for rx, ry, rw, rh in [
        (cx - road_w//2, cy - r_inner + 5, road_w, r_inner - 5),
        (cx - road_w//2, cy,               road_w, r_inner - 5),
        (cx - r_inner+5, cy - road_w//2,   r_inner-5, road_w),
        (cx,             cy - road_w//2,   r_inner-5, road_w),
    ]:
        pygame.draw.rect(surf, (28, 22, 10), (rx, ry, rw, rh))

    # ── Palais Royal (grille) ──
    pr = road_w + 4
    palace = pygame.Rect(cx - pr, cy - pr, pr*2, pr*2)
    pygame.draw.rect(surf, (36, 28, 10), palace, border_radius=2)
    pygame.draw.rect(surf, C_GOLD,       palace, 1, border_radius=2)
    # petite grille intérieure
    for i in range(1, 3):
        x = palace.x + palace.w * i // 3
        pygame.draw.line(surf, C_WALL, (x, palace.y), (x, palace.bottom), 1)
        y = palace.y + palace.h * i // 3
        pygame.draw.line(surf, C_WALL, (palace.x, y), (palace.right, y), 1)

    # ── Forêt des Titans ──
    fx = int(w * 0.746)
    fy = int(h * 0.68)
    for dx, dy in [(-14,0),(0,-12),(14,0),(-7,12),(7,12),(-20,14),(20,14)]:
        tx, ty = fx+dx, fy+dy
        pygame.draw.polygon(surf, (20, 38, 8),
            [(tx, ty-14),(tx+8, ty+8),(tx-8, ty+8)])
        pygame.draw.polygon(surf, (28, 50, 10),
            [(tx, ty-14),(tx+8, ty+8),(tx-8, ty+8)], 1)

    # ── Château Utgard ──
    ux = int(w * 0.304)
    uy = int(h * 0.642)
    cr = pygame.Rect(ux-10, uy-9, 20, 16)
    pygame.draw.rect(surf, (38, 28, 12), cr, border_radius=2)
    pygame.draw.rect(surf, (90, 68, 28), cr, 1, border_radius=2)
    for tx in [ux-9, ux+3]:
        pygame.draw.rect(surf, (50, 38, 14), (tx, uy-15, 6, 8))

    # ── District Shiganshina (ellipse en bas) ──
    sx = cx
    sy = int(h * 0.870)
    pygame.draw.ellipse(surf, (28, 20, 8), (sx-30, sy-12, 60, 22))
    pygame.draw.ellipse(surf, C_WALL,      (sx-30, sy-12, 60, 22), 1)
    # Mur au-dessus de Shiganshina
    pygame.draw.rect(surf, C_WALL, (sx-15, sy-14, 30, 5), border_radius=1)

    return surf


# ─────────────────────────────────────────────────────────────────
# POPUP LATÉRAL
# ─────────────────────────────────────────────────────────────────

class Popup:
    WIDTH = 260

    def __init__(self):
        self.visible          = False
        self.chapter_idx      = None
        self.scroll           = 0
        self._anim            = 0.0
        self.selected_mission = 0

    def open(self, idx):
        self.chapter_idx      = idx
        self.visible          = True
        self.scroll           = 0
        self.selected_mission = 0   # mission sélectionnée par défaut

    def close(self):
        self.visible     = False
        self.chapter_idx = None

    def update(self, dt):
        target = 1.0 if self.visible else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 12)

    def draw(self, screen, sw, sh, save, fonts, hover_start, mx, my):
        """
        Dessine le panneau latéral droit.
        Retourne le rect du bouton "Commencer" (ou None).
        """
        if self._anim < 0.01:
            return None

        pw   = self.WIDTH
        ph   = sh - 50
        px   = int(sw - pw * self._anim)
        py   = 50

        # Fond panneau
        panel = pygame.Surface((pw, ph))
        panel.fill(C_PANEL)
        pygame.draw.line(panel, C_GOLD, (0, 0), (0, ph), 1)

        f_xs  = fonts["xs"]
        f_sm  = fonts["sm"]
        f_md  = fonts["md"]

        if self.chapter_idx is None:
            screen.blit(panel, (px, py))
            return None

        ch = CHAPTERS[self.chapter_idx]
        is_completed = self.chapter_idx in save.get("histoire_completed", [])

        # ── En-tête ──
        pygame.draw.line(panel, C_GOLD, (0, 56), (pw, 56), 1)
        lbl = f_xs.render(ch["label"].upper(), True, C_GOLD)
        panel.blit(lbl, (14, 10))
        title = f_sm.render(ch["title"], True, C_PARCHMENT)
        # Retour à la ligne si trop long
        if title.get_width() > pw - 40:
            words = ch["title"].split()
            lines, cur = [], ""
            for w in words:
                test = cur + (" " if cur else "") + w
                if f_sm.render(test, True, C_PARCHMENT).get_width() > pw - 40:
                    if cur: lines.append(cur)
                    cur = w
                else:
                    cur = test
            if cur: lines.append(cur)
            for i, line in enumerate(lines):
                t = f_sm.render(line, True, C_PARCHMENT)
                panel.blit(t, (14, 26 + i*16))
        else:
            panel.blit(title, (14, 26))

        # Bouton fermer
        close_r = pygame.Rect(pw-28, 8, 20, 20)
        close_col = C_GOLD2 if close_r.move(px, py).collidepoint(mx, my) else C_GOLD
        pygame.draw.rect(panel, C_PANEL, close_r, border_radius=3)
        cl = f_sm.render("x", True, close_col)
        panel.blit(cl, (close_r.x + close_r.w//2 - cl.get_width()//2,
                        close_r.y + close_r.h//2 - cl.get_height()//2))

        start_btn_rect = None
        content_y = 68

        # ── Cinématique ──
        if ch.get("type") == "cinematique":
            msg = "Cinématique d'introduction." if not is_completed else "Déjà vue."
            t = f_xs.render(msg, True, C_MUTED)
            panel.blit(t, (14, content_y))
            content_y += 22
            note = f_xs.render("Aucun objectif requis.", True, C_MUTED)
            panel.blit(note, (14, content_y))
            content_y = ph - 50
            label_btn = "Revoir" if is_completed else "Voir la cinématique"
            start_btn_rect = self._draw_start_btn(panel, f_sm, ph, label_btn, mx-px, my-py)

        # ── Spécial (ch4/ch5) ──
        elif ch.get("special"):
            for line in ch["special"].split("\n"):
                t = f_xs.render(line, True, C_MUTED)
                panel.blit(t, (14, content_y))
                content_y += 18

        # ── Missions ──
        else:
            missions = ch.get("missions", [])
            row_gap = 8
            clip_h = ph - content_y - 55
            from ui import draw_star

            # Pré-calculer la hauteur de chaque ligne de mission selon le texte
            def _wrap_text(font, text, max_w):
                """Retourne une liste de lignes qui tiennent dans max_w."""
                words = text.split()
                lines, cur = [], ""
                for w in words:
                    test = (cur + " " + w).strip()
                    if font.render(test, True, (0,0,0)).get_width() <= max_w:
                        cur = test
                    else:
                        if cur:
                            lines.append(cur)
                        cur = w
                if cur:
                    lines.append(cur)
                return lines if lines else [text]

            obj_line_h = 14
            obj_start_y = 36
            max_obj_w = pw - 32  # largeur dispo pour le texte (après étoile)

            def _mission_row_h(m, locked):
                if locked:
                    return 50
                total = obj_start_y
                for obj in m.get("objectives", []):
                    lines = _wrap_text(f_xs, obj["text"], max_obj_w - 16)
                    total += max(1, len(lines)) * obj_line_h + 2
                return max(60, total + 8)

            clip_surf = pygame.Surface((pw, clip_h), pygame.SRCALPHA)

            # Calculer et stocker les hauteurs pour le clic
            computed_heights = [_mission_row_h(m, not is_mission_unlocked(save, self.chapter_idx, i))
                                 for i, m in enumerate(missions)]
            self.mission_row_heights = computed_heights

            y_cursor = 0
            for i, m in enumerate(missions):
                locked = not is_mission_unlocked(save, self.chapter_idx, i)
                row_h = _mission_row_h(m, locked)
                ry = y_cursor - self.scroll
                y_cursor += row_h + row_gap

                if ry + row_h < 0 or ry > clip_h:
                    continue

                row = pygame.Rect(8, ry, pw-16, row_h)
                stars_done = get_mission_best_stars(save, self.chapter_idx, i)
                n_obj = len(m.get("objectives", []))

                # Fond
                col = (30, 22, 10) if not locked else (18, 14, 6)
                is_sel = (i == self.selected_mission) and not locked
                if is_sel:
                    col = (44, 32, 10)
                pygame.draw.rect(clip_surf, col, row, border_radius=4)
                border_col = (196, 154, 46) if is_sel else ((80, 60, 20) if not locked else (50, 38, 14))
                pygame.draw.rect(clip_surf, border_col, row, 2 if is_sel else 1, border_radius=4)

                # Numéro + nom
                num = f_xs.render(f"{i+1}.", True, C_GOLD)
                clip_surf.blit(num, (row.x+6, row.y+6))
                name_col = C_MUTED if locked else C_PARCHMENT
                nm = f_xs.render(m["name"] + (" \U0001f512" if locked else ""), True, name_col)
                clip_surf.blit(nm, (row.x+22, row.y+6))

                # Étoiles de progression : UNIQUEMENT à gauche des objectifs (pas en haut)
                # Objectifs avec texte multi-ligne
                if not locked:
                    oy = row.y + obj_start_y
                    # Charger les états d'objectifs depuis la save (persistants)
                    obj_key = f"ch{self.chapter_idx}_m{i}_objectives"
                    saved_obj_states = save.get(obj_key, [])
                    for oi, obj in enumerate(m.get("objectives", [])):
                        # Utiliser l'état sauvegardé si disponible, sinon l'état en mémoire
                        done_o = saved_obj_states[oi] if oi < len(saved_obj_states) else obj.get("done", False)
                        star_sz = 12
                        # Étoile à gauche, centrée sur la première ligne de texte
                        draw_star(clip_surf, row.x + 8, oy + 1, star_sz, done_o)
                        oc = C_GOLD if done_o else C_MUTED
                        lines = _wrap_text(f_xs, obj["text"], max_obj_w - 16)
                        for li, line in enumerate(lines):
                            lt = f_xs.render(line, True, oc)
                            clip_surf.blit(lt, (row.x + 22, oy + li * obj_line_h))
                        oy += len(lines) * obj_line_h + 2

            panel.blit(clip_surf, (0, content_y))

            # Bouton commencer
            start_btn_rect = self._draw_start_btn(panel, f_sm, ph, "Commencer", mx-px, my-py)

        screen.blit(panel, (px, py))

        # On retourne le rect global du bouton start
        if start_btn_rect:
            return pygame.Rect(px + start_btn_rect.x, py + start_btn_rect.y,
                               start_btn_rect.w, start_btn_rect.h)
        return None

    def _draw_start_btn(self, surf, font, ph, label, lmx, lmy):
        bw, bh = self.WIDTH - 24, 34
        br = pygame.Rect(12, ph - bh - 10, bw, bh)
        hov = br.collidepoint(lmx, lmy)
        col = C_GOLD3 if hov else C_GOLD2
        pygame.draw.rect(surf, col, br, border_radius=4)
        t = font.render(label, True, C_BG)
        surf.blit(t, (br.x + br.w//2 - t.get_width()//2,
                      br.y + br.h//2 - t.get_height()//2))
        return br


# ─────────────────────────────────────────────────────────────────
# POINTS DE CHAPITRE (cercles animés)
# ─────────────────────────────────────────────────────────────────

class ChapterPoint:
    RADIUS = 14

    def __init__(self, idx, cx_abs, cy_abs):
        self.idx    = idx
        self.cx     = cx_abs
        self.cy     = cy_abs
        self.pulse  = 0.0
        self.ripple = []  # liste de (progress 0→1, max_r)
        self._appear = 0.0  # 0→1 animation d'apparition

    def trigger_unlock(self):
        self.ripple = [(0.0, 32), (0.0, 44), (0.0, 56)]
        self._appear = 0.0

    def update(self, dt, unlocked):
        self.pulse = (self.pulse + dt * 2.0) % (2 * math.pi)
        if unlocked and self._appear < 1.0:
            self._appear = min(1.0, self._appear + dt * 3.0)
        new_rip = []
        for p, mr in self.ripple:
            p += dt * 1.2
            if p < 1.0:
                new_rip.append((p, mr))
        self.ripple = new_rip

    def draw(self, surf, unlocked, completed, hovered, save):
        if not unlocked and self._appear < 0.01:
            return

        ch  = CHAPTERS[self.idx]
        alpha = int(self._appear * 255)
        r   = self.RADIUS

        # Ripple circles
        for p, mr in self.ripple:
            rr = int(r + (mr - r) * p)
            ra = int(255 * (1 - p))
            s = pygame.Surface((rr*2+4, rr*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*ch["color_in"], ra), (rr+2, rr+2), rr, 2)
            surf.blit(s, (self.cx - rr - 2, self.cy - rr - 2))

        if not unlocked:
            return

        # Pulse glow
        pulse_r = r + int(math.sin(self.pulse) * 2)
        glow_s = pygame.Surface((pulse_r*3, pulse_r*3), pygame.SRCALPHA)
        glow_a = int(60 + math.sin(self.pulse) * 30)
        pygame.draw.circle(glow_s, (*ch["color_in"], glow_a),
                           (pulse_r*3//2, pulse_r*3//2), pulse_r + 4)
        surf.blit(glow_s, (self.cx - pulse_r*3//2, self.cy - pulse_r*3//2))

        # Cercle extérieur
        if hovered:
            pygame.draw.circle(surf, C_GOLD3, (self.cx, self.cy), r + 3)
        pygame.draw.circle(surf, ch["color_out"], (self.cx, self.cy), r)
        pygame.draw.circle(surf, ch["color_in"],  (self.cx, self.cy), r-1, 2)

        # Texte ou étoile si complété
        fnt = pygame.font.SysFont("arial", 10, bold=True)
        if completed:
            from ui import draw_star
            star_sz = max(10, r * 2 - 4)
            draw_star(surf, self.cx - star_sz // 2, self.cy - star_sz // 2, star_sz, True)
        else:
            label = fnt.render(str(self.idx), True, C_PARCHMENT)
            surf.blit(label, (self.cx - label.get_width()//2,
                              self.cy - label.get_height()//2))


# ─────────────────────────────────────────────────────────────────
# CINÉMATIQUE TEXTE
# ─────────────────────────────────────────────────────────────────

class Cinematic:
    def __init__(self):
        self.active   = False
        self.lines    = []
        self.idx      = 0
        self.alpha    = 0.0
        self.timer    = 0.0
        self.chapter  = None
        self._fade_dir = 1  # 1=fade in, -1=fade out

    def start(self, chapter_idx):
        self.active    = True
        self.lines     = CHAPTERS[chapter_idx]["cinematic"]
        self.idx       = 0
        self.alpha     = 0.0
        self.timer     = 0.0
        self.chapter   = chapter_idx
        self._fade_dir = 1

    def skip(self):
        self.active = False

    def update(self, dt):
        if not self.active:
            return
        if self._fade_dir == 1:
            self.alpha = min(1.0, self.alpha + dt * 1.5)
            if self.alpha >= 1.0:
                self.timer += dt
                if self.timer >= 2.8:
                    self._fade_dir = -1
                    self.timer = 0.0
        else:
            self.alpha = max(0.0, self.alpha - dt * 2.0)
            if self.alpha <= 0.0:
                self.idx += 1
                if self.idx >= len(self.lines):
                    self.active = False
                else:
                    self._fade_dir = 1

    def draw(self, screen, sw, sh, fonts):
        if not self.active:
            return
        # Fond noir
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230))
        screen.blit(overlay, (0, 0))

        # Barres cinéma
        bar_h = sh // 7
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, sw, bar_h))
        pygame.draw.rect(screen, (0, 0, 0), (0, sh-bar_h, sw, bar_h))

        if self.idx < len(self.lines):
            line = self.lines[self.idx]
            a = int(self.alpha * 255)
            f = fonts["cine"]
            t = f.render(line, True, (232, 223, 200))
            ts = pygame.Surface((t.get_width(), t.get_height()), pygame.SRCALPHA)
            ts.blit(t, (0, 0))
            ts.set_alpha(a)
            screen.blit(ts, (sw//2 - t.get_width()//2, sh//2 - t.get_height()//2))

        # Bouton passer
        skip_f = fonts["xs"]
        skip_t = skip_f.render("[ Passer ]", True, (138, 106, 30))
        screen.blit(skip_t, (sw - skip_t.get_width() - 20, sh - bar_h + 14))


# ─────────────────────────────────────────────────────────────────
# NOTIFICATION DÉBLOCAGE
# ─────────────────────────────────────────────────────────────────

class Notification:
    def __init__(self):
        self.text   = ""
        self.timer  = 0.0
        self.alpha  = 0.0
        self.active = False

    def show(self, text):
        self.text  = text
        self.timer = 3.0
        self.alpha = 0.0
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self.timer -= dt
        if self.timer > 2.5:
            self.alpha = min(1.0, self.alpha + dt * 4)
        elif self.timer < 0.5:
            self.alpha = max(0.0, self.alpha - dt * 4)
        if self.timer <= 0:
            self.active = False

    def draw(self, screen, sw, fonts):
        if not self.active or self.alpha < 0.01:
            return
        f = fonts["sm"]
        t = f.render(self.text, True, C_GOLD2)
        pad = 14
        nw  = t.get_width() + pad * 2
        nh  = t.get_height() + pad
        nx  = sw // 2 - nw // 2
        ny  = 60

        s = pygame.Surface((nw, nh), pygame.SRCALPHA)
        s.fill((18, 14, 8, int(self.alpha * 230)))
        pygame.draw.rect(s, (*C_GOLD, int(self.alpha * 200)),
                         pygame.Rect(0, 0, nw, nh), 1, border_radius=4)
        screen.blit(s, (nx, ny))

        ts = pygame.Surface((t.get_width(), t.get_height()), pygame.SRCALPHA)
        ts.blit(t, (0, 0))
        ts.set_alpha(int(self.alpha * 255))
        screen.blit(ts, (nx + pad, ny + pad // 2))


# ─────────────────────────────────────────────────────────────────
# ENTRYPOINT PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def run_histoire(screen, clock, save):
    """
    Lance le mode Histoire.
    Retourne :
      None  → retour au menu principal
      dict  → {"chapter": idx, "mission": idx, "difficulty": 1}
               pour lancer une partie
    """
    # ── Initialiser la progression dans save ──
    save.setdefault("histoire_unlocked",  [0])
    save.setdefault("histoire_completed", [])

    sw, sh = screen.get_size()

    # ── Fonts ──
    fonts = {
        "xs":   pygame.font.SysFont("arial", 13),
        "sm":   pygame.font.SysFont("arial", 16),
        "md":   pygame.font.SysFont("arial", 20, bold=True),
        "lg":   pygame.font.SysFont("arial", 26, bold=True),
        "cine": pygame.font.SysFont("arial", 18, italic=True),
        "map_sm": pygame.font.SysFont("arial", 11),
        "map_xs": pygame.font.SysFont("arial",  9),
        "wall":   pygame.font.SysFont("arial", 11, bold=True),
    }

    # ── Zone carte ──
    header_h = 50
    map_w = sw - Popup.WIDTH  # espace pour popup
    map_h = sh - header_h
    # On centre la carte dans l'espace disponible
    map_size = min(map_w, map_h)
    map_x = (map_w - map_size) // 2
    map_y = header_h + (map_h - map_size) // 2

    # ── Construire la surface carte ──
    map_surf = _build_map_surface(map_size, map_size)

    # ── Points de chapitre ──
    chapter_points = {}
    for idx, ch in CHAPTERS.items():
        cx_abs = map_x + int(ch["cx"] * map_size)
        cy_abs = map_y + int(ch["cy"] * map_size)
        chapter_points[idx] = ChapterPoint(idx, cx_abs, cy_abs)

    popup  = Popup()
    cine   = Cinematic()
    notif  = Notification()

    # ── Back button ──
    back_rect = pygame.Rect(12, 12, 90, 28)

    prev_time = pygame.time.get_ticks()

    # ── BOUCLE PRINCIPALE ──
    running = True
    while running:
        now = pygame.time.get_ticks()
        dt  = (now - prev_time) / 1000.0
        prev_time = now

        mx, my = pygame.mouse.get_pos()
        clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if cine.active:
                        cine.skip()
                    elif popup.visible:
                        popup.close()
                    else:
                        return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        # ── Dimensions adaptatives (si resize) ──
        cur_sw, cur_sh = screen.get_size()
        if cur_sw != sw or cur_sh != sh:
            sw, sh = cur_sw, cur_sh
            map_w  = sw - Popup.WIDTH
            map_h  = sh - header_h
            map_size = min(map_w, map_h)
            map_x  = (map_w - map_size) // 2
            map_y  = header_h + (map_h - map_size) // 2
            map_surf = _build_map_surface(map_size, map_size)
            for idx, ch in CHAPTERS.items():
                chapter_points[idx].cx = map_x + int(ch["cx"] * map_size)
                chapter_points[idx].cy = map_y + int(ch["cy"] * map_size)

        unlocked_set  = set(save.get("histoire_unlocked", [0]))
        completed_set = set(save.get("histoire_completed", []))

        # ── Update objets ──
        popup.update(dt)
        cine.update(dt)
        notif.update(dt)
        for idx, cp in chapter_points.items():
            cp.update(dt, idx in unlocked_set)

        # ── Dessin fond ──
        screen.fill(C_BG)

        # ── Carte ──
        screen.blit(map_surf, (map_x, map_y))

        # ── Labels carte (toujours au-dessus, sauf popup/cine) ──
        for (text, pct_x, pct_y, size, color, bold) in MAP_LABELS:
            lx = map_x + int(pct_x * map_size)
            ly = map_y + int(pct_y * map_size)
            fkey = "wall" if bold else "map_xs"
            f = fonts.get(fkey) or pygame.font.SysFont("arial", size, bold=bold)
            # Shadow
            s = f.render(text, True, (0, 0, 0))
            screen.blit(s, (lx - s.get_width()//2 + 1, ly - s.get_height()//2 + 1))
            t = f.render(text, True, color)
            screen.blit(t, (lx - t.get_width()//2, ly - t.get_height()//2))

        # ── Points de chapitre ──
        for idx, cp in chapter_points.items():
            unlocked = idx in unlocked_set
            completed = idx in completed_set
            hovered = (
                unlocked
                and math.dist((mx, my), (cp.cx, cp.cy)) < ChapterPoint.RADIUS + 4
                and not cine.active
            )
            cp.draw(screen, unlocked, completed, hovered, save)

        # ── Header ──
        pygame.draw.rect(screen, (10, 8, 4), (0, 0, sw, header_h))
        pygame.draw.line(screen, C_GOLD, (0, header_h), (sw, header_h), 1)
        title_t = fonts["md"].render("Mode Histoire", True, C_PARCHMENT)
        screen.blit(title_t, (sw//2 - title_t.get_width()//2, 15))
        sub_t = fonts["xs"].render("Les Murs - Territoire Humain", True, C_GOLD)
        screen.blit(sub_t, (sw - sub_t.get_width() - 16, 18))

        # Bouton retour
        bh_col = C_GOLD2 if back_rect.collidepoint(mx, my) else C_GOLD
        pygame.draw.rect(screen, (18, 14, 6), back_rect, border_radius=4)
        pygame.draw.rect(screen, bh_col, back_rect, 1, border_radius=4)
        bt = fonts["xs"].render("< Retour", True, bh_col)
        screen.blit(bt, (back_rect.x + back_rect.w//2 - bt.get_width()//2,
                         back_rect.y + back_rect.h//2 - bt.get_height()//2))

        # ── Popup ──
        start_btn = popup.draw(screen, sw, sh, save, fonts, False, mx, my)

        # ── Notification ──
        notif.draw(screen, sw, fonts)

        # ── Cinématique (par-dessus tout) ──
        cine.draw(screen, sw, sh, fonts)

        # ── Gestion des clics ──
        if clicked and not cine.active:
            # Bouton retour
            if back_rect.collidepoint(mx, my):
                sd.save(save)
                return None

            # Bouton fermer popup (zone x)
            if popup.visible:
                close_zone = pygame.Rect(
                    sw - Popup.WIDTH * popup._anim + Popup.WIDTH - 36,
                    50 + 4, 28, 28
                )
                if close_zone.collidepoint(mx, my):
                    popup.close()

            # Bouton commencer
            if start_btn and start_btn.collidepoint(mx, my) and popup.chapter_idx is not None:
                idx = popup.chapter_idx
                ch  = CHAPTERS[idx]

                if ch.get("type") == "cinematique":
                    cine.start(idx)
                    popup.close()
                    # Marquer complété + débloquer suivant
                    _complete_chapter(idx, save, chapter_points, notif, unlocked_set, completed_set)

                elif ch.get("special"):
                    pass  # Rien à lancer

                else:
                    # Vérifier que la mission sélectionnée est bien déverrouillée
                    mission_idx = popup.selected_mission
                    if is_mission_unlocked(save, idx, mission_idx):
                        sd.save(save)
                        return {"chapter": idx, "mission": mission_idx, "difficulty": 1}

            # Clic sur une ligne de mission dans le popup (pour la sélectionner)
            if popup.visible and popup.chapter_idx is not None:
                ch = CHAPTERS[popup.chapter_idx]
                if ch.get("missions"):
                    pw_p = Popup.WIDTH
                    px_p = int(sw - pw_p * popup._anim)
                    py_p = 50
                    content_y_p = 68
                    row_gap_p = 8
                    clip_y = py_p + content_y_p
                    # Utiliser les hauteurs dynamiques si disponibles, sinon fallback 82
                    row_heights = getattr(popup, "mission_row_heights", None)
                    y_cur = clip_y - popup.scroll
                    for i in range(len(ch["missions"])):
                        rh = row_heights[i] if row_heights and i < len(row_heights) else 82
                        row_rect = pygame.Rect(px_p + 8, y_cur, pw_p - 16, rh)
                        if row_rect.collidepoint(mx, my):
                            if is_mission_unlocked(save, popup.chapter_idx, i):
                                popup.selected_mission = i
                            break
                        y_cur += rh + row_gap_p

            # Clic sur un point de chapitre
            if not popup.visible or not pygame.Rect(sw - int(Popup.WIDTH * popup._anim), 50,
                                                     int(Popup.WIDTH * popup._anim),
                                                     sh - 50).collidepoint(mx, my):
                for idx, cp in chapter_points.items():
                    if idx in unlocked_set:
                        if math.dist((mx, my), (cp.cx, cp.cy)) < ChapterPoint.RADIUS + 6:
                            popup.open(idx)
                            break

        # Passer cinématique
        elif clicked and cine.active:
            cine.skip()

        pygame.display.flip()
        clock.tick(60)

    sd.save(save)
    return None


def _complete_chapter(idx, save, chapter_points, notif, unlocked_set, completed_set):
    """Marque un chapitre complété et débloque le suivant."""
    if idx not in completed_set:
        completed_set.add(idx)
        hist_comp = save.get("histoire_completed", [])
        if idx not in hist_comp:
            hist_comp.append(idx)
        save["histoire_completed"] = hist_comp

    ch = CHAPTERS[idx]
    next_idx = ch.get("unlock_next")
    if next_idx is not None and next_idx not in unlocked_set:
        unlocked_set.add(next_idx)
        hist_unl = save.get("histoire_unlocked", [0])
        if next_idx not in hist_unl:
            hist_unl.append(next_idx)
        save["histoire_unlocked"] = hist_unl
        chapter_points[next_idx].trigger_unlock()
        notif.show(f"Nouveau chapitre débloqué : {CHAPTERS[next_idx]['label']}")

    sd.save(save)

# ─────────────────────────────────────────────────────────────────
# API PUBLIQUE — utilisée par game.py
# ─────────────────────────────────────────────────────────────────

def get_mission_objectives(chapter_idx, mission_idx):
    """
    Retourne la liste des objectifs d'une mission (copies fraîches).
    Chaque objectif : {"text": str, "done": bool}
    """
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if 0 <= mission_idx < len(missions):
        import copy
        return copy.deepcopy(missions[mission_idx].get("objectives", []))
    return []


def get_mission_name(chapter_idx, mission_idx):
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if 0 <= mission_idx < len(missions):
        return missions[mission_idx].get("name", "Mission")
    return "Mission"


def has_next_mission(chapter_idx, mission_idx):
    """Retourne True si une mission suivante existe (même chapitre ou chapitre suivant)."""
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if mission_idx + 1 < len(missions):
        return True
    # Chapitre suivant avec missions
    next_ch = CHAPTERS.get(chapter_idx + 1, {})
    return bool(next_ch.get("missions"))


def get_next_mission(chapter_idx, mission_idx):
    """
    Retourne (chapter_idx, mission_idx) de la mission suivante.
    """
    ch = CHAPTERS.get(chapter_idx, {})
    missions = ch.get("missions", [])
    if mission_idx + 1 < len(missions):
        return chapter_idx, mission_idx + 1
    # Chercher dans le chapitre suivant
    next_ch_idx = chapter_idx + 1
    while next_ch_idx in CHAPTERS:
        next_ch = CHAPTERS[next_ch_idx]
        if next_ch.get("missions"):
            return next_ch_idx, 0
        next_ch_idx += 1
    return chapter_idx, mission_idx  # fallback


def save_mission_result(save, chapter_idx, mission_idx, objectives):
    """
    Sauvegarde le résultat d'une mission :
    - Enregistre les étoiles (objectifs complétés)
    - Sauvegarde l'état de chaque objectif individuellement
    - Déverrouille la mission suivante si ≥1 objectif accompli
    - Marque le chapitre complété si toutes missions faites
    """
    stars_done = sum(1 for o in objectives if o.get("done", False))

    # Stockage des étoiles par mission
    key = f"ch{chapter_idx}_m{mission_idx}_stars"
    prev_best = save.get(key, 0)
    save[key] = max(prev_best, stars_done)

    # Sauvegarder l'état de chaque objectif individuellement
    # On ne rétrograde jamais un objectif déjà accompli (max entre ancien et nouveau)
    obj_key = f"ch{chapter_idx}_m{mission_idx}_objectives"
    prev_obj_states = save.get(obj_key, [])
    new_states = [o.get("done", False) for o in objectives]
    # Fusionner : un objectif déjà accompli reste accompli
    merged = []
    for i, done in enumerate(new_states):
        prev_done = prev_obj_states[i] if i < len(prev_obj_states) else False
        merged.append(done or prev_done)
    save[obj_key] = merged

    # Marquer la mission comme terminée (dans la liste histoire_missions_done)
    done_key = f"ch{chapter_idx}_m{mission_idx}_done"
    save[done_key] = True

    # Déverrouiller la mission suivante si au moins 1 étoile
    if stars_done >= 1:
        ch = CHAPTERS.get(chapter_idx, {})
        missions = ch.get("missions", [])
        next_mission_idx = mission_idx + 1

        if next_mission_idx < len(missions):
            # Mission suivante dans le même chapitre
            unlock_key = f"ch{chapter_idx}_m{next_mission_idx}_unlocked"
            save[unlock_key] = True
        else:
            # Fin du chapitre : débloquer le chapitre suivant
            next_ch_idx = ch.get("unlock_next")
            if next_ch_idx is not None:
                hist_unl = save.get("histoire_unlocked", [0])
                if next_ch_idx not in hist_unl:
                    hist_unl.append(next_ch_idx)
                    save["histoire_unlocked"] = hist_unl
                # Débloquer la première mission du chapitre suivant
                unlock_key = f"ch{next_ch_idx}_m0_unlocked"
                save[unlock_key] = True

            # Marquer le chapitre comme complété
            hist_comp = save.get("histoire_completed", [])
            if chapter_idx not in hist_comp:
                hist_comp.append(chapter_idx)
            save["histoire_completed"] = hist_comp

    sd.save(save)
    return stars_done


def is_mission_unlocked(save, chapter_idx, mission_idx):
    """La mission 0 de chaque chapitre est toujours accessible si le chapitre est débloqué."""
    if mission_idx == 0:
        return chapter_idx in save.get("histoire_unlocked", [0])
    key = f"ch{chapter_idx}_m{mission_idx}_unlocked"
    return save.get(key, False)


def get_mission_best_stars(save, chapter_idx, mission_idx):
    key = f"ch{chapter_idx}_m{mission_idx}_stars"
    return save.get(key, 0)


def get_mission_objective_states(save, chapter_idx, mission_idx):
    """
    Retourne la liste des états d'objectifs sauvegardés pour une mission.
    Ex : [True, False, True] — index aligné sur les objectifs de get_mission_objectives().
    Retourne [] si aucune donnée sauvegardée.
    """
    key = f"ch{chapter_idx}_m{mission_idx}_objectives"
    return save.get(key, [])