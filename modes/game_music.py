"""
modes/game_music.py

Helpers de lecture musicale extraits de game.py.
Rien de complexe ici — juste de quoi ne pas répéter les mêmes 5 lignes
pygame.mixer partout dans le code.
"""

import os
import pygame
from core.config import MUSIC_PATH, MUSIC_TRACK_TITLE, MUSIC_TRACK_MENU, MUSIC_TRACK_GAME


def _find_music_file(track_name):
    """
    Cherche le fichier audio en essayant d'abord le nom exact, puis les extensions courantes.
    Utile si les assets changent de format sans qu'on mette à jour la config.
    """
    base = os.path.join(os.path.dirname(__file__), "..", MUSIC_PATH, track_name)
    if os.path.exists(base):
        return base
    # Le fichier exact n'existe pas — on tente les extensions alternatives
    stem, _ = os.path.splitext(track_name)
    for ext in [".mp3", ".ogg", ".wav"]:
        candidate = os.path.join(os.path.dirname(__file__), "..", MUSIC_PATH, stem + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def play_music(track_name, volume=0.8):
    """
    Charge et lance une piste en boucle infinie.
    On échoue silencieusement si le mixer n'est pas init ou si le fichier est introuvable —
    la musique n'est pas critique, pas question de crasher pour ça.
    """
    if not pygame.mixer.get_init():
        return
    track_path = _find_music_file(track_name)
    if not track_path:
        return
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(track_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)  # -1 = boucle infinie
    except Exception:
        pass


def play_title_music(volume=0.8):
    play_music(MUSIC_TRACK_TITLE, volume)


def play_menu_music(volume=0.8):
    play_music(MUSIC_TRACK_MENU, volume)


def play_game_music(volume=0.8):
    play_music(MUSIC_TRACK_GAME, volume)