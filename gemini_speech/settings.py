from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
import sys

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from . import __version__
from . import hotkey
from . import i18n
from . import messages
from . import paths
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
    ("Gemini Live", "gemini"),
)

TRANSLATORS = (
    ("GPT-OSS 120B", "recommended", "openai/gpt-oss-120b"),
    ("GPT-OSS 20B", "fastest", "openai/gpt-oss-20b"),
)

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

    def mousePressEvent(self, event):
        self._previous = self.text()
        self._capturing = True
        self.setText("")
        self.setPlaceholderText(tr("Press the keys"))
        self.setFocus()
        event.accept()

    def focusOutEvent(self, event):
        if self._capturing:
            self._capturing = False
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
            self._capturing = False
            self.setText(self._previous)
            return
        combo = _combo(event, self._allow_bare)
        if not combo:
            return
        self._capturing = False
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
    if note:
        hint = QLabel(note)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        outer.addWidget(hint)
    return box


class Settings(QDialog):
    def __init__(self, on_save, on_close):
        super().__init__()
        self._on_save = on_save
        self._on_close = on_close
        self.setWindowTitle("Speech Dictation")
        self.setWindowIcon(QIcon(paths.ICON))
        self.setMinimumWidth(440)
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
        self.groq_key = QLineEdit()
        self.groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key.setPlaceholderText(tr("console.groq.com API key"))
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText(tr("AI Studio API key"))
        self.spoken = QComboBox()
        self.spoken.addItem(tr("Detect automatically"), "")
        for label, code in LANGUAGES:
            self.spoken.addItem(tr(label), code)
        self.vocabulary = QLineEdit()
        self.vocabulary.setPlaceholderText(tr("Names and terms, separated by commas"))
        self.correct = QCheckBox(tr("Smart correction: fix misheard words"))
        self.translator = QComboBox()
        for label, note, code in TRANSLATORS:
            self.translator.addItem("%s (%s)" % (label, tr(note)), code)
        self.auto_stop = QComboBox()
        for seconds in AUTO_STOP:
            label = tr("After %d s of silence") % seconds if seconds else tr("Off")
            self.auto_stop.addItem(label, seconds)
        self.trim = QCheckBox(tr("Cut pauses before sending"))
        self.sounds = QCheckBox(tr("Play a sound when listening starts and stops"))
        self.startup = QCheckBox(tr("Start with Windows"))
        self.shortcut = ShortcutField()
        self.translate = ShortcutField()
        self.language = QComboBox()
        for label, code in LANGUAGES:
            self.language.addItem(tr(label), code)
        self.app_language = QComboBox()
        for label, code in i18n.LANGUAGES:
            self.app_language.addItem(label, code)
        self.cancel = ShortcutField(allow_bare=True)

        top = _form()
        top.layout().addRow(_label(tr("Service")), self.service)
        layout.addWidget(top)

        # Only the chosen service's own settings show; the general ones always do.
        self._groq = _section("Groq", [
            (tr("Groq key"), self.groq_key),
            (tr("I speak"), self.spoken),
            (tr("Text model"), self.translator),
            (tr("Vocabulary"), self.vocabulary),
            ("", self.correct),
            ("", self.trim),
        ], tr("Whisper writes down what you say. The Text model fixes words it misheard "
              "and does the translating. Vocabulary words are always spelled the way you "
              "write them."))
        self._gemini = _section("Gemini", [
            (tr("Gemini key"), self.api_key),
        ], tr("Gemini Live writes down what you say as you speak, and translates it live."))
        general = [
            (tr("App language"), self.app_language),
            (tr("Record"), self.shortcut),
            (tr("Translate"), self.translate),
            (tr("Translate to"), self.language),
            (tr("Cancel"), self.cancel),
            (tr("Auto-stop"), self.auto_stop),
            ("", self.sounds),
        ]
        if sys.platform == "win32":
            general.append(("", self.startup))
        self._general = _section(tr("General"), general,
            tr("The lock on the floating button keeps it listening through pauses until you stop it."))
        layout.addWidget(self._groq)
        layout.addWidget(self._gemini)
        layout.addWidget(self._general)

        self._save_button = QPushButton(tr("Save"))
        self._save_button.setAutoDefault(False)
        self._save_button.clicked.connect(self._save)
        layout.addWidget(self._save_button)
        layout.addWidget(VersionLink())
        self.service.currentIndexChanged.connect(self._show_service)
        self._show_service()

    def _show_service(self):
        gemini = self.service.currentData() == "gemini"
        self._groq.setVisible(not gemini)
        self._gemini.setVisible(gemini)
        if self.isVisible():
            QTimer.singleShot(0, self._fit)

    def set_values(self, values):
        self.api_key.setText(values["api_key"])
        self.groq_key.setText(values["groq_key"])
        shortcut, translate, cancel = values["shortcut"], values["translate"], values["cancel"]
        self.shortcut.owned = shortcut
        self.translate.owned = translate
        self.cancel.owned = cancel
        self.shortcut.setText(shortcut)
        self.translate.setText(translate)
        self.cancel.setText(cancel)
        for combo, value in (
            (self.language, values["language"]),
            (self.translator, values["translator"]),
            (self.app_language, values["app_language"]),
            (self.service, values["service"]),
            (self.spoken, values["spoken"]),
            (self.auto_stop, values["auto_stop"]),
        ):
            index = combo.findData(value)
            combo.setCurrentIndex(index if index >= 0 else 0)
        self.trim.setChecked(values["trim"])
        self.sounds.setChecked(values["sounds"])
        self.correct.setChecked(values["correct"])
        self.vocabulary.setText(values["vocabulary"])
        self.startup.setChecked(values["startup"])

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
        key = self.api_key.text().strip()
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
            "api_key": key,
            "groq_key": self.groq_key.text().strip(),
            "service": self.service.currentData() or "groq",
            "spoken": self.spoken.currentData() or "",
            "auto_stop": int(self.auto_stop.currentData() or 0),
            "trim": self.trim.isChecked(),
            "sounds": self.sounds.isChecked(),
            "correct": self.correct.isChecked(),
            "vocabulary": self.vocabulary.text().strip(),
            "app_language": self.app_language.currentData() or "en",
            "startup": self.startup.isChecked(),
            "shortcut": record,
            "translate": translate,
            "language": language,
            "translator": self.translator.currentData() or TRANSLATORS[0][2],
            "cancel": cancel,
        })
        self._save_button.setText(tr("Saved"))
        QTimer.singleShot(1500, lambda: self._save_button.setText(tr("Save")))
