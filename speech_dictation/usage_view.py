import os
import time

from PyQt6.QtCore import QRectF, QStandardPaths, Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QToolTip, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import i18n
from . import paths
from . import usage
from .controls import Combo
from .i18n import tr

PERIODS = (
    ("Today", "today"),
    ("Last 7 days", "7"),
    ("This month", "month"),
    ("Last 30 days", "30"),
    ("All time", "all"),
)
KIND_LABELS = {"speech": "Dictation", "correct": "Fixing words", "translate": "Translating"}
STATUS_LABELS = {"done": "Done", "empty": "Nothing heard", "cancelled": "Cancelled", "failed": "Failed"}
CONSOLES = (
    ("Groq", "https://console.groq.com/dashboard/usage"),
    ("ElevenLabs", "https://elevenlabs.io/app/usage"),
    ("Gemini", "https://aistudio.google.com/usage"),
    ("Google Cloud", "https://console.cloud.google.com/billing"),
)
ACCENT = "#3b82f6"
MUTED = "#9aa0ac"
WARN = "#f0b35a"


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


def _number(value, digits=1):
    text = ("%%.%df" % digits) % value
    if digits:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",") if i18n.current == "tr" else text


def money(value):
    if value >= 1:
        return "$%.2f" % value
    if value == 0:
        return "$0"
    if value < 0.0001:
        return "<$0.0001"
    return "$%.4f" % value


def rate(value):
    return "$" + ("%.4f" % value).rstrip("0").rstrip(".")


def minutes(seconds):
    if seconds < 60:
        return tr("%s s") % _number(seconds, 1 if seconds < 10 else 0)
    if seconds < 3600:
        return tr("%s min") % _number(seconds / 60)
    return tr("%s h") % _number(seconds / 3600)


def stamp(moment):
    form = "%d.%m.%Y %H:%M:%S" if i18n.current == "tr" else "%Y-%m-%d %H:%M:%S"
    return time.strftime(form, time.localtime(moment))


def tokens(count):
    return "%sK" % _number(count / 1000) if count >= 1000 else str(count)


def amount(row):
    parts = []
    if row["seconds"]:
        parts.append(minutes(row["seconds"]))
    if row["tokens"]:
        parts.append(tr("%s tokens") % tokens(row["tokens"]))
    if row["chars"]:
        parts.append(tr("%s characters") % format(row["chars"], ","))
    return ", ".join(parts) or "-"


def entry_amount(entry):
    parts = []
    if entry.get("seconds"):
        text = minutes(entry["seconds"])
        if entry.get("recorded"):
            text += " " + tr("(recorded %s)") % minutes(entry["recorded"])
        parts.append(text)
    if entry.get("in") or entry.get("out"):
        parts.append(tr("%s in + %s out tokens") % (entry.get("in", 0), entry.get("out", 0)))
    if entry.get("chars"):
        parts.append(tr("%s characters") % format(entry["chars"], ","))
    return ", ".join(parts) or "-"


UNITS = {"hour": "/h", "minute": "/min", "million": "/M"}
PART_LABELS = {
    "audio": "%s",
    "keyterms": "vocabulary %s",
    "edit": "edit %s",
    "input": "%s in",
    "output": "%s out",
    "chars": "%s characters",
}


def calculation(entry):
    """How the cost was worked out, in words."""
    if entry.get("unbilled"):
        return tr("not billed: the request was refused")
    pieces = usage.entry_parts(entry)
    if pieces is None:
        return tr("not in the price table")
    out = []
    for what, count, unit_price, unit, _dollars in pieces:
        shown = minutes(count) if what in ("audio", "keyterms", "edit") else format(int(count), ",")
        text = tr(PART_LABELS[what]) % shown
        text += " × %s%s" % (rate(unit_price), tr(UNITS[unit]))
        if what == "audio" and count > (entry.get("seconds") or 0) + 0.01:
            text += " " + tr("(at least %s a request)") % minutes(count)
        out.append(text)
    return " + ".join(out) or "-"


def kinds_text(kinds):
    return ", ".join(tr(KIND_LABELS[kind]) for kind in kinds)


def _stat(title):
    box = QWidget()
    box.setObjectName("stat")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(2)
    head = QLabel(title)
    head.setStyleSheet("color: %s; font-size: 12px; background: transparent;" % MUTED)
    value = QLabel("-")
    value.setStyleSheet("color: #f2f4f8; font-size: 20px; font-weight: 600; background: transparent;")
    sub = QLabel("")
    sub.setStyleSheet("color: %s; font-size: 11px; background: transparent;" % MUTED)
    for widget in (head, value, sub):
        layout.addWidget(widget)
    box.setStyleSheet("#stat { background: #20242c; border-radius: 10px; }")
    box.value = value
    box.sub = sub
    return box


def _item(text, right=False, color=None, tip=""):
    item = QTableWidgetItem(text)
    if right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if color:
        item.setForeground(QColor(color))
    if tip:
        item.setToolTip(tip)
    return item


def _fit_columns(view, columns):
    # Fitting to the text alone leaves no room for the cell padding.
    header = view.header() if isinstance(view, QTreeWidget) else view.horizontalHeader()
    for column in columns:
        view.resizeColumnToContents(column)
        header.resizeSection(column, header.sectionSize(column) + 18)


class SpendChart(QWidget):
    """Bars of estimated cost per hour, day or month."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(110)
        self.setMouseTracking(True)
        self._unit = "day"
        self._bars = []

    def set_data(self, unit, bars):
        self._unit = unit
        self._bars = bars
        self.update()

    def _area(self):
        return QRectF(4, 18, self.width() - 8, self.height() - 38)

    def _label(self, moment):
        if self._unit == "hour":
            return time.strftime("%H:00", time.localtime(moment))
        if self._unit == "month":
            return time.strftime("%m.%Y" if i18n.current == "tr" else "%Y-%m", time.localtime(moment))
        return time.strftime("%d.%m" if i18n.current == "tr" else "%m-%d", time.localtime(moment))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1c1f25"))
        if not self._bars:
            return
        area = self._area()
        top = max(spent for _moment, spent in self._bars)
        painter.setPen(QColor(MUTED))
        font = painter.font()
        font.setPixelSize(11)
        painter.setFont(font)
        painter.drawText(QRectF(area.left(), 0, area.width(), 16), Qt.AlignmentFlag.AlignLeft,
                         tr("Highest: %s") % money(top) if top else tr("No cost in this period"))
        width = area.width() / len(self._bars)
        gap = 2 if width > 6 else 0
        for index, (_moment, spent) in enumerate(self._bars):
            x = area.left() + index * width
            painter.fillRect(QRectF(x + gap / 2, area.bottom() - 1, max(1, width - gap), 1), QColor("#2c313b"))
            if top and spent:
                height = max(2.0, area.height() * spent / top)
                painter.fillRect(QRectF(x + gap / 2, area.bottom() - height, max(1, width - gap), height),
                                 QColor(ACCENT))
        painter.setPen(QColor(MUTED))
        bottom = QRectF(area.left(), area.bottom() + 4, area.width(), 16)
        painter.drawText(bottom, Qt.AlignmentFlag.AlignLeft, self._label(self._bars[0][0]))
        painter.drawText(bottom, Qt.AlignmentFlag.AlignRight, self._label(self._bars[-1][0]))

    def mouseMoveEvent(self, event):
        if not self._bars:
            return
        area = self._area()
        index = int((event.position().x() - area.left()) / (area.width() / len(self._bars)))
        if 0 <= index < len(self._bars):
            moment, spent = self._bars[index]
            QToolTip.showText(event.globalPosition().toPoint(), "%s  %s" % (self._label(moment), money(spent)), self)


class UsageWindow(QDialog):
    def __init__(self, budget=lambda: 0.0):
        super().__init__()
        self._budget = budget
        self.setWindowTitle(tr("Usage") + " - Speech Dictation")
        self.setWindowIcon(QIcon(paths.ICON))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint
                            | Qt.WindowType.WindowCloseButtonHint)
        self.setMinimumSize(760, 600)
        self.resize(1100, 720)
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
            "QPushButton:checked { background: #3b82f6; border-color: #3b82f6; color: white; }"
            "QTableWidget, QTreeWidget { background: #1c1f25; color: #e7e9ee; border: 1px solid #2c313b;"
            " border-radius: 8px; gridline-color: #2c313b; font-size: 13px; }"
            "QTableWidget::item, QTreeWidget::item { padding: 4px 6px; }"
            "QTreeWidget::item:selected, QTableWidget::item:selected { background: #2a3550; }"
            "QHeaderView { background: #20242c; }"
            "QHeaderView::section { background: #20242c; color: #9aa0ac; border: none;"
            " border-bottom: 1px solid #2c313b; padding: 6px 8px; font-size: 12px; }"
            "QTabWidget::pane { border: none; }"
            "QTabBar::tab { background: transparent; color: #9aa0ac; padding: 7px 16px;"
            " border-bottom: 2px solid transparent; font-size: 13px; }"
            "QTabBar::tab:selected { color: #f2f4f8; border-bottom: 2px solid #3b82f6; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(tr("Usage"))
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        top.addWidget(title)
        top.addStretch(1)
        self.period = Combo()
        for label, code in PERIODS:
            self.period.addItem(tr(label), code)
        self.period.setCurrentIndex(2)
        self.period.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.period)
        layout.addLayout(top)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_summary(), tr("Summary"))
        self.tabs.addTab(self._build_details(), tr("Details"))
        layout.addWidget(self.tabs, 1)

        note = QLabel(
            tr("Estimates at list prices of %s. Free tiers and free monthly allowances are "
               "not taken off, because the app cannot see whether they still apply. "
               "Requests from before this page existed are not counted. The exact bill "
               "is on each provider's page:")
            % _date(usage.PRICES_DATE)
            + " " + " · ".join('<a style="color:#6ea8fe" href="%s">%s</a>' % (url, name) for name, url in CONSOLES))
        note.setWordWrap(True)
        note.setOpenExternalLinks(True)
        note.setStyleSheet("color: %s; font-size: 12px;" % MUTED)
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

    # Summary

    def _build_summary(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)
        stats = QHBoxLayout()
        stats.setSpacing(10)
        self._cost = _stat(tr("Estimated cost"))
        self._count = _stat(tr("Dictations"))
        self._audio = _stat(tr("Audio sent"))
        self._saved = _stat(tr("Saved by cutting pauses"))
        for box in (self._cost, self._count, self._audio, self._saved):
            stats.addWidget(box)
        layout.addLayout(stats)
        self.chart = SpendChart()
        layout.addWidget(self.chart)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [tr("Model"), tr("Used for"), tr("Requests"), tr("Amount"), tr("Average wait"), tr("Estimated cost")])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setToolTip(tr("Double-click a model to see its requests"))
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.cellDoubleClicked.connect(self._open_model)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.table, 1)
        self.empty = QLabel(tr("Nothing used in this period yet."))
        self.empty.setStyleSheet("color: %s;" % MUTED)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty, 1)
        return page

    def _fill_summary(self, entries, start):
        rows, totals = usage.summarize(entries)
        cost = money(totals["cost"]) + (" +" if totals["unpriced"] else "")
        self._cost.value.setText(cost)
        budget = self._budget() or 0
        if budget and self.period.currentData() == "month":
            share = totals["cost"] / budget * 100
            self._cost.sub.setText(tr("%s%% of the budget (%s)") % (_number(share, 0), money(budget)))
            self._cost.sub.setStyleSheet("color: %s; font-size: 11px; background: transparent;"
                                         % (WARN if share >= 100 else MUTED))
        else:
            self._cost.sub.setText(tr("%s on unfinished takes") % money(totals["wasted"])
                                   if totals["wasted"] else "")
            self._cost.sub.setStyleSheet("color: %s; font-size: 11px; background: transparent;" % MUTED)
        self._count.value.setText(str(totals["dictations"]))
        unfinished = sum(1 for entry in entries if entry.get("kind") == "speech" and entry.get("status") != "done")
        self._count.sub.setText(tr("%d without text") % unfinished if unfinished else "")
        self._audio.value.setText(minutes(totals["seconds"]) if totals["seconds"] else "-")
        cut = totals["recorded"] - totals["seconds"]
        self._audio.sub.setText(tr("recorded %s") % minutes(totals["recorded"]) if cut > 0.5 else "")
        self._saved.value.setText(money(totals["saved"]) if totals["saved"] else "-")
        self._saved.sub.setText(tr("%s of silence cut") % minutes(cut) if cut > 0.5 else "")

        end = time.time()
        if not start:
            start = min((entry.get("t", end) for entry in entries), default=end)
        unit, bars = usage.buckets(entries, start, end)
        self.chart.set_data(unit, bars if entries else [])
        self.chart.setVisible(bool(entries))

        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            spent = money(row["cost"])
            if row["unpriced"]:
                spent = tr("no price") if not row["cost"] else spent + " +"
            cells = (
                _item(usage.label(row["model"])),
                _item(kinds_text(row["kinds"])),
                _item(str(row["requests"]), True),
                _item(amount(row), True),
                _item(tr("%s s") % _number(row["wait"]) if row["wait"] else "-", True),
                _item(spent, True),
            )
            cells[0].setData(Qt.ItemDataRole.UserRole, row["model"])
            for column, item in enumerate(cells):
                self.table.setItem(index, column, item)
        _fit_columns(self.table, range(1, 6))
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)

    def _open_model(self, row, _column):
        model = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        index = self.model_filter.findData(model)
        if index >= 0:
            self.model_filter.setCurrentIndex(index)
        self.tabs.setCurrentIndex(1)

    # Details

    def _build_details(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.flat_button = QPushButton(tr("Every request"))
        self.grouped_button = QPushButton(tr("By dictation"))
        for button in (self.flat_button, self.grouped_button):
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.clicked.connect(self._pick_view)
            bar.addWidget(button)
        self.grouped_button.setChecked(True)
        bar.addSpacing(8)
        self.model_filter = Combo()
        self.model_filter.addItem(tr("All models"), "")
        self.model_filter.currentIndexChanged.connect(self._fill_details_now)
        bar.addWidget(self.model_filter, 1)
        self.status_filter = Combo()
        self.status_filter.addItem(tr("Any status"), "")
        for status in usage.STATUSES:
            self.status_filter.addItem(tr(STATUS_LABELS[status]), status)
        self.status_filter.currentIndexChanged.connect(self._fill_details_now)
        bar.addWidget(self.status_filter)
        self.export_button = QPushButton(tr("Export CSV"))
        self.export_button.setAutoDefault(False)
        self.export_button.clicked.connect(self._export)
        bar.addWidget(self.export_button)
        layout.addLayout(bar)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(7)
        # The amount varies most in width, so it goes last and the cost stays in view.
        self.tree.setHeaderLabels([tr("Time"), tr("Model"), tr("Used for"), tr("Status"),
                                   tr("Estimated cost"), tr("Wait"), tr("Amount")])
        self.tree.currentItemChanged.connect(self._explain)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.tree, 1)
        # How the cost of the chosen row was worked out.
        self.explain = QLabel(tr("Pick a row to see how its cost was worked out."))
        self.explain.setWordWrap(True)
        self.explain.setStyleSheet("background: #20242c; border-radius: 8px; padding: 8px 10px; font-size: 12px;")
        layout.addWidget(self.explain)
        self.details_count = QLabel("")
        self.details_count.setStyleSheet("color: %s; font-size: 12px;" % MUTED)
        layout.addWidget(self.details_count)
        self._entries = []
        return page

    def _pick_view(self):
        grouped = self.sender() is self.grouped_button
        self.grouped_button.setChecked(grouped)
        self.flat_button.setChecked(not grouped)
        self._fill_details_now()

    def _filtered(self):
        model = self.model_filter.currentData()
        status = self.status_filter.currentData()
        return [entry for entry in self._entries
                if (not model or entry.get("model") == model) and (not status or entry.get("status") == status)]

    def _fill_models(self, entries):
        chosen = self.model_filter.currentData()
        models = sorted({entry.get("model", "") for entry in entries}, key=usage.label)
        if chosen and chosen not in models:
            models.append(chosen)
        self.model_filter.blockSignals(True)
        self.model_filter.clear()
        self.model_filter.addItem(tr("All models"), "")
        for model in models:
            self.model_filter.addItem(usage.label(model), model)
        self.model_filter.setCurrentIndex(max(0, self.model_filter.findData(chosen)))
        self.model_filter.blockSignals(False)

    def _fill_details_now(self):
        entries = self._filtered()
        open_takes = set()
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.isExpanded():
                open_takes.add(item.data(0, Qt.ItemDataRole.UserRole))
        scroll = self.tree.verticalScrollBar().value()
        self.tree.clear()
        if self.grouped_button.isChecked():
            groups = usage.takes(entries)
            for take in groups:
                models = []
                for entry in take["items"]:
                    if usage.label(entry.get("model")) not in models:
                        models.append(usage.label(entry.get("model")))
                spent = money(take["cost"]) + (" +" if take["unpriced"] else "")
                parent = self._row(None, [
                    stamp(take["t"]), " + ".join(models), kinds_text(take["kinds"]),
                    tr(STATUS_LABELS.get(take["status"], take["status"])),
                    spent,
                    tr("%s s") % _number(take["wait"]) if take["wait"] else "-",
                    minutes(take["seconds"]) if take["seconds"] else entry_amount(take["items"][0]),
                ], take["status"], self._take_explanation(take))
                parent.setData(0, Qt.ItemDataRole.UserRole, take["items"][0].get("take") or take["t"])
                for entry in take["items"]:
                    self._entry_row(parent, entry)
            self.tree.setRootIsDecorated(True)
            count = tr("%d dictations, %d requests") % (len(groups), len(entries))
        else:
            for entry in sorted(entries, key=lambda entry: -entry.get("t", 0)):
                self._entry_row(None, entry)
            self.tree.setRootIsDecorated(False)
            count = tr("%d requests") % len(entries)
        total = sum(entry.get("cost") or 0 for entry in entries)
        self.details_count.setText("%s · %s" % (count, money(total)) if entries else tr("Nothing to show."))
        self.export_button.setEnabled(bool(entries))
        # Columns fit only the rows on show, so the requests are opened while measuring.
        self.tree.expandAll()
        _fit_columns(self.tree, range(7))
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            item.setExpanded(item.data(0, Qt.ItemDataRole.UserRole) in open_takes)
        self.tree.verticalScrollBar().setValue(scroll)
        self._explain(None)

    def _entry_row(self, parent, entry):
        cost_value = entry.get("cost")
        spent = tr("no price") if cost_value is None else money(cost_value)
        # Under a dictation the date is already on the row above.
        when = time.strftime("%H:%M:%S", time.localtime(entry.get("t", 0))) if parent else stamp(entry.get("t", 0))
        return self._row(parent, [
            when,
            usage.label(entry.get("model", "")),
            kinds_text(usage.kinds_of(entry)),
            tr(STATUS_LABELS.get(entry.get("status"), entry.get("status", ""))),
            spent,
            tr("%s s") % _number(entry["wait"], 2) if entry.get("wait") else "-",
            entry_amount(entry),
        ], entry.get("status", "done"), "%s: %s = %s" % (usage.label(entry.get("model", "")),
                                                         calculation(entry), spent))

    def _take_explanation(self, take):
        lines = ["%s: %s = %s" % (usage.label(entry.get("model", "")), calculation(entry),
                                  tr("no price") if entry.get("cost") is None else money(entry["cost"]))
                 for entry in take["items"]]
        if len(lines) > 1:
            lines.append(tr("Total: %s") % (money(take["cost"]) + (" +" if take["unpriced"] else "")))
        return "\n".join(lines)

    def _explain(self, item, _previous=None):
        text = item.data(0, Qt.ItemDataRole.UserRole + 1) if item is not None else ""
        self.explain.setText(text or tr("Pick a row to see how its cost was worked out."))

    def _row(self, parent, cells, status, explanation):
        item = QTreeWidgetItem(cells)
        for column in (4, 5):
            item.setTextAlignment(column, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, explanation)
        for column in range(len(cells)):
            item.setToolTip(column, explanation)
        if parent is None:
            self.tree.addTopLevelItem(item)
        else:
            parent.addChild(item)
            for column in range(len(cells)):
                item.setForeground(column, QColor(MUTED))
        if status != "done":
            item.setForeground(3, QColor(WARN))
        return item

    def _export(self):
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        name = "speech-dictation-usage-%s.csv" % time.strftime("%Y-%m-%d")
        target, _ = QFileDialog.getSaveFileName(self, tr("Export CSV"), os.path.join(folder, name), "CSV (*.csv)")
        if not target:
            return
        try:
            usage.export_csv(self._filtered(), target, decimal_comma=i18n.current == "tr")
        except OSError as exc:
            QMessageBox.warning(self, tr("Export CSV"), str(exc))

    # Both

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
        start = since(self.period.currentData())
        entries = usage.load(start)
        self._entries = entries
        self._fill_summary(entries, start)
        self._fill_models(entries)
        self._fill_details_now()
        self.clear_button.setEnabled(self._seen is not None)

    def _clear(self):
        answer = QMessageBox.question(
            self, tr("Clear history"),
            tr("Delete the whole usage history on this computer? This cannot be undone."))
        if answer == QMessageBox.StandardButton.Yes:
            usage.clear()
            self.refresh()
