"""
screens/accueil_screen.py
--------------------------
Écran d'accueil in-game : résumé joueur + boutons Jouer.
Retourne un niveau (int ou dict) si "Jouer" est cliqué, None sinon.
"""

import pygame
import theme
from config import DIFFICULTY_LEVELS


class AccueilScreen:
    def __init__(self, save):
        self.save = save

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        pad = 20
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad*2

        # ── Titre section ────────────────────────────────────
        theme.render_text(screen, "✦  Accueil", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, w)
        y += f_sec.get_height() + 14

        # ── Résumé stats joueur ──────────────────────────────
        panel_h = 90
        panel   = pygame.Rect(x, y, w, panel_h)
        theme.draw_panel(screen, panel, border_color=theme.GOLD_DIM)
        theme.draw_corner_ornaments(screen, panel, size=6)

        px, py = panel.x + 14, panel.y + 10
        theme.render_text(screen, f"Soldat — Niveau {save.get('level',1)}",
                          f_lbl, theme.CREAM, px, py, shadow=False)
        py += f_lbl.get_height() + 4

        xp_bar = pygame.Rect(px, py, panel.width - 28, 8)
        theme.draw_xp_bar(screen, xp_bar, save.get("xp",0), max(1,save.get("xp_next",30)))
        py += 12
        theme.render_text(screen, f"{save.get('xp',0)} / {save.get('xp_next',30)} XP",
                          f_ti, theme.GOLD_DIM, px, py, shadow=False)

        # Stats rapides
        stats = [
            ("Victoires",      save.get("battles_won", 0)),
            ("Ennemis vaincus",save.get("enemies_killed", 0)),
            ("Tours placées",  save.get("towers_placed", 0)),
        ]
        sx = panel.x + panel.width//2
        sy = panel.y + 10
        for label, val in stats:
            vs = f_sm.render(f"{label} : {val}", True, theme.CREAM_DIM)
            screen.blit(vs, (sx, sy))
            sy += vs.get_height() + 3

        y += panel_h + 20

        # ── Mode Histoire ────────────────────────────────────
        theme.render_text(screen, "Mode Histoire", f_lbl, theme.CREAM, x, y, shadow=False)
        y += f_lbl.get_height() + 6
        hist_btn = pygame.Rect(x, y, w, 52)
        hov = hist_btn.collidepoint(mx, my)
        theme.draw_panel(screen, hist_btn,
                         color=(30,22,8) if hov else theme.DARK_2,
                         border_color=theme.GOLD if hov else theme.GOLD_DIM,
                         radius=theme.RADIUS_MD, border_w=2)
        theme.draw_corner_ornaments(screen, hist_btn, size=6)
        theme.render_text(screen, "Carte des Murs — Campagne principale",
                          f_sm, theme.GOLD_LIGHT if hov else theme.CREAM,
                          hist_btn.centerx, hist_btn.centery - f_sm.get_height()//2,
                          center=True, shadow=False)
        if clicked and hov:
            return "histoire"   # signal pour main_ui de lancer run_histoire

        y += 52 + 16

        # ── Partie rapide ────────────────────────────────────
        theme.render_text(screen, "Partie rapide", f_lbl, theme.CREAM, x, y, shadow=False)
        y += f_lbl.get_height() + 6

        DIFF_COLORS = {
            1:(80,200,100), 2:(140,220,80), 3:(255,200,40),
            4:(255,120,40), 5:(255,60,60)
        }
        btn_h = 44
        btn_g = 8

        for lvl, info in DIFFICULTY_LEVELS.items():
            if y + btn_h > area.bottom:
                break
            btn = pygame.Rect(x, y, w, btn_h)
            hov2 = btn.collidepoint(mx, my)
            dc = DIFF_COLORS[lvl]
            theme.draw_panel(screen, btn,
                             color=(25,20,10) if hov2 else theme.DARK_2,
                             border_color=dc,
                             radius=theme.RADIUS_MD, border_w=2 if hov2 else 1)
            nl = f_sm.render(f"Niv. {lvl}  —  {info['name']}", True, dc)
            screen.blit(nl, (btn.x+14, btn.y+7))
            dl = f_ti.render(
                f"{info['waves']} vagues  |  x{info['enemy_hp_mult']} HP ennemi  |  {info['coins_reward']} pièces",
                True, theme.CREAM_DIM)
            screen.blit(dl, (btn.x+14, btn.y+26))
            if clicked and hov2:
                return lvl
            y += btn_h + btn_g

        return None