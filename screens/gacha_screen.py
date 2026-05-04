"""
screens/gacha_screen.py
------------------------
Écran Gacha complet — toutes les fonctionnalités de menu_screen.py :
  - Image du coffre (boite_a_objet.png / contrat.png)
  - Badge Lv + barre progression niveau coffre
  - Pitié : tirages restants avant garantie Épique/Légendaire
  - Boutons x1 / x5 avec icônes pièces/gemmes et check ressources
  - Overlay plein écran résultat coffre pièces (fondu entrant/sortant)
  - Résultat coffre tours avec jauge doublons + bouton upgrade
  - Popup taux de rareté par niveau (bouton %)
  - Collection de tours en bas (scrollable)
"""

import os
import pygame
import ui.theme as theme
import core.save_data as sd
from core.config import CHEST_COSTS

_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")
_CACHE: dict = {}

RARITY_COL = {
    "Commun":    (160, 160, 165),
    "Rare":      (60,  130, 255),
    "Épique":    (155,  60, 255),
    "Légendaire":(240, 175,  20),
    "Mythique":  (255,  60, 220),
}

G_GOLD = (220, 170, 40)
G_GEM  = (140,  80, 240)


def _load(filename, size):
    key = (filename, size)
    if key in _CACHE:
        return _CACHE[key]
    path = os.path.join(_ASSETS_DIR, filename)
    surf = None
    if os.path.isfile(path):
        try:
            img  = pygame.image.load(path).convert_alpha()
            surf = pygame.transform.smoothscale(img, (size, size))
        except Exception:
            pass
    _CACHE[key] = surf
    return surf


def _icon(name, size=18):
    """Icône pièce ou gemme (sprite ou fallback vectoriel)."""
    if name == "coin":
        img = _load("pieces.png", size)
        if img:
            return img
    elif name == "gem":
        img = _load("gemmes.png", size)
        if img:
            return img
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    if name == "coin":
        pygame.draw.circle(surf, G_GOLD, (cx, cy), size // 2 - 1)
    else:
        pts = [(cx, 1), (size-2, cy//2), (cx, size-2), (2, cy//2)]
        pygame.draw.polygon(surf, G_GEM, pts)
    return surf


def _rr(screen, col, rect, radius=10, bw=0, bc=None):
    """Draw rounded rect."""
    pygame.draw.rect(screen, col, rect, border_radius=radius)
    if bw and bc:
        pygame.draw.rect(screen, bc, rect, bw, border_radius=radius)



EQUIPMENT_IMAGE_FILES = {
    "cape":   "cape.png",
    "veste":  "veste.png",
    "bottes": "bottes.png",
    "arme":   "lames.png",
    }

def _eq_img_name(item):
    """Retourne le nom du fichier image pour un item d'équipement."""
    return item.get("image") or EQUIPMENT_IMAGE_FILES.get(item.get("slot", ""), "")

class GachaScreen:
    def __init__(self, save):
        self.save = save
        # État coffre pièces
        self.chest_overlay_items = []   # liste d'items à afficher
        self.chest_overlay_timer = 0
        self.gacha_msg           = ""
        self.gacha_msg_timer     = 0
        self.last_item_obtained  = None
        self.gacha_info_popup    = None   # None ou "wood"
        # État coffre tours
        self.tower_results       = []
        self.tower_anim          = 0
        self.tower_scroll        = 0
        self.show_rates          = False
        self.overlay_open_frames = 0   # frames écoulées depuis ouverture overlay

    def draw(self, screen, area, mx, my, clicked, scroll_dy=0):
        save  = self.save
        w, h  = screen.get_size()
        f_sec = theme.font(theme.SZ_SECTION)
        f_lbl = theme.font(theme.SZ_LABEL, body=True)
        f_sm  = theme.font(theme.SZ_SMALL, body=True)
        f_ti  = theme.font(theme.SZ_TINY,  body=True)

        pad    = 14
        x      = area.x + pad
        y      = area.y + pad
        aw     = area.width - pad * 2
        full_w = aw
        col_w  = (full_w - pad) // 2

        # Titre
        theme.render_text(screen, "Gacha — Coffres", f_sec, theme.GOLD_LIGHT, x, y)
        theme.draw_gold_rule(screen, x, y + f_sec.get_height() + 2, aw)
        y += f_sec.get_height() + 10

        content_y = y

        # ────────────────────────────────────────────
        # COFFRE PIÈCES (gauche)
        # ────────────────────────────────────────────
        coin_card = pygame.Rect(x, content_y, col_w, 310)
        _rr(screen, theme.DARK_2, coin_card, radius=14, bw=2, bc=theme.GOLD)

        chest_level_coin = sd.get_coin_chest_level(save)
        coin_pulls_in, coin_pulls_needed, _ = sd.get_coin_chest_progress(save)

        # Badge Lv
        lv_badge = pygame.Rect(coin_card.x + 10, coin_card.y + 10, 46, 24)
        _rr(screen, G_GOLD, lv_badge, radius=6)
        lv_txt = f_ti.render(f"Lv {chest_level_coin}", True, (30, 20, 0))
        screen.blit(lv_txt, (lv_badge.centerx - lv_txt.get_width()//2,
                              lv_badge.centery - lv_txt.get_height()//2))

        # Titre
        ct = theme.font(theme.SZ_LABEL).render("Boîte à objets", True, theme.GOLD_LIGHT)
        screen.blit(ct, (coin_card.x + 62, coin_card.y + 12))

        # Barre progression niveau
        prog_r = pygame.Rect(coin_card.x + 10, coin_card.y + 44, col_w - 20, 14)
        _rr(screen, theme.DARK_3, prog_r, radius=7)
        if chest_level_coin < 10:
            ratio = min(1.0, coin_pulls_in / max(1, coin_pulls_needed))
            prog_lbl_txt = f"{coin_pulls_in}/{coin_pulls_needed}"
        else:
            ratio = 1.0
            prog_lbl_txt = "MAX"
        fw = int(prog_r.w * ratio)
        if fw > 0:
            _rr(screen, G_GOLD, pygame.Rect(prog_r.x, prog_r.y, fw, 14), radius=7)
        pl = f_ti.render(prog_lbl_txt, True, theme.CREAM)
        screen.blit(pl, (prog_r.centerx - pl.get_width()//2, prog_r.centery - pl.get_height()//2))

        # Image coffre pièces
        cimg_r = pygame.Rect(coin_card.x + col_w//2 - 60, coin_card.y + 68, 120, 100)
        cimg = _load("boite_a_objet.png", 120) or _load("coffre_pieces.png", 120) or _load("coffre.png", 120)
        if cimg:
            screen.blit(cimg, cimg_r.topleft)
        else:
            _rr(screen, (80, 60, 20), cimg_r, radius=12, bw=2, bc=G_GOLD)
            ph = f_sm.render("Coffre", True, G_GOLD)
            screen.blit(ph, (cimg_r.centerx - ph.get_width()//2, cimg_r.centery - ph.get_height()//2))

        # Pitié
        epic_thr, legend_thr = sd.COIN_CHEST_PITY.get(chest_level_coin, (30, 100))
        rem_e = max(0, epic_thr  - save.get("coin_chest_pity_epic", 0))
        rem_l = max(0, legend_thr - save.get("coin_chest_pity_legend", 0))

        pe = f_ti.render(f"{rem_e} tirages avant garantie ", True, (220, 80, 80))
        screen.blit(pe, (coin_card.x + 10, coin_card.y + 178))
        ec = f_ti.render("Épique", True, RARITY_COL["Épique"])
        screen.blit(ec, (coin_card.x + 10 + pe.get_width(), coin_card.y + 178))

        pl2 = f_ti.render(f"{rem_l} tirages avant garantie ", True, (220, 80, 80))
        screen.blit(pl2, (coin_card.x + 10, coin_card.y + 196))
        lc = f_ti.render("Légendaire", True, RARITY_COL["Légendaire"])
        screen.blit(lc, (coin_card.x + 10 + pl2.get_width(), coin_card.y + 196))

        # Boutons x1 / x5
        cost_wood = CHEST_COSTS.get("wood", 30)
        coins_now = save.get("coins", 0)
        btn1_c = pygame.Rect(coin_card.x + 10, coin_card.y + 230, (col_w - 30)//2, 52)
        btn5_c = pygame.Rect(btn1_c.right + 10,  coin_card.y + 230, (col_w - 30)//2, 52)

        for btn, cnt, can, cost in [
            (btn1_c, 1, coins_now >= cost_wood,     cost_wood),
            (btn5_c, 5, coins_now >= cost_wood * 5, cost_wood * 5),
        ]:
            hov = btn.collidepoint(mx, my)
            _rr(screen, (55,50,20) if (hov and can) else (38,34,14), btn,
                radius=10, bw=2, bc=G_GOLD if can else (60,60,80))
            lbl = f_sm.render(f"{cnt} Achat{'s' if cnt>1 else ''}", True, theme.CREAM)
            screen.blit(lbl, (btn.centerx - lbl.get_width()//2, btn.y + 6))
            ico = _icon("coin", 16)
            clbl = f_ti.render(str(cost), True, G_GOLD if can else (200, 80, 80))
            cw2 = 20 + clbl.get_width()
            cx2 = btn.centerx - cw2//2
            screen.blit(ico,  (cx2, btn.y + 30))
            screen.blit(clbl, (cx2 + 20, btn.y + 30))
            if clicked and hov and can:
                obtained = []
                for _ in range(cnt):
                    ok, res = sd.open_chest(save, "wood")
                    if ok:
                        obtained.append(res)
                        self.last_item_obtained = res
                    else:
                        self.gacha_msg       = str(res)
                        self.gacha_msg_timer = 120
                        break
                if obtained:
                    self.chest_overlay_items = obtained
                    self.chest_overlay_timer = 600

        # Bouton %
        pct_btn_c = pygame.Rect(coin_card.right - 36, coin_card.y + 10, 28, 28)
        hov_pct_c = pct_btn_c.collidepoint(mx, my)
        _rr(screen, (40,30,12) if hov_pct_c else theme.DARK_3, pct_btn_c, radius=6, bw=1, bc=(60,70,100))
        pc = f_ti.render("%", True, theme.CREAM)
        screen.blit(pc, (pct_btn_c.centerx - pc.get_width()//2, pct_btn_c.centery - pc.get_height()//2))
        if clicked and hov_pct_c:
            self.gacha_info_popup = None if self.gacha_info_popup == "wood" else "wood"

        # ────────────────────────────────────────────
        # COFFRE TOURS (droite)
        # ────────────────────────────────────────────
        gem_card = pygame.Rect(x + col_w + pad, content_y, col_w, 310)
        _rr(screen, theme.DARK_2, gem_card, radius=14, bw=2, bc=(120, 80, 200))

        tower_lv = sd._get_tower_chest_level(save)
        pulls_in, pulls_needed, _ = sd._get_tower_chest_progress(save)
        cost_gem = sd.TOWER_CHEST_COSTS.get(tower_lv, 5)
        pity_e_t, pity_l_t = sd.TOWER_CHEST_PITY.get(tower_lv, (22, 100))

        # Badge Lv
        lv_bg = pygame.Rect(gem_card.x + 10, gem_card.y + 10, 38, 24)
        _rr(screen, G_GEM, lv_bg, radius=6)
        lv_gt = f_ti.render(f"Lv {tower_lv}", True, (240, 220, 255))
        screen.blit(lv_gt, (lv_bg.centerx - lv_gt.get_width()//2, lv_bg.centery - lv_gt.get_height()//2))

        gt = theme.font(theme.SZ_LABEL).render("Contrat Héros / Tour", True, theme.GOLD_LIGHT)
        screen.blit(gt, (gem_card.x + 54, gem_card.y + 12))

        # Barre progression
        prog_g = pygame.Rect(gem_card.x + 10, gem_card.y + 44, col_w - 20, 14)
        _rr(screen, theme.DARK_3, prog_g, radius=7)
        ratio_g = min(1.0, pulls_in / max(1, pulls_needed)) if tower_lv < 10 else 1.0
        fw_g = int(prog_g.w * ratio_g)
        if fw_g > 0:
            _rr(screen, G_GEM, pygame.Rect(prog_g.x, prog_g.y, fw_g, 14), radius=7)
        pg_lbl = f_ti.render(f"{pulls_in}/{pulls_needed}" if tower_lv < 10 else "MAX", True, theme.CREAM)
        screen.blit(pg_lbl, (prog_g.centerx - pg_lbl.get_width()//2, prog_g.centery - pg_lbl.get_height()//2))

        # Image coffre tours
        gimg_r = pygame.Rect(gem_card.x + col_w//2 - 50, gem_card.y + 68, 100, 100)
        gimg = _load("contrat.png", 100) or _load("coffre_tours.png", 100) or _load("coffre_gemmes.png", 100)
        if gimg:
            screen.blit(gimg, gimg_r.topleft)
        else:
            _rr(screen, (50, 20, 80), gimg_r, radius=12, bw=2, bc=G_GEM)
            gph = f_sm.render("Contrat", True, G_GEM)
            screen.blit(gph, (gimg_r.centerx - gph.get_width()//2, gimg_r.centery - gph.get_height()//2))

        # Pitié tours
        rem_e_t = max(0, pity_e_t - save.get("tower_chest_pity_epic", 0))
        rem_l_t = max(0, pity_l_t - save.get("tower_chest_pity_legend", 0))

        pe_t = f_ti.render(f"{rem_e_t} tirages avant tour garantie ", True, (220, 80, 80))
        screen.blit(pe_t, (gem_card.x + 10, gem_card.y + 178))
        ec_t = f_ti.render("Épique", True, RARITY_COL["Épique"])
        screen.blit(ec_t, (gem_card.x + 10 + pe_t.get_width(), gem_card.y + 178))

        pl_t = f_ti.render(f"{rem_l_t} tirages avant tour garantie ", True, (220, 80, 80))
        screen.blit(pl_t, (gem_card.x + 10, gem_card.y + 196))
        lc_t = f_ti.render("Légendaire", True, RARITY_COL["Légendaire"])
        screen.blit(lc_t, (gem_card.x + 10 + pl_t.get_width(), gem_card.y + 196))

        # Boutons x1 / x5
        gems_now = save.get("gems", 0)
        btn1_g = pygame.Rect(gem_card.x + 10, gem_card.y + 230, (col_w - 30)//2, 52)
        btn5_g = pygame.Rect(btn1_g.right + 10, gem_card.y + 230, (col_w - 30)//2, 52)

        for btn, cnt, can, cost in [
            (btn1_g, 1, gems_now >= cost_gem,     cost_gem),
            (btn5_g, 5, gems_now >= cost_gem * 5, cost_gem * 5),
        ]:
            hov = btn.collidepoint(mx, my)
            _rr(screen, (45,20,70) if (hov and can) else (28,14,48), btn,
                radius=10, bw=2, bc=G_GEM if can else (60,60,80))
            lbl = f_sm.render(f"{cnt} Achat{'s' if cnt>1 else ''}", True, theme.CREAM)
            screen.blit(lbl, (btn.centerx - lbl.get_width()//2, btn.y + 6))
            ico = _icon("gem", 16)
            glbl = f_ti.render(str(cost), True, (200,130,255) if can else (200,80,80))
            gw2 = 20 + glbl.get_width()
            gx2 = btn.centerx - gw2//2
            screen.blit(ico,  (gx2, btn.y + 30))
            screen.blit(glbl, (gx2 + 20, btn.y + 30))
            if clicked and hov and can:
                ok, res = sd.open_tower_chest(save, cnt)
                if ok:
                    self.tower_results = res
                    self.tower_anim    = 300
                else:
                    self.gacha_msg       = str(res)
                    self.gacha_msg_timer = 120

        # Bouton % tours
        pct_btn_g = pygame.Rect(gem_card.right - 36, gem_card.y + 10, 28, 28)
        hov_pct_g = pct_btn_g.collidepoint(mx, my)
        _rr(screen, (35,20,50) if hov_pct_g else (25,14,40), pct_btn_g, radius=6, bw=1, bc=(60,70,100))
        pg2 = f_ti.render("%", True, theme.CREAM)
        screen.blit(pg2, (pct_btn_g.centerx - pg2.get_width()//2, pct_btn_g.centery - pg2.get_height()//2))
        if clicked and hov_pct_g:
            self.show_rates = not self.show_rates

        # ────────────────────────────────────────────
        # RÉSULTAT TOURS
        # ────────────────────────────────────────────
        if self.tower_anim > 0:
            self.tower_anim -= 1

        # ────────────────────────────────────────────
        # MESSAGE / ITEM CARD coffre pièces
        # ────────────────────────────────────────────
        if self.gacha_msg_timer > 0:
            self.gacha_msg_timer -= 1
            cx3 = x + full_w//2
            col3 = tuple(self.last_item_obtained["color"]) if self.last_item_obtained else (200,80,80)
            ms = f_sm.render(self.gacha_msg, True, col3)
            screen.blit(ms, (cx3 - ms.get_width()//2, content_y + 328))

        # ────────────────────────────────────────────
        # COLLECTION TOURS (scrollable)
        # ────────────────────────────────────────────
        coll_y = content_y + (438 if self.gacha_msg_timer > 0 else 326)
        coll_h = area.bottom - coll_y - 6
        if coll_h > 60:
            coll_panel = pygame.Rect(x, coll_y, full_w, coll_h)
            _rr(screen, theme.DARK_2, coll_panel, radius=12, bw=1, bc=(60,70,100))
            ct2 = f_sm.render("Ma Collection de Tours", True, theme.CREAM)
            screen.blit(ct2, (coll_panel.x+14, coll_panel.y+10))

            towers_unlocked = save.get("towers_unlocked", {})
            towers_level    = save.get("towers_level", {})
            towers_copies   = save.get("towers_copies", {})

            cell_size = 80
            cell_gap  = 8
            cells_per_row = max(1, (full_w - 20) // (cell_size + cell_gap))
            all_ids = list(sd.TOWER_POOL.keys())

            da_x = coll_panel.x + 6
            da_y = coll_panel.y + 36

            for ti, tid in enumerate(all_ids):
                row_i = ti // cells_per_row
                col_i = ti % cells_per_row
                cx4   = da_x + col_i * (cell_size + cell_gap)
                cy4   = da_y + row_i * (cell_size + cell_gap)
                if cy4 > coll_panel.bottom:
                    continue
                cell_r = pygame.Rect(cx4, cy4, cell_size, cell_size)
                tinfo  = sd.TOWER_POOL[tid]
                is_unl = towers_unlocked.get(tid, False)
                rar_c  = RARITY_COL.get(tinfo["rarity"], (150,150,150)) if is_unl else (40,40,50)
                bg_col = theme.DARK_3 if is_unl else theme.DARK
                _rr(screen, bg_col, cell_r, radius=8, bw=2, bc=rar_c)

                if is_unl:
                    tn = f_ti.render(tinfo["label"][:9], True, rar_c)
                    screen.blit(tn, (cell_r.centerx - tn.get_width()//2, cell_r.y+5))
                    lv_c = towers_level.get(tid, 1)
                    ll   = f_ti.render(f"Niv.{lv_c}", True, theme.CREAM)
                    screen.blit(ll, (cell_r.centerx - ll.get_width()//2, cell_r.y+22))
                    pygame.draw.circle(screen, rar_c, (cell_r.x+6, cell_r.y+6), 4)

                    copies_now = towers_copies.get(tid, 0)
                    if lv_c <= len(sd.TOWER_UPGRADE_COST):
                        needed_up = sd.TOWER_UPGRADE_COST[lv_c-1]
                        can_up    = copies_now >= needed_up
                        gauge = pygame.Rect(cell_r.x+6, cell_r.y+40, cell_r.w-12, 8)
                        _rr(screen, theme.DARK_3, gauge, radius=4)
                        fw4 = max(0, int(gauge.w * min(1.0, copies_now/max(1,needed_up))))
                        fill_c = (100,255,140) if can_up else (130,90,210)
                        if fw4 > 0:
                            _rr(screen, fill_c, pygame.Rect(gauge.x,gauge.y,fw4,8), radius=4)
                        cl2 = f_ti.render(f"{copies_now}/{needed_up}", True, theme.CREAM)
                        screen.blit(cl2, (gauge.centerx - cl2.get_width()//2, gauge.bottom+2))
                        if can_up:
                            up_b = pygame.Rect(cell_r.x+5, cell_r.y+62, cell_r.w-10, 14)
                            hupc = up_b.collidepoint(mx, my)
                            _rr(screen, (60,210,85) if hupc else (40,160,60), up_b, radius=4, bw=1, bc=(100,255,130))
                            ul2 = f_ti.render("▲ Niv. sup.", True, (10,10,10) if hupc else (200,255,200))
                            screen.blit(ul2, (up_b.centerx-ul2.get_width()//2, up_b.centery-ul2.get_height()//2))
                            if clicked and hupc:
                                sd.upgrade_tower(save, tid)
                    else:
                        ml = f_ti.render("✦ MAX", True, G_GOLD)
                        screen.blit(ml, (cell_r.centerx - ml.get_width()//2, cell_r.y+44))
                else:
                    lk = f_sm.render("?", True, (60,60,70))
                    screen.blit(lk, (cell_r.centerx - lk.get_width()//2, cell_r.centery - lk.get_height()//2))
                    rs = f_ti.render(tinfo["rarity"][0], True, RARITY_COL.get(tinfo["rarity"], (100,100,100)))
                    screen.blit(rs, (cell_r.x+4, cell_r.y+4))


        # ────────────────────────────────────────────
        # POPUP TAUX COFFRE TOURS
        # ────────────────────────────────────────────
        if self.show_rates:
            RARS = ["Commun","Rare","Épique","Légendaire"]
            BAR_W, ROW_H, PAD = 90, 20, 10
            COL_LV, COL_GAP, COL_RAR = 28, 6, 52
            pr_w = PAD*2 + COL_LV + COL_GAP + len(RARS)*(COL_RAR+BAR_W+COL_GAP)
            pr_w = min(pr_w, aw-20)
            pr_h = PAD*2 + 28 + 10*(ROW_H+2) + 40
            pr_x = max(x, pct_btn_g.right - pr_w)
            pr_y = max(area.y+4, pct_btn_g.top - pr_h - 6)
            pr   = pygame.Rect(pr_x, pr_y, pr_w, pr_h)
            _rr(screen, theme.DARK_2, pr, radius=12, bw=2, bc=G_GEM)

            tl = f_sm.render("Taux par niveau de coffre", True, (210,170,255))
            screen.blit(tl, (pr.centerx - tl.get_width()//2, pr.y+PAD))

            hdr_y = pr.y + PAD + 28 - 4
            col_starts = []
            cx5 = pr.x + PAD + COL_LV + COL_GAP
            for rar in RARS:
                rh = f_ti.render(rar[:4], True, RARITY_COL[rar])
                screen.blit(rh, (cx5, hdr_y))
                col_starts.append(cx5)
                cx5 += COL_RAR + BAR_W + COL_GAP
            sep_y = hdr_y + 18
            pygame.draw.line(screen, (50,40,80), (pr.x+6, sep_y), (pr.x+pr.w-6, sep_y))

            for lv in range(1, 11):
                row_y = sep_y + 2 + (lv-1)*(ROW_H+2)
                if lv == tower_lv:
                    _rr(screen, (40,28,70), pygame.Rect(pr.x+4, row_y, pr.w-8, ROW_H), radius=4, bw=1, bc=(130,80,210))
                lvc = G_GOLD if lv == tower_lv else theme.GOLD_DIM
                lvt = f_ti.render(f"{'▶' if lv==tower_lv else ' '}{lv}", True, lvc)
                screen.blit(lvt, (pr.x+PAD, row_y+2))
                weights = sd.TOWER_CHEST_WEIGHTS_BY_LEVEL[lv]
                total_w = sum(weights.values()) or 1
                for ri, rar in enumerate(RARS):
                    pct = weights.get(rar, 0) / total_w * 100
                    cx6 = col_starts[ri]
                    rc6 = RARITY_COL[rar]
                    bar = pygame.Rect(cx6, row_y+5, BAR_W, 8)
                    _rr(screen, theme.DARK_3, bar, radius=4)
                    fp = int(BAR_W * pct/100)
                    if fp > 0:
                        _rr(screen, rc6, pygame.Rect(bar.x,bar.y,fp,8), radius=4)
                    pts = f_ti.render(f"{pct:.0f}%" if pct > 0 else "—", True, rc6 if pct>0 else (50,50,60))
                    screen.blit(pts, (cx6+BAR_W+2, row_y+2))

            pity_y = sep_y + 2 + 10*(ROW_H+2) + 4
            pygame.draw.line(screen, (50,40,80), (pr.x+6, pity_y), (pr.x+pr.w-6, pity_y))
            screen.blit(f_ti.render(f"Pitié Épique Lv{tower_lv} : {pity_e_t} pulls garantis", True, RARITY_COL["Épique"]), (pr.x+PAD, pity_y+4))
            screen.blit(f_ti.render(f"Pitié Légend. Lv{tower_lv} : {pity_l_t} pulls garantis", True, RARITY_COL["Légendaire"]), (pr.x+PAD, pity_y+20))

            if clicked and not pr.collidepoint(mx, my):
                self.show_rates = False

        # ────────────────────────────────────────────
        # POPUP TAUX COFFRE PIÈCES
        # ────────────────────────────────────────────
        if self.gacha_info_popup == "wood":
            RARS_C = ["Commun","Rare","Épique","Légendaire","Mythique"]
            BAR_WC, ROW_HC, PAD_C = 70, 20, 10
            COL_LVC, COL_GAPC, COL_RARC = 28, 4, 44
            pi_w = PAD_C*2 + COL_LVC + COL_GAPC + len(RARS_C)*(COL_RARC+BAR_WC+COL_GAPC)
            pi_w = min(pi_w, aw-20)
            pi_h = PAD_C*2 + 28 + 10*(ROW_HC+2)
            pi_x = max(x, pct_btn_c.right - pi_w)
            pi_y = max(area.y+4, pct_btn_c.top - pi_h - 6)
            pi   = pygame.Rect(pi_x, pi_y, pi_w, pi_h)
            _rr(screen, (20,17,8), pi, radius=12, bw=2, bc=G_GOLD)

            tl2 = f_sm.render("Taux par niveau de coffre", True, G_GOLD)
            screen.blit(tl2, (pi.centerx - tl2.get_width()//2, pi.y+PAD_C))

            hdr_yc = pi.y + PAD_C + 28 - 4
            col_sc = []
            cx7 = pi.x + PAD_C + COL_LVC + COL_GAPC
            for rar in RARS_C:
                rh2 = f_ti.render(rar[:4], True, RARITY_COL.get(rar, theme.CREAM_DIM))
                screen.blit(rh2, (cx7, hdr_yc))
                col_sc.append(cx7)
                cx7 += COL_RARC + BAR_WC + COL_GAPC
            sep_yc = hdr_yc + 18
            pygame.draw.line(screen, (80,65,20), (pi.x+6, sep_yc), (pi.x+pi.w-6, sep_yc))

            for lv_c in range(1, 11):
                row_yc = sep_yc + 2 + (lv_c-1)*(ROW_HC+2)
                if lv_c == chest_level_coin:
                    _rr(screen, (55,42,10), pygame.Rect(pi.x+4, row_yc, pi.w-8, ROW_HC), radius=4, bw=1, bc=G_GOLD)
                lvc2 = G_GOLD if lv_c == chest_level_coin else theme.GOLD_DIM
                lvt2 = f_ti.render(f"{'▶' if lv_c==chest_level_coin else ' '}{lv_c}", True, lvc2)
                screen.blit(lvt2, (pi.x+PAD_C, row_yc+2))
                weights_c = sd.COIN_CHEST_WEIGHTS_BY_LEVEL[lv_c]
                total_c   = sum(weights_c.values()) or 1
                for ri_c, rar in enumerate(RARS_C):
                    pct_c = weights_c.get(rar, 0) / total_c * 100
                    cx8   = col_sc[ri_c]
                    rc8   = RARITY_COL.get(rar, theme.CREAM_DIM)
                    bar_c = pygame.Rect(cx8, row_yc+5, BAR_WC, 8)
                    _rr(screen, theme.DARK_3, bar_c, radius=4)
                    fpc = int(BAR_WC * pct_c/100)
                    if fpc > 0:
                        _rr(screen, rc8, pygame.Rect(bar_c.x,bar_c.y,fpc,8), radius=4)
                    pts2 = f_ti.render(f"{pct_c:.0f}%" if pct_c>0 else "—", True, rc8 if pct_c>0 else (50,50,60))
                    screen.blit(pts2, (cx8+BAR_WC+2, row_yc+2))

            if clicked and not pi.collidepoint(mx, my) and not pct_btn_c.collidepoint(mx, my):
                self.gacha_info_popup = None

        # ────────────────────────────────────────────
        # OVERLAY RÉSULTATS (coffre pièces + tours)
        # Fond gris sur tout l'écran
        # 1 item  → 1 grande carte centrée
        # 5 items → 5 cartes côte à côte
        # ────────────────────────────────────────────
        overlay_items = []  # liste de dicts {name, rarity, img_name, rcol}

        # Coffre pièces
        if self.chest_overlay_timer > 0:
            self.chest_overlay_timer -= 1
            for it in self.chest_overlay_items:
                rar = it.get("rarity", "Commun")
                overlay_items.append({
                    "name":     it.get("name", "Objet"),
                    "rarity":   rar,
                    "img_name": it.get("image") or _eq_img_name(it),
                    "rcol":     tuple(RARITY_COL.get(rar, (160,160,160))),
                })

        # Coffre tours (on utilise tower_results quand l'anim est active)
        if self.tower_anim > 0 and self.tower_results and not overlay_items:
            for res in self.tower_results:
                rar = res.get("rarity", "Commun")
                is_hero = res.get("type") == "hero"
                if is_hero:
                    img_name = res.get("sprite_portrait") or res.get("sprite_select") or ""
                else:
                    img_name = f"{res.get('tower_id', '')}.png"
                overlay_items.append({
                    "name":     res.get("label", "Tour"),
                    "rarity":   rar,
                    "img_name": img_name,
                    "rcol":     tuple(RARITY_COL.get(rar, (160,160,160))),
                })

        if overlay_items:
            self.overlay_open_frames += 1
            # Fond gris semi-transparent sur tout l'écran
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 200))
            screen.blit(ov, (0, 0))

            n = len(overlay_items)
            card_w = 100 if n > 1 else 180
            card_h = 150 if n > 1 else 220
            img_size = 64 if n > 1 else 110
            gap = 12

            total_w = n * card_w + (n - 1) * gap
            start_x = w // 2 - total_w // 2
            start_y = h // 2 - card_h // 2

            for i, it in enumerate(overlay_items):
                cx_ = start_x + i * (card_w + gap)
                cy_ = start_y
                rar  = it["rarity"]
                rcol = it["rcol"]

                # Fond coloré selon rareté (assombri)
                r, g, b = rcol
                bg_col = (max(0,r//4), max(0,g//4), max(0,b//4))
                card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                card_surf.fill((*bg_col, 230))
                screen.blit(card_surf, (cx_, cy_))
                # Bordure couleur rareté
                pygame.draw.rect(screen, rcol,
                                 pygame.Rect(cx_, cy_, card_w, card_h), 3, border_radius=14)

                # Image équipement ou tour
                img_name = it.get("img_name")
                img = _load(img_name, img_size) if img_name else None
                img_x = cx_ + card_w // 2 - img_size // 2
                img_y = cy_ + 20
                if img:
                    screen.blit(img, (img_x, img_y))
                else:
                    # Placeholder rectangle couleur rareté
                    ph_r = pygame.Rect(img_x, img_y, img_size, img_size)
                    pygame.draw.rect(screen, (r//3, g//3, b//3), ph_r, border_radius=8)
                    pygame.draw.rect(screen, rcol, ph_r, 2, border_radius=8)

                # Rareté
                rar_s = f_ti.render(rar, True, rcol)
                screen.blit(rar_s, (cx_ + card_w//2 - rar_s.get_width()//2,
                                     img_y + img_size + 8))

                # Nom
                name_s = theme.font(theme.SZ_SMALL, body=True).render(
                    it["name"][:16], True, theme.CREAM)
                screen.blit(name_s, (cx_ + card_w//2 - name_s.get_width()//2,
                                      img_y + img_size + 8 + rar_s.get_height() + 4))

            # Bouton rouge fermer en haut à droite
            close_size = 32
            close_btn  = pygame.Rect(start_x + total_w - close_size//2,
                                     start_y - close_size//2,
                                     close_size, close_size)
            hov_close  = close_btn.collidepoint(mx, my)
            pygame.draw.rect(screen, (180,30,30) if hov_close else (140,20,20),
                             close_btn, border_radius=6)
            pygame.draw.rect(screen, (230,60,60), close_btn, 2, border_radius=6)
            x_lbl = theme.font(theme.SZ_LABEL).render("X", True, (255,220,220))
            screen.blit(x_lbl, (close_btn.centerx - x_lbl.get_width()//2,
                                 close_btn.centery - x_lbl.get_height()//2))

            if clicked and hov_close and self.overlay_open_frames > 2:
                self.chest_overlay_timer = 0
                self.chest_overlay_items = []
                self.tower_anim          = 0
                self.overlay_open_frames = 0

        if not overlay_items:
            self.overlay_open_frames = 0
        return None