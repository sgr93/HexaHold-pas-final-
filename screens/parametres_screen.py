"""
screens/parametres_screen.py
-----------------------------
Écran Paramètres in-game : volume, affichage, réinitialisation.
"""

import pygame
import theme
import save_data as sd


class ParametresScreen:
    def __init__(self, save):
        self.save = save

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save  = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        pad = 16
        x, y = area.x+pad, area.y+pad
        w    = area.width - pad*2

        theme.render_text(screen, "Paramètres", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y+f_sec.get_height()+2, w)
        y += f_sec.get_height()+20

        panel_w = min(500, w)
        px      = area.x + (area.width - panel_w)//2

        # ── Volume musique ───────────────────────────────────
        theme.render_text(screen, "Volume Musique", f_lbl, theme.CREAM, px, y, shadow=False)
        y += f_lbl.get_height()+6
        bar = pygame.Rect(px, y, panel_w, 14)
        mv  = save.get("music_volume", 0.8)
        mv  = self._slider(screen, f_ti, mx, my, clicked, bar, mv)
        save["music_volume"] = mv
        try:
            pygame.mixer.music.set_volume(mv)
        except Exception:
            pass
        y += 28

        # ── Volume sons ──────────────────────────────────────
        theme.render_text(screen, "Volume Sons", f_lbl, theme.CREAM, px, y, shadow=False)
        y += f_lbl.get_height()+6
        bar2 = pygame.Rect(px, y, panel_w, 14)
        sv   = save.get("sound_volume", 0.8)
        sv   = self._slider(screen, f_ti, mx, my, clicked, bar2, sv)
        save["sound_volume"] = sv
        y += 36

        # ── Plein écran ──────────────────────────────────────
        toggle = pygame.Rect(px, y, 32, 18)
        fs     = save.get("fullscreen", False)
        pygame.draw.rect(screen, theme.DARK_3, toggle, border_radius=9)
        pygame.draw.rect(screen, theme.GOLD if fs else theme.GOLD_DIM, toggle, 1, border_radius=9)
        tcx = toggle.right-10 if fs else toggle.x+10
        pygame.draw.circle(screen, theme.GOLD_LIGHT if fs else theme.GOLD_DIM, (tcx, toggle.centery), 7)
        theme.render_text(screen, "Plein écran", f_lbl, theme.CREAM,
                          px+40, y, shadow=False)
        if clicked and toggle.collidepoint(mx, my):
            fs = not fs
            save["fullscreen"] = fs
            try:
                flags = pygame.FULLSCREEN if fs else pygame.RESIZABLE
                pygame.display.set_mode((0,0) if fs else (1280,720), flags)
            except Exception:
                pass
        y += 36

        # ── Sauvegarder ─────────────────────────────────────
        btn_save = pygame.Rect(px, y, 180, 40)
        hov = btn_save.collidepoint(mx, my)
        theme.draw_panel(screen, btn_save,
                         color=(25,18,5) if hov else theme.DARK_2,
                         border_color=theme.GOLD if hov else theme.GOLD_DIM,
                         radius=theme.RADIUS_MD, border_w=2)
        theme.render_text(screen, "Sauvegarder", f_lbl,
                          theme.GOLD_LIGHT if hov else theme.CREAM,
                          btn_save.centerx, btn_save.centery-f_lbl.get_height()//2,
                          center=True, shadow=False)
        if clicked and hov:
            sd.save(save)

        # ── Réinitialiser ────────────────────────────────────
        y += 56
        btn_reset = pygame.Rect(px, y, 220, 40)
        hov2 = btn_reset.collidepoint(mx, my)
        theme.draw_panel(screen, btn_reset,
                         color=(35,10,10) if hov2 else theme.DARK_2,
                         border_color=theme.RED_BADGE,
                         radius=theme.RADIUS_MD, border_w=2)
        theme.render_text(screen, "Réinitialiser la sauvegarde", f_sm,
                          theme.RED_BADGE if hov2 else theme.CREAM_DIM,
                          btn_reset.centerx, btn_reset.centery-f_sm.get_height()//2,
                          center=True, shadow=False)
        if clicked and hov2:
            sd.reset()

        return None

    def _slider(self, screen, f_ti, mx, my, clicked, rect, value):
        pygame.draw.rect(screen, theme.DARK_3, rect, border_radius=3)
        pygame.draw.rect(screen, theme.GOLD_DIM, rect, 1, border_radius=3)
        fw = int(rect.width * value)
        if fw > 0:
            pygame.draw.rect(screen, theme.GOLD, pygame.Rect(rect.x,rect.y,fw,rect.height), border_radius=3)
        pygame.draw.circle(screen, theme.GOLD_LIGHT, (rect.x+fw, rect.centery), 9)
        pygame.draw.circle(screen, theme.DARK, (rect.x+fw, rect.centery), 5)
        pct = f_ti.render(f"{int(value*100)}%", True, theme.GOLD_DIM)
        screen.blit(pct, (rect.right+8, rect.centery-pct.get_height()//2))
        if clicked and rect.inflate(0,24).collidepoint(mx, my):
            value = max(0.0, min(1.0, (mx-rect.x)/rect.width))
        return value
