import os
import sys

from . import paths

# Windows plays the same chimes as its voice typing (Win+H).
_WINDOWS = {
    "start": "Speech On.wav",
    "stop": "Speech Off.wav",
    "cancel": "Speech Sleep.wav",
}

enabled = True
_effects = {}


def play(name):
    if not enabled:
        return
    if sys.platform == "win32" and _play_windows(name):
        return
    _play_bundled(name)


def _play_windows(name):
    path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Media", _WINDOWS[name])
    if not os.path.isfile(path):
        return False
    import winsound
    try:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except RuntimeError:
        return False
    return True


def preload():
    # A sound effect loads in the background, so the first chime would be
    # late or missing if it were loaded only when needed.
    if sys.platform == "win32" and all(
        os.path.isfile(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Media", f))
        for f in _WINDOWS.values()
    ):
        return
    for name in _WINDOWS:
        _effect(name)


def _effect(name):
    effect = _effects.get(name)
    if effect is not None:
        return effect
    path = os.path.join(paths.ASSETS, "sounds", name + ".wav")
    if not os.path.isfile(path):
        return None
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtMultimedia import QSoundEffect
    except ImportError:
        return None
    effect = QSoundEffect()
    effect.setSource(QUrl.fromLocalFile(path))
    effect.setVolume(0.8)
    _effects[name] = effect
    return effect


def _play_bundled(name):
    # macOS and Linux have no such system files, so the app ships its own.
    effect = _effect(name)
    if effect is not None:
        effect.play()
