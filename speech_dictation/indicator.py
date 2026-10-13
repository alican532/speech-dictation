import math
import time

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QColor, QCursor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                         QFontMetrics)
from PyQt6.QtWidgets import QWidget, QApplication

from . import desktop

ICON = 28
GAP = 8
REC = QColor(240, 78, 82)
OK = QColor(80, 205, 140)
ERR = QColor(240, 100, 90)
BUSY = QColor(120, 170, 255)
BG = QColor(22, 24, 29, 230)
EDGE = QColor(58, 63, 74)
# Words the service has settled on, and words it may still change.
FINAL = QColor(231, 233, 238)
INTERIM = QColor(150, 157, 170)
CAPTION_WIDTH = 420
CAPTION_LINES = 3
CAPTION_LEFT = 26
CAPTION_PAD = 7
FADE_IN = 0.2
# Scribe Realtime leaves a whole take partial, so a word that stays the same this long reads as settled.
STEADY = 1.2
SETTLE = 0.3
SCROLL = 0.15


class Indicator(QWidget):
    def __init__(self):
        super().__init__(None)
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        if not desktop.wayland():
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle(desktop.OVERLAY_TITLE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.resize(ICON, ICON)
        self._state = ""
        self._message = ""
        self._phase = 0.0
        self._area = None
        self._caption = Caption()
        self._caption_font = QFont(self.font())
        self._caption_font.setPointSizeF(max(10.0, self.font().pointSizeF()))
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._hide = QTimer(self)
        self._hide.setSingleShot(True)
        self._hide.timeout.connect(self.dismiss)

    def show_recording(self):
        self._caption.reset()
        self._show("recording", "", ICON, ICON)

    def show_preview(self, final, interim=""):
        """The recording dot growing into a live caption of the words heard so far."""
        if self._state != "preview":
            self._caption.reset()
        metrics = QFontMetrics(self._caption_font)
        caption = self._caption
        caption.update(final, interim, metrics, CAPTION_WIDTH)
        if not caption.words:
            self.show_recording()
            return
        rows = min(CAPTION_LINES, len(caption.lines))
        # One line grows with the words; from the second line on the width stays put.
        text_width = caption.lines[0][2] if len(caption.lines) == 1 else CAPTION_WIDTH
        width = CAPTION_LEFT + math.ceil(text_width) + CAPTION_PAD + 3
        height = max(ICON, rows * metrics.lineSpacing() + 2 * CAPTION_PAD)
        self._show("preview", "", width, height)

    def show_busy(self):
        self._show("busy", "", ICON, ICON)

    def show_done(self):
        self._show("done", "", ICON, ICON, 700)

    def show_error(self, message):
        metrics = QFontMetrics(self.font())
        text_width = min(420, metrics.horizontalAdvance(message))
        shown = metrics.elidedText(message, Qt.TextElideMode.ElideRight, text_width)
        width = 32 + metrics.horizontalAdvance(shown)
        self._show("error", shown, max(ICON, width), 26, 4000)

    def dismiss(self):
        self._timer.stop()
        self._hide.stop()
        self._state = ""
        self._caption.reset()
        self.hide()
        desktop.overlay_hidden()

    def _show(self, state, message, width, height, msec=0):
        self._state = state
        self._message = message
        if self.size().width() != width or self.size().height() != height:
            self.resize(width, height)
        self._place()
        if not self.isVisible():
            self.show()
        if not self._timer.isActive():
            self._timer.start()
        self._hide.stop()
        if msec:
            self._hide.start(msec)
        self.update()

    def _place(self):
        if desktop.place(self):
            return
        pos = QCursor.pos()
        x = pos.x() + GAP
        # The caption keeps its top by the cursor and grows downward, so its lines stay put.
        y = pos.y() - (ICON // 2 if self._state == "preview" else self.height() // 2)
        area = self._area
        if area is None or not area.contains(pos):
            screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
            area = screen.availableGeometry() if screen else None
            self._area = area
        if area is not None:
            x = max(area.left(), min(x, area.right() - self.width() + 1))
            y = max(area.top(), min(y, area.bottom() - self.height() + 1))
        point = QPointF(x, y).toPoint()
        if self.pos() != point:
            self.move(point)

    def _tick(self):
        self._phase += 0.18
        if self._state == "preview":
            self._caption.step(QFontMetrics(self._caption_font).lineSpacing())
        before = self.pos()
        self._place()
        if self.pos() != before or self._state in ("recording", "preview", "busy"):
            self.update()

    def paintEvent(self, _event):
        if not self._state:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        preview = self._state == "preview"
        if self._message or preview:
            rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            path = QPainterPath()
            path.addRoundedRect(rect, 8, 8)
            painter.fillPath(path, BG)
            painter.setPen(QPen(EDGE if preview else ERR, 1))
            painter.drawPath(path)
        self._draw(painter)
        if preview:
            self._draw_caption(painter)
            return
        if self._message:
            painter.setPen(ERR)
            painter.setFont(QFont(self.font()))
            painter.drawText(
                QRectF(22, 0, self.width() - 26, self.height()),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                self._message,
            )

    def _draw_caption(self, painter):
        metrics = QFontMetrics(self._caption_font)
        spacing = metrics.lineSpacing()
        width = self.width() - CAPTION_LEFT - CAPTION_PAD
        height = self.height() - 2 * CAPTION_PAD
        if width <= 0 or height <= 0:
            return
        ratio = self.devicePixelRatioF()
        layer = QImage(int(width * ratio) + 1, int(height * ratio) + 1, QImage.Format.Format_ARGB32_Premultiplied)
        layer.setDevicePixelRatio(ratio)
        layer.fill(0)
        canvas = QPainter(layer)
        canvas.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        canvas.setFont(self._caption_font)
        caption = self._caption
        now = time.monotonic()
        rows = min(CAPTION_LINES, len(caption.lines))
        first = len(caption.lines) - rows
        # Lines moving up out of view are drawn too, until the scroll ends.
        start = max(0, first - math.ceil(caption.offset / spacing))
        space = metrics.horizontalAdvance(" ")
        for index in range(start, len(caption.lines)):
            begin, end, _width = caption.lines[index]
            baseline = (index - first) * spacing + caption.offset + metrics.ascent()
            x = 0.0
            for word in range(begin, end):
                color = _word_color(word < caption.final, now - caption.born[word])
                canvas.setPen(color)
                text = caption.words[word]
                canvas.drawText(QPointF(x, baseline), text)
                x += metrics.horizontalAdvance(text) + space
        if start > 0 or first > 0:
            # Earlier text fades out at the top instead of being cut with an ellipsis.
            fade = QLinearGradient(0, 0, 0, spacing)
            fade.setColorAt(0, QColor(0, 0, 0, 0))
            fade.setColorAt(0.5, QColor(0, 0, 0, 110))
            fade.setColorAt(1, QColor(0, 0, 0, 255))
            canvas.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
            canvas.fillRect(QRectF(0, 0, width, spacing), fade)
        canvas.end()
        painter.drawImage(QPointF(CAPTION_LEFT, CAPTION_PAD), layer)

    def _draw(self, painter):
        cx = 14.0 if self._message or self._state == "preview" else self.width() / 2
        if self._state == "preview":
            cy = CAPTION_PAD + QFontMetrics(self._caption_font).lineSpacing() / 2
        else:
            cy = self.height() / 2
        if self._state in ("recording", "preview"):
            pulse = 0.72 + 0.28 * (0.5 + 0.5 * math.sin(self._phase * 1.6))
            glow = QColor(REC)
            glow.setAlphaF(0.2 * pulse)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(cx, cy), 8 * pulse, 8 * pulse)
            painter.setBrush(REC)
            painter.drawEllipse(QPointF(cx, cy), 3.2, 3.2)
            return
        if self._state == "busy":
            pen = QPen(BUSY, 1.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(QRectF(cx - 5, cy - 5, 10, 10), int(-self._phase * 320) % (360 * 16), 100 * 16)
            return
        if self._state == "done":
            pen = QPen(OK, 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(
                QPointF(cx - 3, cy + 0.2), QPointF(cx - 0.7, cy + 2.2), QPointF(cx + 3.2, cy - 2.4)
            )
            return
        pen = QPen(ERR, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
        painter.drawLine(QPointF(cx + 4, cy - 4), QPointF(cx - 4, cy + 4))


def _word_color(settled, age):
    if settled or age >= STEADY + SETTLE:
        color = QColor(FINAL)
    elif age <= STEADY:
        color = QColor(INTERIM)
    else:
        mix = (age - STEADY) / SETTLE
        color = QColor(*(round(a + (b - a) * mix) for a, b in (
            (INTERIM.red(), FINAL.red()), (INTERIM.green(), FINAL.green()), (INTERIM.blue(), FINAL.blue()))))
    if age < FADE_IN:
        color.setAlphaF(0.25 + 0.75 * age / FADE_IN)
    return color


class Caption:
    """Live caption layout.

    The text is always wrapped from its first word at one width, so a line
    never changes once the next one starts; new words only extend the last
    line. When a line is added the view slides up by whole lines.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.words = []
        self.final = 0
        self.born = []
        self.lines = []
        self.offset = 0.0
        self._stepped = time.monotonic()

    def update(self, final, interim, metrics, width):
        settled = (final or "").split()
        words = settled + (interim or "").split()
        now = time.monotonic()
        born = []
        for index, word in enumerate(words):
            same = index < len(self.words) and self.words[index] == word
            born.append(self.born[index] if same else now)
        before = len(self.lines)
        self.words, self.final, self.born = words, len(settled), born
        self.lines = wrap(words, metrics, width)
        hidden_before = max(0, before - CAPTION_LINES)
        hidden = max(0, len(self.lines) - CAPTION_LINES)
        if hidden > hidden_before:
            # At most two lines of slide, so a burst of words does not lag behind.
            self.offset = min(self.offset + (hidden - hidden_before) * metrics.lineSpacing(),
                              2 * metrics.lineSpacing())
        elif hidden < hidden_before:
            self.offset = 0.0

    def step(self, spacing):
        now = time.monotonic()
        elapsed, self._stepped = now - self._stepped, now
        if self.offset > 0:
            self.offset = max(0.0, self.offset - spacing * elapsed / SCROLL)


def wrap(words, metrics, width):
    """Greedy word wrap: a list of (first word, end word, line width)."""
    lines = []
    space = metrics.horizontalAdvance(" ")
    begin, used = 0, 0.0
    for index, word in enumerate(words):
        size = metrics.horizontalAdvance(word)
        if index > begin and used + space + size > width:
            lines.append((begin, index, used))
            begin, used = index, float(size)
        else:
            used = size if index == begin else used + space + size
    if words:
        lines.append((begin, len(words), used))
    return lines
