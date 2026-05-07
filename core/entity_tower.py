"""
entity_tower.py
---------------
Classe Tower — gère le placement, les stats, l'animation et le tir automatique des tours.
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
from core.entity_projectile import Projectile


class Tower:
    """Tour placée sur la grille, tir automatique sur les ennemis à portée."""

    # couleurs utilisées pour le cercle de portée et le fallback visuel
    TYPE_COLORS = {
        "small":  (0, 150, 200),
        "big":    (0, 100, 180),
        "sniper": (230, 180, 60),
        "mortar": (180, 90,  50),
        "frost":  (120, 200, 255),
        "tesla":  (120, 180, 250),
        "cannon": (140, 90, 30),
        "laser":  (180, 60, 180),
    }

    # un seul animateur maître par type, cloné à chaque instanciation
    _anim_cache = {}
    _scaled_frame_cache = {}

    # Système base + arme par niveau :
    #   assets/sprites/towers/<type>_base.png       spritesheet 1 frame par niveau (3 frames)
    #   assets/sprites/towers/<type>_weapon_1.png   arme animée niveau 1
    #   assets/sprites/towers/<type>_weapon_2.png   arme animée niveau 2
    #   assets/sprites/towers/<type>_weapon_3.png   arme animée niveau 3
    # Si ces fichiers sont absents, on retombe sur <type>.png (ancien système).
    _base_cache   = {}   # {tower_type: [surf_lvl1, surf_lvl2, surf_lvl3]}
    _weapon_cache = {}   # {tower_type: {1: animator, 2: animator, 3: animator}}

    @classmethod
    def _build_tower_asset_map(cls):
        """Construit un dictionnaire type → chemin PNG pour les tours connues."""
        towers_dir = os.path.join(_ASSETS_BASE, "towers")
        mapping = {}
        if not os.path.isdir(towers_dir):
            return mapping
        # on ne liste que les types déclarés dans TYPE_COLORS
        for tower_type in cls.TYPE_COLORS:
            path = os.path.join(towers_dir, f"{tower_type}.png")
            if os.path.isfile(path):
                mapping[tower_type] = path
        return mapping

    @classmethod
    def load_sprites(cls):
        """
        Charge tous les sprites de tours au démarrage.
        On tente d'abord le système base+arme (nouveau format),
        et on bascule sur le système classique si les fichiers sont absents.

        Système base+arme :
            <type>_base.png      spritesheet avec 1 frame par niveau de fusion
            <type>_weapon_N.png  arme animée pour le niveau N (1 à 3)

        Système classique (fallback) :
            <type>.png           spritesheet animée unique
        """
        towers_dir = os.path.join(_ASSETS_BASE, "towers")

        for tower_type in cls.TYPE_COLORS:
            base_path = os.path.join(towers_dir, f"{tower_type}_base.png")

            if os.path.isfile(base_path):
                print(f"[Tower] chargement base+weapon pour : {tower_type}")

                # --- chargement de la base statique ---
                # la spritesheet contient 3 frames (une par niveau de fusion)
                try:
                    base_sheet = pygame.image.load(base_path).convert_alpha()
                    bw = base_sheet.get_width()
                    bh = base_sheet.get_height()
                    fw = bw // 3  # largeur d'une frame = largeur totale / 3 niveaux

                    levels = []
                    for i in range(3):
                        frame = base_sheet.subsurface(pygame.Rect(i*fw, 0, fw, bh)).copy()
                        levels.append(frame)
                    cls._base_cache[tower_type] = levels

                except Exception as e:
                    print(f"[entities] impossible de charger {tower_type}_base.png : {e}")

                # --- chargement des armes par niveau ---
                weapons = {}
                for lvl in range(1, 4):
                    wp = os.path.join(towers_dir, f"{tower_type}_weapon_{lvl}.png")
                    if os.path.isfile(wp):
                        try:
                            anim = spr.SpritesheetAnimator(
                                wp, fps=8,
                                target_size=(GRID_SIZE*2, GRID_SIZE*2),
                                loop=True
                            )
                            weapons[lvl] = anim
                            print(f"[Tower] {tower_type}_weapon_{lvl} : {anim.n_frames} frames OK")
                        except Exception as e:
                            print(f"[Tower] erreur {tower_type}_weapon_{lvl} : {e}")
                    else:
                        print(f"[Tower] {tower_type}_weapon_{lvl}.png introuvable")

                if weapons:
                    cls._weapon_cache[tower_type] = weapons
                    print(f"[Tower] {tower_type} : {len(weapons)} weapon(s) chargée(s)")
                else:
                    # base chargée mais aucune arme — on continue quand même
                    print(f"[Tower] {tower_type}_base OK mais aucune weapon trouvée")

            else:
                # --- fallback système classique ---
                # un seul fichier PNG avec toutes les frames d'animation
                path = os.path.join(towers_dir, f"{tower_type}.png")
                if os.path.isfile(path):
                    try:
                        cls._anim_cache[tower_type] = spr.SpritesheetAnimator(
                            path, fps=6,
                            target_size=(GRID_SIZE, GRID_SIZE),
                            loop=True
                        )
                    except Exception as e:
                        print(f"[entities] impossible de charger {tower_type}.png : {e}")

    # police mise en cache au niveau de la classe pour éviter de la recréer à chaque draw
    _level_font = None

    @classmethod
    def _get_level_font(cls):
        """Retourne la police pour afficher le niveau, créée une seule fois."""
        if cls._level_font is None:
            cls._level_font = pygame.font.SysFont(None, 18)
        return cls._level_font

    # nombre de frames avant le tir où l'animation de l'arme démarre
    WINDUP_FRAMES = 30

    def __init__(self, cells, tower_type, gacha_level=1, fusion_level=1):
        self.cells        = cells
        self.tower_type   = tower_type
        self.gacha_level  = gacha_level
        self.fusion_level = fusion_level
        self.level        = fusion_level  # utilisé pour l'affichage visuel
        self.timer        = 0

        # position centrale en pixels, calculée à partir des cellules occupées
        if cells:
            self.x = sum(c[0] for c in cells)/len(cells) * GRID_SIZE + GRID_SIZE/2
            self.y = sum(c[1] for c in cells)/len(cells) * GRID_SIZE + GRID_SIZE/2
        else:
            self.x = GRID_SIZE/2
            self.y = GRID_SIZE/2

        # animateur pour le système classique (fallback)
        master = Tower._anim_cache.get(tower_type)
        self._animator = spr._clone_animator(master) if master else None

        # état de l'animation d'arme
        self._weapon_anim     = None
        self._attacking       = False   # True uniquement pendant l'animation de tir
        self._target_in_range = False   # True si un ennemi est actuellement à portée
        self._refresh_weapon_anim()

        # calcul de l'emprise en pixels pour scaler le sprite sur toutes les cellules
        if cells:
            min_cx = min(c[0] for c in cells)
            min_cy = min(c[1] for c in cells)
            max_cx = max(c[0] for c in cells)
            max_cy = max(c[1] for c in cells)
        else:
            min_cx = min_cy = max_cx = max_cy = 0
        
        self._fp_x = min_cx
        self._fp_y = min_cy
        self._fp_w = (max_cx - min_cx + 1) * GRID_SIZE
        self._fp_h = (max_cy - min_cy + 1) * GRID_SIZE

        # légère réduction pour laisser une marge visuelle autour de la tour
        self._render_w  = max(1, int(self._fp_w*0.94))
        self._render_h  = max(1, int(self._fp_h*0.94))
        self._render_dx = (self._fp_w - self._render_w)//2
        self._render_dy = (self._fp_h - self._render_h)//2

        self.set_stats()

    def _refresh_weapon_anim(self):
        """
        Met à jour l'animateur de l'arme selon le niveau de fusion actuel.
        Si le niveau exact n'est pas disponible, on prend le niveau inférieur le plus proche.
        """
        weapons = Tower._weapon_cache.get(self.tower_type)
        if not weapons:
            self._weapon_anim = None
            return

        # on descend depuis le niveau actuel jusqu'à trouver une arme disponible
        lvl = self.level
        while lvl >= 1:
            master = weapons.get(lvl)
            if master:
                self._weapon_anim = spr._clone_animator(master)
                return
            lvl -= 1

        # aucune arme trouvée pour ce type
        self._weapon_anim = None

    def set_stats(self, damage_bonus=0, cooldown_bonus=0):
        """
        Calcule les stats de la tour en fonction du type, du niveau gacha et du niveau fusion.
        Le niveau fusion applique un multiplicateur de +10% par niveau au-dessus de 1.
        """
        # multiplicateur de fusion : +10% par niveau au-delà du niveau 1
        fusion_mult = 1.0 + (self.fusion_level - 1)*0.1

        if self.tower_type == "small":
            base_damage = 5 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (3*GRID_SIZE + (self.gacha_level-1)*8) * fusion_mult
            self.cooldown = max(38 - (self.gacha_level-1)*4 - cooldown_bonus, 8)

        elif self.tower_type == "big":
            base_damage = 8 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (5*GRID_SIZE + (self.gacha_level-1)*12) * fusion_mult
            self.cooldown = max(72 - (self.gacha_level-1)*9 - cooldown_bonus, 14)

        elif self.tower_type == "sniper":
            # portée maximale, cadence faible — conçue pour les cibles éloignées
            base_damage = 10 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (7*GRID_SIZE + (self.gacha_level-1)*10) * fusion_mult
            self.cooldown = max(110 - (self.gacha_level-1)*12 - cooldown_bonus, 15)

        elif self.tower_type == "mortar":
            base_damage = 9 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (6*GRID_SIZE + (self.gacha_level-1)*10) * fusion_mult
            self.cooldown = max(90 - (self.gacha_level-1)*11 - cooldown_bonus, 14)

        elif self.tower_type == "frost":
            # dégâts faibles mais ralentit les ennemis
            base_damage = 4 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (4*GRID_SIZE + (self.gacha_level-1)*7) * fusion_mult
            self.cooldown = max(78 - (self.gacha_level-1)*9 - cooldown_bonus, 12)

        elif self.tower_type == "tesla":
            base_damage = 7 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (5*GRID_SIZE + (self.gacha_level-1)*7) * fusion_mult
            self.cooldown = max(58 - (self.gacha_level-1)*8 - cooldown_bonus, 12)

        elif self.tower_type == "cannon":
            base_damage = 9 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (5*GRID_SIZE + (self.gacha_level-1)*8) * fusion_mult
            self.cooldown = max(82 - (self.gacha_level-1)*10 - cooldown_bonus, 14)

        elif self.tower_type == "laser":
            # tour la plus puissante, cooldown élevé
            base_damage = 12 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (6*GRID_SIZE + (self.gacha_level-1)*9) * fusion_mult
            self.cooldown = max(102 - (self.gacha_level-1)*13 - cooldown_bonus, 14)

        else:
            # type inconnu, stats par défaut
            base_damage = 4 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.range    = (4*GRID_SIZE + (self.gacha_level-1)*7) * fusion_mult
            self.cooldown = max(44 - (self.gacha_level-1)*7 - cooldown_bonus, 10)

        # application des multiplicateurs globaux définis dans la config
        self.damage        = max(1, int(raw_damage * TOWER_DAMAGE_MULT))
        self._base_damage  = self.damage
        self._eren_boosted  = False
        self._armin_boosted = False
        self.range    = max(1, int(self.range * TOWER_RANGE_MULT))
        self.cooldown = max(1, int(self.cooldown * TOWER_COOLDOWN_MULT))

        # on recharge l'arme si le niveau a changé depuis la dernière fois
        if hasattr(self, '_weapon_anim'):
            self._refresh_weapon_anim()

        # réapplication des buffs persistants si nécessaire
        if hasattr(self, '_armin_buff_mult') and self._armin_boosted:
            self.damage = int(self._base_damage * self._armin_buff_mult)

    def update(self, enemies, projectiles):
        # mise à jour de l'animateur classique s'il existe
        if self._animator:
            self._animator.update()

        # l'arme n'est animée que pendant la phase d'attaque
        if self._weapon_anim:
            if self._attacking:
                self._weapon_anim.update()
                # fin du cycle d'attaque → retour en idle, on reboucle
                if self._weapon_anim.finished:
                    self._attacking = False
                    self._weapon_anim.reset()
                    self._weapon_anim.loop = True

        if self.timer > 0:
            self.timer -= 1

            # windup : on lance l'animation WINDUP_FRAMES avant le tir effectif
            # pour que le mouvement de l'arme soit visible avant l'impact
            if (self._weapon_anim and not self._attacking
                    and self.timer <= Tower.WINDUP_FRAMES):
                range_sq = self.range*self.range
                for e in enemies:
                    if e.is_dead or e._dying:
                        continue
                    dx = self.x - e.x
                    dy = self.y - e.y
                    if dx*dx + dy*dy <= range_sq:
                        # un ennemi est encore à portée, on démarre le windup
                        self._attacking = True
                        self._weapon_anim.reset()
                        self._weapon_anim.loop = False
                        break
            return

        # timer écoulé, on cherche un ennemi à portée pour tirer
        range_sq = self.range*self.range
        for e in enemies:
            if e.is_dead or e._dying:
                continue
            dx = self.x - e.x
            dy = self.y - e.y
            if dx*dx + dy*dy <= range_sq:
                projectiles.append(Projectile(
                    self.x, self.y, e, self.damage, proj_type=self.tower_type
                ))
                self.timer = self.cooldown

                # si le windup n'a pas déjà lancé l'animation, on le fait maintenant
                if self._weapon_anim and not self._attacking:
                    self._attacking = True
                    self._weapon_anim.reset()
                    self._weapon_anim.loop = False
                break  # une seule cible par cycle de tir

    def draw(self, screen, offset_x, offset_y):
        color = self.TYPE_COLORS.get(self.tower_type, (120, 120, 120))
        bx = offset_x + self._fp_x*GRID_SIZE + self._render_dx
        by = offset_y + self._fp_y*GRID_SIZE + self._render_dy

        # on détermine si on utilise le nouveau système ou le fallback
        has_base_weapon = (self.tower_type in Tower._base_cache
                           or self.tower_type in Tower._weapon_cache)

        if has_base_weapon:
            # --- système base + arme ---

            # 1. base statique : on choisit la frame selon le niveau de fusion
            bases = Tower._base_cache.get(self.tower_type, [])
            if bases:
                idx = min(self.level - 1, len(bases) - 1)
                base_surf = bases[idx]

                # la base est légèrement plus grande que la hitbox et décalée vers le haut
                draw_w = int(self._render_w*1.15)
                draw_h = int(self._render_h*1.15)
                base_scaled = pygame.transform.scale(base_surf, (draw_w, draw_h))
                draw_x = bx - (draw_w - self._render_w)//2
                draw_y = by - (draw_h - self._render_h)  # décalage vers le haut
                screen.blit(base_scaled, (draw_x, draw_y))

            # 2. arme centrée sur la hitbox, légèrement remontée
            if self._weapon_anim:
                w_frame = self._weapon_anim.get_frame()
                if w_frame:
                    sq = min(self._render_w, self._render_h)
                    cx = bx + (self._render_w - sq)//2
                    cy = by + (self._render_h - sq)//2 - 10
                    w_scaled = pygame.transform.scale(w_frame, (sq, sq))
                    screen.blit(w_scaled, (cx, cy))

        elif self._animator:
            # --- fallback système classique ---
            frame = self._animator.get_frame()
            if frame:
                # mise en cache des frames scalées pour éviter de rescaler à chaque draw
                if frame.get_size() != (self._render_w, self._render_h):
                    key = (self.tower_type, self._render_w, self._render_h,
                           self._animator._frame_idx)
                    cached = Tower._scaled_frame_cache.get(key)
                    if cached is None:
                        cropped = _crop_alpha_surface(frame)
                        cached  = pygame.transform.scale(cropped, (self._render_w, self._render_h))
                        # on évite que le cache grossisse indéfiniment
                        if len(Tower._scaled_frame_cache) >= _SCALED_FRAME_CACHE_MAX:
                            oldest = next(iter(Tower._scaled_frame_cache))
                            del Tower._scaled_frame_cache[oldest]
                        Tower._scaled_frame_cache[key] = cached
                    frame = cached
                screen.blit(frame, (bx, by))

        # cercle de portée toujours affiché, plus un indicateur de niveau si > 1
        radius = int(self.range)
        pygame.draw.circle(screen, color,
                           (int(self.x)+offset_x, int(self.y)+offset_y), radius, 1)

        if self.level > 1:
            # second cercle intérieur pour indiquer visuellement un niveau supérieur
            pygame.draw.circle(screen, (255, 255, 255),
                               (int(self.x)+offset_x, int(self.y)+offset_y),
                               radius - 10, 1)
            lvl_font = Tower._get_level_font()
            lbl = lvl_font.render(f"L{self.level}", True, (255, 255, 255))
            screen.blit(lbl, (int(self.x)+offset_x - lbl.get_width()//2,
                               int(self.y)+offset_y - lbl.get_height()//2))