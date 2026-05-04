"""
game_passives.py
----------------
Passifs heros et gestion de l'ultime, extraits de game.py.
"""
import math
import pygame
from config import GRID_SIZE
import random as _rnd
import heroes as _hm
from config import ALL_TOWER_TYPES


def _apply_eren_passive(gs, towers, player):
    """Eren : tours dans un rayon de 8 cases autour du joueur = +20% degats."""
    if gs.get("selected_hero") != "eren":
        return
    BOOST = 0.10
    radius_px = 3 * GRID_SIZE
    for t in towers:
        if not hasattr(t, "tower_type"):
            continue
        dist = math.hypot(t.x - player.x, t.y - player.y)
        in_range = dist <= radius_px
        was_boosted = getattr(t, "_eren_boosted", False)
        if in_range and not was_boosted:
            t._eren_boosted = True
            t.damage = int(t.damage * (1.0 + BOOST))
        elif not in_range and was_boosted:
            t._eren_boosted = False
            t.set_stats(damage_bonus=gs.get("tower_damage_bonus", 0),
                        cooldown_bonus=gs.get("tower_cooldown_bonus", 0))


def _apply_armin_passive_on_build(gs, towers):
    """Armin : +40% ATK sur toutes les tours a chaque nouvelle tour construite."""
    if gs.get("selected_hero") != "armin":
        return
    gs["armin_buff_stacks"] = gs.get("armin_buff_stacks", 0) + 1
    total_mult = 1.0 + 0.08 * gs["armin_buff_stacks"]
    for t in towers:
        if not hasattr(t, "tower_type"):
            continue
        base_dmg = getattr(t, "_base_damage", t.damage)
        t._base_damage = base_dmg
        t.damage = int(base_dmg * total_mult)


def _apply_sasha_passive_on_wave(gs):
    """Sasha : ajoute une tour aleatoire dans l'inventaire chaque nouvelle vague."""
    if gs.get("selected_hero") != "sasha":
        return
    wn = gs.get("wave_number", 1)
    done = gs.setdefault("sasha_towers_given", set())
    if wn in done:
        return
    done.add(wn)
    save = gs.get("save") or {}
    hero_level = _hm.get_hero_level(save, "sasha")
    nb = 1 + (hero_level - 1) // 5
    pool = [t for t in ALL_TOWER_TYPES if t not in ("trap",)]
    for _ in range(nb):
        t = _rnd.choice(pool)
        gs["inventory"][t] = gs["inventory"].get(t, 0) + 1
    gs.setdefault("toasts", []).append({
        "text": f"Sasha : +{nb} tour(s) offerte(s) !",
        "ttl": 200, "max_ttl": 200, "color": (160, 120, 80)
    })


def _apply_levi_passive_on_upgrade(gs, tower):
    """Levi : upgrade niveau 1 -> niveau 3 directement."""
    if gs.get("selected_hero") != "levi":
        return False
    if tower.level == 2:
        tower.level = 3
        tower.set_stats(damage_bonus=gs.get("tower_damage_bonus", 0),
                        cooldown_bonus=gs.get("tower_cooldown_bonus", 0))
        return True
    return False


def _apply_mikasa_passive(gs, screen, player, enemies, offset_x, offset_y):
    """Mikasa : zone de degats continus autour du joueur (120px)."""
    if gs.get("selected_hero") != "mikasa":
        return
    RADIUS = 80
    DPS = 4.0
    dt = 1.0 / 60.0
    dmg_per_frame = DPS * dt

    surf = pygame.Surface((RADIUS * 2 + 4, RADIUS * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(surf, (127, 119, 221, 35), (RADIUS + 2, RADIUS + 2), RADIUS)
    pygame.draw.circle(surf, (127, 119, 221, 80), (RADIUS + 2, RADIUS + 2), RADIUS, 2)
    screen.blit(surf, (int(player.x) + offset_x - RADIUS - 2,
                        int(player.y) + offset_y - RADIUS - 2))

    for e in enemies:
        if e.is_dead or e._dying:
            continue
        dist = math.hypot(e.x - player.x, e.y - player.y)
        if dist <= RADIUS:
            e.hp -= dmg_per_frame
            if e.hp <= 0 and not e.is_dead:
                e.is_dead = True


def _draw_eren_passive_zone(screen, player, offset_x, offset_y):
    """Dessine le cercle de portee d'Eren (informatif)."""
    RADIUS = 3 * GRID_SIZE
    surf = pygame.Surface((RADIUS * 2 + 4, RADIUS * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(surf, (213, 90, 48, 20), (RADIUS + 2, RADIUS + 2), RADIUS)
    pygame.draw.circle(surf, (213, 90, 48, 60), (RADIUS + 2, RADIUS + 2), RADIUS, 1)
    screen.blit(surf, (int(player.x) + offset_x - RADIUS - 2,
                        int(player.y) + offset_y - RADIUS - 2))


def _get_ultimate_duration(char_id):
    """Retourne la duree en secondes de l'effet ultime selon le personnage."""
    return {"eren": 8.0, "mikasa": 10.0, "erwin": 12.0}.get(char_id, 8.0)


def _apply_ultimate_start(gs):
    """Active les effets de l'ultime selon le personnage."""
    char = gs["ultimate_info"]["char"]
    player = gs["player"]
    if char == "eren":
        gs["_ult_orig_damage"] = player.damage
        player.damage = int(player.damage * 2)
        gs["_ult_slow_enemies"] = True
    elif char == "mikasa":
        gs["_ult_orig_speed"] = player.speed
        gs["_ult_orig_attack_cd"] = player.attack_cooldown
        player.speed = player.speed * 2
        player.attack_cooldown = max(3, player.attack_cooldown // 2)
    elif char == "erwin":
        gs["_ult_tower_fire_rate"] = True


def _apply_ultimate_end(gs):
    """Retire les effets de l'ultime."""
    char = gs["ultimate_info"]["char"]
    player = gs["player"]
    if char == "eren":
        player.damage = gs.pop("_ult_orig_damage", player.damage)
        gs.pop("_ult_slow_enemies", None)
    elif char == "mikasa":
        player.speed = gs.pop("_ult_orig_speed", player.speed)
        player.attack_cooldown = gs.pop("_ult_orig_attack_cd", player.attack_cooldown)
    elif char == "erwin":
        gs.pop("_ult_tower_fire_rate", None)
    gs["ultimate_active"] = False
    gs["ultimate_timer"] = 0
