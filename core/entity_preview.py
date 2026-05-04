"""
entity_preview.py
-----------------
Helper get_tower_preview.
"""
import math
import random
import os
import pygame
from config import (
    GRID_SIZE, COLS, ROWS,
    SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT,
    START, END, PLAYER_HP,
    TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT,
    TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import sprites as spr
from entity_helpers import (
    _crop_alpha_surface, _direction_from_delta,
    _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)
from entity_tower import Tower

def get_tower_preview(tower_type, width_px, height_px):
    """
    Retourne une surface scalée à (width_px, height_px) représentant
    la frame courante du sprite du type de tour donné.
    Retourne None si aucun sprite n'est chargé pour ce type.
    """
    master = Tower._anim_cache.get(tower_type)
    if master is None:
        return None
    frame = master.get_frame()
    if frame is None:
        return None
    cropped = _crop_alpha_surface(frame)
    preview_w = max(1, int(width_px * 0.94))
    preview_h = max(1, int(height_px * 0.94))
    scaled = pygame.transform.scale(cropped, (preview_w, preview_h))
    if preview_w == width_px and preview_h == height_px:
        return scaled
    surf = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
    surf.blit(scaled, ((width_px - preview_w) // 2, (height_px - preview_h) // 2))
    return surf