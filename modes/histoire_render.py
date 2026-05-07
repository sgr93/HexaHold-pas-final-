"""
modes/histoire_render.py

Helpers de dessin et construction de la carte des murs.
Tout ce qui est purement visuel et réutilisable est ici —
la logique de navigation reste dans histoire.py.
"""

import pygame
from modes.histoire_data import (
    C_BG, C_BG2, C_WALL, C_WALL_LT, C_GOLD, C_GOLD2, C_GOLD3,
    C_PARCHMENT, C_PARCHMENT2, C_RED, C_RED2, C_GREEN_D, C_GREEN_L,
    C_BROWN_D, C_BROWN_L, C_PURPLE_D, C_PURPLE_L, C_LOCKED, C_LOCKED_B,
    C_OVERLAY, C_PANEL, C_PANEL_B, C_TEXT, C_MUTED,
    C_STAR_ON, C_STAR_OFF, C_NOTIF_BG, C_NOTIF_B,
)

# Police pixel pour les titres, Georgia pour le texte courant
_FONT_PIXEL = "assets/fonts/PIXELCRASH.otf"


def _font(size, bold=False):
    """Police pixel si bold, Georgia sinon — cohérent avec le thème médiéval du mode histoire."""
    if bold:
        return pygame.font.Font(_FONT_PIXEL, size)
    return pygame.font.SysFont("georgia", size, bold=bold)


def _draw_text_centered(surf, text, font, color, cx, cy, shadow=True):
    """Texte centré avec ombre portée optionnelle — le shadow=True par défaut donne du relief."""
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        surf.blit(s, (cx - s.get_width() // 2 + 1, cy - s.get_height() // 2 + 1))
    t = font.render(text, True, color)
    surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))


def _draw_rect_alpha(surf, color, rect, radius=0):
    """Rect avec transparence — pygame ne supporte pas l'alpha sur draw.rect directement."""
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)


def _draw_circle_aa(surf, color, cx, cy, r, width=0):
    """Wrapper minimal pour draw.circle avec coords en int — évite les warnings de type."""
    pygame.draw.circle(surf, color, (int(cx), int(cy)), r, width)


def _lerp_color(a, b, t):
    """Interpolation linéaire entre deux couleurs RGB — utile pour les animations de survol."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# CONSTRUCTION DE LA SURFACE CARTE

def _build_map_surface(w, h):
    """
    Dessine la carte des murs (fond, cercles, routes, décorations) sans les
    points de chapitre ni les labels texte. Appelée une fois et mise en cache.
    """
    surf = pygame.Surface((w, h))
    surf.fill(C_BG)

    cx, cy = w // 2, h // 2

    # Rayons des trois murs — proportionnels à la taille de la surface pour scaler proprement
    r_outer = int(min(w, h) * 0.44)  # Wall Maria
    r_rose  = int(min(w, h) * 0.31)  # Wall Rose
    r_inner = int(min(w, h) * 0.18)  # Wall Sheena

    pygame.draw.rect(surf, C_BG2, pygame.Rect(0, 0, w, h))
    pygame.draw.circle(surf, (20, 16, 8), (cx, cy), r_outer + 14)

    # Wall Maria — le plus grand, 4 portes aux points cardinaux
    pygame.draw.circle(surf, C_WALL,    (cx, cy), r_outer, 16)
    pygame.draw.circle(surf, C_WALL_LT, (cx, cy), r_outer,  2)
    for gx, gy, gw, gh in [
        (cx - 12, cy - r_outer - 10, 24, 14),
        (cx - 12, cy + r_outer -  4, 24, 14),
        (cx - r_outer - 10, cy - 12, 14, 24),
        (cx + r_outer -  4, cy - 12, 14, 24),
    ]:
        pygame.draw.rect(surf, C_WALL,    (gx, gy, gw, gh), border_radius=2)
        pygame.draw.rect(surf, C_WALL_LT, (gx, gy, gw, gh), 1, border_radius=2)

    # Wall Rose — mur intermédiaire, même structure que Maria en plus petit
    pygame.draw.circle(surf, C_WALL,    (cx, cy), r_rose, 12)
    pygame.draw.circle(surf, C_WALL_LT, (cx, cy), r_rose,  2)
    for gx, gy, gw, gh in [
        (cx - 9, cy - r_rose - 8, 18, 12),
        (cx - 9, cy + r_rose - 4, 18, 12),
        (cx - r_rose - 8, cy - 9, 12, 18),
        (cx + r_rose - 4, cy - 9, 12, 18),
    ]:
        pygame.draw.rect(surf, C_WALL,    (gx, gy, gw, gh), border_radius=2)
        pygame.draw.rect(surf, C_WALL_LT, (gx, gy, gw, gh), 1, border_radius=2)

    # Wall Sheena — mur intérieur qui protège la capitale
    pygame.draw.circle(surf, C_WALL,    (cx, cy), r_inner, 10)
    pygame.draw.circle(surf, C_WALL_LT, (cx, cy), r_inner,  1)
    for gx, gy, gw, gh in [
        (cx - 6, cy - r_inner - 6, 12, 10),
        (cx - 6, cy + r_inner - 4, 12, 10),
        (cx - r_inner - 6, cy - 6, 10, 12),
        (cx + r_inner - 4, cy - 6, 10, 12),
    ]:
        pygame.draw.rect(surf, C_WALL,    (gx, gy, gw, gh), border_radius=1)
        pygame.draw.rect(surf, C_WALL_LT, (gx, gy, gw, gh), 1, border_radius=1)

    # Remplissage intérieur de Sheena — couleur légèrement plus chaude pour la capitale
    pygame.draw.circle(surf, (26, 20, 8), (cx, cy), r_inner - 5)

    # Routes en croix à l'intérieur de Sheena — largeur proportionnelle à la taille
    road_w = max(12, w // 40)
    for rx, ry, rw, rh in [
        (cx - road_w // 2, cy - r_inner + 5, road_w, r_inner - 5),
        (cx - road_w // 2, cy,               road_w, r_inner - 5),
        (cx - r_inner + 5, cy - road_w // 2, r_inner - 5, road_w),
        (cx,               cy - road_w // 2, r_inner - 5, road_w),
    ]:
        pygame.draw.rect(surf, (28, 22, 10), (rx, ry, rw, rh))

    # Palais Royal au centre — grille intérieure pour suggérer un bâtiment
    pr = road_w + 4
    palace = pygame.Rect(cx - pr, cy - pr, pr * 2, pr * 2)
    pygame.draw.rect(surf, (36, 28, 10), palace, border_radius=2)
    pygame.draw.rect(surf, C_GOLD,       palace, 1, border_radius=2)
    for i in range(1, 3):
        x = palace.x + palace.w * i // 3
        pygame.draw.line(surf, C_WALL, (x, palace.y), (x, palace.bottom), 1)
        y = palace.y + palace.h * i // 3
        pygame.draw.line(surf, C_WALL, (palace.x, y), (palace.right, y), 1)

    # Forêt des Titans — petits triangles pour évoquer des arbres, pas plus
    fx = int(w * 0.746)
    fy = int(h * 0.68)
    for dx, dy in [(-14, 0), (0, -12), (14, 0), (-7, 12), (7, 12), (-20, 14), (20, 14)]:
        tx, ty = fx + dx, fy + dy
        pygame.draw.polygon(surf, (20, 38,  8), [(tx, ty - 14), (tx + 8, ty + 8), (tx - 8, ty + 8)])
        pygame.draw.polygon(surf, (28, 50, 10), [(tx, ty - 14), (tx + 8, ty + 8), (tx - 8, ty + 8)], 1)

    # Château Utgard — petit rectangle avec deux tours
    ux = int(w * 0.304)
    uy = int(h * 0.642)
    cr = pygame.Rect(ux - 10, uy - 9, 20, 16)
    pygame.draw.rect(surf, (38, 28, 12), cr, border_radius=2)
    pygame.draw.rect(surf, (90, 68, 28), cr, 1, border_radius=2)
    for tx in [ux - 9, ux + 3]:
        pygame.draw.rect(surf, (50, 38, 14), (tx, uy - 15, 6, 8))

    # District de Shiganshina — ellipse en bas avec un petit bout de mur au-dessus
    sx = cx
    sy = int(h * 0.870)
    pygame.draw.ellipse(surf, (28, 20,  8), (sx - 30, sy - 12, 60, 22))
    pygame.draw.ellipse(surf, C_WALL,       (sx - 30, sy - 12, 60, 22), 1)
    pygame.draw.rect(surf, C_WALL, (sx - 15, sy - 14, 30, 5), border_radius=1)

    return surf