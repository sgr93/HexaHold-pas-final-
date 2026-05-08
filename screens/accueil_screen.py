"""
screens/accueil_screen.py

Ecran d'accueil : carte joueur, stats, mode infini, parties rapides et section heros.
C'est l'ecran qu'on voit en premier apres le menu — il doit donner envie de jouer.
"""

import math
import pygame
import ui.theme as theme
import core.heroes as hm
import core.save_data as sd
from core.config import DIFFICULTY_LEVELS, XP_MULTS


DIFF_COLORS = {
    1: (80,  200, 100),
    2: (180, 220,  60),
    3: (255, 200,  40),
    4: (255, 120,  40),
    5: (255,  60,  60),
}
DIFF_SHORT = {
    1: "Facile",
    2: "Normal",
    3: "Difficile",
    4: "T.Diff.",
    5: "Cauchemar",
}
# XP_MULTS importé depuis core/config.py


def _rarity_color(rarity):
    """Couleur associee a chaque rarete de heros."""
    return {"Legendaire": (220, 160, 30), "Rare": (80, 140, 220)}.get(rarity, (160, 155, 145))


class AccueilScreen:
    def __init__(self, save):
        self.save         = save
        self._tick        = 0
        self._hero_popup  = False
        self._hero_detail = None  # None = grille affichee, sinon dict du heros selectionne
        hm.init_heroes_save(save)

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        self._tick += 1
        save  = self.save
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        pad = 14
        x   = area.x + pad
        y   = area.y + pad
        w   = area.width - pad * 2

        # Carte joueur — nom, niveau, barre XP
        card_h = 64
        card   = pygame.Rect(x, y, w, card_h)
        theme.draw_panel(screen, card, border_color=theme.GOLD_DIM)

        av_r  = 18
        av_cx = card.x + 14 + av_r
        av_cy = card.centery
        pygame.draw.circle(screen, theme.DARK_2, (av_cx, av_cy), av_r + 2)
        pygame.draw.circle(screen, theme.GOLD,   (av_cx, av_cy), av_r + 2, 2)

        icon_name = save.get("player_icon", "icone0")
        if icon_name.endswith(".png"):
            icon_name = icon_name[:-4]
        icon = theme.load_sprite(icon_name + ".png", (av_r * 2 - 4, av_r * 2 - 4))
        if icon:
            screen.blit(icon, (av_cx - av_r + 2, av_cy - av_r + 2))
        else:
            # Fallback : initiale du joueur si l'icone est absente
            ini = f_lbl.render((save.get("player_name") or "S")[0].upper(), True, theme.GOLD_LIGHT)
            screen.blit(ini, (av_cx - ini.get_width() // 2, av_cy - ini.get_height() // 2))

        tx = av_cx + av_r + 12
        ty = card.y + 8
        lvl    = save.get("level", 1)
        name_s = f_lbl.render(save.get("player_name", "Soldat"), True, theme.CREAM)
        lvl_s  = f_ti.render(f"Niveau {lvl}", True, theme.GOLD_DIM)
        screen.blit(name_s, (tx, ty))
        screen.blit(lvl_s,  (tx + name_s.get_width() + 8, ty + 2))
        ty    += name_s.get_height() + 5
        xp     = save.get("xp", 0)
        xp_nxt = max(1, save.get("xp_next", 30))
        theme.draw_xp_bar(screen, pygame.Rect(tx, ty, card.right - tx - 14, 5), xp, xp_nxt)
        ty += 8
        screen.blit(f_ti.render(f"{xp} / {xp_nxt} XP", True, theme.GOLD_DIM), (tx, ty))

        y += card_h + 8

        # 3 tuiles de stats — chiffres en Arial pour la lisibilite rapide
        tile_w  = (w - 8) // 3
        tile_h  = 44
        f_arial = pygame.font.SysFont("arial", 18, bold=True)
        stats = [
            ("Victoires",     save.get("battles_won",    0)),
            ("Tours placees", save.get("towers_placed",  0)),
            ("Ennemis tues",  save.get("enemies_killed", 0)),
        ]
        for i, (lbl, val) in enumerate(stats):
            tr = pygame.Rect(x + i * (tile_w + 4), y, tile_w, tile_h)
            theme.draw_panel(screen, tr, color=theme.DARK_3, border_color=(40, 35, 25))
            vs = f_arial.render(str(val), True, theme.CREAM)
            ls = f_ti.render(lbl, True, theme.GOLD_DIM)
            screen.blit(vs, (tr.centerx - vs.get_width() // 2, tr.y + 6))
            screen.blit(ls, (tr.centerx - ls.get_width() // 2, tr.bottom - ls.get_height() - 4))
        y += tile_h + 10

        # Mode infini — fond violet distinct pour le demarquer des autres modes
        inf_h    = 90
        inf_rect = pygame.Rect(x, y, w, inf_h)
        inf_hov  = inf_rect.collidepoint(mx, my) and not self._hero_popup
        record   = save.get("max_wave_reached", 0)

        pygame.draw.rect(screen, (18, 8, 38), inf_rect, border_radius=theme.RADIUS_LG)
        bdr_col = (210, 150, 255) if inf_hov else (120, 50, 200)
        pygame.draw.rect(screen, bdr_col, inf_rect, 3 if inf_hov else 2, border_radius=theme.RADIUS_LG)
        theme.draw_corner_ornaments(screen, inf_rect, size=6, color=(120, 50, 200))

        f_inf     = theme.font(theme.SZ_SECTION)
        f_inf_sub = theme.font(theme.SZ_SMALL, body=True)
        screen.blit(f_inf.render("Mode Infini", True, (210, 150, 255)),
                    (inf_rect.x + 14, inf_rect.y + 10))
        screen.blit(f_inf_sub.render("Difficulte croissante - survivez le plus longtemps possible",
                                     True, (130, 80, 180)),
                    (inf_rect.x + 14, inf_rect.y + 10 + f_inf.get_height() + 4))

        # Record de vagues a droite
        f_rec_num = pygame.font.SysFont("arial", 26, bold=True)
        f_rec_lbl = pygame.font.SysFont("arial", 11)
        rec_n = f_rec_num.render(str(record), True, (210, 150, 255))
        rec_l = f_rec_lbl.render("vagues record",  True, (130, 80, 180))
        screen.blit(rec_n, (inf_rect.right - rec_n.get_width() - 14, inf_rect.y + 10))
        screen.blit(rec_l, (inf_rect.right - rec_l.get_width() - 14,
                             inf_rect.y + 10 + rec_n.get_height() + 2))
        if clicked and inf_hov:
            return "infini"
        y += inf_h + 8

        # Parties rapides par difficulte
        screen.blit(f_ti.render("PARTIE RAPIDE", True, theme.GOLD_DIM), (x, y))
        y += f_ti.get_height() + 4

        n_diff    = len(DIFFICULTY_LEVELS)
        bw        = (w - (n_diff - 1) * 4) // n_diff
        bh        = 72
        f_info2   = pygame.font.SysFont("arial", 11, bold=True)
        diff_done = set(save.get("difficulty_completed", []))

        for i, (lvl, info) in enumerate(DIFFICULTY_LEVELS.items()):
            bx  = x + i * (bw + 4)
            btn = pygame.Rect(bx, y, bw, bh)
            # Verrou : il faut avoir fini la difficulte precedente pour debloquer la suivante
            locked = lvl > 1 and (lvl - 1) not in diff_done
            hov    = btn.collidepoint(mx, my) and not self._hero_popup and not locked
            dc     = DIFF_COLORS[lvl]

            theme.draw_panel(screen, btn,
                             color=(14, 10, 4) if locked else ((20, 15, 5) if hov else theme.DARK_2),
                             border_color=(60, 55, 45) if locked else dc,
                             radius=theme.RADIUS_MD, border_w=2 if hov else 1)

            name_col = (90, 80, 60) if locked else dc
            nl = f_sm.render(DIFF_SHORT[lvl], True, name_col)
            screen.blit(nl, (btn.centerx - nl.get_width() // 2, btn.y + 7))

            sep_y   = btn.y + 7 + nl.get_height() + 4
            sep_col = (30, 28, 22) if locked else (dc[0] // 3, dc[1] // 3, dc[2] // 3)
            pygame.draw.line(screen, sep_col, (btn.x + 6, sep_y), (btn.right - 6, sep_y), 1)

            iy = sep_y + 8
            if locked:
                # Affichage du pre-requis de deblocage
                lock_msg = f_info2.render(f"Finir {DIFF_SHORT[lvl - 1]}", True, (140, 110, 70))
                screen.blit(lock_msg, (btn.centerx - lock_msg.get_width() // 2, iy))
                lk = theme.load_sprite("cadenas.png", (16, 16))
                if lk:
                    screen.blit(lk, (btn.right - 18, btn.y + 4))
                else:
                    xs = f_info2.render("X", True, (160, 100, 60))
                    screen.blit(xs, (btn.right - xs.get_width() - 4, btn.y + 4))
            else:
                coins    = info.get("coins_reward", 0)
                waves    = info.get("waves", 1)
                xp_mult  = XP_MULTS.get(lvl, 1.0)
                s_vagues = f_info2.render(f"Vagues:{waves}",      True, theme.GOLD_DIM)
                s_pieces = f_info2.render(f"Pieces:{coins}",      True, theme.GOLD_DIM)
                s_xp     = f_info2.render(f"XP:x{xp_mult:.1f}",  True, theme.GOLD_DIM)
                gap      = 5
                total_w2 = s_vagues.get_width() + gap + s_pieces.get_width() + gap + s_xp.get_width()
                lx       = btn.centerx - total_w2 // 2
                screen.blit(s_vagues, (lx, iy))
                screen.blit(s_pieces, (lx + s_vagues.get_width() + gap, iy))
                screen.blit(s_xp,    (lx + s_vagues.get_width() + gap + s_pieces.get_width() + gap, iy))

            if clicked and hov:
                return lvl
        y += bh + 10

        # Section heros en bas — hauteur dynamique selon l'espace restant
        y += 20
        remaining = area.bottom - y - 4
        hero_h    = min(remaining, int(area.height * 0.40))
        if hero_h >= 60:
            self._draw_hero_section(screen, x, y, w, hero_h, save,
                                    f_lbl, f_sm, f_ti, mx, my, clicked, area)
        return None

    def _draw_hero_section(self, screen, x, y, w, h, save,
                           f_lbl, f_sm, f_ti, mx, my, clicked, area):
        """Section portrait du heros actif avec bouton d'ouverture du popup de selection."""
        selected_id = hm.get_selected_hero(save)
        sel_def     = hm.HEROES[selected_id]
        rc          = _rarity_color(sel_def["rarity"])
        zone        = pygame.Rect(x, y, w, h)

        # Fond fond_hero.png en "cover" — conserve le ratio et recadre pour remplir
        bg_img = theme.load_sprite("fond_hero.png", None)
        if bg_img:
            iw, ih  = bg_img.get_size()
            scale   = max(w / iw, h / ih)
            new_w   = int(iw * scale)
            new_h   = int(ih * scale)
            bg_scl  = pygame.transform.smoothscale(bg_img, (new_w, new_h))
            ox      = (new_w - w) // 2
            oy      = (new_h - h) // 2
            screen.blit(bg_scl, (zone.x, zone.y), pygame.Rect(ox, oy, w, h))
        else:
            pygame.draw.rect(screen, (22, 17, 10), zone, border_radius=theme.RADIUS_MD)
            pygame.draw.rect(screen, (30, 24, 14), zone.inflate(-4, -4), border_radius=theme.RADIUS_MD)

        pygame.draw.rect(screen, (70, 58, 35), zone, 2, border_radius=theme.RADIUS_MD)
        theme.draw_corner_ornaments(screen, zone, size=5, color=(90, 72, 40))

        # Portrait du heros — ratio conserve, pas force en carre
        img_size     = min(h - 24, 220)
        portrait_raw = theme.load_sprite(sel_def["sprite_portrait"], None)
        if portrait_raw:
            ow, oh   = portrait_raw.get_size()
            scale    = min(img_size / ow, img_size / oh)
            portrait = pygame.transform.smoothscale(portrait_raw,
                                                    (int(ow * scale), int(oh * scale)))
        else:
            portrait = None

        if portrait:
            screen.blit(portrait, (zone.centerx - portrait.get_width() // 2,
                                   zone.y + (h - portrait.get_height()) // 2))
        else:
            fb = f_lbl.render(sel_def["name"].split()[0], True, rc)
            screen.blit(fb, (zone.centerx - fb.get_width() // 2,
                              zone.centery - fb.get_height() // 2))

        # Bouton "Heros" centre en haut de la zone
        btn_lbl  = f_sm.render("Heros", True, (20, 14, 4))
        btn_w2   = btn_lbl.get_width() + 24
        btn_h2   = btn_lbl.get_height() + 8
        hero_btn = pygame.Rect(zone.centerx - btn_w2 // 2, zone.y + 8, btn_w2, btn_h2)
        zone_hov = zone.collidepoint(mx, my)
        pygame.draw.rect(screen, (220, 170, 30) if zone_hov else (180, 130, 20),
                         hero_btn, border_radius=6)
        screen.blit(btn_lbl, (hero_btn.centerx - btn_lbl.get_width() // 2,
                               hero_btn.centery - btn_lbl.get_height() // 2))

        # Nom du passif en bas de la zone
        f_pa = pygame.font.SysFont("arial", 14, bold=True)
        pa_s = f_pa.render(f"Passif : {sel_def['passive_name']}", True, (25, 18, 10))
        screen.blit(pa_s, (zone.centerx - pa_s.get_width() // 2,
                           zone.bottom - pa_s.get_height() - 5))

        if clicked and zone.collidepoint(mx, my) and not self._hero_popup:
            self._hero_popup  = True
            self._hero_detail = None

        if self._hero_popup:
            self._draw_popup(screen, area, save, f_lbl, f_sm, f_ti, mx, my, clicked)

    def _draw_popup(self, screen, area, save, f_lbl, f_sm, f_ti, mx, my, clicked):
        """
        Popup de selection de heros — deux vues : grille des heros et fiche detail.
        La hauteur s'adapte selon qu'on affiche la grille ou la fiche.
        """
        CELL   = 52
        COLS_P = 5
        PAD    = 10
        HDR_H  = 36

        pop_w = COLS_P * (CELL + PAD) + PAD
        rows  = (len(hm.HERO_ORDER) + COLS_P - 1) // COLS_P
        pop_h = HDR_H + 220 if self._hero_detail else HDR_H + rows * (CELL + PAD) + PAD

        pop_x = max(area.x + 4, min(area.centerx - pop_w // 2, area.right - pop_w - 4))
        pop_y = max(area.y + 4, area.bottom - pop_h - 4)
        pop   = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

        theme.draw_rect_alpha(screen, (*theme.DARK_2, 255), pop, radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.GOLD_DIM, pop, 1, border_radius=theme.RADIUS_LG)
        theme.draw_corner_ornaments(screen, pop, size=6)

        # Header : titre ou bouton retour selon la vue
        if self._hero_detail:
            back_s    = f_sm.render("< Retour", True, theme.GOLD_DIM)
            back_rect = pygame.Rect(pop.x + 8, pop.y + (HDR_H - back_s.get_height()) // 2,
                                    back_s.get_width() + 12, back_s.get_height() + 6)
            if back_rect.collidepoint(mx, my):
                pygame.draw.rect(screen, (30, 25, 15), back_rect, border_radius=4)
            screen.blit(back_s, (back_rect.x + 6, back_rect.y + 3))
            if clicked and back_rect.collidepoint(mx, my):
                self._hero_detail = None
                return
            title_s = f_sm.render(self._hero_detail["name"], True, theme.CREAM)
        else:
            title_s = f_sm.render("Choisir un heros", True, theme.CREAM)
        screen.blit(title_s, (pop.centerx - title_s.get_width() // 2,
                               pop.y + (HDR_H - title_s.get_height()) // 2))

        # Bouton fermer — croix rouge en haut a droite
        cx_r  = 10
        cx_x  = pop.right - cx_r - 8
        cx_y  = pop.y + HDR_H // 2
        cx_c  = pygame.Rect(cx_x - cx_r, cx_y - cx_r, cx_r * 2, cx_r * 2)
        hov_x = cx_c.collidepoint(mx, my)
        pygame.draw.circle(screen, theme.RED_BADGE if hov_x else (50, 18, 18), (cx_x, cx_y), cx_r)
        xs = f_ti.render("X", True, theme.CREAM)
        screen.blit(xs, (cx_x - xs.get_width() // 2, cx_y - xs.get_height() // 2))
        if clicked and hov_x:
            self._hero_popup  = False
            self._hero_detail = None
            return

        theme.draw_gold_rule(screen, pop.x + 6, pop.y + HDR_H, pop_w - 12)
        content_y = pop.y + HDR_H + 6

        if not self._hero_detail:
            self._draw_hero_grid(screen, pop, content_y, save, f_ti, mx, my, clicked,
                                 CELL, COLS_P, PAD)
        else:
            self._draw_hero_detail(screen, pop, content_y, save, f_lbl, f_sm, f_ti,
                                   mx, my, clicked)

    def _draw_hero_grid(self, screen, pop, content_y, save, f_ti,
                        mx, my, clicked, CELL, COLS_P, PAD):
        """Grille de tous les heros avec indicateur de selection et de verrouillage."""
        selected_id = hm.get_selected_hero(self.save)
        for idx, hid in enumerate(hm.HERO_ORDER):
            hdef     = hm.HEROES[hid]
            col_i    = idx % COLS_P
            row_i    = idx // COLS_P
            cx       = pop.x + PAD + col_i * (CELL + PAD)
            cy       = content_y + row_i * (CELL + PAD)
            cell     = pygame.Rect(cx, cy, CELL, CELL)
            unlocked = hm.is_hero_unlocked(self.save, hid)
            is_sel   = hid == selected_id
            rc       = _rarity_color(hdef["rarity"])

            bg  = (20, 14, 4) if is_sel else theme.DARK_2
            bdr = rc if is_sel else ((rc[0] // 2, rc[1] // 2, rc[2] // 2) if unlocked else (40, 35, 25))
            theme.draw_panel(screen, cell, color=bg, border_color=bdr,
                             radius=theme.RADIUS_MD, border_w=2 if is_sel else 1)

            img = theme.load_sprite(hdef["sprite_select"], (CELL - 8, CELL - 8))
            if img:
                tmp = img.copy()
                if not unlocked:
                    tmp.set_alpha(55)  # heros non obtenu — tres transparent
                screen.blit(tmp, (cx + 4, cy + 4))
            else:
                ini = f_ti.render(hdef["name"][0], True, rc if unlocked else (50, 45, 35))
                screen.blit(ini, (cx + CELL // 2 - ini.get_width() // 2,
                                  cy + CELL // 2 - ini.get_height() // 2))

            if not unlocked:
                lock = theme.load_sprite("cadenas.png", (16, 16))
                if lock:
                    screen.blit(lock, (cx + CELL - 18, cy + CELL - 18))
                else:
                    ls = f_ti.render("X", True, (160, 50, 50))
                    screen.blit(ls, (cx + CELL - ls.get_width() - 3, cy + 3))

            if clicked and cell.collidepoint(mx, my):
                h_save = hm.get_hero_save(self.save, hid)
                self._hero_detail = {
                    "id":           hid,
                    "name":         hdef["name"],
                    "rarity":       hdef["rarity"],
                    "passive_name": hdef["passive_name"],
                    "passive_desc": hdef["passive_desc"],
                    "sprite_select": hdef["sprite_select"],
                    "unlocked":     unlocked,
                    "level":        h_save.get("level",  1),
                    "copies":       h_save.get("copies", 0),
                }

    def _draw_hero_detail(self, screen, pop, content_y, save, f_lbl, f_sm, f_ti,
                          mx, my, clicked):
        """Fiche detaillee d'un heros : portrait, rarete, passif, copies et boutons."""
        h   = self._hero_detail
        rc  = _rarity_color(h["rarity"])
        px  = content_y
        pop_w = pop.width

        # Icone + meta a droite
        row_rect = pygame.Rect(pop.x + 10, px, pop_w - 20, 60)
        img = theme.load_sprite(h["sprite_select"], (54, 54))
        if img:
            if not h["unlocked"]:
                img.set_alpha(70)
            screen.blit(img, (row_rect.x, px))
        ix_end = row_rect.x + 60

        n_s = f_lbl.render(h["name"], True, theme.CREAM)
        screen.blit(n_s, (ix_end, px))

        r_s = f_ti.render(h["rarity"], True, rc)
        rb  = pygame.Rect(ix_end, px + n_s.get_height() + 4, r_s.get_width() + 12, r_s.get_height() + 4)
        pygame.draw.rect(screen, (20, 14, 6), rb, border_radius=10)
        pygame.draw.rect(screen, rc,           rb, 1, border_radius=10)
        screen.blit(r_s, (rb.x + 6, rb.y + 2))

        copies = hm.get_hero_save(self.save, h["id"]).get("copies", h["copies"])
        bar_y2 = px + n_s.get_height() + rb.height + 8

        # Copies necessaires pour level-up : formule 2 * 1.5^(level-1)
        copies_needed = max(1, math.ceil(2 * (1.5 ** (h["level"] - 1))))
        extra_copies  = max(0, copies - 1)

        cp_s = f_ti.render(f"Niv. {h['level']}  {extra_copies}/{copies_needed} copies",
                           True, (100, 85, 60))
        screen.blit(cp_s, (ix_end, bar_y2))

        if h["unlocked"]:
            can_levelup = extra_copies >= copies_needed
            lv_col  = (120, 220, 120) if can_levelup else (60, 55, 45)
            lv_bg   = (20, 40, 20)   if can_levelup else (22, 20, 16)
            lv_bc   = (80, 180, 80)  if can_levelup else (40, 38, 30)
            lv_t    = f_ti.render(f"Niv. sup ({extra_copies}/{copies_needed})", True, lv_col)
            lv_rect = pygame.Rect(row_rect.right - lv_t.get_width() - 12,
                                  bar_y2 - 1, lv_t.get_width() + 10, cp_s.get_height() + 4)
            pygame.draw.rect(screen, lv_bg, lv_rect, border_radius=4)
            pygame.draw.rect(screen, lv_bc, lv_rect, 1, border_radius=4)
            screen.blit(lv_t, (lv_rect.x + 5, lv_rect.y + 2))
            if clicked and lv_rect.collidepoint(mx, my) and can_levelup:
                h_save = hm.get_hero_save(self.save, h["id"])
                h_save["copies"] = max(0, h_save.get("copies", 1) - copies_needed)
                h_save["level"]  = h_save.get("level", 1) + 1
                self._hero_detail["level"]  = h_save["level"]
                self._hero_detail["copies"] = h_save["copies"]
                sd.save(self.save)

        bar_y2 += cp_s.get_height() + 2
        br = pygame.Rect(ix_end, bar_y2, row_rect.right - ix_end, 5)
        pygame.draw.rect(screen, (40, 35, 25), br, border_radius=3)
        fw = int(br.width * min(1.0, extra_copies / copies_needed))
        if fw > 0:
            pygame.draw.rect(screen, rc, pygame.Rect(br.x, br.y, fw, br.height), border_radius=3)
        px += 68

        pygame.draw.line(screen, (40, 35, 25), (pop.x + 8, px), (pop.right - 8, px), 1)
        px += 8

        # Passif — nom et description sur plusieurs lignes
        screen.blit(f_ti.render("COMPETENCE PASSIVE", True, (80, 70, 50)), (pop.x + 10, px))
        px += f_ti.get_height() + 4
        screen.blit(f_sm.render(h["passive_name"], True, rc), (pop.x + 10, px))
        px += f_sm.get_height() + 4

        words = h["passive_desc"].replace("\n", " ").split()
        line  = ""
        max_w = pop_w - 20
        for word in words:
            test = line + (" " if line else "") + word
            if f_ti.render(test, True, (0, 0, 0)).get_width() > max_w and line:
                screen.blit(f_ti.render(line, True, (140, 120, 85)), (pop.x + 10, px))
                px  += f_ti.get_height() + 1
                line = word
            else:
                line = test
        if line:
            screen.blit(f_ti.render(line, True, (140, 120, 85)), (pop.x + 10, px))
            px += f_ti.get_height() + 4

        bonus = {"Commun": "10%", "Rare": "20%", "Legendaire": "30%"}.get(h["rarity"], "10%")
        screen.blit(f_ti.render(f"Bonus par niveau : +{bonus} ATK/HP", True, (80, 70, 50)),
                    (pop.x + 10, px))
        px += f_ti.get_height() + 6

        if not h["unlocked"]:
            lock_msg = f_ti.render("Non obtenu - disponible via le Gacha (gemmes)", True, (180, 80, 80))
            screen.blit(lock_msg, (pop.centerx - lock_msg.get_width() // 2, px))
            px += lock_msg.get_height() + 6

        # Boutons Selectionner / Fermer
        btn_w3 = (pop_w - 24) // 2
        sel_r  = pygame.Rect(pop.x + 8,           px, btn_w3, 28)
        fer_r  = pygame.Rect(sel_r.right + 8,     px, btn_w3, 28)

        if h["unlocked"]:
            sel_hov = sel_r.collidepoint(mx, my)
            pygame.draw.rect(screen, (220, 170, 30) if sel_hov else (160, 120, 20),
                             sel_r, border_radius=6)
            sel_t = f_sm.render("Selectionner", True, (20, 14, 4))
        else:
            pygame.draw.rect(screen, (35, 30, 20), sel_r, border_radius=6)
            pygame.draw.rect(screen, (50, 40, 30), sel_r, 1, border_radius=6)
            sel_t = f_sm.render("Non obtenu", True, (80, 65, 45))
        screen.blit(sel_t, (sel_r.centerx - sel_t.get_width() // 2,
                            sel_r.centery - sel_t.get_height() // 2))

        fer_hov = fer_r.collidepoint(mx, my)
        pygame.draw.rect(screen, (30, 25, 18) if fer_hov else (25, 20, 15),
                         fer_r, border_radius=6)
        pygame.draw.rect(screen, (50, 45, 35), fer_r, 1, border_radius=6)
        fer_t = f_sm.render("Fermer", True, (120, 105, 75))
        screen.blit(fer_t, (fer_r.centerx - fer_t.get_width() // 2,
                            fer_r.centery - fer_t.get_height() // 2))

        if clicked and sel_r.collidepoint(mx, my) and h["unlocked"]:
            hm.select_hero(self.save, h["id"])
            sd.save(self.save)
            self._hero_popup  = False
            self._hero_detail = None
        if clicked and fer_r.collidepoint(mx, my):
            self._hero_detail = None