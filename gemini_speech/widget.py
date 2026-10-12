import math
import sys

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QMenu, QToolTip, QWidget

MARGIN = 6
HEIGHT = 52
WIDTH = 224
MIC = 40
SIDE = 32
CLOSE = 26

BG = QColor(28, 31, 37, 242)
EDGE = QColor(255, 255, 255, 28)
SHADOW = QColor(0, 0, 0, 70)
IDLE = QColor(48, 53, 63)
HOVER = QColor(62, 68, 80)
REC = QColor(240, 78, 82)
BUSY = QColor(120, 170, 255)
LOCK = QColor(245, 180, 70)
GLYPH = QColor(236, 238, 242)
DIM = QColor(150, 156, 168)

# Segoe Fluent Icons ships with Windows 11, Segoe MDL2 Assets with Windows 10.
_GLYPHS = {"mic": "\uE720", "lock": "\uE72E", "unlock": "\uE785", "gear": "\uE713", "close": "\uE8BB"}


def _icon_font():
    families = set(QFontDatabase.families())
    for name in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
        if name in families:
            return name
    return ""


class FloatingButton(QWidget):
    """A small always-on-top bar, like Windows voice typing.

    It never takes focus, so the text still lands in the window you were
    typing in. Drag it anywhere; it remembers where it was left. The cross
    hides it until the next dictation starts.
    """

    toggled = pyqtSignal()
    lock_changed = pyqtSignal(bool)
    settings_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    moved = pyqtSignal(int, int)

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.setWindowTitle("Speech Dictation")
        self.setFixedSize(WIDTH + MARGIN * 2, HEIGHT + MARGIN * 2)
        self._font = _icon_font()
        self.state = "idle"
        self.locked = False
        self.level = 0.0
        self.countdown = None
        self._hover = ""
        self._press = None
        self._press_at = QPoint()
        self._dragging = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._native_done = False

    # Layout -----------------------------------------------------------

    def _body(self):
        return QRectF(MARGIN, MARGIN, WIDTH, HEIGHT)

    def _mic_rect(self):
        body = self._body()
        return QRectF(body.center().x() - MIC / 2, body.center().y() - MIC / 2, MIC, MIC)

    def _lock_rect(self):
        mic = self._mic_rect()
        return QRectF(mic.left() - 12 - SIDE, mic.center().y() - SIDE / 2, SIDE, SIDE)

    def _gear_rect(self):
        mic = self._mic_rect()
        return QRectF(mic.right() + 12, mic.center().y() - SIDE / 2, SIDE, SIDE)

    def _close_rect(self):
        body = self._body()
        return QRectF(body.right() - 12 - CLOSE, body.center().y() - CLOSE / 2, CLOSE, CLOSE)

    def _part_at(self, pos):
        point = QPointF(pos)
        if self._mic_rect().adjusted(-4, -4, 4, 4).contains(point):
            return "mic"
        if self._lock_rect().contains(point):
            return "lock"
        if self._gear_rect().contains(point):
            return "gear"
        if self._close_rect().contains(point):
            return "close"
        if self._body().contains(point):
            return "grip"
        return ""

    # State --------------------------------------------------------------

    def set_state(self, state):
        self.state = state
        if state != "recording":
            self.level = 0.0
            self.countdown = None
        self._sync_timer()
        self.update()

    def set_locked(self, locked):
        self.locked = bool(locked)
        if self.locked:
            self.countdown = None
        self.update()

    def set_level(self, level, countdown=None):
        self.level = level
        self.countdown = countdown
        self.update()

    def place(self, x=None, y=None):
        screen = QApplication.primaryScreen()
        area = screen.availableGeometry() if screen else None
        if x is None or y is None:
            if area is None:
                return
            x = area.center().x() - self.width() // 2
            y = area.bottom() - self.height() - 24
        target = QPoint(int(x), int(y))
        screen = QApplication.screenAt(target + QPoint(self.width() // 2, self.height() // 2)) or screen
        if screen is not None:
            area = screen.availableGeometry()
            target.setX(max(area.left(), min(target.x(), area.right() - self.width() + 1)))
            target.setY(max(area.top(), min(target.y(), area.bottom() - self.height() + 1)))
        self.move(target)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._native_done:
            self._native_done = True
            _no_activate(int(self.winId()))

    def _sync_timer(self):
        if self.state in ("recording", "busy"):
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def _tick(self):
        self._phase += 0.12
        self.update()

    # Mouse --------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._menu(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press = self._part_at(event.position().toPoint())
        self._press_at = event.globalPosition().toPoint()
        self._origin = self.pos()
        self._dragging = False

    def mouseMoveEvent(self, event):
        if self._press is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_at
            if self._dragging or delta.manhattanLength() > 5:
                self._dragging = True
                self.move(self._origin + delta)
            return
        part = self._part_at(event.position().toPoint())
        if part != self._hover:
            self._hover = part
            self.setCursor(Qt.CursorShape.SizeAllCursor if part == "grip" else Qt.CursorShape.PointingHandCursor)
            tip = self._tip(part)
            if tip:
                QToolTip.showText(event.globalPosition().toPoint(), tip, self)
            else:
                QToolTip.hideText()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        part = self._press
        self._press = None
        if self._dragging:
            self._dragging = False
            self.place(self.x(), self.y())
            self.moved.emit(self.x(), self.y())
            return
        if part != self._part_at(event.position().toPoint()):
            return
        if part == "mic":
            self.toggled.emit()
        elif part == "lock":
            self.set_locked(not self.locked)
            self.lock_changed.emit(self.locked)
        elif part == "gear":
            self.settings_requested.emit()
        elif part == "close":
            self._hover = ""
            QToolTip.hideText()
            self.hide_requested.emit()

    def leaveEvent(self, event):
        self._hover = ""
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def _tip(self, part):
        if part == "mic":
            return "Stop" if self.state == "recording" else "Start dictation"
        if part == "lock":
            return "Keep listening until I stop" if not self.locked else "Locked: auto-stop is off"
        if part == "gear":
            return "Settings"
        if part == "close":
            return "Hide until the next dictation"
        return ""

    def _menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Settings", self.settings_requested.emit)
        menu.addSeparator()
        menu.addAction("Quit", self.quit_requested.emit)
        menu.exec(pos)

    # Painting -----------------------------------------------------------

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = self._body()
        radius = HEIGHT / 2
        shadow = QPainterPath()
        shadow.addRoundedRect(body.adjusted(-2, -1, 2, 3), radius + 2, radius + 2)
        painter.fillPath(shadow, SHADOW)
        path = QPainterPath()
        path.addRoundedRect(body, radius, radius)
        painter.fillPath(path, BG)
        painter.setPen(QPen(EDGE, 1))
        painter.drawPath(path)
        self._draw_grip(painter, body)
        self._draw_lock(painter)
        self._draw_gear(painter)
        self._draw_close(painter)
        self._draw_mic(painter)

    def _draw_grip(self, painter, body):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 45))
        x = body.left() + 14
        for row in range(3):
            for col in range(2):
                painter.drawEllipse(QPointF(x + col * 5, body.center().y() - 5 + row * 5), 1.3, 1.3)

    def _round_button(self, painter, rect, hover, fill=None):
        painter.setPen(Qt.PenStyle.NoPen)
        if fill is not None:
            painter.setBrush(fill)
            painter.drawEllipse(rect)
        elif hover:
            painter.setBrush(HOVER)
            painter.drawEllipse(rect)

    def _glyph(self, painter, rect, name, color, size):
        if not self._font:
            return False
        font = QFont(self._font)
        font.setPixelSize(size)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), _GLYPHS[name])
        return True

    def _draw_lock(self, painter):
        rect = self._lock_rect()
        fill = QColor(LOCK.red(), LOCK.green(), LOCK.blue(), 50) if self.locked else None
        self._round_button(painter, rect, self._hover == "lock", fill)
        color = LOCK if self.locked else DIM
        if self._glyph(painter, rect, "lock" if self.locked else "unlock", color, 15):
            return
        c = rect.center()
        painter.setPen(QPen(color, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(c.x() - 6, c.y() - 1, 12, 9), 2, 2)
        lift = 0 if self.locked else 3
        painter.drawArc(QRectF(c.x() - 4, c.y() - 8 - lift, 8, 10), 0, 180 * 16)

    def _draw_gear(self, painter):
        rect = self._gear_rect()
        self._round_button(painter, rect, self._hover == "gear")
        if self._glyph(painter, rect, "gear", DIM, 15):
            return
        c = rect.center()
        painter.setPen(QPen(DIM, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(c, 5, 5)
        for step in range(8):
            angle = step * math.pi / 4
            painter.drawLine(
                QPointF(c.x() + 5 * math.cos(angle), c.y() + 5 * math.sin(angle)),
                QPointF(c.x() + 7.5 * math.cos(angle), c.y() + 7.5 * math.sin(angle)),
            )

    def _draw_close(self, painter):
        rect = self._close_rect()
        self._round_button(painter, rect, self._hover == "close")
        if self._glyph(painter, rect, "close", DIM, 10):
            return
        c = rect.center()
        pen = QPen(DIM, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(c.x() - 4, c.y() - 4), QPointF(c.x() + 4, c.y() + 4))
        painter.drawLine(QPointF(c.x() + 4, c.y() - 4), QPointF(c.x() - 4, c.y() + 4))

    def _draw_mic(self, painter):
        rect = self._mic_rect()
        c = rect.center()
        if self.state == "recording":
            # The halo grows with the voice, so it is clear the microphone hears you.
            loud = min(1.0, self.level / 2500.0)
            pulse = 0.5 + 0.5 * math.sin(self._phase * 1.4)
            halo = QColor(REC)
            halo.setAlphaF(0.18 + 0.12 * pulse)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo)
            grow = 2 + 7 * loud
            painter.drawEllipse(c, MIC / 2 + grow * 0.6, MIC / 2 + grow * 0.6)
            painter.setBrush(REC)
            painter.drawEllipse(rect)
            if self.countdown is not None and not self.locked:
                pen = QPen(LOCK, 2.4)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                span = int(360 * 16 * max(0.0, min(1.0, self.countdown)))
                painter.drawArc(rect.adjusted(-3, -3, 3, 3), 90 * 16, -span)
            glyph = GLYPH
        elif self.state == "busy":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(IDLE)
            painter.drawEllipse(rect)
            pen = QPen(BUSY, 2.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(rect.adjusted(-3, -3, 3, 3), int(-self._phase * 400) % (360 * 16), 110 * 16)
            glyph = DIM
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(HOVER if self._hover == "mic" else IDLE)
            painter.drawEllipse(rect)
            glyph = GLYPH
        if self._glyph(painter, rect, "mic", glyph, 18):
            return
        painter.setPen(QPen(glyph, 1.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(c.x() - 3.5, c.y() - 9, 7, 12), 3.5, 3.5)
        painter.drawArc(QRectF(c.x() - 6.5, c.y() - 4, 13, 10), 180 * 16, 180 * 16)
        painter.drawLine(QPointF(c.x(), c.y() + 6), QPointF(c.x(), c.y() + 9))


def _no_activate(hwnd):
    # Qt asks for no focus, but Windows can still activate the window on a
    # click. WS_EX_NOACTIVATE keeps the app you are typing in in front.
    if sys.platform != "win32":
        return
    import ctypes
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_NOACTIVATE = 0x08000000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_TOPMOST = 0x00000008
    get = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    put = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get.restype = ctypes.c_ssize_t
    get.argtypes = [ctypes.c_void_p, ctypes.c_int]
    put.restype = ctypes.c_ssize_t
    put.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
    style = get(hwnd, GWL_EXSTYLE)
    put(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)
