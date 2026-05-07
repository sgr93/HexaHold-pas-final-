"""
ui/sprites.py

Moteur d'animation par sprites pour Hexahold.
Trois formats supportés : spritesheet horizontale, PNG séquentiels, frames directes.
Le SpriteSet regroupe toutes les animations d'une entité et gère les transitions.
"""

import os
import glob
import pygame


# Vitesses d'animation en frames par seconde de jeu (à 60 fps)
# Ces valeurs sont calibrées pour que les animations aient l'air naturelles —
# trop rapide = nerveux, trop lent = mou
ANIM_FPS_WALK   = 8
ANIM_FPS_ATTACK = 10
ANIM_FPS_IDLE   = 5
ANIM_FPS_HURT   = 12
ANIM_FPS_DEATH  = 6


# FORMAT A : Spritesheet horizontale

class SpritesheetAnimator:
    """
    Lit une spritesheet horizontale (frames carrées côte à côte).
    La hauteur de l'image définit la taille d'une frame — on suppose des frames carrées.
    Le fond noir/quasi-noir est rendu transparent au chargement.
    """

    def __init__(self, path, fps=8, target_size=(32, 32), loop=True):
        self.loop        = loop
        self.fps         = fps
        self.target_size = target_size
        self._timer      = 0.0
        self._frame_idx  = 0
        self.finished    = False

        sheet = pygame.image.load(path).convert_alpha()

        # Rend le fond noir transparent — beaucoup de spritesheets ont un fond #000000
        arr  = pygame.surfarray.pixels3d(sheet)
        alp  = pygame.surfarray.pixels_alpha(sheet)
        mask = (arr[:, :, 0].astype(int) < 15) & \
               (arr[:, :, 1].astype(int) < 15) & \
               (arr[:, :, 2].astype(int) < 15)
        alp[mask] = 0
        del arr, alp

        sh, sw  = sheet.get_height(), sheet.get_width()
        frame_w = sh  # frames carrées
        n       = sw // frame_w

        raw_frames = []
        for i in range(n):
            frame = sheet.subsurface(pygame.Rect(i * frame_w, 0, frame_w, sh)).copy()
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
        """Avance d'une frame de jeu — à appeler à chaque tick à 60 fps."""
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
        """Retourne la surface de la frame courante, flippée si demandé."""
        return (self._frames_flip if flip_h else self._frames)[self._frame_idx]


# FORMAT B : PNG séquentiels

class SequenceAnimator:
    """
    Charge un ensemble de PNG numérotés (un fichier par frame).
    Chaque image est croppée à son contenu non-transparent puis mise à l'échelle —
    utile pour les sprites Wraith qui ont beaucoup d'espace vide autour.
    """

    def __init__(self, paths, fps=8, target_size=(64, 64), loop=True):
        self.loop        = loop
        self.fps         = fps
        self.target_size = target_size
        self._timer      = 0.0
        self._frame_idx  = 0
        self.finished    = False

        self._frames      = [self._crop_and_scale(pygame.image.load(p).convert_alpha(), target_size)
                              for p in paths]
        self._frames_flip = [pygame.transform.flip(f, True, False) for f in self._frames]

    @staticmethod
    def _crop_and_scale(surface, target_size):
        """
        Rogne au bounding box des pixels non-transparents puis scale.
        Evite d'avoir des marges énormes autour du personnage.
        """
        arr      = pygame.surfarray.array_alpha(surface)
        col_mask = arr.max(axis=1) > 10
        row_mask = arr.max(axis=0) > 10

        if not col_mask.any() or not row_mask.any():
            return pygame.transform.scale(surface, target_size)

        x_min = int(col_mask.argmax())
        x_max = int(len(col_mask) - col_mask[::-1].argmax() - 1)
        y_min = int(row_mask.argmax())
        y_max = int(len(row_mask) - row_mask[::-1].argmax() - 1)

        cropped = surface.subsurface(
            pygame.Rect(x_min, y_min, max(1, x_max - x_min + 1), max(1, y_max - y_min + 1))
        ).copy()
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
        return (self._frames_flip if flip_h else self._frames)[self._frame_idx]


# FORMAT C : Frames pygame directes

class _DirectFrameAnimator:
    """
    Animateur qui reçoit directement une liste de surfaces pygame.
    Même interface que SpritesheetAnimator — utilisé pour les RPG Maker sheets
    où on extrait les frames manuellement avant de créer l'animateur.
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
        return (self._frames_flip if flip_h else self._frames)[self._frame_idx]


# SPRITESET : regroupe les animations d'une entité

class SpriteSet:
    """
    Conteneur d'animations pour une entité.
    Gère les transitions entre états et le flip automatique pour les directions.

    Etats reconnus : 'idle', 'walk', 'attack', 'hurt', 'death'
    Directions     : 'down', 'up', 'right', 'left' (left = flip auto de right)

    Utilisation :
        ss = SpriteSet.from_roguelike_folder(path, size)
        ss.set_state('walk', direction='down')
        ss.update()
        frame = ss.get_frame()
    """

    def __init__(self):
        self._anims   = {}    # {(state, direction): animator}
        self._current = None
        self._state   = 'idle'
        self._dir     = 'down'
        self._flip    = False

    def add(self, state, direction, animator):
        self._anims[(state, direction)] = animator

    def _resolve_key(self, state, direction):
        """
        Trouve la clé disponible la plus proche.
        Si 'left' n'existe pas, on flippe 'right' — pas besoin de doubler les assets.
        """
        if (state, direction) in self._anims:
            return (state, direction), False
        if direction == 'left' and (state, 'right') in self._anims:
            return (state, 'right'), True
        if (state, 'down') in self._anims:
            return (state, 'down'), False
        # Dernier recours — premier état disponible
        for k in self._anims:
            if k[0] == state:
                return k, False
        return None, False

    def set_state(self, state, direction=None, force_reset=False):
        """
        Change l'état et/ou la direction.
        Ne remet pas à zéro si l'état n'a pas changé — évite les saccades.
        """
        direction    = direction or self._dir
        key, flip    = self._resolve_key(state, direction)
        if key is None:
            return
        changed       = (key != self._current) or force_reset
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
        """True si l'animation courante est non-bouclée et terminée (mort, attaque...)."""
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
        A appeler chaque frame depuis le update() du personnage pour que l'animation
        reste synchronisée avec le déplacement réel.
        """
        ratio   = max(0.2, speed / max(0.01, base_speed))
        new_fps = ANIM_FPS_WALK * ratio
        for (state, _dir), anim in self._anims.items():
            if state == 'walk':
                anim.fps = new_fps

    @classmethod
    def from_rpgmaker_sheet(cls, path, target_size=(64, 64)):
        """
        Charge une spritesheet RPG Maker VX Ace / MV (3 cols x 4 rows).
        Layout : row 0 = bas, 1 = gauche, 2 = droite, 3 = haut.
        Chaque row a 3 frames : walk_L, idle, walk_R.
        """
        sheet  = pygame.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()
        fw, fh = sw // 3, sh // 4

        # Rend le fond noir transparent — même chose que SpritesheetAnimator
        arr  = pygame.surfarray.pixels3d(sheet)
        alp  = pygame.surfarray.pixels_alpha(sheet)
        mask = (arr[:, :, 0].astype(int) < 15) & \
               (arr[:, :, 1].astype(int) < 15) & \
               (arr[:, :, 2].astype(int) < 15)
        alp[mask] = 0
        del arr, alp

        def get_frame(col, row):
            surf = sheet.subsurface(pygame.Rect(col * fw, row * fh, fw, fh)).copy()
            return pygame.transform.scale(surf, target_size)

        ss      = cls()
        ROW_MAP = {0: 'down', 1: 'left', 2: 'right', 3: 'up'}

        for row, direction in ROW_MAP.items():
            walk_l = get_frame(0, row)
            idle   = get_frame(1, row)
            walk_r = get_frame(2, row)

            ss.add('walk',   direction, _DirectFrameAnimator([walk_l, idle, walk_r], fps=ANIM_FPS_WALK,   loop=True))
            ss.add('idle',   direction, _DirectFrameAnimator([idle],                 fps=ANIM_FPS_IDLE,   loop=True))
            ss.add('hurt',   direction, _DirectFrameAnimator([idle],                 fps=ANIM_FPS_HURT,   loop=False))
            ss.add('attack', direction, _DirectFrameAnimator([walk_l, idle, walk_r], fps=ANIM_FPS_ATTACK, loop=False))
            ss.add('death',  direction, _DirectFrameAnimator([idle],                 fps=ANIM_FPS_DEATH,  loop=False))

        ss.set_state('idle', 'down')
        return ss

    @classmethod
    def from_roguelike_folder(cls, folder, target_size=(32, 32)):
        """
        Charge un jeu de sprites roguelike depuis un dossier.
        Nommage attendu : {D|S|U}_{Attack|Walk|Idle|Death|Hurt}.png
        Le 'left' n'a pas de fichier dédié — il est géré par flip automatique de 'right'.
        """
        ss = cls()
        DIR_MAP  = {'S': 'down', 'U': 'up', 'D': 'right'}
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
            parts = fname[:-4].split('_')
            if len(parts) != 2:
                continue
            dir_code, anim_name = parts
            if dir_code not in DIR_MAP or anim_name not in ANIM_MAP:
                continue
            state, fps, loop = ANIM_MAP[anim_name]
            ss.add(state, DIR_MAP[dir_code],
                   SpritesheetAnimator(os.path.join(folder, fname), fps=fps,
                                       target_size=target_size, loop=loop))

        ss.set_state('idle', 'down')
        return ss

    @classmethod
    def from_sequence_folder(cls, folder, prefix, target_size=(64, 64)):
        """
        Charge un jeu de sprites Wraith (PNG séquentiels) depuis un dossier.
        Structure attendue : Attacking/, Walking/, Idle Blink/, Dying/, Hurt/
        Tous les Wraiths sont orientés face au joueur, donc direction 'down' uniquement.
        """
        ss = cls()

        def load_seq(subdir, state, fps, loop):
            paths = sorted(glob.glob(os.path.join(folder, subdir, '*.png')))
            if paths:
                ss.add(state, 'down',
                       SequenceAnimator(paths, fps=fps, target_size=target_size, loop=loop))

        load_seq('Attacking',  'attack', ANIM_FPS_ATTACK, False)
        load_seq('Walking',    'walk',   ANIM_FPS_WALK,   True)
        load_seq('Idle Blink', 'idle',   ANIM_FPS_IDLE,   True)
        load_seq('Dying',      'death',  ANIM_FPS_DEATH,  False)
        load_seq('Hurt',       'hurt',   ANIM_FPS_HURT,   False)

        ss.set_state('idle', 'down')
        return ss


# CHARGEMENT GLOBAL

# Cache global — évite de recharger les sprites à chaque ennemi spawné
_cache = {}


def load_spriteset(entity_type, assets_base):
    """
    Retourne un SpriteSet pour le type d'entité donné.
    Les surfaces sont partagées via le cache — pas de copie mémoire inutile.
    Retourne None si les assets sont introuvables (le jeu continue sans sprite).
    """
    if entity_type in _cache:
        return _clone_spriteset(_cache[entity_type])

    folder = os.path.join(assets_base, entity_type)
    if not os.path.isdir(folder):
        return None

    try:
        # Tailles différentes selon l'importance visuelle de l'entité
        size_map = {
            'enemy_normal': (52, 52),
            'enemy_fast':   (52, 52),
            'boss':         (68, 68),
            'boss_final':   (82, 82),
            'boss_chapter': (100, 100),  # plus grand que boss_final pour se démarquer
        }

        if entity_type == 'player':
            # Le player ne va pas dans le cache — il change selon le héros sélectionné
            size = (40, 40)
            pngs = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
            rpgmaker = [f for f in pngs if not any(f.startswith(p) for p in ('S_', 'D_', 'U_', 'L_', 'N_'))]
            if rpgmaker:
                return SpriteSet.from_rpgmaker_sheet(os.path.join(folder, rpgmaker[0]), target_size=size)
            return SpriteSet.from_roguelike_folder(folder, target_size=size)

        if entity_type not in size_map:
            return None

        ss = SpriteSet.from_roguelike_folder(folder, target_size=size_map[entity_type])
        _cache[entity_type] = ss
        return _clone_spriteset(ss)

    except Exception as e:
        print(f"[sprites] Impossible de charger '{entity_type}': {e}")
        return None


def _clone_spriteset(source):
    """
    Crée un SpriteSet avec son propre état mais qui partage les surfaces du cache.
    Les surfaces pygame sont déjà en mémoire vidéo — pas besoin de les copier.
    """
    ss = SpriteSet()
    for (state, direction), anim in source._anims.items():
        ss._anims[(state, direction)] = _clone_animator(anim)
    ss.set_state('idle', 'down')
    return ss


def _clone_animator(anim):
    """
    Copie légère d'un animator — même surfaces, état réinitialisé.
    Utilise object.__new__ pour éviter d'appeler __init__ et de recharger les assets.
    """
    clone = object.__new__(type(anim))
    clone.loop         = anim.loop
    clone.fps          = anim.fps
    clone.target_size  = anim.target_size
    clone._timer       = 0.0
    clone._frame_idx   = 0
    clone.finished     = False
    clone._frames      = anim._frames       # surfaces partagées — pas de copie
    clone._frames_flip = anim._frames_flip
    return clone