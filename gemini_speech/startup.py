import os
import sys

from . import paths

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NAME = "SpeechDictation"


def command():
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    # pythonw has no console window, so nothing flashes at sign-in.
    exe = sys.executable
    windowed = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.isfile(windowed):
        exe = windowed
    return '"%s" "%s"' % (exe, os.path.join(paths.ROOT, "launch.py"))


def enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY) as key:
            winreg.QueryValueEx(key, _NAME)
        return True
    except OSError:
        return False


def set_enabled(on):
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, command())
            return
        try:
            winreg.DeleteValue(key, _NAME)
        except FileNotFoundError:
            pass
