"""
main.py
-------
Point d'entree : boucle de jeu principale.

"""

import time
import random
import pygame

from config import (
    COLS, ROWS, GRID_SIZE,
    GRID_WIDTH, GRID_HEIGHT, INTERFACE_WIDTH,
    START, END,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    LEVEL_START, XP_START, XP_TO_NEXT_LVL_START, XP_GROWTH_FACTOR,
    WAVE_NUMBER_START, MAX_WAVES, WAVE_DURATION, BOSS_DURATION,
    ENEMY_SPAWN_INTERVAL_BASE, DANGER_WEIGHT,
    WALLS_ENABLED, WALLS_COUNT, WALLS_ZONE_START, WALLS_ZONE_END,
    BACKGROUND_COLOR, PAUSE_KEY,
)
import render
from render import GridCache
from grid import Grid
from entities import Player, Goal, Enemy, Tower, Trap
from ui import (
    main_menu, draw_hud, draw_ghost,
    draw_inventory,
    draw_pause_screen, draw_gameover_screen, draw_start_hint,
    INV_BAR_HEIGHT, ITEM_LABELS,
)
from walls import spawn_random_walls


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def make_can_place(grid, start_cell, item_type=None):
    """
    Retourne une closure can_place(cells) verifiant la legalite d'un placement.
    FIX #3 : creee une seule fois par frame, partagee entre ghost et clic.
    """
    def can_place(cells):
        for x, y in cells:
            if not grid.in_bounds(x, y):
                return False
            if not grid.walkable[x][y]:
                return False

        if item_type == "trap":
            occupied = set()
            for t in grid.towers_ref:
                if hasattr(t, "trap_type"):
                    occupied.update(t.cells)
            return not any((x, y) in occupied for x, y in cells)

        # Test de connectivite temporaire
        blocked = []
        for x, y in cells:
            blocked.append((x, y, grid.walkable[x][y]))
            grid.walkable[x][y] = False
        grid.compute_integration_field()
        valid = grid.integration_field[start_cell[0]][start_cell[1]] != float("inf")
        for x, y, prev in blocked:
            grid.walkable[x][y] = prev
        grid.recompute()
        return valid

    return can_place


def place_tower_on_grid(grid, towers, cells, item_type, grid_cache):
    """
    Place ou ameliore une tour/piege sur la grille.

    Contrairement a l'ancien systeme, cette fonction ne consomme PAS de token —
    le token a deja ete consomme lors de l'ajout a l'inventaire.

    Retourne True si le placement/upgrade a reussi, False sinon.
    FIX #2 : un seul grid.recompute() apres ajout.
    OPTIM-GRID : invalide le GridCache apres tout recompute.
    """
    for t in towers:
        t_type = getattr(t, "tower_type", getattr(t, "trap_type", None))
        match_type = (t_type == item_type) or (
            item_type == "trap" and t_type == "spikes"
        )
        if match_type and any(cell in t.cells for cell in cells):
            if t.level < 3:
                t.level += 1
                t.set_stats()
                if item_type != "trap":
                    grid.recompute()
                    grid_cache.invalidate()
                return True   # upgrade reussi
            return False      # niveau max, echec

    # Nouveau placement
    if item_type == "trap":
        towers.append(Trap(cells, trap_type="spikes"))
        grid.recompute()
        grid_cache.invalidate()
    else:
        for x, y in cells:
            grid.walkable[x][y] = False
        towers.append(Tower(cells, item_type))
        grid.recompute()
        grid_cache.invalidate()

    return True


def cells_for_item(item_type, gx, gy):
    """Retourne la liste de cases occupees pour un item a la position (gx, gy)."""
    if item_type == "small":
        return [(gx, gy), (gx+1, gy), (gx, gy+1), (gx+1, gy+1)]
    elif item_type == "big":
        return [
            (gx, gy), (gx+1, gy), (gx+2, gy),
            (gx, gy+1), (gx+1, gy+1), (gx+2, gy+1),
        ]
    elif item_type == "trap":
        return [(gx+i, gy+j) for i in range(2) for j in range(4)]
    return []


def start_new_wave(state):
    """Incremente la vague et reinitialise les compteurs associes."""
    state["wave_number"]              += 1
    state["last_wave_time"]            = time.time()
    state["last_enemy_spawn"]          = time.time()
    state["mobs_killed_this_wave"]     = 0
    state["enemies_spawned_this_wave"] = 0
    state["max_enemies_this_wave"]     = 5 + state["wave_number"] * 2
    state["boss_active"]               = False
    state["wave_timer"]                = WAVE_DURATION
    state["boss_timer"]                = BOSS_DURATION


def build_initial_state():
    """
    Cree et retourne l'etat initial complet du jeu.
    Appele au demarrage et a chaque "Rejouer".
    """
    towers      = []
    projectiles = []
    enemies     = []

    grid = Grid(towers_ref=towers, danger_weight=DANGER_WEIGHT)
    grid.recompute()

    goal   = Goal(*END)
    player = Player(
        START[0] * GRID_SIZE + GRID_SIZE // 2,
        START[1] * GRID_SIZE + GRID_SIZE // 2,
    )

    if WALLS_ENABLED:
        spawn_random_walls(grid, WALLS_COUNT, WALLS_ZONE_START, WALLS_ZONE_END)
        grid.recompute()

    return {
        # Progression
        "level":                    LEVEL_START,
        "xp":                       XP_START,
        "xp_to_next_level":         XP_TO_NEXT_LVL_START,

        # Etat de jeu
        "game_started":             False,
        "paused":                   False,
        "game_over":                False,
        "game_win":                 False,

        # Tokens de construction (utilises pour acheter dans le shop)
        "build_tokens":             1,
        "player_buff_tokens":       0,

        # --- INVENTAIRE ---
        # Dict { item_type: quantite_en_stock }
        # Initialement vide. Les items sont ajoutes via le shop.
        # Un clic sur un item du shop consomme 1 token et ajoute 1 exemplaire ici.
        # Un clic sur un slot de l'inventaire selectionne l'item pour placement.
        # Placer un item sur la grille decremente sa quantite dans l'inventaire.
        "inventory":                {"small": 0, "big": 0, "trap": 0},

        # Item actuellement selectionne dans l'inventaire (ou None)
        "selected_item":            None,

        # Vagues
        "wave_number":              WAVE_NUMBER_START,
        "max_waves":                MAX_WAVES,
        "wave_timer":               WAVE_DURATION,
        "last_wave_time":           time.time(),
        "boss_active":              False,
        "boss_timer":               BOSS_DURATION,
        "boss_start_time":          0,
        "enemies_spawned_this_wave": 0,
        "max_enemies_this_wave":    5 + WAVE_NUMBER_START * 2,
        "mobs_killed_this_wave":    0,
        "last_enemy_spawn":         time.time(),
        "enemy_spawn_interval":     ENEMY_SPAWN_INTERVAL_BASE,

        # Entites
        "towers":                   towers,
        "projectiles":              projectiles,
        "enemies":                  enemies,
        "grid":                     grid,
        "goal":                     goal,
        "player":                   player,
    }


# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

def main():
    render.init_pygame()
    main_menu(render.screen, render.clock)

    grid_cache = GridCache()
    gs         = build_initial_state()
    grid_cache.invalidate()

    # FIX-PAUSE-TIMER : stocke le moment ou la pause commence
    _pause_start = None

    running = True
    while running:

        render.clock.tick(60)
        render.screen.fill(BACKGROUND_COLOR)

        mouse_clicked_left = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Echap deselectione l'item d'abord, quitte si rien de selectionne
                    if gs["selected_item"]:
                        gs["selected_item"] = None
                    else:
                        running = False
                elif event.key == PAUSE_KEY and gs["game_started"] \
                        and not gs["game_over"] and not gs["game_win"]:
                    if not gs["paused"]:
                        # FIX-4/5 : on note l'heure de debut de pause
                        gs["paused"] = True
                        _pause_start = time.time()
                    else:
                        gs["paused"] = False
                        # Decale tous les timers de la duree totale de pause
                        if _pause_start is not None:
                            paused_duration = time.time() - _pause_start
                            gs["last_wave_time"]   += paused_duration
                            gs["last_enemy_spawn"] += paused_duration
                            if gs["boss_start_time"]:
                                gs["boss_start_time"] += paused_duration
                            _pause_start = None
            elif event.type == pygame.VIDEORESIZE:
                render.screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE
                )
                # FIX-11 : force le recalcul du cache de grille apres redim
                grid_cache.invalidate()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked_left = True

        win_w, win_h = render.screen.get_size()

        # La grille est centree horizontalement dans la zone hors inventaire.
        # La barre d'inventaire occupe INV_BAR_HEIGHT pixels en bas.
        total_width = GRID_WIDTH + INTERFACE_WIDTH
        offset_x    = (win_w - total_width) // 2
        # L'espace vertical disponible hors inventaire
        usable_h    = win_h - INV_BAR_HEIGHT
        offset_y    = max(40, (usable_h - GRID_HEIGHT) // 2)

        mx, my = pygame.mouse.get_pos()
        gx = (mx - offset_x) // GRID_SIZE
        gy = (my - offset_y) // GRID_SIZE

        # Raccourcis locaux
        gs_grid        = gs["grid"]
        gs_towers      = gs["towers"]
        gs_enemies     = gs["enemies"]
        gs_projectiles = gs["projectiles"]
        gs_goal        = gs["goal"]
        gs_player      = gs["player"]
        gs_inv         = gs["inventory"]

        # FIX #5 : game_over cumulatif
        if not gs["game_over"]:
            gs["game_over"] = gs_goal.hp <= 0
        if not gs["game_over"] and not gs_player.alive:
            gs["game_over"] = True

        # ===================================================
        # GESTION DES VAGUES
        # ===================================================
        current_time = time.time()

        if not gs["game_started"]:
            gs["last_wave_time"]   = current_time
            gs["last_enemy_spawn"] = current_time

        if not gs["paused"] and not gs["game_over"] and not gs["game_win"]:

            if not gs["boss_active"]:
                gs["wave_timer"] = max(0, WAVE_DURATION - (current_time - gs["last_wave_time"]))

            if gs["game_started"] and gs["wave_number"] <= gs["max_waves"]:
                gs["enemy_spawn_interval"] = max(0.2, 1.2 - 0.1 * (gs["wave_number"] - 1))

            if (gs["game_started"]
                    and not gs["boss_active"]
                    and gs["enemies_spawned_this_wave"] < gs["max_enemies_this_wave"]
                    and current_time - gs["last_enemy_spawn"] >= gs["enemy_spawn_interval"]):
                is_fast = random.random() < 0.15
                hp      = 15 + (gs["wave_number"] - 1) * 4
                gs_enemies.append(Enemy(hp=hp, speed=1.6 if is_fast else 1.0, is_fast=is_fast))
                gs["enemies_spawned_this_wave"] += 1
                gs["last_enemy_spawn"]           = current_time

            # FIX #8 : calcules une seule fois
            # Exclut les ennemis en cours d'animation de mort (_dying)
            alive_enemies  = [e for e in gs_enemies if not e.is_dead and not e._dying]
            has_boss       = any(e.is_boss       for e in alive_enemies)
            has_final_boss = any(e.is_final_boss for e in alive_enemies)

            if (not gs["boss_active"]
                    and gs["enemies_spawned_this_wave"] >= gs["max_enemies_this_wave"]
                    and not alive_enemies):
                gs["boss_active"]     = True
                gs["boss_start_time"] = current_time
                is_final = gs["wave_number"] == gs["max_waves"]
                if is_final:
                    boss_hp = 500 + 100 * (gs["wave_number"] - 1)
                    gs_enemies.append(Enemy(hp=boss_hp, speed=0.6, radius=50,
                                            is_boss=True, is_final_boss=True))
                else:
                    boss_hp = 150 + 50 * gs["wave_number"]
                    gs_enemies.append(Enemy(hp=boss_hp, speed=0.3, radius=25, is_boss=True))
                alive_enemies  = [e for e in gs_enemies if not e.is_dead and not e._dying]
                has_boss       = any(e.is_boss       for e in alive_enemies)
                has_final_boss = any(e.is_final_boss for e in alive_enemies)

            if gs["boss_active"]:
                gs["boss_timer"] = max(0, BOSS_DURATION - (current_time - gs["boss_start_time"]))
                if gs["boss_timer"] <= 0 and has_boss:
                    gs["game_over"] = True

            if gs["boss_active"] and not has_boss:
                gs["boss_active"] = False
                if gs["wave_number"] == gs["max_waves"]:
                    gs["game_win"] = True
                else:
                    sl = {
                        "wave_number": gs["wave_number"],
                        "last_wave_time": gs["last_wave_time"],
                        "last_enemy_spawn": gs["last_enemy_spawn"],
                        "mobs_killed_this_wave": gs["mobs_killed_this_wave"],
                        "enemies_spawned_this_wave": gs["enemies_spawned_this_wave"],
                        "max_enemies_this_wave": gs["max_enemies_this_wave"],
                        "boss_active": gs["boss_active"],
                        "wave_timer": gs["wave_timer"],
                        "boss_timer": gs["boss_timer"],
                    }
                    start_new_wave(sl)
                    gs.update(sl)

            if gs["wave_number"] > gs["max_waves"] and not gs_enemies:
                gs["game_win"] = True
            if not gs["boss_active"] and gs["wave_timer"] <= 0 and gs_enemies:
                gs["game_over"] = True

        # ===================================================
        # UPDATE
        # ===================================================
        if gs["game_started"] and not gs["game_over"] and not gs["paused"]:
            keys_pressed = pygame.key.get_pressed()
            gs_player.update(keys_pressed, gs_enemies, gs_projectiles, False)

            for e in gs_enemies[:]:
                e.update(gs_grid, gs_goal, player=gs_player)

                # HP epuise mais pas encore marque : declenche l'anim de mort
                if not e.is_dead and not e._dying and e.hp <= 0:
                    e.mark_dead()

                # Suppression : seulement quand is_dead=True
                # (apres la fin de l'animation death si sprite present)
                # FIX-1/10 : on distribue XP/tokens UNE SEULE FOIS au moment
                # de la suppression effective de la liste (is_dead=True)
                if e.is_dead:
                    if e.is_final_boss:
                        gs["game_win"] = True
                    gs["xp"] += 7 if e.is_boss else 3
                    if not e.is_boss:
                        gs["mobs_killed_this_wave"] += 1
                    else:
                        gs["player_buff_tokens"] += 1
                    gs_enemies.remove(e)

            for t in gs_towers:
                t.update(gs_enemies, gs_projectiles)
            for p in gs_projectiles:
                p.update()

            # FIX #9 : nettoyage in-place
            i = len(gs_projectiles) - 1
            while i >= 0:
                if not gs_projectiles[i].alive:
                    gs_projectiles.pop(i)
                i -= 1
        elif gs["game_over"] or gs["game_win"]:
            # FIX-12 : vider les projectiles en vol quand la partie est terminee
            gs_projectiles.clear()

        # ===================================================
        # LEVEL UP
        # ===================================================
        while gs["xp"] >= gs["xp_to_next_level"]:
            gs["xp"]             -= gs["xp_to_next_level"]
            gs["level"]          += 1
            gs["xp_to_next_level"] = int(gs["xp_to_next_level"] * XP_GROWTH_FACTOR)
            gs["build_tokens"]   += 1

        # ===================================================
        # RENDU
        # ===================================================

        # OPTIM-GRID : 1 blit au lieu de 252 draw calls
        grid_cache.draw(render.screen, gs_grid, offset_x, offset_y)

        # Spawn zone (FIX-2 : affichee uniquement avant le demarrage du jeu)
        if not gs["game_started"]:
            spawn_surf = pygame.Surface((SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT), pygame.SRCALPHA)
            spawn_surf.fill((255, 255, 0, 60))
            render.screen.blit(spawn_surf, (offset_x + SPAWN_ZONE_X, offset_y + SPAWN_ZONE_Y))

        # Pieges (sous ennemis)
        for t in gs_towers:
            if hasattr(t, "trap_type"):
                t.draw(render.screen, offset_x, offset_y)

        # Ennemis + barre boss final
        for e in gs_enemies:
            if e.is_final_boss:
                bw2, bh2 = 400, 30
                bx2 = (win_w - bw2) // 2
                by2 = 50
                pygame.draw.rect(render.screen, (200, 0, 0), (bx2, by2, bw2, bh2))
                bfill = int(bw2 * e.hp / max(1, e.max_hp))
                pygame.draw.rect(render.screen, (0, 200, 0), (bx2, by2, bfill, bh2))
                bt = render.big_font.render("BOSS FINAL !", True, (255, 0, 0))
                render.screen.blit(bt, ((win_w - bt.get_width()) // 2, by2 - 40))
            e.draw(render.screen, offset_x, offset_y)

        gs_goal.draw(render.screen, offset_x, offset_y)

        # Tours (au-dessus ennemis)
        for t in gs_towers:
            if hasattr(t, "tower_type"):
                t.draw(render.screen, offset_x, offset_y)

        for p in gs_projectiles:
            p.draw(render.screen, offset_x, offset_y)

        gs_player.draw(render.screen, offset_x, offset_y)

        # HUD
        draw_hud(
            render.screen, render.font, render.big_font,
            gs["level"], gs["xp"], gs["xp_to_next_level"],
            gs["wave_number"], gs["max_waves"],
            gs["mobs_killed_this_wave"], gs["max_enemies_this_wave"],
            gs["boss_active"], gs["boss_timer"], gs["wave_timer"],
            offset_x, offset_y,
            player_hp=gs_player.hp, player_max_hp=gs_player.max_hp,
        )

        if not gs["game_started"]:
            draw_start_hint(render.screen, render.font, offset_x, offset_y)

        # ===================================================
        # PANEL GAUCHE : buffs joueur
        # ===================================================
        left_base_x = max(10, offset_x - 210)
        left_base_y = offset_y + 190

        pts_p = render.font.render(
            f"Jetons Joueur : {gs['player_buff_tokens']}", True, (255, 100, 100)
        )
        render.screen.blit(pts_p, (left_base_x + 10, left_base_y))
        left_base_y += 35

        buff_items  = {
            "Joueur (Vitesse)":  ("speed",    "player"),
            "Joueur (Degats)":   ("damage",   "player"),
            "Joueur (Attaque)":  ("cooldown", "player"),
        }
        rects_buffs = {}

        for buff_name, (buff_key, buff_type) in buff_items.items():
            btn_rect = pygame.Rect(left_base_x + 10, left_base_y, 180, 40)
            can_buy  = buff_type == "player" and gs["player_buff_tokens"] > 0
            color    = (80, 50, 50)
            pygame.draw.rect(render.screen, color, btn_rect, border_radius=5)
            b_color  = (255, 255, 255) if can_buy else (150, 50, 50)
            pygame.draw.rect(render.screen, b_color, btn_rect, 2, border_radius=5)
            lbl = render.font.render(buff_name, True, (255, 255, 255))
            render.screen.blit(lbl, (btn_rect.x + 10, btn_rect.y + 10))
            rects_buffs[buff_name] = (btn_rect, buff_key, buff_type)
            left_base_y += 45

        # ===================================================
        # PANEL DROIT : boutique
        # Le shop vend des items qui vont dans l'INVENTAIRE.
        # Chaque achat consomme 1 token et incremente inventory[item].
        # ===================================================
        base_x = offset_x + GRID_WIDTH
        base_y = offset_y + 100

        pts_txt = render.font.render(
            f"Jetons : {gs['build_tokens']}", True, (255, 255, 0)
        )
        render.screen.blit(pts_txt, (base_x + 10, base_y))
        base_y += 30

        # Titre boutique
        shop_title = render.font.render("--- BOUTIQUE ---", True, (200, 200, 200))
        render.screen.blit(shop_title, (base_x + 10, base_y))
        base_y += 25

        hint_lbl = render.font.render("(ajoute a l'inventaire)", True, (140, 140, 140))
        render.screen.blit(hint_lbl, (base_x + 10, base_y))
        base_y += 20

        shop_items  = {"TOURS": ["small", "big"], "PIEGES": ["trap"]}
        rects_shop  = {}

        for category, items in shop_items.items():
            cat_lbl = render.font.render(f"-- {category} --", True, (180, 180, 180))
            render.screen.blit(cat_lbl, (base_x + 10, base_y))
            base_y += 22
            for item in items:
                btn_rect  = pygame.Rect(base_x + 10, base_y, 180, 40)
                can_buy   = gs["build_tokens"] > 0
                # Couleur : plus claire si on peut acheter
                col       = (70, 100, 70) if can_buy else (50, 50, 80)
                pygame.draw.rect(render.screen, col, btn_rect, border_radius=5)
                b_col     = (180, 255, 120) if can_buy else (100, 100, 100)
                pygame.draw.rect(render.screen, b_col, btn_rect, 2, border_radius=5)

                lbl_text = ITEM_LABELS.get(item, item.capitalize())
                lbl      = render.font.render(lbl_text, True, (255, 255, 255))
                render.screen.blit(lbl, (btn_rect.x + 10, btn_rect.y + 10))

                # Affiche la quantite deja en inventaire dans le coin du bouton
                qty = gs_inv.get(item, 0)
                if qty > 0:
                    qty_font = pygame.font.SysFont(None, 18)
                    qty_lbl  = qty_font.render(f"x{qty}", True, (255, 220, 80))
                    render.screen.blit(qty_lbl, (btn_rect.right - qty_lbl.get_width() - 4,
                                                  btn_rect.y + 4))

                rects_shop[item] = btn_rect
                base_y += 45
            base_y += 8

        # ===================================================
        # INVENTAIRE BAS-ECRAN
        # ===================================================
        inv_rects = draw_inventory(
            render.screen, render.font,
            gs_inv, gs["selected_item"],
            win_w, win_h
        )

        # ===================================================
        # ZONES DE CLIC
        # ===================================================
        in_buff_area = mx < offset_x
        in_shop_area = mx >= offset_x + GRID_WIDTH
        in_inv_area  = my >= win_h - INV_BAR_HEIGHT
        in_grid_area = (not in_buff_area and not in_shop_area and not in_inv_area
                        and offset_x <= mx < offset_x + GRID_WIDTH
                        and offset_y <= my < offset_y + GRID_HEIGHT)

        if mouse_clicked_left and not gs["game_over"] and not gs["game_win"] and not gs["paused"]:

            # --- Clic dans le shop : acheter → ajouter a l'inventaire ---
            if in_shop_area:
                for item, rect in rects_shop.items():
                    if rect.collidepoint(mx, my) and gs["build_tokens"] > 0:
                        gs_inv[item]      = gs_inv.get(item, 0) + 1
                        gs["build_tokens"] -= 1
                        # Auto-selectionne l'item achete si rien n'est selectionne
                        if gs["selected_item"] is None:
                            gs["selected_item"] = item

            # --- Clic dans l'inventaire : selectionner / deselectionner ---
            elif in_inv_area:
                for item_type, rect in inv_rects.items():
                    if rect.collidepoint(mx, my):
                        if gs["selected_item"] == item_type:
                            gs["selected_item"] = None   # deselectionne
                        else:
                            gs["selected_item"] = item_type
                        break

            # --- Clic buffs joueur ---
            elif in_buff_area:
                for buff_name, (rect, buff_key, buff_type) in rects_buffs.items():
                    if rect.collidepoint(mx, my):
                        if buff_type == "player" and gs["player_buff_tokens"] > 0:
                            gs["player_buff_tokens"] -= 1
                            if buff_key == "speed":
                                gs_player.speed += 0.5
                            elif buff_key == "damage":
                                gs_player.damage += 2
                            elif buff_key == "cooldown":
                                gs_player.attack_cooldown = max(5, gs_player.attack_cooldown - 2)

        # ===================================================
        # GHOST + PLACEMENT SUR LA GRILLE
        # ===================================================
        sel = gs["selected_item"]

        # L'item selectionne doit exister en stock dans l'inventaire
        if sel and gs_inv.get(sel, 0) > 0 and not gs["game_over"] and not gs["paused"]:
            cells = cells_for_item(sel, gx, gy)

            if cells:
                # FIX #3 : instance unique par frame
                can_place_fn = make_can_place(gs_grid, START, sel)

                is_upgrade = any(
                    (
                        (getattr(t, "tower_type", getattr(t, "trap_type", None)) == sel)
                        or (sel == "trap" and getattr(t, "trap_type", None) == "spikes")
                    )
                    and any(cell in t.cells for cell in cells)
                    for t in gs_towers
                )

                # Ghost (seulement si la souris est sur la grille)
                if in_grid_area or (offset_x <= mx < offset_x + GRID_WIDTH
                                    and offset_y <= my < offset_y + GRID_HEIGHT):
                    draw_ghost(
                        render.screen, cells, gx, gy, sel, gs_towers,
                        can_place_fn, offset_x, offset_y,
                    )

                # Clic sur la grille : tenter le placement
                if (mouse_clicked_left
                        and in_grid_area
                        and not in_inv_area
                        and (is_upgrade or can_place_fn(cells))):

                    placed = place_tower_on_grid(gs_grid, gs_towers, cells, sel, grid_cache)
                    if placed:
                        # Decremente le stock de l'inventaire
                        gs_inv[sel] -= 1
                        gs["game_started"] = True
                        # Deselectionne si le stock est epuise
                        if gs_inv[sel] <= 0:
                            gs["selected_item"] = None

        # ===================================================
        # ECRAN DE PAUSE
        # ===================================================
        if gs["paused"]:
            draw_pause_screen(render.screen, render.big_font, render.font)

        # ===================================================
        # ECRAN DE FIN
        # ===================================================
        if gs["game_over"] or (gs["game_win"] and not gs_enemies):
            restart = draw_gameover_screen(
                render.screen, render.big_font, render.font,
                win=gs["game_win"],
                mouse_pos=(mx, my),
                clicked=mouse_clicked_left,
            )
            if restart:
                gs = build_initial_state()
                grid_cache.invalidate()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
