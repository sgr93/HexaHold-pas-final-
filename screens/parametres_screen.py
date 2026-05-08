"""
screens/parametres_screen.py

class parametrescreen :
Écran Paramètres — volume musique / sons, statistiques détaillées,
et réinitialisation de la sauvegarde (avec confirmation double clic).
"""

import os
import pygame
import ui.theme as theme
import core.save_data as sd


class ParametresScreen:
    def __init__(self, save):
        self.save           = save
        self._confirm_reset = False  # True après le premier clic sur "Réinitialiser"
        self._show_stats    = False  # popup stats ouverte ou non

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        # Les clics sur le fond sont bloqués quand la popup stats est ouverte
        clicked_bg = clicked and not self._show_stats

        pad = 24
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad * 2

        theme.render_text(screen, "Paramètres", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, w)
        y += f_sec.get_height() + 20

        # Panneau volume — centré dans la zone
        panel_w = min(520, w)
        panel   = pygame.Rect(area.centerx - panel_w // 2, y, panel_w, 200)
        theme.draw_panel(screen, panel, color=theme.DARK_2,
                         border_color=theme.GOLD_DIM, radius=theme.RADIUS_LG)
        theme.draw_corner_ornaments(screen, panel, size=6)
        py = panel.y + 20

        # Volume musique — appliqué en temps réel pour que le joueur entende l'effet
        lbl_m = f_lbl.render("Volume Musique", True, theme.CREAM)
        screen.blit(lbl_m, (panel.x + 20, py))
        py += lbl_m.get_height() + 6
        music_vol = save.get("music_volume", 0.8)
        new_music = self._slider(screen, f_sm, mx, my, clicked_bg,
                                 pygame.Rect(panel.x + 20, py, panel_w - 40, 14), music_vol)
        if new_music != music_vol:
            save["music_volume"] = new_music
            try:
                pygame.mixer.music.set_volume(new_music)
            except Exception:
                pass
            sd.save(save)
        py += 30 + 20

        # Volume sons
        lbl_s = f_lbl.render("Volume Sons", True, theme.CREAM)
        screen.blit(lbl_s, (panel.x + 20, py))
        py += lbl_s.get_height() + 6
        sound_vol = save.get("sound_volume", 0.8)
        new_sound = self._slider(screen, f_sm, mx, my, clicked_bg,
                                 pygame.Rect(panel.x + 20, py, panel_w - 40, 14), sound_vol)
        if new_sound != sound_vol:
            save["sound_volume"] = new_sound
            sd.save(save)

        # Note de sauvegarde automatique
        note = f_ti.render("Les changements sont sauvegardés automatiquement.", True, theme.GOLD_DIM)
        screen.blit(note, (area.centerx - note.get_width() // 2, panel.bottom + 14))

        # Bouton Statistiques
        sbtn = pygame.Rect(area.centerx - 140, panel.bottom + 50, 280, 40)
        s_hov = sbtn.collidepoint(mx, my) and not self._show_stats
        theme.draw_panel(screen, sbtn,
                         color=theme.DARK_3 if s_hov else theme.DARK_2,
                         border_color=theme.GOLD if s_hov else theme.GOLD_DIM,
                         radius=theme.RADIUS_MD, border_w=2)
        sl = f_lbl.render("Statistiques", True, theme.GOLD_LIGHT if s_hov else theme.GOLD)
        screen.blit(sl, (sbtn.centerx - sl.get_width() // 2, sbtn.centery - sl.get_height() // 2))
        if clicked_bg and s_hov:
            self._show_stats = True

        # Bouton Réinitialiser — rouge pour signaler le danger, confirmation sur 2 clics
        btn = pygame.Rect(area.centerx - 140, sbtn.bottom + 12, 280, 40)
        hov = btn.collidepoint(mx, my) and not self._show_stats
        theme.draw_panel(screen, btn,
                         color=(60, 12, 12) if hov else theme.DARK_2,
                         border_color=theme.RED_BADGE if hov else (80, 40, 40),
                         radius=theme.RADIUS_MD, border_w=2)
        bl = f_lbl.render("Réinitialiser la sauvegarde", True,
                          (255, 100, 100) if hov else (180, 70, 70))
        screen.blit(bl, (btn.centerx - bl.get_width() // 2, btn.centery - bl.get_height() // 2))

        if clicked_bg and hov:
            if self._confirm_reset:
                # Deuxième clic — on supprime le fichier et on recharge une save vierge
                save_file = os.path.join(os.path.dirname(__file__), "..", "save.json")
                try:
                    os.remove(save_file)
                except Exception:
                    pass
                new_save = sd.load()
                self.save.clear()
                self.save.update(new_save)
                sd.save(self.save)
                self._confirm_reset = False
            else:
                self._confirm_reset = True  # premier clic — on demande confirmation

        # Message sous le bouton — avertissement si en attente de confirmation, hint sinon
        if self._confirm_reset:
            warn = f_sm.render("Cliquez à nouveau pour confirmer — action irréversible !", True, (255, 160, 60))
            screen.blit(warn, (area.centerx - warn.get_width() // 2, btn.bottom + 8))
        else:
            hint = f_ti.render("Remet les pièces, gemmes, niveaux et progression à zéro.", True, (100, 80, 70))
            screen.blit(hint, (area.centerx - hint.get_width() // 2, btn.bottom + 8))

        # Popup stats — rendue en dernier pour passer par-dessus tout le reste
        if self._show_stats:
            self._draw_stats_popup(screen, area, mx, my, clicked, f_sec, f_lbl, f_sm, f_ti)

        return None

    def _draw_stats_popup(self, screen, area, mx, my, clicked, f_sec, f_lbl, f_sm, f_ti):
        """
        Popup statistiques — deux colonnes (Histoire / Infini) + bandeau total en bas.
        Fermée par le bouton X en haut à droite.
        """
        save = self.save

        # Voile sombre derrière la popup
        veil = pygame.Surface((area.width, area.height), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 180))
        screen.blit(veil, (area.x, area.y))

        pop_w = min(560, area.width - 40)
        pop_h = min(480, area.height - 40)
        pop   = pygame.Rect(area.centerx - pop_w // 2, area.centery - pop_h // 2, pop_w, pop_h)
        theme.draw_panel(screen, pop, color=theme.DARK_2,
                         border_color=theme.GOLD, radius=theme.RADIUS_LG, border_w=2)
        theme.draw_corner_ornaments(screen, pop, size=8)

        title = f_sec.render("Statistiques", True, theme.GOLD_LIGHT)
        screen.blit(title, (pop.centerx - title.get_width() // 2, pop.y + 16))
        theme.draw_gold_rule(screen, pop.x + 24, pop.y + 16 + title.get_height() + 4, pop_w - 48)

        # Bouton fermer
        close = pygame.Rect(pop.right - 36, pop.y + 8, 28, 28)
        c_hov = close.collidepoint(mx, my)
        pygame.draw.rect(screen, (90, 30, 30) if c_hov else theme.DARK_3, close, border_radius=6)
        pygame.draw.rect(screen, theme.GOLD_DIM, close, 1, border_radius=6)
        cx_lbl = f_lbl.render("X", True, (255, 120, 120) if c_hov else theme.GOLD_LIGHT)
        screen.blit(cx_lbl, (close.centerx - cx_lbl.get_width() // 2, close.centery - cx_lbl.get_height() // 2))
        if clicked and c_hov:
            self._show_stats = False
            return

        # Récupération des stats depuis la save
        h_battles = save.get("histoire_battles_won",    0)
        h_kills   = save.get("histoire_enemies_killed",  0)
        h_towers  = save.get("histoire_towers_placed",  0)
        h_chap    = len(save.get("histoire_completed",  []))
        i_battles = save.get("infini_battles_won",       0)
        i_kills   = save.get("infini_enemies_killed",    0)
        i_towers  = save.get("infini_towers_placed",    0)
        i_wave    = save.get("max_wave_reached",         0)
        t_battles = save.get("battles_won",              0)
        t_kills   = save.get("enemies_killed",           0)
        t_towers  = save.get("towers_placed",            0)
        lvl       = save.get("level", 1)

        # Deux colonnes côte à côte
        col_w  = (pop_w - 60) // 2
        col_y  = pop.y + 70
        col_h  = pop_h - 170
        col_x1 = pop.x + 20
        col_x2 = pop.x + 20 + col_w + 20

        def draw_col(x, label, rows, accent):
            box = pygame.Rect(x, col_y, col_w, col_h)
            theme.draw_panel(screen, box, color=theme.DARK_3, border_color=accent,
                             radius=theme.RADIUS_MD, border_w=2)
            hdr = f_lbl.render(label, True, accent)
            screen.blit(hdr, (box.centerx - hdr.get_width() // 2, box.y + 10))
            ry = box.y + 10 + hdr.get_height() + 10
            for k, v in rows:
                k_s = f_sm.render(k, True, theme.CREAM)
                v_s = f_sm.render(str(v), True, theme.GOLD_LIGHT)
                screen.blit(k_s, (box.x + 12, ry))
                screen.blit(v_s, (box.right - 12 - v_s.get_width(), ry))
                ry += k_s.get_height() + 8

        draw_col(col_x1, "Histoire", [
            ("Chapitres terminés", h_chap),
            ("Batailles gagnées",  h_battles),
            ("Ennemis vaincus",    h_kills),
            ("Tours placées",      h_towers),
        ], theme.GOLD)

        draw_col(col_x2, "Infini", [
            ("Vague max",          i_wave),
            ("Batailles gagnées",  i_battles),
            ("Ennemis vaincus",    i_kills),
            ("Tours placées",      i_towers),
        ], (120, 180, 255))

        # Bandeau total en bas de la popup
        tot = pygame.Rect(pop.x + 20, col_y + col_h + 14, pop_w - 40, 56)
        theme.draw_panel(screen, tot, color=theme.DARK_3,
                         border_color=theme.GOLD_DIM, radius=theme.RADIUS_MD, border_w=1)
        thdr = f_lbl.render(f"Total  -  Niveau {lvl}", True, theme.GOLD_LIGHT)
        screen.blit(thdr, (tot.x + 12, tot.y + 6))
        tline = f_sm.render(
            f"Batailles : {t_battles}    Ennemis : {t_kills}    Tours : {t_towers}",
            True, theme.CREAM)
        screen.blit(tline, (tot.x + 12, tot.y + 6 + thdr.get_height() + 4))

    def _slider(self, screen, f_small, mx, my, clicked, rect, value):
        """
        Slider horizontal. Retourne la nouvelle valeur entre 0.0 et 1.0.
        La zone de clic est élargie verticalement pour être plus facile à attraper.
        """
        pygame.draw.rect(screen, theme.DARK_3, rect, border_radius=3)
        pygame.draw.rect(screen, theme.GOLD_DIM, rect, 1, border_radius=3)
        fw = int(rect.width * value)
        if fw > 0:
            pygame.draw.rect(screen, theme.GOLD,
                             pygame.Rect(rect.x, rect.y, fw, rect.height), border_radius=3)
        cx = rect.x + fw
        pygame.draw.circle(screen, theme.GOLD_LIGHT, (cx, rect.centery), 9)
        pygame.draw.circle(screen, theme.DARK,       (cx, rect.centery), 5)
        pct = f_small.render(f"{int(value * 100)}%", True, theme.GOLD_DIM)
        screen.blit(pct, (rect.right + 8, rect.centery - pct.get_height() // 2))
        if clicked and rect.inflate(0, 24).collidepoint(mx, my):
            value = max(0.0, min(1.0, (mx - rect.x) / rect.width))
        return value