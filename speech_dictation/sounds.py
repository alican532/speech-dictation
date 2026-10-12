import os
import sys

# The same chimes Windows voice typing (Win+H) plays.
_FILES = {
    "start": "Speech On.wav",
    "stop": "Speech Off.wav",
    "cancel": "Speech Sleep.wav",
}

enabled = True


def play(name):
    if not enabled or sys.platform != "win32":
        return
    path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Media", _FILES[name])
    if not os.path.isfile(path):
        return
    import winsound
    try:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except RuntimeError:
        pass
