"""
entities.py
-----------
Facade : re-exporte toutes les entites depuis leurs modules dedies.
Le code a ete decoupe pour rester lisible mais l'API publique est inchangee.
"""
from core.entity_helpers import (
    _crop_alpha_surface, _direction_from_delta, _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)
from core.entity_player import Player
from core.entity_goal import Goal
from core.entity_enemy import Enemy
from core.entity_tower import Tower
from core.entity_trap import Trap
from core.entity_projectile import Projectile
from core.entity_preview import get_tower_preview
