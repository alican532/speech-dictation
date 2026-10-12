"""Start at sign-in.

Windows: a value under HKCU\\...\\Run.
macOS: a LaunchAgent in ~/Library/LaunchAgents.
Linux: an XDG autostart entry in ~/.config/autostart.
"""
import os
import sys

from . import paths

_NAME = "SpeechDictation"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_AGENT_ID = "com.speechdictation.app"


def _arguments():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    exe = sys.executable
    if sys.platform == "win32":
        # pythonw has no console window, so nothing flashes at sign-in.
        windowed = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(windowed):
            exe = windowed
    return [exe, os.path.join(paths.ROOT, "launch.py")]


def command():
    return " ".join('"%s"' % part for part in _arguments())


def _agent_path():
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % _AGENT_ID)


def _autostart_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "autostart", "speech-dictation.desktop")


def enabled():
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                winreg.QueryValueEx(key, _NAME)
            return True
        except OSError:
            return False
    if sys.platform == "darwin":
        return os.path.isfile(_agent_path())
    return os.path.isfile(_autostart_path())


def set_enabled(on):
    if sys.platform == "win32":
        _set_windows(on)
    elif sys.platform == "darwin":
        _set_file(_agent_path(), _agent() if on else None)
    else:
        _set_file(_autostart_path(), _desktop_entry() if on else None)


def _set_windows(on):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, _NAME, 0, winreg.REG_SZ, command())
            return
        try:
            winreg.DeleteValue(key, _NAME)
        except FileNotFoundError:
            pass


def _set_file(path, text):
    if text is None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _agent():
    # launchd reads this at the next sign-in; nothing has to be loaded now.
    import plistlib
    return plistlib.dumps({
        "Label": _AGENT_ID,
        "ProgramArguments": _arguments(),
        "WorkingDirectory": paths.ROOT,
        "RunAtLoad": True,
        "ProcessType": "Interactive",
    }).decode("utf-8")


def _desktop_entry():
    # Exec quotes each argument, as the desktop entry spec asks.
    exec_line = " ".join('"%s"' % part.replace('"', '\\"') for part in _arguments())
    icon = paths.ICON if os.path.isfile(paths.ICON) else "speech-dictation"
    return """[Desktop Entry]
Type=Application
Name=Speech Dictation
Comment=Tray dictation with Groq Whisper and Gemini
Exec=%s
Path=%s
Icon=%s
Terminal=false
X-GNOME-Autostart-enabled=true
""" % (exec_line, paths.ROOT, icon)
