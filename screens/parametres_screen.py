"""
screens/parametres_screen.py
-----------------------------
Écran Paramètres — volume musique / sons uniquement.
Le toggle plein écran a été retiré.
"""

import pygame
import theme
import save_data as sd


class ParametresScreen:
    def __init__(self, save):
        self.save           = save
        self._confirm_reset = False

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        pad = 24
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad * 2

        # ── Titre ───────────────────────────────────────────────
        theme.render_text(screen, "Paramètres", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, w)
        y += f_sec.get_height() + 20

        panel_w = min(520, w)
        panel_h = 200
        panel   = pygame.Rect(area.centerx - panel_w // 2, y, panel_w, panel_h)
        theme.draw_panel(screen, panel, color=theme.DARK_2,
                         border_color=theme.GOLD_DIM, radius=theme.RADIUS_LG)
        theme.draw_corner_ornaments(screen, panel, size=6)

        py = panel.y + 20

        # ── Volume musique ──────────────────────────────────────
        lbl_m = f_lbl.render("Volume Musique", True, theme.CREAM)
        screen.blit(lbl_m, (panel.x + 20, py))
        py += lbl_m.get_height() + 6

        bar_m = pygame.Rect(panel.x + 20, py, panel_w - 40, 14)
        music_vol = save.get("music_volume", 0.8)
        new_music = self._slider(screen, f_sm, mx, my, clicked, bar_m, music_vol)
        if new_music != music_vol:
            save["music_volume"] = new_music
            try:
                pygame.mixer.music.set_volume(new_music)
            except Exception:
                pass
            sd.save(save)
        py += 30 + 20

        # ── Volume sons ─────────────────────────────────────────
        lbl_s = f_lbl.render("Volume Sons", True, theme.CREAM)
        screen.blit(lbl_s, (panel.x + 20, py))
        py += lbl_s.get_height() + 6

        bar_s = pygame.Rect(panel.x + 20, py, panel_w - 40, 14)
        sound_vol = save.get("sound_volume", 0.8)
        new_sound = self._slider(screen, f_sm, mx, my, clicked, bar_s, sound_vol)
        if new_sound != sound_vol:
            save["sound_volume"] = new_sound
            sd.save(save)

        # ── Note bas ────────────────────────────────────────────
        note = f_ti.render("Les changements sont sauvegardés automatiquement.", True, theme.GOLD_DIM)
        screen.blit(note, (area.centerx - note.get_width() // 2,
                           panel.bottom + 14))

        # ── Bouton Réinitialiser la partie ──────────────────────
        btn_w  = 280
        btn_h  = 40
        btn_y  = panel.bottom + 50
        btn_x  = area.centerx - btn_w // 2
        btn    = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        hov    = btn.collidepoint(mx, my)
        theme.draw_panel(screen, btn,
                         color=(60, 12, 12) if hov else theme.DARK_2,
                         border_color=theme.RED_BADGE if hov else (80, 40, 40),
                         radius=theme.RADIUS_MD, border_w=2)
        bl = f_lbl.render("Reinitialiser la sauvegarde", True,
                          (255, 100, 100) if hov else (180, 70, 70))
        screen.blit(bl, (btn.centerx - bl.get_width() // 2,
                         btn.centery - bl.get_height() // 2))

        # Confirmation sur 2 clics
        if clicked and hov:
            if self._confirm_reset:
                # Deuxieme clic : reset
                import save_data as _sd
                import os as _os
                save_file = _os.path.join(_os.path.dirname(__file__), "..", "save.json")
                try:
                    _os.remove(save_file)
                except Exception:
                    pass
                new_save = _sd.load()
                self.save.clear()
                self.save.update(new_save)
                _sd.save(self.save)
                self._confirm_reset = False
            else:
                self._confirm_reset = True

        # Afficher avertissement si premier clic
        if self._confirm_reset:
            warn = f_sm.render("Cliquez a nouveau pour confirmer - cette action est irreversible !", True, (255, 160, 60))
            screen.blit(warn, (area.centerx - warn.get_width() // 2, btn.bottom + 8))
        else:
            hint = f_ti.render("Remet les pièces, gemmes, niveaux et progression à zero.", True, (100, 80, 70))
            screen.blit(hint, (area.centerx - hint.get_width() // 2, btn.bottom + 8))

        return None

    def _slider(self, screen, f_small, mx, my, clicked, rect, value):
        """Slider horizontal. Retourne la nouvelle valeur."""
        pygame.draw.rect(screen, theme.DARK_3, rect, border_radius=3)
        pygame.draw.rect(screen, theme.GOLD_DIM, rect, 1, border_radius=3)
        fw = int(rect.width * value)
        if fw > 0:
            pygame.draw.rect(screen, theme.GOLD,
                             pygame.Rect(rect.x, rect.y, fw, rect.height),
                             border_radius=3)
        cx = rect.x + fw
        pygame.draw.circle(screen, theme.GOLD_LIGHT, (cx, rect.centery), 9)
        pygame.draw.circle(screen, theme.DARK,       (cx, rect.centery), 5)
        pct = f_small.render(f"{int(value * 100)}%", True, theme.GOLD_DIM)
        screen.blit(pct, (rect.right + 8, rect.centery - pct.get_height() // 2))
        if clicked and rect.inflate(0, 24).collidepoint(mx, my):
            value = max(0.0, min(1.0, (mx - rect.x) / rect.width))
        return value