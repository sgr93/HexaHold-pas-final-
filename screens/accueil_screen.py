"""
screens/accueil_screen.py
"""

import math
import pygame
import theme
import heroes as hm
import save_data as sd
from config import DIFFICULTY_LEVELS

DIFF_COLORS = {
    1: (80,  200, 100),
    2: (180, 220,  60),
    3: (255, 200,  40),
    4: (255, 120,  40),
    5: (255,  60,  60),
}
DIFF_SHORT = {1:"Facile", 2:"Normal", 3:"Difficile", 4:"T.Diff.", 5:"Cauchemar"}


class AccueilScreen:
    def __init__(self, save):
        self.save         = save
        self._tick        = 0
        self._hero_popup  = False
        self._hero_detail = None   # None = grille affichee, sinon dict du heros
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

        # ── Carte joueur ──────────────────────────────────────
        card_h = 64
        card   = pygame.Rect(x, y, w, card_h)
        theme.draw_panel(screen, card, border_color=theme.GOLD_DIM)

        av_r  = 18
        av_cx = card.x + 14 + av_r
        av_cy = card.centery
        pygame.draw.circle(screen, theme.DARK_2, (av_cx, av_cy), av_r + 2)
        pygame.draw.circle(screen, theme.GOLD,   (av_cx, av_cy), av_r + 2, 2)
        icon_name = save.get("player_icon", "icone0")
        if icon_name.endswith(".png"): icon_name = icon_name[:-4]
        icon = theme.load_sprite(icon_name + ".png", (av_r*2-4, av_r*2-4))
        if icon:
            screen.blit(icon, (av_cx - av_r + 2, av_cy - av_r + 2))
        else:
            ini = f_lbl.render((save.get("player_name") or "S")[0].upper(), True, theme.GOLD_LIGHT)
            screen.blit(ini, (av_cx - ini.get_width()//2, av_cy - ini.get_height()//2))

        tx = av_cx + av_r + 12
        ty = card.y + 8
        lvl = save.get("level", 1)
        name_s = f_lbl.render(save.get("player_name","Soldat"), True, theme.CREAM)
        lvl_s  = f_ti.render(f"Niveau {lvl}", True, theme.GOLD_DIM)
        screen.blit(name_s, (tx, ty))
        screen.blit(lvl_s,  (tx + name_s.get_width() + 8, ty + 2))
        ty += name_s.get_height() + 5
        xp     = save.get("xp", 0)
        xp_nxt = max(1, save.get("xp_next", 30))
        xp_bar = pygame.Rect(tx, ty, card.right - tx - 14, 5)
        theme.draw_xp_bar(screen, xp_bar, xp, xp_nxt)
        ty += 8
        xp_s = f_ti.render(f"{xp} / {xp_nxt} XP", True, theme.GOLD_DIM)
        screen.blit(xp_s, (tx, ty))

        y += card_h + 8

        # ── Stats (3 tuiles, chiffres en Arial) ──────────────
        tile_w  = (w - 8) // 3
        tile_h  = 44
        f_arial = pygame.font.SysFont("arial", 18, bold=True)
        stats = [
            ("Victoires",     save.get("battles_won", 0)),
            ("Tours placees", save.get("towers_placed", 0)),
            ("Ennemis tues",  save.get("enemies_killed", 0)),
        ]
        for i, (lbl, val) in enumerate(stats):
            tr = pygame.Rect(x + i*(tile_w+4), y, tile_w, tile_h)
            theme.draw_panel(screen, tr, color=theme.DARK_3, border_color=(40,35,25))
            vs = f_arial.render(str(val), True, theme.CREAM)
            ls = f_ti.render(lbl, True, theme.GOLD_DIM)
            screen.blit(vs, (tr.centerx - vs.get_width()//2, tr.y + 6))
            screen.blit(ls, (tr.centerx - ls.get_width()//2, tr.bottom - ls.get_height() - 4))
        y += tile_h + 10

        # ── Mode infini ───────────────────────────────────────
        inf_h    = 90
        inf_rect = pygame.Rect(x, y, w, inf_h)
        inf_hov  = inf_rect.collidepoint(mx, my) and not self._hero_popup
        record   = save.get("max_wave_reached", 0)

        # Fond violet plus prononce + bordure plus epaisse
        pygame.draw.rect(screen, (18, 8, 38), inf_rect, border_radius=theme.RADIUS_LG)
        bdr_col  = (210, 150, 255) if inf_hov else (120, 50, 200)
        bdr_w    = 3 if inf_hov else 2
        pygame.draw.rect(screen, bdr_col, inf_rect, bdr_w, border_radius=theme.RADIUS_LG)
        theme.draw_corner_ornaments(screen, inf_rect, size=6, color=(120,50,200))

        f_inf   = theme.font(theme.SZ_SECTION)
        f_inf_sub = theme.font(theme.SZ_SMALL, body=True)
        ti_s  = f_inf.render("Mode Infini", True, (210, 150, 255))
        sub_s = f_inf_sub.render("Difficulte croissante — survivez le plus longtemps possible", True, (130, 80, 180))
        screen.blit(ti_s,  (inf_rect.x + 14, inf_rect.y + 10))
        screen.blit(sub_s, (inf_rect.x + 14, inf_rect.y + 10 + ti_s.get_height() + 4))

        f_rec_num = pygame.font.SysFont("arial", 26, bold=True)
        f_rec_lbl = pygame.font.SysFont("arial", 11)
        rec_n = f_rec_num.render(str(record), True, (210, 150, 255))
        rec_l = f_rec_lbl.render("vagues record", True, (130, 80, 180))
        screen.blit(rec_n, (inf_rect.right - rec_n.get_width() - 14, inf_rect.y + 10))
        screen.blit(rec_l, (inf_rect.right - rec_l.get_width() - 14,
                             inf_rect.y + 10 + rec_n.get_height() + 2))
        if clicked and inf_hov:
            return "infini"
        y += inf_h + 8

        # ── Partie rapide ─────────────────────────────────────
        sec_lbl = f_ti.render("PARTIE RAPIDE", True, theme.GOLD_DIM)
        screen.blit(sec_lbl, (x, y))
        y += sec_lbl.get_height() + 4

        XP_MULTS = {1: 1.0, 2: 1.5, 3: 2.0, 4: 3.0, 5: 5.0}

        n_diff  = len(DIFFICULTY_LEVELS)
        bw      = (w - (n_diff-1)*4) // n_diff
        bh      = 72
        f_info  = pygame.font.SysFont("arial", 9)
        diff_done = set(save.get("difficulty_completed", []))
        for i, (lvl, info) in enumerate(DIFFICULTY_LEVELS.items()):
            bx  = x + i*(bw+4)
            btn = pygame.Rect(bx, y, bw, bh)
            # Verrou : au-delà de Difficile (lvl >= 4) il faut avoir fini la difficulté précédente
            locked = lvl >= 4 and (lvl - 1) not in diff_done
            hov = btn.collidepoint(mx, my) and not self._hero_popup and not locked
            dc  = DIFF_COLORS[lvl]
            border_c = (60, 55, 45) if locked else dc
            theme.draw_panel(screen, btn,
                             color=(14, 10, 4) if locked else
                                   ((20,15,5) if hov else theme.DARK_2),
                             border_color=border_c,
                             radius=theme.RADIUS_MD, border_w=2 if hov else 1)

            # Nom difficulte (grisé si verrouillé)
            name_col = (90, 80, 60) if locked else dc
            nl  = f_sm.render(DIFF_SHORT[lvl], True, name_col)
            screen.blit(nl, (btn.centerx - nl.get_width()//2, btn.y + 7))

            # Separateur
            sep_y = btn.y + 7 + nl.get_height() + 4
            sep_col = ((30, 28, 22) if locked
                       else (dc[0]//3, dc[1]//3, dc[2]//3))
            pygame.draw.line(screen, sep_col,
                             (btn.x+6, sep_y), (btn.right-6, sep_y), 1)

            # Infos : vagues, pieces, xp
            coins   = info.get("coins_reward", 0)
            waves   = info.get("waves", 1)
            xp_mult = XP_MULTS.get(lvl, 1.0)

            f_info2 = pygame.font.SysFont("arial", 11, bold=True)
            iy = sep_y + 8

            if locked:
                # Affichage verrou + texte requis
                lock_msg = f_info2.render(f"Finir {DIFF_SHORT[lvl-1]}", True, (140, 110, 70))
                screen.blit(lock_msg, (btn.centerx - lock_msg.get_width()//2, iy))
                lk = theme.load_sprite("cadenas.png", (16, 16))
                if lk:
                    screen.blit(lk, (btn.right - 18, btn.y + 4))
                else:
                    xs = f_info2.render("X", True, (160, 100, 60))
                    screen.blit(xs, (btn.right - xs.get_width() - 4, btn.y + 4))
            else:
                # Tout sur une ligne : Vagues  Pieces  XP
                s_vagues = f_info2.render(f"Vagues:{waves}", True, theme.GOLD_DIM)
                s_pieces = f_info2.render(f"Pieces:{coins}", True, theme.GOLD_DIM)
                s_xp     = f_info2.render(f"XP:x{xp_mult:.1f}", True, theme.GOLD_DIM)
                gap = 5
                total_w = s_vagues.get_width() + gap + s_pieces.get_width() + gap + s_xp.get_width()
                lx = btn.centerx - total_w // 2
                screen.blit(s_vagues, (lx, iy))
                screen.blit(s_pieces, (lx + s_vagues.get_width() + gap, iy))
                screen.blit(s_xp,    (lx + s_vagues.get_width() + gap + s_pieces.get_width() + gap, iy))

            if clicked and hov:
                return lvl
        y += bh + 10

        # ── Section Heros ─────────────────────────────────────
        y += 20   # marge supplementaire pour descendre la section
        remaining = area.bottom - y - 4
        hero_h    = min(remaining, int(area.height * 0.40))
        if hero_h >= 60:
            self._draw_hero_section(screen, x, y, w, hero_h, save,
                                    f_lbl, f_sm, f_ti, mx, my, clicked, area)
        return None

    # ──────────────────────────────────────────────────────────

    def _draw_hero_section(self, screen, x, y, w, h, save,
                           f_lbl, f_sm, f_ti, mx, my, clicked, area):
        selected_id = hm.get_selected_hero(save)
        sel_def     = hm.HEROES[selected_id]
        rc          = _rarity_color(sel_def["rarity"])

        # Zone portrait
        zone = pygame.Rect(x, y, w, h)
        bg_img = theme.load_sprite("fond_hero.png", None)  # charge sans redimensionner
        if bg_img:
            # Mise a l'echelle "cover" : ratio conserve, recadre pour remplir la zone
            iw, ih = bg_img.get_size()
            scale = max(w / iw, h / ih)
            new_w = int(iw * scale)
            new_h = int(ih * scale)
            bg_scaled = pygame.transform.smoothscale(bg_img, (new_w, new_h))
            ox = (new_w - w) // 2
            oy = (new_h - h) // 2
            screen.blit(bg_scaled, (zone.x, zone.y), pygame.Rect(ox, oy, w, h))
        else:
            # Fallback si image non trouvee
            pygame.draw.rect(screen, (22, 17, 10), zone, border_radius=theme.RADIUS_MD)
            inner = zone.inflate(-4, -4)
            pygame.draw.rect(screen, (30, 24, 14), inner, border_radius=theme.RADIUS_MD)
        pygame.draw.rect(screen, (70, 58, 35), zone, 2, border_radius=theme.RADIUS_MD)
        theme.draw_corner_ornaments(screen, zone, size=5, color=(90, 72, 40))

        # Portrait centré
        img_size = min(h - 24, 220)
        portrait_raw = theme.load_sprite(sel_def["sprite_portrait"], (img_size, img_size))
        # Recharge sans forcer le carre pour conserver le ratio
        portrait_orig = theme.load_sprite(sel_def["sprite_portrait"], None)
        if portrait_orig:
            ow, oh = portrait_orig.get_size()
            scale = min(img_size / ow, img_size / oh)
            pw = int(ow * scale)
            ph = int(oh * scale)
            portrait = pygame.transform.smoothscale(portrait_orig, (pw, ph))
        else:
            portrait = portrait_raw
        if portrait:
            screen.blit(portrait, (zone.centerx - portrait.get_width()//2,
                                   zone.y + (h - portrait.get_height())//2))
        else:
            fb = f_lbl.render(sel_def["name"].split()[0], True, rc)
            screen.blit(fb, (zone.centerx - fb.get_width()//2,
                              zone.centery - fb.get_height()//2))

        # Bouton "Heros" — bien visible, centré en haut
        btn_lbl  = f_sm.render("Heros", True, (20,14,4))
        btn_w2   = btn_lbl.get_width() + 24
        btn_h2   = btn_lbl.get_height() + 8
        btn_rx   = zone.centerx - btn_w2//2
        btn_ry   = zone.y + 8
        hero_btn = pygame.Rect(btn_rx, btn_ry, btn_w2, btn_h2)
        zone_hov = zone.collidepoint(mx, my)
        pygame.draw.rect(screen,
                         (220,170,30) if zone_hov else (180,130,20),
                         hero_btn, border_radius=6)
        screen.blit(btn_lbl, (hero_btn.centerx - btn_lbl.get_width()//2,
                               hero_btn.centery - btn_lbl.get_height()//2))

        # Nom du passif en bas
        f_pa = pygame.font.SysFont("arial", 14, bold=True)
        pa_s = f_pa.render(f"Passif : {sel_def['passive_name']}", True, (25, 18, 10))
        screen.blit(pa_s, (zone.centerx - pa_s.get_width()//2, zone.bottom - pa_s.get_height() - 5))

        if clicked and zone.collidepoint(mx, my) and not self._hero_popup:
            self._hero_popup  = True
            self._hero_detail = None

        # Popup
        if self._hero_popup:
            self._draw_popup(screen, area, save, f_lbl, f_sm, f_ti, mx, my, clicked)

    def _draw_popup(self, screen, area, save, f_lbl, f_sm, f_ti, mx, my, clicked):
        CELL   = 52
        COLS_P = 5
        PAD    = 10
        HDR_H  = 36

        pop_w  = COLS_P*(CELL+PAD) + PAD
        rows   = (len(hm.HERO_ORDER) + COLS_P - 1) // COLS_P
        # Hauteur : soit grille soit fiche
        if self._hero_detail:
            pop_h = HDR_H + 220
        else:
            pop_h = HDR_H + rows*(CELL+PAD) + PAD

        pop_x = max(area.x+4, area.centerx - pop_w//2)
        pop_x = min(pop_x, area.right - pop_w - 4)
        pop_y = max(area.y+4, area.bottom - pop_h - 4)
        pop   = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

        # Fond
        theme.draw_rect_alpha(screen, (*theme.DARK_2, 255), pop, radius=theme.RADIUS_LG)
        pygame.draw.rect(screen, theme.GOLD_DIM, pop, 1, border_radius=theme.RADIUS_LG)
        theme.draw_corner_ornaments(screen, pop, size=6)

        # Header
        if self._hero_detail:
            # Bouton retour
            back_s = f_sm.render("< Retour", True, theme.GOLD_DIM)
            back_rect = pygame.Rect(pop.x+8, pop.y + (HDR_H-back_s.get_height())//2,
                                    back_s.get_width()+12, back_s.get_height()+6)
            back_hov = back_rect.collidepoint(mx, my)
            if back_hov:
                pygame.draw.rect(screen, (30,25,15), back_rect, border_radius=4)
            screen.blit(back_s, (back_rect.x+6, back_rect.y+3))
            if clicked and back_rect.collidepoint(mx, my):
                self._hero_detail = None
                return
            title_s = f_sm.render(self._hero_detail["name"], True, theme.CREAM)
        else:
            title_s = f_sm.render("Choisir un heros", True, theme.CREAM)
        screen.blit(title_s, (pop.centerx - title_s.get_width()//2,
                               pop.y + (HDR_H - title_s.get_height())//2))

        # Croix fermer
        cx_r = 10
        cx_x = pop.right - cx_r - 8
        cx_y = pop.y + HDR_H//2
        cx_c = pygame.Rect(cx_x-cx_r, cx_y-cx_r, cx_r*2, cx_r*2)
        pygame.draw.circle(screen, theme.RED_BADGE if cx_c.collidepoint(mx,my) else (50,18,18),
                           (cx_x, cx_y), cx_r)
        xs = f_ti.render("X", True, theme.CREAM)
        screen.blit(xs, (cx_x-xs.get_width()//2, cx_y-xs.get_height()//2))
        if clicked and cx_c.collidepoint(mx,my):
            self._hero_popup  = False
            self._hero_detail = None
            return

        theme.draw_gold_rule(screen, pop.x+6, pop.y+HDR_H, pop_w-12)
        content_y = pop.y + HDR_H + 6

        # ── Vue grille ────────────────────────────────────────
        if not self._hero_detail:
            selected_id = hm.get_selected_hero(self.save)
            for idx, hid in enumerate(hm.HERO_ORDER):
                hdef     = hm.HEROES[hid]
                col_i    = idx % COLS_P
                row_i    = idx // COLS_P
                cx       = pop.x + PAD + col_i*(CELL+PAD)
                cy       = content_y + row_i*(CELL+PAD)
                cell     = pygame.Rect(cx, cy, CELL, CELL)
                unlocked = hm.is_hero_unlocked(self.save, hid)
                is_sel   = (hid == selected_id)
                rc       = _rarity_color(hdef["rarity"])

                bg  = (20,14,4) if is_sel else theme.DARK_2
                bdr = rc if is_sel else (rc[0]//2, rc[1]//2, rc[2]//2) if unlocked else (40,35,25)
                theme.draw_panel(screen, cell, color=bg, border_color=bdr,
                                 radius=theme.RADIUS_MD, border_w=2 if is_sel else 1)

                img = theme.load_sprite(hdef["sprite_select"], (CELL-8, CELL-8))
                if img:
                    tmp = img.copy()
                    if not unlocked: tmp.set_alpha(55)
                    screen.blit(tmp, (cx+4, cy+4))
                else:
                    ini = f_ti.render(hdef["name"][0], True, rc if unlocked else (50,45,35))
                    screen.blit(ini, (cx+CELL//2-ini.get_width()//2,
                                      cy+CELL//2-ini.get_height()//2))
                if not unlocked:
                    lock = theme.load_sprite("cadenas.png", (16,16))
                    if lock:
                        screen.blit(lock, (cx+CELL-18, cy+CELL-18))
                    else:
                        ls = f_ti.render("X", True, (160,50,50))
                        screen.blit(ls, (cx+CELL-ls.get_width()-3, cy+3))

                if clicked and cell.collidepoint(mx, my):
                    h_save = hm.get_hero_save(self.save, hid)
                    self._hero_detail = {
                        "id": hid, "name": hdef["name"],
                        "rarity": hdef["rarity"],
                        "passive_name": hdef["passive_name"],
                        "passive_desc": hdef["passive_desc"],
                        "sprite_select": hdef["sprite_select"],
                        "unlocked": unlocked,
                        "level": h_save.get("level", 1),
                        "copies": h_save.get("copies", 0),
                    }

        # ── Vue fiche ─────────────────────────────────────────
        else:
            h  = self._hero_detail
            rc = _rarity_color(h["rarity"])
            px = content_y

            # Icone + meta
            row_rect = pygame.Rect(pop.x+10, px, pop_w-20, 60)
            img = theme.load_sprite(h["sprite_select"], (54,54))
            if img:
                if not h["unlocked"]: img.set_alpha(70)
                screen.blit(img, (row_rect.x, px))
            ix_end = row_rect.x + 60

            n_s = f_lbl.render(h["name"], True, theme.CREAM)
            screen.blit(n_s, (ix_end, px))

            r_s = f_ti.render(h["rarity"], True, rc)
            rb  = pygame.Rect(ix_end, px+n_s.get_height()+4, r_s.get_width()+12, r_s.get_height()+4)
            pygame.draw.rect(screen, (20,14,6), rb, border_radius=10)
            pygame.draw.rect(screen, rc, rb, 1, border_radius=10)
            screen.blit(r_s, (rb.x+6, rb.y+2))

            copies = hm.get_hero_save(self.save, h["id"]).get("copies", h["copies"])
            bar_y2 = px + n_s.get_height() + rb.height + 8

            # Calcul copies_needed pour l'affichage (avant le bloc unlocked)
            copies_needed_display = max(1, math.ceil(2 * (1.5 ** (h["level"] - 1))))
            extra_copies_display  = max(0, copies - 1)

            # Ligne : "Niv. X  X/N copies"  +  bouton [Niveau sup] a droite
            cp_s = f_ti.render(f"Niv. {h['level']}  {extra_copies_display}/{copies_needed_display} copies", True, (100,85,60))
            screen.blit(cp_s, (ix_end, bar_y2))

            if h["unlocked"]:
                copies_needed = max(1, math.ceil(2 * (1.5 ** (h["level"] - 1))))
                extra_copies  = max(0, copies - 1)
                can_levelup   = extra_copies >= copies_needed
                lv_col  = (120,220,120) if can_levelup else (60,55,45)
                lv_bg   = (20,40,20)   if can_levelup else (22,20,16)
                lv_bc   = (80,180,80)  if can_levelup else (40,38,30)
                lv_t    = f_ti.render(f"Niv. sup ({extra_copies}/{copies_needed})", True, lv_col)
                lv_rect = pygame.Rect(br_end_x := row_rect.right - lv_t.get_width() - 12,
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
            pygame.draw.rect(screen, (40,35,25), br, border_radius=3)
            fw = int(br.width * min(1.0, extra_copies_display / copies_needed_display))
            if fw > 0:
                pygame.draw.rect(screen, rc,
                                 pygame.Rect(br.x, br.y, fw, br.height), border_radius=3)
            px += 68

            pygame.draw.line(screen, (40,35,25), (pop.x+8, px), (pop.right-8, px), 1)
            px += 8

            # Passif
            pa_lbl = f_ti.render("COMPETENCE PASSIVE", True, (80,70,50))
            screen.blit(pa_lbl, (pop.x+10, px))
            px += pa_lbl.get_height() + 4

            pa_nm = f_sm.render(h["passive_name"], True, rc)
            screen.blit(pa_nm, (pop.x+10, px))
            px += pa_nm.get_height() + 4

            # Description sur plusieurs lignes
            words  = h["passive_desc"].replace("\n"," ").split()
            line   = ""
            max_w  = pop_w - 20
            for word in words:
                test = line + (" " if line else "") + word
                ts   = f_ti.render(test, True, (140,120,85))
                if ts.get_width() > max_w and line:
                    ls2 = f_ti.render(line, True, (140,120,85))
                    screen.blit(ls2, (pop.x+10, px))
                    px  += ls2.get_height() + 1
                    line = word
                else:
                    line = test
            if line:
                ls2 = f_ti.render(line, True, (140,120,85))
                screen.blit(ls2, (pop.x+10, px))
                px += ls2.get_height() + 4

            rarity = h["rarity"]
            bonus  = {"Commun":"10%","Rare":"20%","Legendaire":"30%"}.get(rarity,"10%")
            bns = f_ti.render(f"Bonus par niveau : +{bonus} ATK/HP", True, (80,70,50))
            screen.blit(bns, (pop.x+10, px))
            px += bns.get_height() + 6

            if not h["unlocked"]:
                lock_msg = f_ti.render("Non obtenu - disponible via le Gacha (gemmes)", True, (180,80,80))
                screen.blit(lock_msg, (pop.centerx - lock_msg.get_width()//2, px))
                px += lock_msg.get_height() + 6

            # Boutons
            btn_w3  = (pop_w - 24) // 2
            sel_r   = pygame.Rect(pop.x+8, px, btn_w3, 28)
            fer_r   = pygame.Rect(sel_r.right+8, px, btn_w3, 28)

            if h["unlocked"]:
                sel_hov = sel_r.collidepoint(mx,my)
                pygame.draw.rect(screen,
                                 (220,170,30) if sel_hov else (160,120,20),
                                 sel_r, border_radius=6)
                sel_t = f_sm.render("Selectionner", True, (20,14,4))
            else:
                pygame.draw.rect(screen, (35,30,20), sel_r, border_radius=6)
                pygame.draw.rect(screen, (50,40,30), sel_r, 1, border_radius=6)
                sel_t = f_sm.render("Non obtenu", True, (80,65,45))
            screen.blit(sel_t, (sel_r.centerx-sel_t.get_width()//2,
                                sel_r.centery-sel_t.get_height()//2))

            fer_hov = fer_r.collidepoint(mx,my)
            pygame.draw.rect(screen, (30,25,18) if fer_hov else (25,20,15),
                             fer_r, border_radius=6)
            pygame.draw.rect(screen, (50,45,35), fer_r, 1, border_radius=6)
            fer_t = f_sm.render("Fermer", True, (120,105,75))
            screen.blit(fer_t, (fer_r.centerx-fer_t.get_width()//2,
                                fer_r.centery-fer_t.get_height()//2))

            if clicked and sel_r.collidepoint(mx,my) and h["unlocked"]:
                hm.select_hero(self.save, h["id"])
                sd.save(self.save)
                self._hero_popup  = False
                self._hero_detail = None
            if clicked and fer_r.collidepoint(mx,my):
                self._hero_detail = None


def _rarity_color(rarity):
    return {"Legendaire":(220,160,30),"Rare":(80,140,220)}.get(rarity,(160,155,145))