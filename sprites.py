"""
sprites.py
----------
Moteur d'animation par sprites pour Hexahold.

"""

import os
import glob
import pygame

# Vitesses d'animation (frames par seconde de jeu à 60 fps)
ANIM_FPS_WALK   = 8
ANIM_FPS_ATTACK = 10
ANIM_FPS_IDLE   = 5
ANIM_FPS_HURT   = 12
ANIM_FPS_DEATH  = 6


# ============================================================
# FORMAT A : Spritesheet horizontale
# ============================================================

class SpritesheetAnimator:
    """
    Lit une spritesheet horizontale (frames carrées côte à côte).
    La hauteur de l'image = côté d'une frame.

    Paramètres :
        path        : chemin vers le fichier PNG
        fps         : vitesse de défilement (frames d'animation par seconde)
        target_size : tuple (w, h) de rendu — la frame est mise à l'échelle
        loop        : True = boucle continue, False = s'arrête sur la dernière frame
    """

    def __init__(self, path, fps=8, target_size=(32, 32), loop=True):
        self.loop        = loop
        self.fps         = fps
        self.target_size = target_size
        self._timer      = 0.0      # accumulateur en frames de jeu
        self._frame_idx  = 0
        self.finished    = False    # True quand loop=False et dernière frame atteinte

        sheet = pygame.image.load(path).convert_alpha()
        sh, sw = sheet.get_height(), sheet.get_width()
        frame_w = sh                        # frames carrées
        n       = sw // frame_w

        raw_frames = []
        for i in range(n):
            rect  = pygame.Rect(i * frame_w, 0, frame_w, sh)
            frame = sheet.subsurface(rect).copy()
            if target_size != (frame_w, sh):
                frame = pygame.transform.scale(frame, target_size)
            raw_frames.append(frame)

        self._frames      = raw_frames
        self._frames_flip = [pygame.transform.flip(f, True, False) for f in raw_frames]

    @property
    def n_frames(self):
        return len(self._frames)

    def reset(self):
        self._timer     = 0.0
        self._frame_idx = 0
        self.finished   = False

    def update(self):
        """Avance d'une frame de jeu (appelé chaque tick à 60 fps)."""
        if self.finished:
            return
        ticks_per_frame = 60.0 / self.fps
        self._timer += 1
        if self._timer >= ticks_per_frame:
            self._timer -= ticks_per_frame
            self._frame_idx += 1
            if self._frame_idx >= len(self._frames):
                if self.loop:
                    self._frame_idx = 0
                else:
                    self._frame_idx = len(self._frames) - 1
                    self.finished   = True

    def get_frame(self, flip_h=False):
        """Retourne la surface pygame de la frame courante."""
        frames = self._frames_flip if flip_h else self._frames
        return frames[self._frame_idx]


# ============================================================
# FORMAT B : PNG séquentiels (Wraith)
# ============================================================

class SequenceAnimator:
    """
    Charge un ensemble de PNG numérotés depuis un dossier ou une liste de chemins.
    Chaque image est croppée à son contenu non-transparent puis mise à l'échelle.

    Paramètres :
        paths       : liste de chemins PNG triés (un par frame)
        fps         : vitesse d'animation
        target_size : tuple (w, h) de rendu
        loop        : True = boucle, False = s'arrête
    """

    def __init__(self, paths, fps=8, target_size=(64, 64), loop=True):
        self.loop        = loop
        self.fps         = fps
        self.target_size = target_size
        self._timer      = 0.0
        self._frame_idx  = 0
        self.finished    = False

        self._frames = []
        for p in paths:
            raw   = pygame.image.load(p).convert_alpha()
            frame = self._crop_and_scale(raw, target_size)
            self._frames.append(frame)
            # flip horizontal
        self._frames_flip = [pygame.transform.flip(f, True, False) for f in self._frames]

    @staticmethod
    def _crop_and_scale(surface, target_size):
        """
        Rogne la surface à son contenu non-transparent (bounding box alpha)
        puis met à l'échelle vers target_size.
        """
        # Utilise pygame.surfarray pour trouver la bbox des pixels non-transparents
        arr = pygame.surfarray.array_alpha(surface)  # (w, h)
        # Colonnes et lignes avec au moins un pixel visible
        col_mask = arr.max(axis=1) > 10   # par colonne (x)
        row_mask = arr.max(axis=0) > 10   # par ligne (y)

        if not col_mask.any() or not row_mask.any():
            # Surface vide — on retourne juste une surface vide mise à l'échelle
            return pygame.transform.scale(surface, target_size)

        x_min = int(col_mask.argmax())
        x_max = int(len(col_mask) - col_mask[::-1].argmax() - 1)
        y_min = int(row_mask.argmax())
        y_max = int(len(row_mask) - row_mask[::-1].argmax() - 1)

        w = max(1, x_max - x_min + 1)
        h = max(1, y_max - y_min + 1)

        # Crop via subsurface
        rect    = pygame.Rect(x_min, y_min, w, h)
        cropped = surface.subsurface(rect).copy()
        return pygame.transform.scale(cropped, target_size)

    @property
    def n_frames(self):
        return len(self._frames)

    def reset(self):
        self._timer     = 0.0
        self._frame_idx = 0
        self.finished   = False

    def update(self):
        if self.finished:
            return
        ticks_per_frame = 60.0 / self.fps
        self._timer += 1
        if self._timer >= ticks_per_frame:
            self._timer -= ticks_per_frame
            self._frame_idx += 1
            if self._frame_idx >= len(self._frames):
                if self.loop:
                    self._frame_idx = 0
                else:
                    self._frame_idx = len(self._frames) - 1
                    self.finished   = True

    def get_frame(self, flip_h=False):
        frames = self._frames_flip if flip_h else self._frames
        return frames[self._frame_idx]


# ============================================================
# FORMAT C : Frames pygame directes (pour RPG Maker sheet)
# ============================================================

class _DirectFrameAnimator:
    """
    Animateur qui recoit directement une liste de surfaces pygame.
    Meme interface que SpritesheetAnimator.
    """

    def __init__(self, frames, fps=8, loop=True):
        self.loop         = loop
        self.fps          = fps
        self.target_size  = frames[0].get_size() if frames else (64, 64)
        self._timer       = 0.0
        self._frame_idx   = 0
        self.finished     = False
        self._frames      = frames
        self._frames_flip = [pygame.transform.flip(f, True, False) for f in frames]

    @property
    def n_frames(self):
        return len(self._frames)

    def reset(self):
        self._timer     = 0.0
        self._frame_idx = 0
        self.finished   = False

    def update(self):
        if self.finished:
            return
        ticks_per_frame = 60.0 / self.fps
        self._timer += 1
        if self._timer >= ticks_per_frame:
            self._timer -= ticks_per_frame
            self._frame_idx += 1
            if self._frame_idx >= len(self._frames):
                if self.loop:
                    self._frame_idx = 0
                else:
                    self._frame_idx = len(self._frames) - 1
                    self.finished   = True

    def get_frame(self, flip_h=False):
        frames = self._frames_flip if flip_h else self._frames
        return frames[self._frame_idx]


# ============================================================
# SPRITESET : regroupe les animations d'une entité
# ============================================================

class SpriteSet:
    """
    Conteneur d'animations pour une entité.
    Gère la transition entre états et la direction de flip.

    États reconnus : 'idle', 'walk', 'attack', 'hurt', 'death'
    Directions     : 'down' (S), 'up' (U), 'right' (D), 'left' (flip D)

    Utilisation :
        ss = SpriteSet.from_roguelike_folder(path, size)
        ss.set_state('walk', direction='down')
        ss.update()
        frame = ss.get_frame()
    """

    def __init__(self):
        # {(state, direction): animator}
        self._anims   = {}
        self._current = None     # clé active
        self._state   = 'idle'
        self._dir     = 'down'
        self._flip    = False

    def add(self, state, direction, animator):
        self._anims[(state, direction)] = animator

    def _resolve_key(self, state, direction):
        """
        Cherche la clé (state, direction) disponible.
        Fallback : 'down' si la direction exacte n'existe pas.
        """
        if (state, direction) in self._anims:
            return (state, direction), False
        if direction == 'left' and (state, 'right') in self._anims:
            return (state, 'right'), True     # flip horizontal
        if (state, 'down') in self._anims:
            return (state, 'down'), False
        # Dernier recours : premier disponible
        for k in self._anims:
            if k[0] == state:
                return k, False
        return None, False

    def set_state(self, state, direction=None, force_reset=False):
        """
        Change l'état et/ou la direction.
        Ne remet pas à zéro l'animation si l'état ne change pas (sauf force_reset).
        """
        direction = direction or self._dir
        key, flip = self._resolve_key(state, direction)
        if key is None:
            return

        changed = (key != self._current) or force_reset
        self._current = key
        self._state   = state
        self._dir     = direction
        self._flip    = flip

        if changed:
            self._anims[key].reset()

    def update(self):
        if self._current and self._current in self._anims:
            self._anims[self._current].update()

    def is_finished(self):
        """Vrai si l'animation courante est non-bouclée et terminée."""
        if self._current and self._current in self._anims:
            return self._anims[self._current].finished
        return False

    def get_frame(self):
        if self._current and self._current in self._anims:
            return self._anims[self._current].get_frame(flip_h=self._flip)
        return None

    def set_walk_speed(self, speed, base_speed=1.0):
        """
        Ajuste le fps de tous les animateurs 'walk' proportionnellement à la vitesse.
        Appeler chaque frame depuis le update() du personnage.
          speed      : vitesse actuelle du personnage
          base_speed : vitesse de référence (celle pour laquelle ANIM_FPS_WALK est calibré)
        """
        ratio = max(0.2, speed / max(0.01, base_speed))
        new_fps = ANIM_FPS_WALK * ratio
        for (state, _dir), anim in self._anims.items():
            if state == 'walk':
                anim.fps = new_fps

    # ------------------------------------------------------------------
    # Constructeurs de factory
    # ------------------------------------------------------------------

    @classmethod
    def from_rpgmaker_sheet(cls, path, target_size=(64, 64)):
        """
        Charge une spritesheet RPG Maker VX Ace / MV format 3 cols x 4 rows.

        Layout :
            Row 0 : bas    (down)
            Row 1 : gauche (left)
            Row 2 : droite (right)
            Row 3 : haut   (up)

        Chaque row a 3 frames : [walk_L, idle, walk_R]
        """
        import pygame as _pg

        sheet = _pg.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()
        fw = sw // 3
        fh = sh // 4

        # Rend le fond noir/quasi-noir transparent
        arr = _pg.surfarray.pixels3d(sheet)
        alp = _pg.surfarray.pixels_alpha(sheet)
        mask = (arr[:,:,0].astype(int) < 15) & \
               (arr[:,:,1].astype(int) < 15) & \
               (arr[:,:,2].astype(int) < 15)
        alp[mask] = 0
        del arr, alp

        def get_frame(col, row):
            surf = sheet.subsurface(
                _pg.Rect(col * fw, row * fh, fw, fh)
            ).copy()
            return _pg.transform.scale(surf, target_size)

        ss = cls()

        ROW_MAP = {
            0: ('down',  'S'),
            1: ('left',  'L'),
            2: ('right', 'D'),
            3: ('up',    'U'),
        }

        for row, (direction, _code) in ROW_MAP.items():
            walk_l = get_frame(0, row)
            idle   = get_frame(1, row)
            walk_r = get_frame(2, row)

            # Walk : 3 frames en boucle
            walk_anim = _DirectFrameAnimator(
                [walk_l, idle, walk_r], fps=ANIM_FPS_WALK, loop=True
            )
            ss.add('walk', direction, walk_anim)

            # Idle : frame centrale en boucle lente
            idle_anim = _DirectFrameAnimator(
                [idle], fps=ANIM_FPS_IDLE, loop=True
            )
            ss.add('idle', direction, idle_anim)

            # Hurt : flash rapide sur la frame idle
            hurt_anim = _DirectFrameAnimator(
                [idle], fps=ANIM_FPS_HURT, loop=False
            )
            ss.add('hurt', direction, hurt_anim)

            # Attack : 3 frames
            attack_anim = _DirectFrameAnimator(
                [walk_l, idle, walk_r], fps=ANIM_FPS_ATTACK, loop=False
            )
            ss.add('attack', direction, attack_anim)

            # Death : fondu sur idle
            death_anim = _DirectFrameAnimator(
                [idle], fps=ANIM_FPS_DEATH, loop=False
            )
            ss.add('death', direction, death_anim)

        ss.set_state('idle', 'down')
        return ss

    @classmethod
    def from_roguelike_folder(cls, folder, target_size=(32, 32)):
        """
        Charge un jeu de sprites roguelike depuis un dossier.
        Nommage attendu : {D|S|U}_{Attack|Walk|Idle|Death|Hurt}.png

        Mapping directions :
            S → 'down'
            U → 'up'
            D → 'right'  (left = flip automatique)
        """
        ss  = cls()
        MAP = {
            'S': 'down',
            'U': 'up',
            'D': 'right',
        }
        ANIM_MAP = {
            'Attack': ('attack', ANIM_FPS_ATTACK, False),
            'Walk':   ('walk',   ANIM_FPS_WALK,   True),
            'Idle':   ('idle',   ANIM_FPS_IDLE,   True),
            'Death':  ('death',  ANIM_FPS_DEATH,  False),
            'Hurt':   ('hurt',   ANIM_FPS_HURT,   False),
        }

        for fname in os.listdir(folder):
            if not fname.endswith('.png'):
                continue
            parts = fname[:-4].split('_')   # "S_Attack" → ['S', 'Attack']
            if len(parts) != 2:
                continue
            dir_code, anim_name = parts
            if dir_code not in MAP or anim_name not in ANIM_MAP:
                continue

            direction            = MAP[dir_code]
            state, fps, loop     = ANIM_MAP[anim_name]
            path                 = os.path.join(folder, fname)
            anim = SpritesheetAnimator(path, fps=fps, target_size=target_size, loop=loop)
            ss.add(state, direction, anim)

        # Ajoute 'left' via flip de 'right' pour walk et attack
        for state in ('walk', 'attack', 'idle', 'hurt', 'death'):
            if (state, 'right') in ss._anims and (state, 'left') not in ss._anims:
                # Le flip est géré automatiquement par _resolve_key
                pass

        ss.set_state('idle', 'down')
        return ss

    @classmethod
    def from_sequence_folder(cls, folder, prefix, target_size=(64, 64)):
        """
        Charge un jeu de sprites Wraith (PNG séquentiels) depuis un dossier.
        Structure attendue :
            folder/Attacking/prefix_Attack_000.png ...
            folder/Walking/prefix_Moving Forward_000.png ...
            folder/Idle Blink/prefix_Idle Blinking_000.png ...
            folder/Dying/prefix_Dying_000.png ...
            folder/Hurt/prefix_Hurt_000.png ...

        Tous les wraithes sont orientés face au joueur → direction 'down' uniquement.
        """
        ss = cls()

        def load_seq(subdir, state, fps, loop):
            pattern = os.path.join(folder, subdir, '*.png')
            paths   = sorted(glob.glob(pattern))
            if paths:
                anim = SequenceAnimator(paths, fps=fps, target_size=target_size, loop=loop)
                ss.add(state, 'down', anim)

        load_seq('Attacking',   'attack', ANIM_FPS_ATTACK, False)
        load_seq('Walking',     'walk',   ANIM_FPS_WALK,   True)
        load_seq('Idle Blink',  'idle',   ANIM_FPS_IDLE,   True)
        load_seq('Dying',       'death',  ANIM_FPS_DEATH,  False)
        load_seq('Hurt',        'hurt',   ANIM_FPS_HURT,   False)

        ss.set_state('idle', 'down')
        return ss


# ============================================================
# CHARGEMENT GLOBAL (appelé une seule fois depuis main.py)
# ============================================================

# Cache global pour éviter de recharger les sprites à chaque ennemi spawné
_cache = {}

def load_spriteset(entity_type, assets_base):
    """
    Retourne un SpriteSet pré-chargé pour le type d'entité donné.
    Le cache évite les re-lectures disque.

    entity_type : 'player' | 'enemy_normal' | 'enemy_fast' | 'boss' | 'boss_final'
    assets_base : chemin absolu vers le dossier assets/sprites/

    Retourne None si les assets sont introuvables (le jeu continue sans sprite).
    """
    if entity_type in _cache:
        # Clone léger — on recrée un SpriteSet pointant sur les mêmes surfaces
        # (les surfaces pygame sont déjà en mémoire vidéo, pas de copie pixel)
        return _clone_spriteset(_cache[entity_type])

    folder = os.path.join(assets_base, entity_type)
    if not os.path.isdir(folder):
        return None

    try:
        if entity_type in ('enemy_normal', 'enemy_fast'):
            size = (52, 52)
            ss   = SpriteSet.from_roguelike_folder(folder, target_size=size)
        elif entity_type == 'player':
            size = (40, 40)
            pngs = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
            rpgmaker_sheet = [f for f in pngs
                              if not any(f.startswith(p)
                                         for p in ('S_','D_','U_','L_','N_'))]
            if rpgmaker_sheet:
                sheet_path = os.path.join(folder, rpgmaker_sheet[0])
                ss = SpriteSet.from_rpgmaker_sheet(sheet_path, target_size=size)
            else:
                ss = SpriteSet.from_roguelike_folder(folder, target_size=size)
            return ss  # pas de cache - change selon le heros
        elif entity_type == 'boss':
            ss = SpriteSet.from_sequence_folder(
                folder,
                prefix='Wraith_01',
                target_size=(68, 68),
            )
        elif entity_type == 'boss_final':
            ss = SpriteSet.from_sequence_folder(
                folder,
                prefix='Wraith_03',
                target_size=(76, 76),
            )
        else:
            return None

        _cache[entity_type] = ss
        return _clone_spriteset(ss)

    except Exception as e:
        print(f"[sprites] Impossible de charger '{entity_type}': {e}")
        return None


def _clone_spriteset(source):
    """
    Crée un nouveau SpriteSet qui partage les mêmes objets animator
    mais avec son propre état (frame_idx, timer, state).

    Les surfaces pygame (frames) sont partagées — aucune copie mémoire.
    Les animateurs sont ré-instanciés avec les mêmes listes de surfaces.
    """
    ss = SpriteSet()
    for (state, direction), anim in source._anims.items():
        clone = _clone_animator(anim)
        ss._anims[(state, direction)] = clone
        # Régénère aussi les flips (déjà dans les listes partagées)
    ss.set_state('idle', 'down')
    return ss


def _clone_animator(anim):
    """Cree une copie legere d'un animator avec etat reinitialise."""
    if isinstance(anim, SpritesheetAnimator):
        clone                 = object.__new__(SpritesheetAnimator)
        clone.loop            = anim.loop
        clone.fps             = anim.fps
        clone.target_size     = anim.target_size
        clone._timer          = 0.0
        clone._frame_idx      = 0
        clone.finished        = False
        clone._frames         = anim._frames
        clone._frames_flip    = anim._frames_flip
    elif isinstance(anim, _DirectFrameAnimator):
        clone                 = object.__new__(_DirectFrameAnimator)
        clone.loop            = anim.loop
        clone.fps             = anim.fps
        clone.target_size     = anim.target_size
        clone._timer          = 0.0
        clone._frame_idx      = 0
        clone.finished        = False
        clone._frames         = anim._frames        # surfaces partagees
        clone._frames_flip    = anim._frames_flip
    else:  # SequenceAnimator
        clone                 = object.__new__(SequenceAnimator)
        clone.loop            = anim.loop
        clone.fps             = anim.fps
        clone.target_size     = anim.target_size
        clone._timer          = 0.0
        clone._frame_idx      = 0
        clone.finished        = False
        clone._frames         = anim._frames
        clone._frames_flip    = anim._frames_flip
    return clone