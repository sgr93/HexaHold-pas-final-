"""
game_infinite.py
----------------
Mode infini : recompenses de vague, collecte de loot et popups associees.
Bouton ultime extrait egalement ici.
"""
import math as _math
import random
import pygame
import core.save_data as sd
from core.config import GRID_WIDTH, GRID_HEIGHT, XP_GROWTH_FACTOR
from modes.game_passives import _get_ultimate_duration, _apply_ultimate_start
import random as _rnd
from core.config import EQUIPMENT_SLOTS, EQUIPMENT_STATS, RARITY_COLORS
import random as _r2
import core.heroes as _hm
import ui.theme as _theme


def _give_infinite_rewards(gs, wave_number, save):
    """
    Accumule les recompenses de vague dans gs["infinite_loot"].
    Tout est donne en une seule fois au moment du game over.
    """
    wn = wave_number

    loot = gs.setdefault("infinite_loot", {
        "coins": 0, "gems": 0, "items": []
    })

    loot["coins"] += 20 + wn * 16

    if wn >= 20 :
        gems = _rnd.randint(100, 200)
    if wn >= 15:
        gems = _rnd.randint(50, 80)
    elif wn >= 10:
        gems = _rnd.randint(25, 40)
    elif wn >= 6:
        gems = _rnd.randint(15, 25)
    elif wn >= 3:
        gems = _rnd.randint(5, 10)
    else:
        gems = 0
    loot["gems"] += gems

    if wn >= 20:
        rarities = ["Legendaire", "Mythique"]
        weights = [55, 45]
    if wn >= 15:
        rarities = ["Epique", "Legendaire", "Mythique"]
        weights = [20, 45, 35]
    elif wn >= 10:
        rarities = ["Rare", "Epique", "Legendaire"]
        weights = [30, 50, 20]
    elif wn >= 6:
        rarities = ["Commun", "Rare", "Epique"]
        weights = [20, 55, 25]
    elif wn >= 3:
        rarities = ["Commun", "Rare"]
        weights = [60, 40]
    else:
        rarities = ["Commun"]
        weights = [100]

    nb_equip = 2 if wn >= 21 else 1
    for _ in range(nb_equip):
        RARITY_MAP = {
            "Commun": "Commun", "Rare": "Rare",
            "Epique": "Epique", "Legendaire": "Legendaire", "Mythique": "Mythique"
        }
        rarity_key = _r2.choices(rarities, weights=weights, k=1)[0]
        rarity_cfg = rarity_key
        for r in ["Commun", "Rare", "Epique", "Legendaire", "Mythique"]:
            if r.lower() == rarity_key.lower():
                rarity_cfg = r
                break
        slot = _r2.choice(EQUIPMENT_SLOTS)
        stat_info = EQUIPMENT_STATS[slot]
        value = None
        for k, v in stat_info["values"].items():
            if k.lower().replace("é", "e").replace("è", "e") == rarity_cfg.lower().replace("é", "e"):
                value = v
                break
        if value is None:
            value = list(stat_info["values"].values())[0]
        NAMES = {"cape": "Cape", "veste": "Veste", "bottes": "Bottes", "arme": "Lames", "tour": "Relique"}
        IMGS = {"cape": "cape.png", "veste": "veste.png", "bottes": "bottes.png",
                "arme": "lames.png", "tour": "tour.png"}
        col = list(RARITY_COLORS.get(rarity_cfg, (180, 180, 180)))
        item = {
            "slot": slot, "rarity": rarity_cfg, "stat": stat_info["stat"],
            "value": value, "label": stat_info["label"],
            "name": NAMES.get(slot, slot), "image": IMGS.get(slot, ""),
            "color": col,
        }
        loot["items"].append(item)


def _collect_infinite_loot(gs, save):
    """
    Credite le loot accumule dans la save et retourne le dict pour affichage.
    Appele une seule fois au moment du game over en mode infini.
    """
    loot = gs.get("infinite_loot", {"coins": 0, "gems": 0, "items": []})
    save["coins"] = save.get("coins", 0) + loot["coins"]
    save["gems"] = save.get("gems", 0) + loot["gems"]
    for item in loot["items"]:
        save.setdefault("inventory_equipment", []).append(item)

    wn = gs.get("wave_number", 1)

    if wn >= 28:
        if wn >= 40:
            hero_chance = 0.40
            pool = ["levi", "mikasa", "armin", "sasha"]
        elif wn >= 35:
            hero_chance = 0.25
            pool = ["armin", "sasha", "levi", "mikasa"]
        else:
            hero_chance = 0.12
            pool = ["armin", "sasha"]
        if random.random() < hero_chance:
            hero_id = random.choice(pool)
            _hm.init_heroes_save(save)
            _hm.add_hero_copy(save, hero_id)
            hdef = _hm.HEROES[hero_id]
            loot.setdefault("hero_drop", []).append({
                "id": hero_id,
                "name": hdef["name"],
                "rarity": hdef["rarity"],
                "color": list(_hm.RARITY_COLORS.get(hdef["rarity"], (180, 180, 180))),
            })

    xp_gain = sum(10 + 3 * w for w in range(1, wn + 1))
    save["xp"] = save.get("xp", 0) + xp_gain
    xp_next = save.get("xp_next", 30)
    while save["xp"] >= xp_next:
        save["xp"] -= xp_next
        save["level"] = save.get("level", 1) + 1
        save["skill_points"] = save.get("skill_points", 0) + 1
        save["pending_skillpoint_anim"] = True
        xp_next = int(xp_next * XP_GROWTH_FACTOR)
    save["xp_next"] = xp_next
    sd.save(save)
    return loot


def _draw_infinite_loot_popup(screen, loot, wave_reached, mx, my, clicked):
    """
    Popup affiche a la mort en mode infini.
    Montre le total pieces/gemmes + tous les equipements droppe, style coffre.
    Retourne True si le joueur clique sur "Continuer".
    """

    W, H = min(520, screen.get_width() - 40), min(560, screen.get_height() - 40)
    rx = (screen.get_width() - W) // 2
    ry = (screen.get_height() - H) // 2
    pop = pygame.Rect(rx, ry, W, H)

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    _theme.draw_panel(screen, pop, color=(18, 12, 30),
                      border_color=(130, 80, 200), radius=_theme.RADIUS_LG, border_w=2)
    _theme.draw_corner_ornaments(screen, pop, size=8, color=(130, 80, 200))

    f_ti = _theme.font(_theme.SZ_SECTION)
    f_lbl = _theme.font(_theme.SZ_LABEL, body=True)
    f_sm = _theme.font(_theme.SZ_SMALL, body=True)
    f_xs = _theme.font(_theme.SZ_TINY, body=True)

    py = pop.y + 14

    t1 = f_ti.render("Partie terminee", True, (180, 100, 255))
    screen.blit(t1, (pop.centerx - t1.get_width()//2, py))
    py += t1.get_height() + 2

    t2 = f_xs.render(f"Vague atteinte : {wave_reached}", True, (120, 70, 180))
    screen.blit(t2, (pop.centerx - t2.get_width()//2, py))
    py += t2.get_height() + 8

    _theme.draw_gold_rule(screen, pop.x + 16, py, W - 32)
    py += 10

    coins = loot.get("coins", 0)
    gems = loot.get("gems", 0)

    row_y = py
    coin_icon = _theme.load_sprite("pieces.png", (22, 22))
    if coin_icon:
        screen.blit(coin_icon, (pop.x + 20, row_y))
    c_s = f_lbl.render(f"+{coins} pieces", True, _theme.GOLD_LIGHT)
    screen.blit(c_s, (pop.x + 48, row_y + (22 - c_s.get_height())//2))

    gem_icon = _theme.load_sprite("gemmes.png", (22, 22))
    gx = pop.x + 20 + W//2 - 20
    if gem_icon:
        screen.blit(gem_icon, (gx, row_y))
    g_s = f_lbl.render(f"+{gems} gemmes", True, (180, 140, 255) if gems > 0 else (100, 100, 100))
    screen.blit(g_s, (gx + 28, row_y + (22 - g_s.get_height())//2))
    py += 30

    _theme.draw_gold_rule(screen, pop.x + 16, py, W - 32)
    py += 10

    items = loot.get("items", [])
    if items:
        lbl_eq = f_xs.render("Equipements obtenus :", True, (100, 70, 140))
        screen.blit(lbl_eq, (pop.x + 16, py))
        py += lbl_eq.get_height() + 6

        CELL = 54
        COLS_P = (W - 32) // (CELL + 6)
        for idx, item in enumerate(items):
            col_i = idx % COLS_P
            row_i = idx // COLS_P
            cx = pop.x + 16 + col_i * (CELL + 6)
            cy_item = py + row_i * (CELL + 6)
            if cy_item + CELL > pop.bottom - 50:
                break
            cell = pygame.Rect(cx, cy_item, CELL, CELL)
            col = tuple(item.get("color", (180, 180, 180)))
            _theme.draw_panel(screen, cell, color=(20, 14, 30),
                              border_color=col, radius=_theme.RADIUS_MD, border_w=2)
            img_name = item.get("image", "")
            img = _theme.load_sprite(img_name, (CELL - 10, CELL - 10)) if img_name else None
            if img:
                screen.blit(img, (cx + 5, cy_item + 5))
            else:
                lbl = f_xs.render(item.get("name", "?")[:5], True, col)
                screen.blit(lbl, (cx + CELL//2 - lbl.get_width()//2,
                                  cy_item + CELL//2 - lbl.get_height()//2))
            rar = f_xs.render(item.get("rarity", "")[:3], True, col)
            screen.blit(rar, (cx + CELL//2 - rar.get_width()//2, cy_item + CELL - 13))

        rows_used = (len(items) + COLS_P - 1) // COLS_P
        py += rows_used * (CELL + 6) + 4
    else:
        no_eq = f_xs.render("Aucun equipement obtenu.", True, (80, 60, 100))
        screen.blit(no_eq, (pop.centerx - no_eq.get_width()//2, py))
        py += no_eq.get_height() + 8

    hero_drops = loot.get("hero_drop", [])
    if hero_drops:
        hd_lbl = f_xs.render("Heros obtenus :", True, (140, 100, 200))
        screen.blit(hd_lbl, (pop.x + 16, py))
        py += hd_lbl.get_height() + 4
        for hd in hero_drops:
            col = tuple(hd.get("color", (180, 180, 180)))
            hd_s = f_sm.render(f"{hd['name']}  [{hd['rarity']}]", True, col)
            screen.blit(hd_s, (pop.x + 16, py))
            py += hd_s.get_height() + 3

    btn_w, btn_h = 160, 36
    btn = pygame.Rect(pop.centerx - btn_w//2, pop.bottom - btn_h - 14, btn_w, btn_h)
    hov = btn.collidepoint(mx, my)
    _theme.draw_panel(screen, btn,
                      color=(40, 20, 70) if hov else (25, 12, 45),
                      border_color=(180, 100, 255) if hov else (100, 60, 160),
                      radius=_theme.RADIUS_MD, border_w=2)
    cont = f_lbl.render("Continuer", True, (220, 180, 255) if hov else (160, 120, 220))
    screen.blit(cont, (btn.centerx - cont.get_width()//2,
                       btn.centery - cont.get_height()//2))

    return clicked and hov


def _draw_ultimate_button(screen, gs, offset_x, offset_y, mx, my, clicked):
    """
    Dessine le bouton de competence ultime en bas a droite de la grille.
    Activable par clic ou touche Q.
    """
    CHAR_COLORS = {"eren": (213, 90, 48), "mikasa": (127, 119, 221), "erwin": (29, 158, 117)}
    CHAR_ICONS = {"eren": "eren_normal.png", "mikasa": "mikasa_normal.png", "erwin": "erwin_normal.png"}

    info = gs["ultimate_info"]
    char = info["char"]
    name = info["name"]
    color = CHAR_COLORS.get(char, (200, 160, 30))
    cooldown = gs.get("ultimate_cooldown", 0)
    cooldown_max = gs.get("ultimate_cooldown_max", 1)
    active = gs.get("ultimate_active", False)
    ult_timer = gs.get("ultimate_timer", 0)
    ready = not active and cooldown <= 0

    BTN = 64
    PAD = 8
    bx = offset_x + GRID_WIDTH - BTN - PAD
    by = offset_y + GRID_HEIGHT - BTN - PAD

    btn_rect = pygame.Rect(bx, by, BTN, BTN)
    tick = pygame.time.get_ticks()

    if active:
        pulse = int(40 + 30 * _math.sin(tick * 0.008))
        _theme.draw_rect_alpha(screen, (*color, 120 + pulse), btn_rect, radius=12)
        pygame.draw.rect(screen, color, btn_rect, 3, border_radius=12)
    elif ready:
        pulse = int(20 + 15 * _math.sin(tick * 0.005))
        _theme.draw_rect_alpha(screen, (*color, 60 + pulse), btn_rect, radius=12)
        pygame.draw.rect(screen, color, btn_rect, 2, border_radius=12)
    else:
        _theme.draw_rect_alpha(screen, (20, 15, 10, 200), btn_rect, radius=12)
        pygame.draw.rect(screen, (70, 60, 45), btn_rect, 2, border_radius=12)

    icon = _theme.load_sprite(CHAR_ICONS.get(char, ""), (BTN - 10, BTN - 10))
    if icon:
        tmp = icon.copy()
        if not ready and not active:
            tmp.set_alpha(80)
        screen.blit(tmp, (bx + 5, by + 5))

    if not ready and not active:
        dark_surf = pygame.Surface((BTN, BTN), pygame.SRCALPHA)
        pygame.draw.rect(dark_surf, (0, 0, 0, 150), dark_surf.get_rect(), border_radius=12)
        screen.blit(dark_surf, (bx, by))
        f_cd = pygame.font.SysFont("arial", 18, bold=True)
        cd_txt = f_cd.render(f"{int(cooldown)}s", True, (220, 200, 160))
        screen.blit(cd_txt, (bx + BTN//2 - cd_txt.get_width()//2,
                             by + BTN//2 - cd_txt.get_height()//2))

    if active:
        f_dur = pygame.font.SysFont("arial", 14, bold=True)
        dur_txt = f_dur.render(f"{ult_timer:.1f}s", True, (255, 255, 200))
        screen.blit(dur_txt, (bx + BTN//2 - dur_txt.get_width()//2, by - 18))

    f_lbl = pygame.font.SysFont("arial", 10)
    lbl = f_lbl.render(f"[Q] {name[:12]}", True, color if ready or active else (80, 70, 55))
    screen.blit(lbl, (bx + BTN//2 - lbl.get_width()//2, by + BTN + 3))

    if clicked and btn_rect.collidepoint(mx, my) and ready:
        gs["ultimate_active"] = True
        gs["ultimate_cooldown"] = gs["ultimate_cooldown_max"]
        gs["ultimate_timer"] = _get_ultimate_duration(char)
        _apply_ultimate_start(gs)
