import os
import sys


def root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT = root()
ICON = os.path.join(ROOT, "assets", "icon.png")
if not os.path.isfile(ICON):
    bundled = getattr(sys, "_MEIPASS", "")
    if bundled and os.path.isfile(os.path.join(bundled, "assets", "icon.png")):
        ICON = os.path.join(bundled, "assets", "icon.png")
# A frozen macOS app keeps its data apart from the executable, so assets are
# found wherever the icon was.
ASSETS = os.path.dirname(ICON)


def config_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, "SpeechDictation")
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)
        # Bring the key and shortcuts over from the original app once.
        old = os.path.join(base, "GeminiSpeechAPI", "config.json")
        if os.path.isfile(old):
            import shutil
            shutil.copyfile(old, os.path.join(path, "config.json"))
    return path


def config_path():
    return os.path.join(config_dir(), "config.json")


def log_dir():
    path = os.path.join(config_dir(), "logs")
    os.makedirs(path, exist_ok=True)
    return path
