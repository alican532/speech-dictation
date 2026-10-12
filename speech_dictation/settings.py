from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
import sys

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from . import __version__
from . import hotkey
from . import i18n
from . import messages
from . import paths
from . import textproc
from .i18n import tr

LANGUAGES = (
    ("English", "en"),
    ("Turkish", "tr"),
    ("German", "de"),
    ("French", "fr"),
    ("Spanish", "es"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Polish", "pl"),
    ("Russian", "ru"),
    ("Ukrainian", "uk"),
    ("Arabic", "ar"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
)

SERVICES = (
    ("Groq Whisper Large v3", "groq"),
    ("Groq Whisper Large v3 Turbo", "groq-turbo"),
    ("ElevenLabs Scribe v2", "elevenlabs"),
    ("ElevenLabs Scribe v2 Realtime", "elevenlabs-live"),
    ("Gemini Live", "gemini"),
)

SERVICE_NOTES = {
    "groq": "Whisper writes down what you say once you stop. Vocabulary words are spelled the way you write them.",
    "groq-turbo": "Whisper writes down what you say once you stop. Vocabulary words are spelled the way you write them.",
    "elevenlabs": "Scribe writes down what you say once you stop. Vocabulary words are listened for and spelled the way you write them.",
    "elevenlabs-live": "Scribe writes down what you say while you speak, so the text is ready soon after you stop. Vocabulary words are listened for. ElevenLabs edit needs Scribe v2.",
    "gemini": "Gemini Live writes down what you say as you speak, and translates it live.",
}

# engine -> (label, note)
ENGINE_LABELS = {
    "off": ("Off", ""),
    "elevenlabs": ("ElevenLabs edit", "same request"),
    "groq-120b": ("Groq GPT-OSS 120B", "recommended"),
    "groq-20b": ("Groq GPT-OSS 20B", "fastest"),
    "gemini-lite": ("Gemini Flash-Lite", "fast"),
    "gemini-flash": ("Gemini Flash", ""),
    "google": ("Google Translate", ""),
    "gemini-live": ("Gemini Live", "live"),
}

AUTO_STOP = (0, 2, 3, 4, 5, 8)

REPO_URL = "https://github.com/alican532/speech-dictation"


class VersionLink(QLabel):
    def __init__(self):
        super().__init__(__version__)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(REPO_URL.split("//", 1)[1])
        self.setStyleSheet("color: #7d8490; font-size: 11px;")

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl(REPO_URL))
        event.accept()


class ShortcutField(QLineEdit):
    _MODS = {
        Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
    }

    def __init__(self, allow_bare=False):
        super().__init__()
        self._allow_bare = allow_bare
        self._capturing = False
        self._previous = ""
        self.setReadOnly(True)
        self.setPlaceholderText(tr("Click, then press the keys"))
        self.owned = ""
        # Told when capture starts and ends: the app's shortcuts would
        # otherwise take the keys before this field sees them.
        self.on_capture = None

    def _set_capturing(self, on):
        if self._capturing == on:
            return
        self._capturing = on
        if self.on_capture is not None:
            self.on_capture(on)

    def mousePressEvent(self, event):
        self._previous = self.text()
        self._set_capturing(True)
        self.setText("")
        self.setPlaceholderText(tr("Press the keys"))
        self.setFocus()
        event.accept()

    def focusOutEvent(self, event):
        if self._capturing:
            self._set_capturing(False)
            self.setText(self._previous)
            self.setPlaceholderText(tr("Click, then press the keys"))
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            event.ignore()
            return
        event.accept()
        if event.key() in self._MODS:
            return
        if event.key() == Qt.Key.Key_Escape:
            self._set_capturing(False)
            self.setText(self._previous)
            return
        combo = _combo(event, self._allow_bare)
        if not combo:
            return
        self._set_capturing(False)
        self.setPlaceholderText(tr("Click, then press the keys"))
        reason = hotkey.windows_conflict(combo, current=self.owned or self._previous)
        if reason:
            self.setText(self._previous)
            QMessageBox.warning(self.window(), tr(messages.SHORTCUT_TITLE), reason)
            return
        self.setText(combo)


def _combo(event, allow_bare=False):
    mods = event.modifiers()
    parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        parts.append("Shift")
    if mods & Qt.KeyboardModifier.MetaModifier:
        parts.append("Meta")
    key = event.key()
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z or Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        name = chr(key)
    elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        name = "F%d" % (key - Qt.Key.Key_F1 + 1)
    elif key == Qt.Key.Key_Space:
        name = "Space"
    elif key == Qt.Key.Key_Escape:
        name = "Esc"
    else:
        name = ""
    if not name or (not parts and not allow_bare):
        return ""
    return "+".join(parts + [name])


LABEL_WIDTH = 118


def _label(text):
    label = QLabel(text)
    label.setFixedWidth(LABEL_WIDTH)
    return label


def _form():
    box = QWidget()
    form = QFormLayout(box)
    form.setContentsMargins(0, 0, 0, 0)
    form.setSpacing(10)
    return box


def _section(title, rows, note=""):
    box = QWidget()
    outer = QVBoxLayout(box)
    outer.setContentsMargins(0, 6, 0, 0)
    outer.setSpacing(8)
    head = QLabel(title.upper())
    head.setStyleSheet("color: #7d8490; font-size: 11px; font-weight: 600; letter-spacing: 1px;"
                       " border-bottom: 1px solid #2c313b; padding-bottom: 4px;")
    outer.addWidget(head)
    inner = _form()
    for text, widget in rows:
        inner.layout().addRow(_label(text), widget)
    outer.addWidget(inner)
    box.form = inner.layout()
    box.note = None
    if note:
        hint = box.note = QLabel(note)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        outer.addWidget(hint)
    return box


def _key_field(placeholder):
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    return field


class Settings(QDialog):
    def __init__(self, on_save, on_close, on_capture=None, on_usage=None):
        super().__init__()
        self._on_save = on_save
        self._on_close = on_close
        self._on_capture = on_capture
        self.setWindowTitle("Speech Dictation")
        self.setWindowIcon(QIcon(paths.ICON))
        self.setMinimumWidth(460)
        self.setStyleSheet(
            "QDialog { background: #17191e; }"
            "QLabel { color: #e7e9ee; font-size: 13px; }"
            "QLineEdit, QComboBox { background: #242830; color: #f2f4f8; border: 1px solid #3c4250;"
            " border-radius: 8px; padding: 8px 10px; }"
            "QComboBox QAbstractItemView { background: #242830; color: #f2f4f8;"
            " selection-background-color: #3b82f6; }"
            "QPushButton { background: #3b82f6; color: white; border: none;"
            " border-radius: 8px; padding: 8px 14px; }"
            "QPushButton:hover { background: #5b97f7; }"
            "QCheckBox { color: #e7e9ee; font-size: 13px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        self.service = QComboBox()
        for label, code in SERVICES:
            self.service.addItem(label, code)
        self.groq_key = _key_field(tr("console.groq.com API key"))
        self.elevenlabs_key = _key_field(tr("elevenlabs.io API key"))
        self.api_key = _key_field(tr("AI Studio API key"))
        self.google_key = _key_field(tr("Google Cloud key with Cloud Translation on"))
        self._keys = {
            "groq": self.groq_key, "elevenlabs": self.elevenlabs_key,
            "gemini": self.api_key, "google": self.google_key,
        }
        self.spoken = QComboBox()
        self.spoken.addItem(tr("Detect automatically"), "")
        for label, code in LANGUAGES:
            self.spoken.addItem(tr(label), code)
        self.vocabulary = QLineEdit()
        self.vocabulary.setPlaceholderText(tr("Names and terms, separated by commas"))
        self.corrector = QComboBox()
        self.translator = QComboBox()
        # The engine picked last, kept while another service hides it.
        self._chosen = {"corrector": "off", "translator": ""}
        self.auto_stop = QComboBox()
        for seconds in AUTO_STOP:
            label = tr("After %d s of silence") % seconds if seconds else tr("Off")
            self.auto_stop.addItem(label, seconds)
        self.trim = QCheckBox(tr("Cut pauses before sending"))
        self.no_verbatim = QCheckBox(tr("Leave out filler words (um, uh)"))
        self.sounds = QCheckBox(tr("Play a sound when listening starts and stops"))
        self.startup = QCheckBox(tr("Start with Windows") if sys.platform == "win32" else tr("Start at login"))
        self.shortcut = ShortcutField()
        self.translate = ShortcutField()
        self.language = QComboBox()
        for label, code in LANGUAGES:
            self.language.addItem(tr(label), code)
        self.app_language = QComboBox()
        for label, code in i18n.LANGUAGES:
            self.app_language.addItem(label, code)
        self.cancel = ShortcutField(allow_bare=True)
        for field in (self.shortcut, self.translate, self.cancel):
            field.on_capture = on_capture

        top = _form()
        top.layout().addRow(_label(tr("Service")), self.service)
        layout.addWidget(top)

        # Only what the chosen service and engines use shows.
        self._keys_box = _section(tr("API keys"), [
            (tr("Groq key"), self.groq_key),
            (tr("ElevenLabs key"), self.elevenlabs_key),
            (tr("Gemini key"), self.api_key),
            (tr("Google key"), self.google_key),
        ])
        self._speech = _section(tr("Speech"), [
            (tr("I speak"), self.spoken),
            (tr("Vocabulary"), self.vocabulary),
            ("", self.trim),
            ("", self.no_verbatim),
        ], " ")
        self._text = _section(tr("Text"), [
            (tr("Correction"), self.corrector),
            (tr("Translation"), self.translator),
            (tr("Translate to"), self.language),
        ], tr("Correction fixes words the speech service misheard. Translation runs when "
              "you use the Translate shortcut or the badge on the button. ElevenLabs edit "
              "adds 30% to the ElevenLabs price; Google Translate only translates."))
        general = [
            (tr("App language"), self.app_language),
            (tr("Record"), self.shortcut),
            (tr("Translate"), self.translate),
            (tr("Cancel"), self.cancel),
            (tr("Auto-stop"), self.auto_stop),
            ("", self.sounds),
            ("", self.startup),
        ]
        self._general = _section(tr("General"), general,
            tr("The lock on the floating button keeps it listening through pauses until you stop it."))
        for box in (self._keys_box, self._speech, self._text, self._general):
            layout.addWidget(box)

        self._save_button = QPushButton(tr("Save"))
        self._save_button.setAutoDefault(False)
        self._save_button.clicked.connect(self._save)
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        if on_usage is not None:
            usage = QPushButton(tr("Usage"))
            usage.setAutoDefault(False)
            usage.setStyleSheet("QPushButton { background: #2a2f39; border: 1px solid #3c4250; }"
                                "QPushButton:hover { background: #343a46; }")
            usage.clicked.connect(on_usage)
            buttons.addWidget(usage)
        buttons.addWidget(self._save_button, 1)
        layout.addLayout(buttons)
        layout.addWidget(VersionLink())
        self.service.currentIndexChanged.connect(self._refresh)
        self.corrector.activated.connect(lambda: self._pick("corrector"))
        self.translator.activated.connect(lambda: self._pick("translator"))
        self._refresh()

    def _pick(self, kind):
        combo = self.corrector if kind == "corrector" else self.translator
        self._chosen[kind] = combo.currentData()
        self._refresh()

    def _fill(self, kind, service):
        combo = self.corrector if kind == "corrector" else self.translator
        choices = textproc.CORRECTORS if kind == "corrector" else textproc.TRANSLATORS
        picked = textproc.usable(kind, self._chosen[kind], service)
        combo.blockSignals(True)
        combo.clear()
        for engine in choices:
            if textproc.available(engine, service):
                label, note = ENGINE_LABELS[engine]
                combo.addItem("%s (%s)" % (tr(label), tr(note)) if note else tr(label), engine)
        combo.setCurrentIndex(max(0, combo.findData(picked)))
        combo.blockSignals(False)

    def _refresh(self):
        service = self.service.currentData() or "groq"
        self._fill("corrector", service)
        self._fill("translator", service)
        corrector = self.corrector.currentData()
        translator = self.translator.currentData()
        own = textproc.service_provider(service)
        needed = {own, textproc.key_provider(translator)}
        if corrector != "off":
            needed.add(textproc.key_provider(corrector))
        form = self._keys_box.form
        for provider, field in self._keys.items():
            form.setRowVisible(field, provider in needed)
        live = service == "gemini"
        prompts = corrector != "off" or translator not in ("google", "gemini-live", "elevenlabs")
        form = self._speech.form
        form.setRowVisible(self.spoken, not live or corrector != "off")
        form.setRowVisible(self.vocabulary, not live or prompts)
        form.setRowVisible(self.trim, service in ("groq", "groq-turbo", "elevenlabs"))
        form.setRowVisible(self.no_verbatim, own == "elevenlabs")
        self._speech.note.setText(tr(SERVICE_NOTES[service]))
        if self.isVisible():
            QTimer.singleShot(0, self._fit)

    def set_values(self, values):
        for provider, field in self._keys.items():
            field.setText(values["keys"].get(provider, ""))
        shortcut, translate, cancel = values["shortcut"], values["translate"], values["cancel"]
        self.shortcut.owned = shortcut
        self.translate.owned = translate
        self.cancel.owned = cancel
        self.shortcut.setText(shortcut)
        self.translate.setText(translate)
        self.cancel.setText(cancel)
        for combo, value in (
            (self.language, values["language"]),
            (self.app_language, values["app_language"]),
            (self.spoken, values["spoken"]),
            (self.auto_stop, values["auto_stop"]),
        ):
            index = combo.findData(value)
            combo.setCurrentIndex(index if index >= 0 else 0)
        self._chosen = {"corrector": values["corrector"], "translator": values["translator"]}
        self.service.blockSignals(True)
        self.service.setCurrentIndex(max(0, self.service.findData(values["service"])))
        self.service.blockSignals(False)
        self.trim.setChecked(values["trim"])
        self.no_verbatim.setChecked(values["no_verbatim"])
        self.sounds.setChecked(values["sounds"])
        self.vocabulary.setText(values["vocabulary"])
        self.startup.setChecked(values["startup"])
        self._refresh()

    def closeEvent(self, event):
        super().closeEvent(event)
        self._on_close()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._fit)

    def _fit(self):
        layout = self.layout()
        layout.invalidate()
        layout.activate()
        hint = layout.sizeHint()
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        height = hint.height()
        self.resize(max(self.minimumWidth(), hint.width()), height)
        self.setFixedHeight(height)

    def _save(self):
        record = self.shortcut.text().strip()
        translate = self.translate.text().strip()
        cancel = self.cancel.text().strip() or "Esc"
        language = self.language.currentData() or "en"
        if record and translate and hotkey.same_shortcut(record, translate):
            QMessageBox.warning(self, tr(messages.SHORTCUT_TITLE), tr(messages.SHORTCUT_SAME))
            return
        if record:
            reason = hotkey.windows_conflict(record, current=self.shortcut.owned)
            if reason:
                QMessageBox.warning(self, tr(messages.SHORTCUT_TITLE), reason)
                return
        if translate:
            reason = hotkey.windows_conflict(translate, current=self.translate.owned)
            if reason:
                QMessageBox.warning(self, tr(messages.SHORTCUT_TITLE), reason)
                return
        cancel_reason = hotkey.windows_conflict(cancel, probe=False, current=self.cancel.owned)
        if cancel_reason:
            QMessageBox.warning(self, tr(messages.SHORTCUT_TITLE), cancel_reason)
            return
        self._on_save({
            "keys": {provider: field.text().strip() for provider, field in self._keys.items()},
            "service": self.service.currentData() or "groq",
            "spoken": self.spoken.currentData() or "",
            "auto_stop": int(self.auto_stop.currentData() or 0),
            "trim": self.trim.isChecked(),
            "no_verbatim": self.no_verbatim.isChecked(),
            "sounds": self.sounds.isChecked(),
            "corrector": self._chosen["corrector"] or "off",
            "translator": self._chosen["translator"] or self.translator.currentData(),
            "vocabulary": self.vocabulary.text().strip(),
            "app_language": self.app_language.currentData() or "en",
            "startup": self.startup.isChecked(),
            "shortcut": record,
            "translate": translate,
            "language": language,
            "cancel": cancel,
        })
        self._save_button.setText(tr("Saved"))
        QTimer.singleShot(1500, lambda: self._save_button.setText(tr("Save")))
