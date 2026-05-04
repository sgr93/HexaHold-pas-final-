"""
screens/quetes_screen.py
------------------------
Écran Quêtes — grille de cartes style RPG avec barre de progression.
Sections : Quotidiennes | Missions | Événements
"""

import pygame
import ui.theme as theme
import core.quetes as qm
import core.save_data as sd


SECTIONS = [
    ("quotidiennes", "Quotidiennes"),
    ("missions",     "Missions"),
    ("evenements",   "Histoire"),
]


class QuetesScreen:
    def __init__(self, save):
        self.save    = save
        self.section = "quotidiennes"
        self.scroll  = 0

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save = self.save
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        pad = 16
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad * 2

        # ── Titre
        theme.render_text(screen, "Quetes et Missions", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, w)
        y += f_sec.get_height() + 14

        # ── Sous-onglets
        stab_w = w // len(SECTIONS)
        stab_h = 32
        for i, (key, label) in enumerate(SECTIONS):
            sr = pygame.Rect(x + i * stab_w, y, stab_w - 4, stab_h)
            is_act = key == self.section
            theme.draw_panel(screen, sr,
                             color=(30, 22, 8) if is_act else theme.DARK_2,
                             border_color=theme.GOLD if is_act else theme.GOLD_DIM,
                             radius=theme.RADIUS_SM, border_w=2 if is_act else 1)
            theme.render_text(screen, label, f_sm,
                              theme.GOLD_LIGHT if is_act else theme.CREAM_DIM,
                              sr.centerx, sr.centery - f_sm.get_height()//2,
                              center=True, shadow=False)
            if clicked and sr.collidepoint(mx, my):
                self.section = key
                self.scroll  = 0
        y += stab_h + 12

        # ── Quêtes
        quests = qm.get_quests_by_section(self.section)
        self.scroll = max(0, self.scroll - scroll_dy * 20)

        card_h   = 120
        card_gap = 10
        cols     = 2
        col_w    = (w - card_gap) // cols

        clip = pygame.Rect(area.x, y, area.width, area.bottom - y)
        screen.set_clip(clip)

        cy_base = y - self.scroll
        for idx, (qid, quest) in enumerate(quests.items()):
            col = idx % cols
            row = idx // cols
            cx  = x + col * (col_w + card_gap)
            cy  = cy_base + row * (card_h + card_gap)
            if cy + card_h < clip.top or cy > clip.bottom:
                continue
            progress  = qm.get_quest_progress(save, qid)
            self._draw_card(screen, pygame.Rect(cx, cy, col_w, card_h),
                            qid, quest,
                            progress["completed"], progress["available"], progress["claimed"],
                            f_lbl, f_sm, f_ti, mx, my, clicked, save)

        screen.set_clip(None)

        rows_total = (len(quests) + cols - 1) // cols
        max_scroll = max(0, rows_total * (card_h + card_gap) - (area.bottom - y - 10))
        self.scroll = min(self.scroll, max_scroll)
        return None

    def _draw_card(self, screen, rect, qid, quest,
                   done, claimable, claimed,
                   f_lbl, f_sm, f_ti, mx, my, clicked, save):
        hov  = rect.collidepoint(mx, my)
        bcol = theme.GREEN_OK if claimable else (theme.GOLD_DIM if claimed else
                                                  (theme.GOLD_DIM if hov else (50,42,28)))
        theme.draw_panel(screen, rect,
                         color=theme.DARK_3 if hov else theme.DARK_2,
                         border_color=bcol,
                         radius=theme.RADIUS_MD, border_w=2 if (claimable or hov) else 1)
        theme.draw_corner_ornaments(screen, rect, size=6,
                                    color=theme.GOLD if claimable else theme.GOLD_DIM)

        # Bande colorée haut
        band_col = theme.GREEN_OK if claimable else (theme.GOLD_DIM if claimed else (50,42,28))
        pygame.draw.rect(screen, band_col,
                         pygame.Rect(rect.x, rect.y, rect.width, 5),
                         border_radius=theme.RADIUS_MD)

        px, py = rect.x + 12, rect.y + 10

        name_s = f_lbl.render(quest["nom"], True,
                               theme.GOLD_LIGHT if claimable else theme.CREAM)
        screen.blit(name_s, (px, py))
        py += name_s.get_height() + 2

        desc_s = f_sm.render(quest["description"], True, theme.CREAM_DIM)
        screen.blit(desc_s, (px, py))
        py += desc_s.get_height() + 6

        # Barre de progression
        prog_rect = pygame.Rect(px, py, rect.width - 24, 6)
        fill = 1 if (done or claimed) else 0
        theme.draw_progress_bar(screen, prog_rect, fill, 1)
        py += 12

        # Récompenses
        ry = rect.bottom - f_ti.get_height() - 8
        parts = []
        if quest.get("xp"):     parts.append(f"+{quest['xp']} XP")
        if quest.get("pieces"): parts.append(f"+{quest['pieces']} pièces")
        if quest.get("gemmes"): parts.append(f"+{quest['gemmes']} gemmes")
        rew_s = f_ti.render(",  ".join(parts), True, theme.GOLD_DIM)
        screen.blit(rew_s, (px, ry))

        if claimable:
            btn = pygame.Rect(rect.right - 100, ry - 4, 90, 22)
            bhov = btn.collidepoint(mx, my)
            theme.draw_panel(screen, btn,
                             color=(20,50,20) if bhov else (15,35,15),
                             border_color=theme.GREEN_OK, radius=theme.RADIUS_SM, border_w=2)
            theme.render_text(screen, "Reclamer", f_ti, theme.GREEN_OK,
                              btn.centerx, btn.centery - f_ti.get_height()//2,
                              center=True, shadow=False)
            if clicked and bhov:
                qm.claim_quest_reward(save, qid)
                sd.save(save)
        elif claimed:
            bdg = f_ti.render("Reclamee", True, theme.GOLD_DIM)
            screen.blit(bdg, (rect.right - bdg.get_width() - 10, ry))