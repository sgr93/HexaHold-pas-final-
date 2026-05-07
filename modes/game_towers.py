"""
modes/game_towers.py

Helpers de placement et upgrade des tours et pièges.
Tout ce qui touche à "poser quelque chose sur la grille" passe par ici —
la logique de can_place, les cellules occupées, et les bonus de stats.
"""

from core.config import TOWER_MAX_LEVEL
from core.entities import Tower, Trap


def make_can_place(grid, start_cell, item_type=None):
    """
    Retourne une fonction can_place(cells) qui vérifie si le placement est légal.
    On met les résultats en cache par (item_type, cells, grid.version) pour ne pas
    refaire le calcul du flow field à chaque frame — c'est coûteux.
    """
    cache = {}

    def can_place(cells):
        cache_key = (item_type, tuple(sorted(cells)), grid.version)
        if cache_key in cache:
            return cache[cache_key]

        # Vérif basique avant de toucher au flow field
        for x, y in cells:
            if not grid.in_bounds(x, y):
                cache[cache_key] = False
                return False
            if not grid.walkable[x][y]:
                cache[cache_key] = False
                return False

        # Pièges et mines : pas besoin de vérifier le chemin, juste qu'il n'y en a pas déjà un
        if item_type in ("trap", "mine"):
            occupied = set()
            for t in grid.towers_ref:
                if hasattr(t, "trap_type"):
                    occupied.update(t.cells)
            result = not any((x, y) in occupied for x, y in cells)
            cache[cache_key] = result
            return result

        # Tours normales : on bloque temporairement les cellules et on vérifie
        # que le chemin START → END existe toujours — puis on remet comme avant
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

        # On restore la grille dans son état d'origine quoi qu'il arrive
        for x, y in blocked:
            grid.walkable[x][y] = True
        grid.recompute()
        cache[cache_key] = valid
        return valid

    return can_place


def _is_matching_upgrade_target(tower, item_type, cells):
    """Vérifie si une tour existante peut recevoir un upgrade de ce type sur ces cellules."""
    t_type = getattr(tower, "tower_type", getattr(tower, "trap_type", None))
    # trap → spikes et mine → mine : les noms internes diffèrent parfois du type item
    match_type = (
        t_type == item_type
        or (item_type == "trap" and t_type == "spikes")
        or (item_type == "mine" and t_type == "mine")
    )
    return match_type and set(tower.cells) == set(cells)


def cells_for_item(item_type, gx, gy):
    """
    Retourne les cellules occupées par un item à la position (gx, gy).
    Les pièges sont en 2x4, toutes les autres tours en 2x2.
    """
    if item_type == "trap":
        return [(gx + i, gy + j) for i in range(2) for j in range(4)]
    return [(gx, gy), (gx + 1, gy), (gx, gy + 1), (gx + 1, gy + 1)]


def place_tower_on_grid(grid, towers, cells, item_type, grid_cache,
                        damage_bonus=0, cooldown_bonus=0, tower_level=1,
                        levi_callback=None, armin_callback=None):
    """
    Place une tour/piège ou upgrade si une tour compatible est déjà là.
    Retourne True si le placement ou l'upgrade a réussi, False sinon.
    Les callbacks passifs (levi, armin) sont injectés depuis l'extérieur
    pour garder cette fonction agnostique du système de héros.
    """
    target_cells = set(cells)

    # Upgrade d'une tour existante si les cellules et le type correspondent
    for t in towers:
        if _is_matching_upgrade_target(t, item_type, target_cells):
            if t.fusion_level >= TOWER_MAX_LEVEL:
                return False  # Déjà au max, on refuse silencieusement
            t.fusion_level += 1
            t.level = t.fusion_level  # level et fusion_level doivent rester synchronisés
            t.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
            if item_type not in ("trap", "mine"):
                grid.recompute()
                grid_cache.invalidate()
            if levi_callback:
                levi_callback(t)
            if armin_callback:
                armin_callback(towers)
            return True

    # Nouveau placement — pièges d'abord, tours normales ensuite
    if item_type in ("trap", "mine"):
        trap_type = "spikes" if item_type == "trap" else "mine"
        new_trap = Trap(cells, trap_type=trap_type, gacha_level=tower_level)
        new_trap.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)
        towers.append(new_trap)
        grid.recompute()
        grid_cache.invalidate()
        if armin_callback:
            armin_callback(towers)
        return True

    # Tour normale : on bloque les cellules dans la grille avant de créer l'objet
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
    """Applique les bonus de dégâts et cooldown sur une tour individuelle."""
    tower.set_stats(damage_bonus=damage_bonus, cooldown_bonus=cooldown_bonus)


def apply_all_tower_bonuses(towers, damage_bonus, cooldown_bonus):
    """Remet à jour les stats de toutes les tours — appelé après chaque level-up buff."""
    for tower in towers:
        # On ignore les pièges ici, ils ont leur propre logique de stats
        if hasattr(tower, "tower_type"):
            apply_tower_bonuses(tower, damage_bonus, cooldown_bonus)