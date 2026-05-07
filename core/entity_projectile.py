"""
entity_projectile.py
--------------------
Classe Projectile — gère le déplacement vers la cible,
l'animation en vol et l'animation d'impact au moment du hit.
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


class Projectile:
    """
    Projectile tiré par le joueur ou une tour vers une cible ennemie.

    Les sprites sont cherchés dans assets/sprites/projectiles/ :
        <type>.png          spritesheet en vol (frames horizontales, hauteur = taille d'une frame)
        <type>_impact.png   animation d'impact jouée une seule fois au contact

    Le sprite en vol doit pointer vers la droite (0°),
    la rotation vers la cible est calculée et appliquée à chaque frame.
    Si aucun fichier n'est trouvé, on affiche un simple cercle jaune en fallback.
    """

    # taille d'affichage en pixels pour le fallback sans sprite
    SPRITE_SIZE = 16

    # taille des projectiles animés
    ANIM_SIZE = 18

    # taille de l'animation d'impact au moment du hit
    IMPACT_SIZE = 64

    # certains sprites ne pointent pas vers la droite par défaut,
    # on corrige l'angle ici selon le type
    ANGLE_OFFSET = {
        "player": 180,
    }

    # ces caches sont partagés entre toutes les instances pour éviter
    # de recharger les mêmes fichiers à chaque nouveau projectile
    _anim_cache: dict   = {}   # animateur en vol par type
    _impact_cache: dict = {}   # animateur d'impact par type
    _sprite_cache: dict = {}   # images statiques legacy

    @classmethod
    def _find_sprite_path(cls, type_key, suffix=""):
        """
        Cherche le fichier sprite correspondant au type donné.
        La recherche est insensible à la casse pour éviter les problèmes
        selon le système de fichiers.
        """
        folder = os.path.join(_ASSETS_BASE, "projectiles")
        name   = f"{type_key}{suffix}.png"
        direct = os.path.join(folder, name)

        # chemin direct d'abord, c'est le cas le plus fréquent
        if os.path.isfile(direct):
            return direct

        # sinon on parcourt le dossier en comparant en minuscules
        target = name.lower()
        if os.path.isdir(folder):
            for fname in os.listdir(folder):
                if fname.lower() == target:
                    return os.path.join(folder, fname)

        # fichier introuvable
        return None

    @classmethod
    def _load_sprite(cls, type_key):
        """
        Charge le sprite du projectile depuis le disque et le met en cache.
        On distingue deux cas : spritesheet animée (plusieurs frames) ou image statique.
        L'animation d'impact est chargée séparément si le fichier existe.
        """
        # si ce type a déjà été traité (même si rien n'a été trouvé), on ne recharge pas
        if type_key in cls._anim_cache:
            return cls._sprite_cache.get(type_key)

        proj_path   = cls._find_sprite_path(type_key)
        impact_path = cls._find_sprite_path(type_key, "_impact")

        # --- sprite en vol ---
        if proj_path:
            try:
                img = pygame.image.load(proj_path).convert_alpha()
                h = img.get_height()
                # on détermine le nombre de frames en divisant la largeur par la hauteur
                n = img.get_width() // h

                if n > 1:
                    # c'est une spritesheet animée, on crée un animateur dédié
                    cls._anim_cache[type_key] = spr.SpritesheetAnimator(
                        proj_path, fps=12,
                        target_size=(cls.ANIM_SIZE, cls.ANIM_SIZE),
                        loop=True
                    )
                    cls._sprite_cache[type_key] = None
                    print(f"[Projectile] anim chargée : {os.path.basename(proj_path)} ({n} frames)")
                else:
                    # image unique, on garde l'ancien comportement statique
                    surface = pygame.transform.scale(img, (cls.SPRITE_SIZE, cls.SPRITE_SIZE))
                    cls._sprite_cache[type_key] = surface
                    cls._anim_cache[type_key]   = None
                    print(f"[Projectile] sprite statique : {os.path.basename(proj_path)}")

            except Exception as e:
                # en cas d'erreur de chargement, on bascule sur le fallback cercle
                print(f"[Projectile] erreur chargement {type_key}.png : {e}")
                cls._anim_cache[type_key]   = None
                cls._sprite_cache[type_key] = None
        else:
            # aucun fichier trouvé pour ce type, le fallback sera utilisé à l'affichage
            cls._anim_cache[type_key]   = None
            cls._sprite_cache[type_key] = None

        # --- animation d'impact ---
        if impact_path:
            try:
                # l'impact ne boucle pas, il se joue une seule fois puis le projectile disparaît
                cls._impact_cache[type_key] = spr.SpritesheetAnimator(
                    impact_path, fps=14,
                    target_size=(cls.IMPACT_SIZE, cls.IMPACT_SIZE),
                    loop=False
                )
                print(f"[Projectile] impact chargé : {os.path.basename(impact_path)}")
            except Exception as e:
                print(f"[Projectile] erreur chargement impact {type_key} : {e}")
                cls._impact_cache[type_key] = None
        else:
            # pas d'impact visuel pour ce type, le projectile disparaît directement
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

        # déclenche le chargement si ce type n'a pas encore été vu
        self._sprite = Projectile._load_sprite(proj_type)

        # chaque instance reçoit son propre clone de l'animateur
        # pour que les frames soient indépendantes entre projectiles
        master_anim = Projectile._anim_cache.get(proj_type)
        self._anim = spr._clone_animator(master_anim) if master_anim else None

        # l'impact est initialisé à None, il sera créé au moment du contact
        self._impact_anim = None
        self._impacting   = False  # passe à True dès que la cible est touchée
        self._impact_x    = 0.0
        self._impact_y    = 0.0

        # angle de rotation vers la cible, mis à jour à chaque frame
        self._angle = 0.0

    def update(self):
        # si l'impact est en cours, on attend juste que l'animation se termine
        if self._impacting:
            if self._impact_anim:
                self._impact_anim.update()
                # une fois l'animation terminée, le projectile peut être retiré de la liste
                if self._impact_anim.finished:
                    self.alive = False
            else:
                self.alive = False
            return

        # si la cible est déjà morte entre-temps, inutile de continuer
        if not self.alive or self.target.is_dead or self.target._dying:
            self.alive = False
            return

        # avance l'animation en vol
        if self._anim:
            self._anim.update()

        dx   = self.target.x - self.x
        dy   = self.target.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            # on est suffisamment proche pour considérer qu'on a touché la cible
            self.target.receive_damage(self.damage)
            if self.target.hp <= 0:
                self.target.mark_dead()

            # si une animation d'impact est disponible, on l'enclenche
            master_impact = Projectile._impact_cache.get(self.proj_type)
            if master_impact:
                self._impact_anim = spr._clone_animator(master_impact)
                self._impact_anim.reset()
                self._impacting = True
                # on mémorise la position du hit pour afficher l'impact au bon endroit
                self._impact_x  = self.target.x
                self._impact_y  = self.target.y
            else:
                # pas d'impact visuel, suppression immédiate
                self.alive = False
        else:
            # déplacement progressif vers la cible, on met aussi l'angle à jour
            self._angle = -math.degrees(math.atan2(dy, dx))
            self.x += dx/dist * self.speed
            self.y += dy/dist * self.speed

    def draw(self, screen, offset_x, offset_y):
        # pendant l'impact, on affiche l'animation à la position du hit et rien d'autre
        if self._impacting:
            if self._impact_anim:
                frame = self._impact_anim.get_frame()
                if frame:
                    cx = int(self._impact_x) + offset_x
                    cy = int(self._impact_y) + offset_y
                    s  = Projectile.IMPACT_SIZE
                    screen.blit(frame, (cx - s//2, cy - s//2))
            return

        cx = int(self.x) + offset_x
        cy = int(self.y) + offset_y

        if self._anim:
            # on récupère la frame courante et on la fait pointer vers la cible
            frame = self._anim.get_frame()
            if frame:
                angle_off = Projectile.ANGLE_OFFSET.get(self.proj_type, 0)
                rotated   = pygame.transform.rotate(frame, self._angle + angle_off)
                rw, rh    = rotated.get_size()
                screen.blit(rotated, (cx - rw//2, cy - rh//2))

        elif self._sprite is not None:
            # même logique avec le sprite statique (ancien format)
            angle_off = Projectile.ANGLE_OFFSET.get(self.proj_type, 0)
            rotated   = pygame.transform.rotate(self._sprite, self._angle + angle_off)
            rw, rh    = rotated.get_size()
            screen.blit(rotated, (cx - rw//2, cy - rh//2))

        else:
            # aucun sprite disponible, on affiche juste un petit cercle jaune
            pygame.draw.circle(screen, (255, 255, 0), (cx, cy), 4)