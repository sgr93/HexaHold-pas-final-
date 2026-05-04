"""
entity_projectile.py
--------------------
Classe Projectile.
"""
import math
import random
import os
import pygame
from core.config import (
    GRID_SIZE, COLS, ROWS, SPAWN_ZONE_X, SPAWN_ZONE_Y, SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, START, END, PLAYER_HP, TOWER_DAMAGE_MULT, TOWER_COOLDOWN_MULT, TOWER_RANGE_MULT, TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import ui.sprites as spr
from core.entity_helpers import (
    _crop_alpha_surface, _direction_from_delta, _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)


class Projectile:
    """
    Projectile tiré par le joueur ou une tour.

    Sprites dans assets/sprites/projectiles/ :
        <type>.png          spritesheet animée en vol (frames horizontales, hauteur = taille frame)
        <type>_impact.png   spritesheet d'impact jouée une fois au moment du hit

    Convention : le sprite en vol pointe vers la DROITE (0°).
    Si les fichiers sont absents, fallback sur le cercle jaune.
    """

    # Taille d'affichage des projectiles sans sprite (fallback)
    SPRITE_SIZE = 16

    # Taille d'affichage des projectiles animés (pixels carrés)
    ANIM_SIZE = 18

    # Taille d'affichage de l'impact
    IMPACT_SIZE = 64

    # Offset d'angle par type
    ANGLE_OFFSET = {
        "player": 180,
    }

    # Cache des animateurs maîtres — partagés, clonés par instance
    _anim_cache: dict   = {}   # {type_key: SpritesheetAnimator | None}
    _impact_cache: dict = {}   # {type_key: SpritesheetAnimator | None}
    # Cache legacy (image statique) conservé pour la compatibilité
    _sprite_cache: dict = {}

    @classmethod
    def _find_sprite_path(cls, type_key, suffix=""):
        folder = os.path.join(_ASSETS_BASE, "projectiles")
        name   = f"{type_key}{suffix}.png"
        direct = os.path.join(folder, name)
        if os.path.isfile(direct):
            return direct
        target = name.lower()
        if os.path.isdir(folder):
            for fname in os.listdir(folder):
                if fname.lower() == target:
                    return os.path.join(folder, fname)
        return None

    @classmethod
    def _load_sprite(cls, type_key):
        """
        Charge le projectile : d'abord spritesheet animée, sinon image statique legacy.
        Charge aussi l'impact si <type>_impact.png existe.
        """
        # Déjà traité
        if type_key in cls._anim_cache:
            return cls._sprite_cache.get(type_key)

        proj_path   = cls._find_sprite_path(type_key)
        impact_path = cls._find_sprite_path(type_key, "_impact")

        # ── Projectile en vol ──
        if proj_path:
            try:
                img = pygame.image.load(proj_path).convert_alpha()
                h = img.get_height()
                n = img.get_width() // h
                if n > 1:
                    # Spritesheet animée
                    cls._anim_cache[type_key] = spr.SpritesheetAnimator(
                        proj_path, fps=12, target_size=(cls.ANIM_SIZE, cls.ANIM_SIZE), loop=True
                    )
                    cls._sprite_cache[type_key] = None  # pas de sprite statique
                    print(f"[Projectile] Anim chargée : {os.path.basename(proj_path)} ({n} frames)")
                else:
                    # Image statique legacy
                    surface = pygame.transform.scale(img, (cls.SPRITE_SIZE, cls.SPRITE_SIZE))
                    cls._sprite_cache[type_key] = surface
                    cls._anim_cache[type_key]   = None
                    print(f"[Projectile] Sprite statique : {os.path.basename(proj_path)}")
            except Exception as e:
                print(f"[Projectile] Erreur {type_key}.png : {e}")
                cls._anim_cache[type_key]   = None
                cls._sprite_cache[type_key] = None
        else:
            cls._anim_cache[type_key]   = None
            cls._sprite_cache[type_key] = None

        # ── Impact ──
        if impact_path:
            try:
                cls._impact_cache[type_key] = spr.SpritesheetAnimator(
                    impact_path, fps=14, target_size=(cls.IMPACT_SIZE, cls.IMPACT_SIZE), loop=False
                )
                print(f"[Projectile] Impact chargé : {os.path.basename(impact_path)}")
            except Exception as e:
                print(f"[Projectile] Erreur impact {type_key} : {e}")
                cls._impact_cache[type_key] = None
        else:
            cls._impact_cache[type_key] = None

        return cls._sprite_cache.get(type_key)

    def __init__(self, x, y, target, damage, speed=5, proj_type="player"):
        self.x         = float(x)
        self.y         = float(y)
        self.target    = target
        self.damage    = damage
        self.speed     = speed
        self.alive     = True
        self.proj_type = proj_type

        # S'assurer que les animateurs sont chargés
        self._sprite = Projectile._load_sprite(proj_type)

        # Cloner l'animateur en vol (indépendant par instance)
        master_anim = Projectile._anim_cache.get(proj_type)
        self._anim = spr._clone_animator(master_anim) if master_anim else None

        # Animateur d'impact (None tant qu'on n'a pas touché)
        self._impact_anim  = None
        self._impacting    = False   # True après le hit, pendant l'anim d'impact
        self._impact_x     = 0.0
        self._impact_y     = 0.0

        self._angle = 0.0

    def update(self):
        if self._impacting:
            # Jouer l'animation d'impact jusqu'à la fin
            if self._impact_anim:
                self._impact_anim.update()
                if self._impact_anim.finished:
                    self.alive = False
            else:
                self.alive = False
            return

        if not self.alive or self.target.is_dead or self.target._dying:
            self.alive = False
            return

        # Avancer l'animation en vol
        if self._anim:
            self._anim.update()

        dx   = self.target.x - self.x
        dy   = self.target.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            # Impact
            self.target.receive_damage(self.damage)
            if self.target.hp <= 0:
                self.target.mark_dead()

            master_impact = Projectile._impact_cache.get(self.proj_type)
            if master_impact:
                self._impact_anim = spr._clone_animator(master_impact)
                self._impact_anim.reset()
                self._impacting = True
                self._impact_x  = self.target.x
                self._impact_y  = self.target.y
            else:
                self.alive = False
        else:
            self._angle = -math.degrees(math.atan2(dy, dx))
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def draw(self, screen, offset_x, offset_y):
        if self._impacting:
            # Dessiner l'impact à la position du hit
            if self._impact_anim:
                frame = self._impact_anim.get_frame()
                if frame:
                    cx = int(self._impact_x) + offset_x
                    cy = int(self._impact_y) + offset_y
                    s  = Projectile.IMPACT_SIZE
                    screen.blit(frame, (cx - s // 2, cy - s // 2))
            return

        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        if self._anim:
            # Sprite animé en vol, orienté vers la cible
            frame = self._anim.get_frame()
            if frame:
                angle_off = Projectile.ANGLE_OFFSET.get(self.proj_type, 0)
                rotated   = pygame.transform.rotate(frame, self._angle + angle_off)
                rw, rh    = rotated.get_size()
                screen.blit(rotated, (cx - rw // 2, cy - rh // 2))
        elif self._sprite is not None:
            # Sprite statique legacy
            angle_off = Projectile.ANGLE_OFFSET.get(self.proj_type, 0)
            rotated   = pygame.transform.rotate(self._sprite, self._angle + angle_off)
            rw, rh    = rotated.get_size()
            screen.blit(rotated, (cx - rw // 2, cy - rh // 2))
        else:
            pygame.draw.circle(screen, (255, 255, 0), (cx, cy), 4)


# ============================================================
# HELPER GHOST
# ============================================================
