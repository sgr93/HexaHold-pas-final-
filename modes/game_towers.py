"""
game_towers.py
--------------
Helpers de placement / upgrade des tours et pieges, extraits de game.py.
"""
from core.config import TOWER_MAX_LEVEL
from core.entities import Tower, Trap


def make_can_place(grid, start_cell, item_type=None):
    """
    Retourne une fonction can_place(cells) qui verifie :
      - in_bounds
      - walkable
      - pas de piege deja present (pour trap)
      - le chemin START -> END reste possible (flow field)
    """
    cache = {}

    def can_place(cells):
        cache_key = (item_type, tuple(sorted(cells)), grid.version)
        if cache_key in cache:
            return cache[cache_key]
        for x, y in cells:
            if not grid.in_bounds(x, y):
                cache[cache_key] = False
                return False
            if not grid.walkable[x][y]:
                cache[cache_key] = False
                return False

        if item_type in ("trap", "mine"):
            occupied = set()
            for t in grid.towers_ref:
                if hasattr(t, "trap_type"):
                    occupied.update(t.cells)
            result = not any((x, y) in occupied for x, y in cells)
            cache[cache_key] = result
            return result

        blocked = []
        actually_changed = False
        for x, y in cells:
            if grid.walkable[x][y]:
                grid.walkable[x][y] = False
                blocked.append((x, y))
                actually_changed = True

        if not actually_changed:
            cache[cache_key] = False
            return False

        grid.compute_integration_field()
        valid = grid.integration_field[start_cell[0]][start_cell[1]] != float("inf")

        for x, y in blocked:
            grid.walkable[x][y] = True
        grid.recompute()
        cache[cache_key] = valid
        return valid

    return can_place


def _is_matching_upgrade_target(tower, item_type, cells):
    t_type = getattr(tower, "tower_type", getattr(tower, "trap_type", None))
    match_type = (t_type == item_type) or (
        item_type == "trap" and t_type == "spikes"
    ) or (
        item_type == "mine" and t_type == "mine"
    )
    return match_type and set(tower.cells) == set(cells)


def cells_for_item(item_type, gx, gy):
    """
    Retourne la liste des cellules occupees par un type de tour donne.
    """
    if item_type == "trap":
        return [(gx+i, gy+j) for i in range(2) for j in range(4)]
    return [(gx, gy), (gx+1, gy), (gx, gy+1), (gx+1, gy+1)]


def place_tower_on_grid(grid, towers, cells, item_type, grid_cache,
                        damage_bonus=0, cooldown_bonus=0, tower_level=1,
                        levi_callback=None, armin_callback=None):
    """
    Place une tour ou un piege sur la grille, ou upgrade si deja present.
    Retourne True si placement/upgrade effectue, False sinon.
    """
    target_cells = set(cells)
    for t in towers:
        if _is_matching_upgrade_target(t, item_type, target_cells):
            if t.fusion_level < TOWER_MAX_LEVEL:
                t.fusion_level += 1
                t.level = t.fusion_level  # Mettre à jour le niveau affiché
                t.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
                if item_type not in ("trap", "mine"):
                    grid.recompute()
                    grid_cache.invalidate()
                if levi_callback:
                    levi_callback(t)
                if armin_callback:
                    armin_callback(towers)
                return True
            return False

    if item_type == "trap":
        trap = Trap(cells, trap_type="spikes", gacha_level=tower_level)
        trap.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
        towers.append(trap)
        grid.recompute()
        grid_cache.invalidate()
        if armin_callback:
            armin_callback(towers)
        return True
    if item_type == "mine":
        mine = Trap(cells, trap_type="mine", gacha_level=tower_level)
        mine.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
        towers.append(mine)
        grid.recompute()
        grid_cache.invalidate()
        if armin_callback:
            armin_callback(towers)
        return True

    for x, y in cells:
        grid.walkable[x][y] = False
    tower = Tower(cells, item_type, gacha_level=tower_level)
    tower.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
    towers.append(tower)
    grid.recompute()
    grid_cache.invalidate()
    if armin_callback:
        armin_callback(towers)
    return True


def apply_tower_bonuses(tower, damage_bonus, cooldown_bonus):
    tower.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)


def apply_all_tower_bonuses(towers, damage_bonus, cooldown_bonus):
    for tower in towers:
        if hasattr(tower, "tower_type"):
            apply_tower_bonuses(tower, damage_bonus, cooldown_bonus)
