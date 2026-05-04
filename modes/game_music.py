"""
game_music.py
-------------
Helpers de lecture musicale extraits de game.py.
"""
import os
import pygame
from core.config import (
    MUSIC_PATH, MUSIC_TRACK_TITLE, MUSIC_TRACK_MENU, MUSIC_TRACK_GAME,
)


def _find_music_file(track_name):
    base = os.path.join(os.path.dirname(__file__), "..", MUSIC_PATH, track_name)
    if os.path.exists(base):
        return base
    stem, ext = os.path.splitext(track_name)
    for candidate_ext in [".mp3", ".ogg", ".wav"]:
        candidate = os.path.join(os.path.dirname(__file__), "..", MUSIC_PATH, stem + candidate_ext)
        if os.path.exists(candidate):
            return candidate
    return None


def play_music(track_name, volume=0.8):
    if not pygame.mixer.get_init():
        return
    track_path = _find_music_file(track_name)
    if not track_path:
        return
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(track_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
    except Exception:
        pass


def play_title_music(volume=0.8):
    play_music(MUSIC_TRACK_TITLE, volume)


def play_menu_music(volume=0.8):
    play_music(MUSIC_TRACK_MENU, volume)


def play_game_music(volume=0.8):
    play_music(MUSIC_TRACK_GAME, volume)
