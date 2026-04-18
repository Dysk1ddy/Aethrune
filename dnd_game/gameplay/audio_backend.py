from __future__ import annotations

import ctypes
from pathlib import Path

try:
    import pygame
except ImportError:  # pragma: no cover - optional dependency
    pygame = None

try:
    import winsound
except ImportError:  # pragma: no cover - Windows-only fallback
    winsound = None


_MIXER_INIT_FAILED = False
_SOUND_CACHE: dict[str, object] = {}
_MIXER_FREQUENCY = 44_100
_MIXER_SAMPLE_SIZE = -16
_MIXER_CHANNELS = 2
_MIXER_BUFFER = 512
_MIXER_SOUND_CHANNEL_COUNT = 16
_MCI_MUSIC_ALIAS = "dnd_game_music"
_MCI_MUSIC_EXTENSIONS = frozenset({".mp3", ".wav"})
_MCI_MUSIC_OPEN = False
_WINMM = None


def pygame_is_available() -> bool:
    return pygame is not None


def _winmm():
    global _WINMM
    if _WINMM is not None:
        return _WINMM
    try:
        _WINMM = ctypes.windll.winmm
    except (AttributeError, OSError):
        return None
    return _WINMM


def mci_music_is_available() -> bool:
    return _winmm() is not None


def music_is_available() -> bool:
    return pygame is not None or mci_music_is_available()


def music_file_is_supported(path: Path) -> bool:
    if pygame is not None:
        return True
    return mci_music_is_available() and path.suffix.lower() in _MCI_MUSIC_EXTENSIONS


def sound_effects_are_available() -> bool:
    return pygame is not None or winsound is not None


def mixer_is_ready() -> bool:
    return pygame is not None and pygame.mixer.get_init() is not None


def ensure_mixer() -> bool:
    global _MIXER_INIT_FAILED
    if pygame is None or _MIXER_INIT_FAILED:
        return False
    if mixer_is_ready():
        return True
    try:
        pygame.mixer.init(
            frequency=_MIXER_FREQUENCY,
            size=_MIXER_SAMPLE_SIZE,
            channels=_MIXER_CHANNELS,
            buffer=_MIXER_BUFFER,
        )
        pygame.mixer.set_num_channels(_MIXER_SOUND_CHANNEL_COUNT)
    except pygame.error:
        _MIXER_INIT_FAILED = True
        return False
    return True


def load_sound(path: Path):
    if not ensure_mixer():
        return None
    cache_key = str(path.resolve())
    cached = _SOUND_CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        sound = pygame.mixer.Sound(str(path))
    except (pygame.error, FileNotFoundError):
        return None
    _SOUND_CACHE[cache_key] = sound
    return sound


def play_sound(path: Path) -> bool:
    sound = load_sound(path)
    if sound is not None:
        channel = sound.play()
        return channel is not None
    if winsound is None:
        return False
    try:
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except (RuntimeError, OSError):
        return False
    return True


def _mci_send(command: str) -> bool:
    winmm = _winmm()
    if winmm is None:
        return False
    return winmm.mciSendStringW(command, None, 0, None) == 0


def _mci_file_type(path: Path) -> str:
    extension = path.suffix.lower()
    if extension == ".mp3":
        return "mpegvideo"
    if extension == ".wav":
        return "waveaudio"
    return ""


def play_mci_music(path: Path, *, loops: int = -1) -> bool:
    global _MCI_MUSIC_OPEN
    if not path.exists() or path.suffix.lower() not in _MCI_MUSIC_EXTENSIONS:
        return False
    stop_mci_music()
    file_type = _mci_file_type(path)
    type_clause = f" type {file_type}" if file_type else ""
    if not _mci_send(f'open "{path.resolve()}"{type_clause} alias {_MCI_MUSIC_ALIAS}'):
        return False
    _MCI_MUSIC_OPEN = True
    play_command = f"play {_MCI_MUSIC_ALIAS}"
    if loops == -1:
        play_command += " repeat"
    if _mci_send(play_command):
        return True
    stop_mci_music()
    return False


def stop_mci_music() -> None:
    global _MCI_MUSIC_OPEN
    if not _MCI_MUSIC_OPEN:
        return
    _mci_send(f"stop {_MCI_MUSIC_ALIAS}")
    _mci_send(f"close {_MCI_MUSIC_ALIAS}")
    _MCI_MUSIC_OPEN = False


def play_music(path: Path, *, loops: int = -1) -> bool:
    if ensure_mixer():
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play(loops=loops)
        except (pygame.error, FileNotFoundError):
            return play_mci_music(path, loops=loops)
        return True
    return play_mci_music(path, loops=loops)


def stop_music() -> None:
    if mixer_is_ready():
        try:
            pygame.mixer.music.stop()
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()
        except pygame.error:
            pass
    stop_mci_music()
