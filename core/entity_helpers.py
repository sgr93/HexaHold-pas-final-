"""
entity_helpers.py

contient des fonctions réutilisables et des constantes
pour éviter de dupliquer du code dans toutes les entités
"""

import os

_SCALED_FRAME_CACHE_MAX = 512  # limite cache pour éviter surcharge mémoire
_ASSETS_BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")


def _crop_alpha_surface(surface):
    """Supprime les marges transparentes inutiles autour d’un sprite."""

    rect = surface.get_bounding_rect(min_alpha=10)

    if rect.width <= 0 or rect.height <= 0:
        return surface

    return surface.subsurface(rect).copy()


def _direction_from_delta(dx, dy):
    """Convertit un déplacement en direction d’animation."""

    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'

    return 'down' if dy >= 0 else 'up'