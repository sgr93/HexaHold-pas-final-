"""
entity_helpers.py
-----------------
Helpers et constantes partages entre les entites.
"""
import os

# Taille max du cache de frames scalees (evite fuite memoire)
_SCALED_FRAME_CACHE_MAX = 512

# Chemin de base vers les assets (relatif au fichier main.py)
_ASSETS_BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")


def _crop_alpha_surface(surface):
    """Rogne les marges transparentes d'une surface pour mieux remplir sa hitbox visuelle."""
    rect = surface.get_bounding_rect(min_alpha=10)
    if rect.width <= 0 or rect.height <= 0:
        return surface
    return surface.subsurface(rect).copy()


def _direction_from_delta(dx, dy):
    """
    Convertit un vecteur deplacement en direction pour le SpriteSet.
    Retourne : 'down', 'up', 'left', 'right'
    """
    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'
    return 'down' if dy >= 0 else 'up'
