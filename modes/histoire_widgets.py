"""
histoire_widgets.py
-------------------
Composants UI du mode histoire : Popup, ChapterPoint, Cinematic, Notification.
"""
import math
import pygame
from modes.histoire_data import (
    CHAPTERS, C_BG, C_GOLD, C_GOLD2, C_GOLD3, C_PARCHMENT, C_PANEL, C_MUTED,
)
from modes.histoire_data import is_mission_unlocked, get_mission_best_stars
from ui.ui import draw_star


def _is_mission_unlocked(save, chapter_idx, mission_idx):
    # Lazy import pour eviter l'import circulaire histoire <-> histoire_widgets
    return is_mission_unlocked(save, chapter_idx, mission_idx)


def _get_mission_best_stars(save, chapter_idx, mission_idx):
    return get_mission_best_stars(save, chapter_idx, mission_idx)


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
            computed_heights = [_mission_row_h(m, not _is_mission_unlocked(save, self.chapter_idx, i))
                                 for i, m in enumerate(missions)]
            self.mission_row_heights = computed_heights

            y_cursor = 0
            for i, m in enumerate(missions):
                locked = not _is_mission_unlocked(save, self.chapter_idx, i)
                row_h = _mission_row_h(m, locked)
                ry = y_cursor - self.scroll
                y_cursor += row_h + row_gap

                if ry + row_h < 0 or ry > clip_h:
                    continue

                row = pygame.Rect(8, ry, pw-16, row_h)
                stars_done = _get_mission_best_stars(save, self.chapter_idx, i)
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
