import os
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import i18n
from . import paths
from . import usage
from .i18n import tr

PERIODS = (
    ("Today", "today"),
    ("Last 7 days", "7"),
    ("This month", "month"),
    ("Last 30 days", "30"),
    ("All time", "all"),
)
KIND_LABELS = {"speech": "Dictation", "correct": "Fixing words", "translate": "Translating"}
CONSOLES = (
    ("Groq", "https://console.groq.com/dashboard/usage"),
    ("ElevenLabs", "https://elevenlabs.io/app/usage"),
    ("Gemini", "https://aistudio.google.com/usage"),
    ("Google Cloud", "https://console.cloud.google.com/billing"),
)


def since(period, now=None):
    now = time.time() if now is None else now
    day = time.localtime(now)
    midnight = time.mktime((day.tm_year, day.tm_mon, day.tm_mday, 0, 0, 0, 0, 0, -1))
    if period == "today":
        return midnight
    if period == "month":
        return time.mktime((day.tm_year, day.tm_mon, 1, 0, 0, 0, 0, 0, -1))
    if period == "all":
        return 0.0
    return midnight - (int(period) - 1) * 86400


def _date(iso):
    year, month, day = iso.split("-")
    return "%s.%s.%s" % (day, month, year) if i18n.current == "tr" else iso


def money(value):
    if value >= 1:
        return "$%.2f" % value
    if value == 0:
        return "$0"
    if value < 0.0001:
        return "<$0.0001"
    return "$%.4f" % value


def minutes(seconds):
    if seconds < 60:
        return tr("%d s") % round(seconds)
    if seconds < 3600:
        return tr("%.1f min") % (seconds / 60)
    return tr("%.1f h") % (seconds / 3600)


def amount(row):
    parts = []
    if row["seconds"]:
        parts.append(minutes(row["seconds"]))
    if row["tokens"]:
        count = row["tokens"]
        parts.append(tr("%s tokens") % ("%.1fK" % (count / 1000) if count >= 1000 else count))
    if row["chars"]:
        parts.append(tr("%s characters") % format(row["chars"], ","))
    return ", ".join(parts) or "-"


def _stat(title):
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(2)
    head = QLabel(title)
    head.setStyleSheet("color: #9aa0ac; font-size: 12px;")
    value = QLabel("-")
    value.setStyleSheet("color: #f2f4f8; font-size: 20px; font-weight: 600;")
    layout.addWidget(head)
    layout.addWidget(value)
    box.setStyleSheet("QWidget { background: #20242c; border-radius: 10px; }")
    box.value = value
    return box


class UsageWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("Usage") + " - Speech Dictation")
        self.setWindowIcon(QIcon(paths.ICON))
        self.setMinimumSize(640, 460)
        self.setStyleSheet(
            "QDialog { background: #17191e; }"
            "QLabel { color: #e7e9ee; font-size: 13px; }"
            "QComboBox { background: #242830; color: #f2f4f8; border: 1px solid #3c4250;"
            " border-radius: 8px; padding: 6px 10px; }"
            "QComboBox QAbstractItemView { background: #242830; color: #f2f4f8;"
            " selection-background-color: #3b82f6; }"
            "QPushButton { background: #2a2f39; color: #e7e9ee; border: 1px solid #3c4250;"
            " border-radius: 8px; padding: 7px 14px; }"
            "QPushButton:hover { background: #343a46; }"
            "QTableWidget { background: #1c1f25; color: #e7e9ee; border: 1px solid #2c313b;"
            " border-radius: 8px; gridline-color: #2c313b; font-size: 13px; }"
            "QTableWidget::item { padding: 4px 8px; }"
            "QHeaderView::section { background: #20242c; color: #9aa0ac; border: none;"
            " border-bottom: 1px solid #2c313b; padding: 6px 8px; font-size: 12px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(tr("Usage"))
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        top.addWidget(title)
        top.addStretch(1)
        self.period = QComboBox()
        for label, code in PERIODS:
            self.period.addItem(tr(label), code)
        self.period.setCurrentIndex(2)
        self.period.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.period)
        layout.addLayout(top)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self._cost = _stat(tr("Estimated cost"))
        self._count = _stat(tr("Dictations"))
        self._audio = _stat(tr("Audio"))
        for box in (self._cost, self._count, self._audio):
            stats.addWidget(box)
        layout.addLayout(stats)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [tr("Model"), tr("Used for"), tr("Requests"), tr("Amount"), tr("Estimated cost")])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.table, 1)

        self.empty = QLabel(tr("Nothing used in this period yet."))
        self.empty.setStyleSheet("color: #9aa0ac;")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty, 1)

        note = QLabel(
            tr("Estimates at list prices of %s. Free tiers and free monthly allowances are "
               "not taken off, because the app cannot see whether they still apply. "
               "Requests from before this page existed are not counted. The exact bill "
               "is on each provider's page:")
            % _date(usage.PRICES_DATE)
            + " " + " · ".join('<a style="color:#6ea8fe" href="%s">%s</a>' % (url, name) for name, url in CONSOLES))
        note.setWordWrap(True)
        note.setOpenExternalLinks(True)
        note.setStyleSheet("color: #9aa0ac; font-size: 12px;")
        layout.addWidget(note)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.clear_button = QPushButton(tr("Clear history"))
        self.clear_button.setAutoDefault(False)
        self.clear_button.clicked.connect(self._clear)
        bottom.addWidget(self.clear_button)
        layout.addLayout(bottom)

        # New dictations show up while the window is open.
        self._seen = None
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._poll)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def _stamp(self):
        try:
            info = os.stat(usage.path())
            return info.st_mtime, info.st_size
        except OSError:
            return None

    def _poll(self):
        if self._stamp() != self._seen:
            self.refresh()

    def refresh(self):
        self._seen = self._stamp()
        entries = usage.load(since(self.period.currentData()))
        rows, totals = usage.summarize(entries)
        cost = money(totals["cost"])
        if totals["unpriced"]:
            cost += " +"
        self._cost.value.setText(cost)
        self._count.value.setText(str(totals["dictations"]))
        self._audio.value.setText(minutes(totals["seconds"]) if totals["seconds"] else "-")
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            spent = money(row["cost"])
            if row["unpriced"]:
                spent = tr("no price") if not row["cost"] else spent + " +"
            cells = (
                usage.label(row["model"]),
                ", ".join(tr(KIND_LABELS[kind]) for kind in row["kinds"]),
                str(row["requests"]),
                amount(row),
                spent,
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(index, column, item)
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        self.clear_button.setEnabled(bool(usage.load()))

    def _clear(self):
        answer = QMessageBox.question(
            self, tr("Clear history"),
            tr("Delete the whole usage history on this computer? This cannot be undone."))
        if answer == QMessageBox.StandardButton.Yes:
            usage.clear()
            self.refresh()
