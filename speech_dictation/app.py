import json
import os
import sys

from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPixmap, QColor
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import desktop
from . import elevenlabs
from . import groq
from . import hotkey
from . import i18n
from . import indicator
from . import messages
from . import paste
from . import paths
from . import sounds
from . import speech
from . import startup
from . import textproc
from .audio import Recorder, level
from .i18n import tr
from .settings import LANGUAGES, Settings
from .usage_view import UsageWindow
from .vad import Silence
from .widget import FloatingButton


class _Update(QThread):
    found = pyqtSignal(str)
    ready = pyqtSignal(str, str)

    def run(self):
        from . import update
        try:
            info = update.check()
            if not info:
                return
            self.found.emit(info["version"])
            path = update.download(info)
        except Exception as exc:
            update._log("failed: %s" % exc)
            return
        self.ready.emit(path, info["version"])


class _Finish(QThread):
    text_ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, live):
        super().__init__()
        self._live = live

    def run(self):
        live = self._live
        self._live = None
        try:
            self.text_ready.emit(live.finish())
        except Exception as exc:
            self.failed.emit(str(exc)[:80])


def _qt_log(mode, _context, message):
    from .crashlog import note
    note("qt %s: %s" % (mode, message))


_INSTANCE_NAME = "Local\\SpeechDictation.single"
_SHOW_NAME = "Local\\SpeechDictation.show"
_INSTANCE_HANDLE = None
_SHOW_HANDLE = None
_LOCAL_NAME = "SpeechDictation-single"
_LOCAL_SERVER = None
_LOCAL_SHOW = False


def _kernel32():
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateEventW.restype = ctypes.c_void_p
    kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenEventW.restype = ctypes.c_void_p
    kernel32.SetEvent.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    return kernel32


def _claim_single_instance():
    global _INSTANCE_HANDLE, _SHOW_HANDLE
    if sys.platform != "win32":
        return True
    kernel32 = _kernel32()
    kernel32.SetLastError(0)
    _INSTANCE_HANDLE = kernel32.CreateMutexW(None, False, _INSTANCE_NAME)
    if kernel32.GetLastError() == 183:
        # The tray app has no window, so a second launch opens Settings in the first.
        event = kernel32.OpenEventW(0x0002, False, _SHOW_NAME)
        if event:
            kernel32.SetEvent(event)
            kernel32.CloseHandle(event)
        return False
    _SHOW_HANDLE = kernel32.CreateEventW(None, False, False, _SHOW_NAME)
    return True


def _claim_local_instance():
    # macOS and Linux: a local socket plays the part of the Windows mutex.
    # A second launch, for example a manual one after start at sign-in,
    # asks the first to open Settings and quits.
    global _LOCAL_SERVER
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    name = "%s-%s" % (_LOCAL_NAME, os.environ.get("USER") or os.getuid())
    probe = QLocalSocket()
    probe.connectToServer(name)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return False
    # A crash can leave the socket file behind, which would block listen().
    QLocalServer.removeServer(name)
    _LOCAL_SERVER = QLocalServer()
    _LOCAL_SERVER.newConnection.connect(_local_connection)
    _LOCAL_SERVER.listen(name)
    return True


def _local_connection():
    global _LOCAL_SHOW
    while _LOCAL_SERVER.hasPendingConnections():
        _LOCAL_SERVER.nextPendingConnection().deleteLater()
        _LOCAL_SHOW = True


def _show_requested():
    global _LOCAL_SHOW
    if _LOCAL_SHOW:
        _LOCAL_SHOW = False
        return True
    if not _SHOW_HANDLE:
        return False
    return _kernel32().WaitForSingleObject(_SHOW_HANDLE, 0) == 0


def main():
    from PyQt6.QtCore import Qt, qInstallMessageHandler
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SpeechDictation.App")
    if not _claim_single_instance():
        return
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    qInstallMessageHandler(_qt_log)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if sys.platform != "win32" and not _claim_local_instance():
        return
    if sys.platform.startswith("linux"):
        app.setDesktopFileName("speech-dictation")
    # Held here: the garbage collector otherwise frees it, taking the tray and timers.
    tray_app = GeminiSpeech()
    tray_app.start()
    app.exec()
    os._exit(0)


class GeminiSpeech(QObject):
    def __init__(self):
        super().__init__()
        self.shortcut = "Alt+Z"
        self.translate = ""
        self.language = "en"
        self.cancel = "Esc"
        self.api_key = ""
        self.groq_key = ""
        self.elevenlabs_key = ""
        self.google_key = ""
        self.service = "groq"
        self.spoken = ""
        self.auto_stop = 3
        self.trim = True
        self.no_verbatim = True
        self.sounds = True
        # Engines for the text after it is heard; see textproc.
        self.corrector = "groq-120b"
        self.translator = "groq-120b"
        self.vocabulary = "Claude"
        self.app_language = ""
        self.widget_pos = None
        self.recorder = Recorder()
        self.silence = Silence()
        self._locked = False
        self._capturing = False
        self._from_button = False
        self.indicator = indicator.Indicator()
        self.keys = hotkey.Hotkey()
        self.keys.failed.connect(self._fail)
        self._quitting = False
        self.busy = False
        self._job = None
        self._live = None
        self._warm = None
        self._rewarm_at = 0.0
        self._stopping = False
        self._finish_token = 0
        self._updating = False
        self._update_job = None
        self._pending_update = None
        self._load()
        i18n.set_language(self.app_language or i18n.system_language())
        self.settings = self._build_settings()
        self.usage = None
        self.tray = QSystemTrayIcon(self._dot(False))
        QApplication.instance().setWindowIcon(QIcon(paths.ICON))
        self.tray.setToolTip("Speech Dictation")
        self.menu = QMenu()
        settings = self.settings_action = QAction(tr("Settings"), self.menu)
        settings.triggered.connect(self.show_settings)
        usage_ = self.usage_action = QAction(tr("Usage"), self.menu)
        usage_.triggered.connect(self.show_usage)
        quit_ = self.quit_action = QAction(tr("Quit"), self.menu)
        quit_.triggered.connect(self.quit)
        self.menu.addAction(settings)
        self.menu.addAction(usage_)
        self.menu.addAction(quit_)
        self.button = FloatingButton()
        self.button.toggled.connect(lambda: self.toggle(source="button"))
        self.button.translate_toggled.connect(lambda: self.toggle("translate", source="button"))
        self.button.set_target(self.language)
        self.button.lock_changed.connect(self._lock_changed)
        self.button.hide_requested.connect(self._hide_button)
        self.button.moved.connect(self._button_moved)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._activated)
        self.cancel_watch = QTimer()
        self.cancel_watch.setInterval(40)
        self.cancel_watch.timeout.connect(self._watch_cancel)

    def start(self):
        desktop.start()
        sounds.preload()
        self._arm_shortcut()
        from .crashlog import note
        note("tray shown")
        QTimer.singleShot(0, self.tray.show)
        QTimer.singleShot(0, self._show_button)
        self.cancel_watch.start()
        self._sync_tip()
        self._ensure_warm()
        QTimer.singleShot(4000, self._check_update)
        self._update_timer = QTimer()
        self._update_timer.setInterval(6 * 60 * 60 * 1000)
        self._update_timer.timeout.connect(self._check_update)
        self._update_timer.start()
        if not self._key_for(self.service):
            self.show_settings()

    def _keys(self):
        return {
            "groq": self.groq_key,
            "elevenlabs": self.elevenlabs_key,
            "gemini": self.api_key,
            "google": self.google_key,
        }

    def _key_for(self, service):
        return self._keys()[textproc.service_provider(service)]

    def _values(self):
        return {
            "keys": self._keys(),
            "service": self.service,
            "spoken": self.spoken,
            "auto_stop": self.auto_stop,
            "trim": self.trim,
            "no_verbatim": self.no_verbatim,
            "sounds": self.sounds,
            "startup": startup.enabled(),
            "shortcut": self.shortcut,
            "translate": self.translate,
            "language": self.language,
            "translator": self.translator,
            "corrector": self.corrector,
            "vocabulary": self.vocabulary,
            "app_language": i18n.current,
            "cancel": self.cancel,
        }

    def _show_button(self):
        if self._quitting:
            return
        if not self.button.isVisible():
            pos = self.widget_pos or (None, None)
            self.button.place(*pos)
            self.button.show()
        self.button.raise_()

    def _hide_button(self):
        # Like Windows voice typing: closing the bar also ends what it was hearing.
        if self.recorder.active and not self._stopping:
            self._drop_recording()
            self.busy = False
            self._sync_tray()
            self._ensure_warm()
        self.button.hide()

    def _button_moved(self, x, y):
        self.widget_pos = (x, y)
        self._store()

    def _retranslate(self):
        # Every label is set when its widget is built, so the dialog is built again.
        self.settings_action.setText(tr("Settings"))
        self.usage_action.setText(tr("Usage"))
        self.quit_action.setText(tr("Quit"))
        self._sync_tip()
        old = self.settings
        was_open = old.isVisible()
        where = old.pos()
        self.settings = self._build_settings()
        old.hide()
        old.deleteLater()
        if self.usage is not None:
            usage_open = self.usage.isVisible()
            self.usage.hide()
            self.usage.deleteLater()
            self.usage = None
            if usage_open:
                self.show_usage()
        if was_open:
            self.show_settings()
            self.settings.move(where)

    def _lock_changed(self, locked):
        self._locked = locked

    def _check_update(self):
        if self._updating or self._quitting or self.recorder.active or self.busy:
            return
        self._updating = True
        job = _Update()
        job.found.connect(self._update_found, Qt.ConnectionType.QueuedConnection)
        job.ready.connect(self._update_ready, Qt.ConnectionType.QueuedConnection)
        job.finished.connect(self._update_finished)
        job.finished.connect(job.deleteLater)
        self._update_job = job
        job.start()

    def _update_finished(self):
        self._update_job = None
        if not self._pending_update:
            self._updating = False

    def _update_found(self, version):
        self.tray.showMessage("Speech Dictation", tr("Downloading version %s") % version, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _update_ready(self, path, version):
        self._pending_update = (path, version)
        self._install_update()

    def _install_update(self):
        pending = self._pending_update
        if not pending or self._quitting:
            return
        if self.recorder.active or self.busy or self._stopping or self.settings.isVisible():
            QTimer.singleShot(5000, self._install_update)
            return
        path, version = pending
        from . import update
        if sys.platform == "darwin":
            self._pending_update = None
            self._updating = False
            self.tray.showMessage("Speech Dictation", tr("Version %s is ready to install") % version, QSystemTrayIcon.MessageIcon.Information, 5000)
            update.launch(path)
            return
        self.tray.showMessage("Speech Dictation", tr("Installing version %s, the app will restart") % version, QSystemTrayIcon.MessageIcon.Information, 3000)
        QTimer.singleShot(1500, lambda: self._run_installer(path))

    def _run_installer(self, path):
        from . import update
        if self._quitting:
            return
        if update.launch(path):
            self.quit()
            return
        self._pending_update = None
        self._updating = False
        self._overlay("error", "Update failed")

    def _build_settings(self):
        return Settings(self.save_settings, self._settings_closed, self._capturing_shortcut, self.show_usage)

    def show_usage(self):
        if self.usage is None:
            self.usage = UsageWindow()
        self.usage.show()
        self.usage.raise_()
        self.usage.activateWindow()

    def show_settings(self):
        self.settings.set_values(self._values())
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def _settings_closed(self):
        if self._quitting:
            return
        self._arm_shortcut()
        self._sync_tip()

    def _capturing_shortcut(self, on):
        self._capturing = on
        self._arm_shortcut()

    def _settings_in_front(self):
        return self.settings.isVisible() and self.settings.isActiveWindow()

    def _arm_shortcut(self):
        # Shortcuts stay on while Settings is open, except while a shortcut
        # field waits for keys: Windows would hand them to the hotkey instead.
        if self._capturing:
            self.keys.stop()
            return
        if self.shortcut or self.translate:
            self.keys.start(self.shortcut, self.translate)
        else:
            self.keys.stop()

    def save_settings(self, values):
        keys = values["keys"]
        self.api_key = keys["gemini"].strip()
        self.groq_key = keys["groq"].strip()
        self.elevenlabs_key = keys["elevenlabs"].strip()
        self.google_key = keys["google"].strip()
        self.service = values["service"]
        self.spoken = values["spoken"]
        self.auto_stop = values["auto_stop"]
        self.trim = values["trim"]
        self.no_verbatim = values["no_verbatim"]
        self.sounds = sounds.enabled = values["sounds"]
        record = self.shortcut = values["shortcut"]
        translate = self.translate = values["translate"]
        self.language = values["language"] or "en"
        self.button.set_target(self.language)
        self.translator = values["translator"]
        self.corrector = values["corrector"]
        self.vocabulary = values["vocabulary"]
        if values["app_language"] != i18n.current:
            self.app_language = values["app_language"]
            i18n.set_language(self.app_language)
            QTimer.singleShot(0, self._retranslate)
        cancel = self.cancel = values["cancel"] or "Esc"
        try:
            startup.set_enabled(values["startup"])
        except OSError as exc:
            label = tr("Start with Windows") if sys.platform == "win32" else tr("Start at login")
            self._overlay("error", "%s: %s" % (label, exc))
        self._store()
        self.settings.shortcut.owned = record
        self.settings.translate.owned = translate
        self.settings.cancel.owned = cancel
        self._arm_shortcut()
        self._sync_tip()
        self._ensure_warm()

    def _ensure_warm(self):
        if self.service != "gemini" and self._warm is not None:
            self._warm.cancel()
            self._warm = None
        if self._quitting or self.service != "gemini" or not self.api_key or self._live is not None:
            return
        warm = self._warm
        if warm is not None and warm.fresh() and warm._key == self.api_key and not warm._language:
            return
        if warm is not None:
            warm.cancel()
        self._warm = speech.LiveSession(self.api_key)
        self._warm.open()

    def _take_live(self):
        warm = self._warm
        self._warm = None
        if warm is None or not warm.fresh():
            if warm is not None:
                warm.cancel()
            warm = speech.LiveSession(self.api_key)
            warm.open()
        return warm

    def toggle(self, mode="record", source="shortcut"):
        from .crashlog import note
        if self.busy:
            note("toggle skipped")
            return
        if self._settings_in_front():
            # The text would land in a Settings field, perhaps the key field.
            note("toggle skipped: settings in front")
            self._overlay("error", messages.SETTINGS_IN_FRONT)
            return
        if self.recorder.active:
            self._finish()
            return
        service = self.service
        corrector = textproc.usable("corrector", self.corrector, service)
        translator = textproc.usable("translator", self.translator, service) if mode == "translate" else ""
        needed = [textproc.service_provider(service)]
        if translator:
            needed.append(textproc.key_provider(translator))
        elif corrector != "off":
            needed.append(textproc.key_provider(corrector))
        keys = self._keys()
        missing = next((provider for provider in needed if not keys.get(provider)), None)
        if missing:
            note("toggle no %s key" % missing)
            self._overlay("error", textproc.KEY_MISSING[missing])
            self.show_settings()
            return
        try:
            desktop.remember_focus()
            note("opening %s session" % service)
            self._live = self._session(service, corrector, translator)
            self.silence.reset()
            self._mode = mode
            self._from_button = source == "button"
            self._show_button()
            self.recorder.on_chunk = self._on_chunk
            note("opening microphone")
            self.recorder.start()
            sounds.play("start")
            note("microphone open")
            self._overlay("recording")
            note("indicator shown")
        except Exception as exc:
            self._drop_recording()
            self._overlay("error", str(exc)[:80])
            return
        self._sync_tray()
        note("toggle returned")

    def _session(self, service, corrector, translator):
        target = next((name for name, code in LANGUAGES if code == self.language), "English")
        spoken = next((name for name, code in LANGUAGES if code == self.spoken), "")
        words = self.vocabulary
        edit = None
        if translator == "elevenlabs":
            edit = ("translate", textproc.translate_instruction(target, words, textproc.EDIT))
        elif not translator and corrector == "elevenlabs":
            edit = ("correct", textproc.correct_instruction(spoken, words, textproc.EDIT))
        if service == "gemini" and translator == "gemini-live":
            session = speech.LiveSession(self.api_key, self.language)
            session.open()
        elif service == "gemini":
            session = self._take_live()
        elif service == "elevenlabs":
            session = elevenlabs.ElevenLabsSession(
                self.elevenlabs_key, self.spoken, self.trim, words, self.no_verbatim, edit)
            session.open()
        elif service == "elevenlabs-live":
            session = elevenlabs.ElevenLabsLive(self.elevenlabs_key, self.spoken, words, self.no_verbatim)
            session.open()
        else:
            session = groq.GroqSession(self.groq_key, service, self.spoken, self.trim, words)
            session.open()
        processor = textproc.Processor(self._keys(), spoken, words)
        return textproc.Pipeline(session, processor, corrector, translator, target, self.language)

    def _on_chunk(self, pcm):
        self.silence.feed(pcm)
        live = self._live
        if live is not None:
            live.push(pcm)

    def _finish(self):
        if self._stopping or self.busy:
            return
        self._stopping = True
        self.busy = True
        sounds.play("stop")
        self._sync_tray()
        self._overlay("busy")
        self._finish_token += 1
        token = self._finish_token
        self.recorder.mark()
        self._tail_quiet = 0
        self._tail_started = __import__("time").monotonic()
        QTimer.singleShot(40, lambda: self._watch_tail(token))

    def _watch_tail(self, token):
        if token != self._finish_token or self._quitting or not self.recorder.active:
            return
        elapsed = __import__("time").monotonic() - self._tail_started
        tail = self.recorder.since_mark()
        recent = tail[-int(0.08 * 32000):]
        if level(recent) >= 400:
            self._tail_quiet = 0
        else:
            self._tail_quiet += 40
        # The last word can still be in the driver. Keep it if it arrives, then stop at the quiet.
        if elapsed >= 0.7 or (elapsed >= 0.22 and self._tail_quiet >= 160):
            self._finish_capture(token)
            return
        QTimer.singleShot(40, lambda: self._watch_tail(token))

    def _finish_capture(self, token):
        if token != self._finish_token or self._quitting:
            return
        self.recorder.stop()
        self.recorder.on_chunk = None
        live = self._live
        self._live = None
        self._stopping = False
        self._unlock()
        self._sync_tray()
        if live is None:
            self.busy = False
            return
        job = _Finish(live)
        job.text_ready.connect(self._pasted, Qt.ConnectionType.QueuedConnection)
        job.failed.connect(self._transcribe_failed, Qt.ConnectionType.QueuedConnection)
        job.finished.connect(job.deleteLater)
        self._job = job
        job.start()

    def _drop_recording(self):
        if self.recorder.active:
            sounds.play("cancel")
        self._finish_token += 1
        self._unlock()
        self._stopping = False
        self.recorder.on_chunk = None
        self.recorder.stop()
        live = self._live
        self._live = None
        if live is not None:
            live.cancel()

    def _pasted(self, text):
        self._ensure_warm()
        if not (text or "").strip():
            self._overlay("error", messages.NO_SPEECH)
        elif self._settings_in_front():
            # Settings came to the front while listening, so the text is only copied.
            QApplication.clipboard().setText(text.strip())
            self._overlay("error", messages.PASTE_FAILED)
        elif self._from_button and not desktop.button_keeps_focus():
            # GNOME and other Wayland desktops focused the button on the click.
            QApplication.clipboard().setText(text.strip())
            self._overlay("error", messages.COPIED_PRESS_PASTE)
        elif paste.paste_text(text):
            self._overlay("done")
        else:
            self._overlay("error", messages.PASTE_FAILED)
        self.busy = False
        self._sync_tray()

    def _unlock(self):
        self._locked = False
        self.button.set_locked(False)

    def _watch_silence(self):
        if not self.recorder.active or self.busy or self._stopping:
            return
        quiet = self.silence.quiet_for()
        countdown = None
        wait = self.auto_stop
        if wait and not self._locked:
            if self.silence.heard:
                if quiet >= wait:
                    self._finish()
                    return
                if quiet >= 1.0 and wait > 1.0:
                    countdown = 1.0 - (quiet - 1.0) / (wait - 1.0)
            else:
                # Some people take a breath before they start, so the first word gets longer.
                grace = wait + 2.0
                elapsed = self.silence.elapsed()
                if elapsed >= grace:
                    self._drop_recording()
                    self._sync_tray()
                    self._overlay("error", messages.NO_SPEECH)
                    self._ensure_warm()
                    return
                if elapsed >= 1.0:
                    countdown = 1.0 - (elapsed - 1.0) / (grace - 1.0)
        self.button.set_level(self.silence.level, countdown)

    def _transcribe_failed(self, message):
        self.busy = False
        self._sync_tray()
        self._ensure_warm()
        self._overlay("error", message)

    def _watch_cancel(self):
        if _show_requested() and not (self.recorder.active or self.busy):
            self.show_settings()
        error = self.keys.take_error()
        if error:
            self._fail(error)
        action = self.keys.take()
        if action:
            self.toggle(action)
        if (self.recorder.active or self._stopping) and hotkey.held(self.cancel):
            self._drop_recording()
            self.busy = False
            self._sync_tray()
            self._overlay("hide")
            self._ensure_warm()
            return
        if self._live is None and (self._warm is None or self._warm.done.is_set()):
            import time
            if time.monotonic() - self._rewarm_at > 2:
                self._rewarm_at = time.monotonic()
                self._ensure_warm()
        self._watch_silence()
        live = self._live
        if self.recorder.active and live is not None and not self.busy and live.done.is_set():
            if live.text.strip() or live.limit_hit.is_set():
                self._finish()
            else:
                message = live.error or messages.REQUEST_FAILED
                self._drop_recording()
                self._overlay("error", message)

    def _sync_tip(self):
        if self._key_for(self.service):
            self.tray.setToolTip(tr("Speech Dictation is ready"))
        else:
            self.tray.setToolTip(tr("Speech Dictation: add an API key"))

    def _fail(self, message):
        self._overlay("error", message[:80])

    def quit(self):
        if self._quitting:
            return
        self._quitting = True
        self.cancel_watch.stop()
        timer = getattr(self, "_update_timer", None)
        if timer is not None:
            timer.stop()
        desktop.stop()
        self.indicator.dismiss()
        self.button.hide()
        self.settings.hide()
        self.tray.hide()
        self.keys.stop()
        self._drop_recording()
        warm = self._warm
        self._warm = None
        if warm is not None:
            warm.cancel()
        from .crashlog import note
        note("quit")
        app = QApplication.instance()
        if app is not None:
            app.quit()
        # The tray and the hotkey thread otherwise keep this process alive,
        # so the next launch finds the shortcuts still taken.
        os._exit(0)

    def _activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle()

    def _load(self):
        path = paths.config_path()
        if not os.path.exists(path):
            return
        try:
            data = json.loads(open(path, encoding="utf-8").read())
        except Exception:
            return
        if "shortcut" in data:
            self.shortcut = data.get("shortcut") or ""
        if "translate" in data:
            self.translate = data.get("translate") or ""
        if data.get("language"):
            self.language = data["language"]
        if data.get("cancel"):
            self.cancel = data["cancel"]
        if data.get("api_key"):
            self.api_key = data["api_key"]
        if data.get("groq_key"):
            self.groq_key = data["groq_key"]
        if data.get("elevenlabs_key"):
            self.elevenlabs_key = data["elevenlabs_key"]
        if data.get("google_key"):
            self.google_key = data["google_key"]
        if data.get("service") in ("groq", "groq-turbo", "elevenlabs", "elevenlabs-live", "gemini"):
            self.service = data["service"]
        elif "service" not in data and self.api_key:
            # A config from the original app has only a Gemini key.
            self.service = "gemini"
        self.spoken = data.get("spoken") or ""
        if isinstance(data.get("auto_stop"), int):
            self.auto_stop = data["auto_stop"]
        if "trim" in data:
            self.trim = bool(data["trim"])
        if "no_verbatim" in data:
            self.no_verbatim = bool(data["no_verbatim"])
        # 2.0 kept a Groq model id and a correction switch; both became engines.
        old = {"openai/gpt-oss-120b": "groq-120b", "openai/gpt-oss-20b": "groq-20b"}
        translator = old.get(data.get("translator"), data.get("translator"))
        if translator in textproc.TRANSLATORS:
            self.translator = translator
        if data.get("corrector") in textproc.CORRECTORS:
            self.corrector = data["corrector"]
        elif self.service == "gemini":
            # Gemini had no correction, and translated live.
            self.corrector = "off"
            self.translator = "gemini-live"
        elif "correct" in data:
            groq_engine = translator if translator in ("groq-120b", "groq-20b") else "groq-120b"
            self.corrector = groq_engine if data["correct"] else "off"
        if isinstance(data.get("vocabulary"), str):
            self.vocabulary = data["vocabulary"]
        if data.get("app_language"):
            self.app_language = data["app_language"]
        if "sounds" in data:
            self.sounds = sounds.enabled = bool(data["sounds"])
        pos = data.get("widget_pos")
        if isinstance(pos, list) and len(pos) == 2:
            self.widget_pos = (int(pos[0]), int(pos[1]))

    def _store(self):
        os.makedirs(os.path.dirname(paths.config_path()), exist_ok=True)
        open(paths.config_path(), "w", encoding="utf-8").write(
            json.dumps({
                "api_key": self.api_key,
                "groq_key": self.groq_key,
                "elevenlabs_key": self.elevenlabs_key,
                "google_key": self.google_key,
                "service": self.service,
                "spoken": self.spoken,
                "auto_stop": self.auto_stop,
                "trim": self.trim,
                "no_verbatim": self.no_verbatim,
                "sounds": self.sounds,
                "translator": self.translator,
                "corrector": self.corrector,
                "vocabulary": self.vocabulary,
                "app_language": self.app_language,
                "widget_pos": list(self.widget_pos) if self.widget_pos else None,
                "shortcut": self.shortcut,
                "translate": self.translate,
                "language": self.language,
                "cancel": self.cancel,
            }, ensure_ascii=False)
        )

    def _overlay(self, kind, message=""):
        # Showing the overlay in the same event-loop turn as QAudioSource start/stop aborts the frozen build.
        QTimer.singleShot(0, lambda: self._show_overlay(kind, message))

    def _show_overlay(self, kind, message):
        if kind in ("recording", "busy") and self.button.isVisible():
            # The floating button already shows it, so the cursor stays clear.
            return
        if kind == "recording":
            self.indicator.show_recording()
        elif kind == "busy":
            self.indicator.show_busy()
        elif kind == "done":
            self.indicator.show_done()
        elif kind == "error":
            self.indicator.show_error(tr(message))
        elif kind == "hide":
            self.indicator.dismiss()

    def _sync_tray(self):
        self.tray.setIcon(self._dot(self.recorder.active))
        if self.busy or self._stopping:
            self.button.set_state("busy")
        elif self.recorder.active:
            self.button.set_state("recording", getattr(self, "_mode", "record"))
        else:
            self.button.set_state("idle")

    def _dot(self, listening):
        from PyQt6.QtGui import QPainter
        pix = QPixmap(32, 32)
        pix.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(QColor(240, 78, 82) if listening else QColor(154, 160, 170))
        painter.drawEllipse(8, 8, 16, 16)
        painter.end()
        return QIcon(pix)
