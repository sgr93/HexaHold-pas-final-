"""
entity_preview.py
-----------------
Fonction helper pour générer la preview d'une tour avant placement.
"""
import math
import random
import os
import pygame
from core.config import (
    GRID_SIZE, COLS, ROWS, SPAWN_ZONE_X, SPAWN_ZONE_Y,
    SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, START, END,
    PLAYER_HP, TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT,
    TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import ui.sprites as spr
from core.entity_helpers import (
    _crop_alpha_surface, _direction_from_delta,
    _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)
from core.entity_tower import Tower


def get_tower_preview(tower_type, width_px, height_px):
    """
    Retourne une surface redimensionnée à (width_px, height_px) contenant
    la frame courante du sprite de la tour demandée.
    Retourne None si le type de tour n'est pas dans le cache d'animation.
    """
    # on récupère le spriteset depuis le cache, None si la tour n'existe pas
    master = Tower._anim_cache.get(tower_type)
    if master is None:
        return None

    frame = master.get_frame()
    if frame is None:
        return None

    # supprime les zones transparentes autour du sprite avant de scaler
    cropped = _crop_alpha_surface(frame)

    # légère réduction (94%) pour garder une petite marge visuelle autour
    preview_w = max(1, int(width_px*0.94))
    preview_h = max(1, int(height_px*0.94))
    scaled = pygame.transform.scale(cropped, (preview_w, preview_h))

    # si les dimensions correspondent déjà, on retourne directement
    if preview_w == width_px and preview_h == height_px:
        return scaled

    # sinon on centre le sprite sur une surface transparente aux bonnes dimensions
    surf = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
    surf.blit(scaled, ((width_px - preview_w)//2, (height_px - preview_h)//2))
    return surf