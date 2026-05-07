"""
entity_trap.py
--------------
Classe Trap, pièges posés sur la grille.
Contrairement aux tours ils n'ont pas de portée, l'ennemi doit
marcher dessus pour que ça se déclenche.
"""
import os
import pygame
from core.config import (
    GRID_SIZE, COLS, ROWS, SPAWN_ZONE_X, SPAWN_ZONE_Y,
    SPAWN_ZONE_WIDTH, SPAWN_ZONE_HEIGHT, START, END,
    TRAP_DAMAGE_MULT, TRAP_COOLDOWN_MULT,
)
import ui.sprites as spr
from core.entity_helpers import (
    _crop_alpha_surface, _direction_from_delta,
    _ASSETS_BASE, _SCALED_FRAME_CACHE_MAX,
)


class Trap:
    """
    Piège posé sur la grille, invisible pour le pathfinding donc les ennemis
    ne cherchent pas à l'éviter. Se déclenche au contact, pas à portée.

    Sprites dans assets/sprites/traps/ :
        <type>_idle.png    boucle tant que le piège attend un ennemi
        <type>_attack.png  jouée une fois au déclenchement puis retour idle

    La mine a 3 frames dans idle, une par niveau de fusion —
    les spikes ont une vraie animation en boucle.
    """

    _idle_cache   = {}
    _attack_cache = {}
    _anim_cache   = {}  # ancien format, conservé pour les assets pas encore migrés

    @classmethod
    def load_sprites(cls):
        traps_dir = os.path.join(_ASSETS_BASE, "traps")

        for trap_type in ("spikes", "mine"):
            idle_path   = os.path.join(traps_dir, f"{trap_type}_idle.png")
            attack_path = os.path.join(traps_dir, f"{trap_type}_attack.png")

            # idle en boucle, visible en permanence quand le piège attend
            if os.path.isfile(idle_path):
                try:
                    cls._idle_cache[trap_type] = spr.SpritesheetAnimator(
                        idle_path, fps=8, target_size=(GRID_SIZE, GRID_SIZE), loop=True
                    )
                    print(f"[Trap] {trap_type}_idle : {cls._idle_cache[trap_type].n_frames} frames")
                except Exception as e:
                    print(f"[Trap] {trap_type}_idle non chargé : {e}")

            # attack jouée une seule fois quand un ennemi marche dessus
            if os.path.isfile(attack_path):
                try:
                    cls._attack_cache[trap_type] = spr.SpritesheetAnimator(
                        attack_path, fps=12, target_size=(GRID_SIZE, GRID_SIZE), loop=False
                    )
                    print(f"[Trap] {trap_type}_attack : {cls._attack_cache[trap_type].n_frames} frames")
                except Exception as e:
                    print(f"[Trap] {trap_type}_attack non chargé : {e}")

            # si pas d'idle trouvé on tente l'ancien format single-sheet
            if trap_type not in cls._idle_cache:
                path = os.path.join(traps_dir, f"{trap_type}.png")
                if os.path.isfile(path):
                    try:
                        cls._anim_cache[trap_type] = spr.SpritesheetAnimator(
                            path, fps=6, target_size=(GRID_SIZE, GRID_SIZE), loop=True)
                    except Exception as e:
                        print(f"[Trap] fallback {trap_type}.png raté aussi : {e}")

    _level_font = None

    @classmethod
    def _get_level_font(cls):
        if cls._level_font is None:
            cls._level_font = pygame.font.SysFont(None, 16)
        return cls._level_font

    def __init__(self, cells, trap_type="spikes", gacha_level=1, fusion_level=1):
        self.cells        = cells
        self.trap_type    = trap_type
        self.gacha_level  = gacha_level
        self.fusion_level = fusion_level
        self.level        = fusion_level
        self.timer        = 0
        self._attacking   = False

        # position centrale en pixels, utile pour les calculs de distance si besoin
        if cells:
            self.x = sum(c[0] for c in cells)/len(cells) * GRID_SIZE + GRID_SIZE/2
            self.y = sum(c[1] for c in cells)/len(cells) * GRID_SIZE + GRID_SIZE/2
        else:
            self.x = GRID_SIZE/2
            self.y = GRID_SIZE/2

        # chaque piège a son propre clone pour que deux mines posées côte à côte
        # n'explosent pas en même temps visuellement — sinon elles partageraient
        # le même index de frame et avanceraient ensemble
        master_idle = Trap._idle_cache.get(trap_type)
        self._idle_anim = spr._clone_animator(master_idle) if master_idle else None

        # idem pour l'attaque, chaque déclenchement est indépendant
        master_attack = Trap._attack_cache.get(trap_type)
        self._attack_anim = spr._clone_animator(master_attack) if master_attack else None

        # fallback si les deux caches ci-dessus sont vides
        master_legacy = Trap._anim_cache.get(trap_type)
        self._animator = spr._clone_animator(master_legacy) if master_legacy else None

        self.set_stats()

    def set_stats(self, damage_bonus=0, cooldown_bonus=0):
        # +10% de dégâts par niveau de fusion, le niveau gacha augmente la base
        fusion_mult = 1.0 + (self.fusion_level-1)*0.1

        if self.trap_type == "spikes":
            # spikes : dégâts modérés mais cooldown court, efficaces sur les couloirs denses
            # où les ennemis passent souvent — moins utiles en terrain ouvert
            base_damage = 5 + (self.gacha_level-1)*10
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.cooldown = max(60 - (self.gacha_level-1)*15 - cooldown_bonus, 20)

        elif self.trap_type == "mine":
            # mine : peut one-shot les petits ennemis aux niveaux élevés,
            # mais le cooldown est si long qu'elle est peu utile sur un chemin très fréquenté
            # — plutôt à placer sur des embuscades
            base_damage = 30 + (self.gacha_level-1)*20
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.cooldown = max(200 - (self.gacha_level-1)*40 - cooldown_bonus, 60)

        else:
            # type inconnu, stats génériques pour ne pas planter
            base_damage = 10 * self.gacha_level
            raw_damage  = base_damage*fusion_mult + damage_bonus
            self.cooldown = max(50 - (self.gacha_level-1)*10 - cooldown_bonus, 15)

        self.damage       = max(1, int(raw_damage * TRAP_DAMAGE_MULT))
        self._base_damage = self.damage
        self._eren_boosted  = False
        self._armin_boosted = False
        self.cooldown = max(1, int(self.cooldown * TRAP_COOLDOWN_MULT))

        # buffs persistants réappliqués si le héros correspondant est actif sur la map
        if hasattr(self, '_armin_buff_mult') and self._armin_boosted:
            self.damage = int(self._base_damage * self._armin_buff_mult)

    def update(self, enemies, projectiles):
        # les animations avancent ici et pas dans draw — si draw était appelé deux fois
        # dans la même frame (ex: minimap) les animations doubleraient de vitesse
        if self._attacking and self._attack_anim:
            self._attack_anim.update()
            # fin de l'explosion ou de l'animation d'attaque, le piège repasse en veille
            if self._attack_anim.finished:
                self._attacking = False
                self._attack_anim.reset()
        elif self._idle_anim and self.trap_type != "mine":
            # la mine ne boucle pas son idle, sa frame est fixée selon le niveau dans draw
            self._idle_anim.update()
        elif self._animator:
            self._animator.update()

        # piège en recharge, on ne vérifie pas les ennemis
        if self.timer > 0:
            self.timer -= 1
            return

        # set pour que la vérification de cellule soit O(1) même si le piège couvre plusieurs cases
        trap_cells = set(self.cells)
        triggered  = False

        for e in enemies:
            if e.is_dead or e._dying:
                continue
            # get_cell() retourne la cellule du centre de l'ennemi —
            # un ennemi rapide peut donc "sauter" une case et éviter le piège involontairement
            ex, ey = e.get_cell()
            if (ex, ey) in trap_cells:
                e.receive_damage(self.damage)
                # on continue de blesser tous les ennemis présents sur le piège,
                # pas seulement le premier trouvé
                if e.hp <= 0:
                    e.mark_dead()
                triggered = True

        # on déclenche l'animation d'attaque seulement si au moins un ennemi a été touché
        if triggered:
            self.timer = self.cooldown
            if self._attack_anim:
                self._attacking = True
                self._attack_anim.reset()

    def draw(self, screen, offset_x, offset_y):
        if self.trap_type == "mine" and self.cells:
            # la mine occupe potentiellement plusieurs cases mais s'affiche
            # comme un seul sprite centré sur la hitbox globale
            min_cx = min(c[0] for c in self.cells)
            min_cy = min(c[1] for c in self.cells)
            max_cx = max(c[0] for c in self.cells)
            max_cy = max(c[1] for c in self.cells)
            total_w = (max_cx-min_cx+1)*GRID_SIZE
            total_h = (max_cy-min_cy+1)*GRID_SIZE
            # on centre le sprite sur la hitbox globale
            px = offset_x + min_cx*GRID_SIZE + (total_w-GRID_SIZE)//2
            py = offset_y + min_cy*GRID_SIZE + (total_h-GRID_SIZE)//2

            if self._attacking and self._attack_anim:
                frame = self._attack_anim.get_frame()
                if frame:
                    # l'explosion couvre toute la hitbox pour un effet visuel plus impactant
                    scaled = pygame.transform.scale(frame, (total_w, total_h))
                    screen.blit(scaled, (offset_x + min_cx*GRID_SIZE,
                                         offset_y + min_cy*GRID_SIZE))
            elif self._idle_anim:
                # on pointe directement sur la bonne frame selon le niveau de fusion,
                # la mine n'a pas d'animation en boucle — juste 3 visuels différents
                idx = min(self.level-1, self._idle_anim.n_frames-1)
                self._idle_anim._frame_idx = idx
                frame = self._idle_anim.get_frame()
                if frame:
                    screen.blit(frame, (px, py))

        else:
            # les spikes couvrent chaque case indépendamment,
            # un piège 2x1 affiche deux sprites côte à côte
            for cx, cy in self.cells:
                px = offset_x + cx*GRID_SIZE
                py = offset_y + cy*GRID_SIZE

                if self._attacking and self._attack_anim:
                    frame = self._attack_anim.get_frame()
                elif self._idle_anim:
                    frame = self._idle_anim.get_frame()
                elif self._animator:
                    frame = self._animator.get_frame()
                else:
                    frame = None

                if frame:
                    screen.blit(frame, (px, py))

        # jauge bleue sous le piège — donne une info visuelle au joueur
        # sur le temps restant avant que le piège puisse se déclencher à nouveau
        if self.cooldown > 0 and self.cells:
            min_cx = min(c[0] for c in self.cells)
            max_cx = max(c[0] for c in self.cells)
            max_cy = max(c[1] for c in self.cells)
            gauge_x = offset_x + min_cx*GRID_SIZE
            gauge_y = offset_y + max_cy*GRID_SIZE + GRID_SIZE - 5
            gauge_w = (max_cx-min_cx+1)*GRID_SIZE

            pygame.draw.rect(screen, (50, 50, 70), (gauge_x, gauge_y, gauge_w, 4), border_radius=2)
            # ratio 1.0 = rechargé et prêt, 0.0 = vient juste de se déclencher
            ratio  = 1.0 - (self.timer/self.cooldown) if self.timer > 0 else 1.0
            fill_w = int(gauge_w*ratio)
            if fill_w > 0:
                pygame.draw.rect(screen, (60, 160, 255),
                                 (gauge_x, gauge_y, fill_w, 4), border_radius=2)

        # indicateur de niveau affiché uniquement à partir du niveau 2,
        # le niveau 1 est considéré comme l'état par défaut donc pas besoin de le montrer
        if self.level > 1 and self.cells:
            lvl_font = Trap._get_level_font()
            lbl = lvl_font.render(f"L{self.level}", True, (255, 255, 255))
            sx = offset_x + self.cells[0][0]*GRID_SIZE
            sy = offset_y + self.cells[0][1]*GRID_SIZE
            screen.blit(lbl, (sx+4, sy+2))