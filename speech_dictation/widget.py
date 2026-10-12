import math
import sys

from PyQt6.QtCore import QLineF, QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QToolTip, QWidget

from . import desktop
from .i18n import tr

MARGIN = 6
HEIGHT = 48
PAD = 8
GAP = 6
MIC = 40
SIDE = 32
CLOSE = 26
BADGE = 19
WIDTH = PAD + SIDE + GAP + MIC + GAP + CLOSE + PAD

BG = QColor(28, 31, 37, 150)
EDGE = QColor(255, 255, 255, 40)
SHADOW = QColor(0, 0, 0, 35)
IDLE = QColor(48, 53, 63, 190)
HOVER = QColor(62, 68, 80, 210)
REC = QColor(240, 78, 82)
BUSY = QColor(120, 170, 255)
LOCK = QColor(245, 180, 70)
GLYPH = QColor(236, 238, 242)
DIM = QColor(222, 226, 234)

# Segoe Fluent Icons ships with Windows 11, Segoe MDL2 Assets with Windows 10.
_GLYPHS = {"mic": "\uE720", "lock": "\uE72E", "unlock": "\uE785", "close": "\uE8BB"}


def _icon_font():
    families = set(QFontDatabase.families())
    for name in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
        if name in families:
            return name
    return ""


class FloatingButton(QWidget):
    """A small always-on-top bar, like Windows voice typing.

    It never takes focus, so the text still lands in the window you were
    typing in. Drag it by any spot outside the buttons; it remembers where
    it was left. The cross hides it until the next dictation starts.
    """

    toggled = pyqtSignal()
    translate_toggled = pyqtSignal()
    lock_changed = pyqtSignal(bool)
    hide_requested = pyqtSignal()
    moved = pyqtSignal(int, int)

    def __init__(self):
        super().__init__(None)
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        # On Wayland a Tool window wants a parent; a plain window shows the same.
        if not desktop.wayland():
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # macOS hides tool windows whenever another app is in front, which is
        # exactly when the button is needed.
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        # KWin and Hyprland find the bar by this title to keep it on top and unfocused.
        self.setWindowTitle(desktop.BUTTON_TITLE)
        self.setFixedSize(WIDTH + MARGIN * 2, HEIGHT + MARGIN * 2)
        self._font = _icon_font()
        self.state = "idle"
        self.mode = "record"
        self.target = "EN"
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

    def _lock_rect(self):
        body = self._body()
        return QRectF(body.left() + PAD, body.center().y() - SIDE / 2, SIDE, SIDE)

    def _mic_rect(self):
        lock = self._lock_rect()
        return QRectF(lock.right() + GAP, lock.center().y() - MIC / 2, MIC, MIC)

    def _close_rect(self):
        body = self._body()
        return QRectF(body.right() - PAD - CLOSE, body.center().y() - CLOSE / 2, CLOSE, CLOSE)

    def _badge_rect(self):
        # Sits on the microphone's top-right edge, like a notification badge.
        mic = self._mic_rect()
        cx = mic.center().x() + MIC * 0.36
        cy = mic.center().y() - MIC * 0.36
        return QRectF(cx - BADGE / 2, cy - BADGE / 2, BADGE, BADGE)

    def _part_at(self, pos):
        point = QPointF(pos)
        badge = self._badge_rect()
        if QLineF(point, badge.center()).length() <= BADGE / 2 + 2:
            return "translate"
        if self._mic_rect().contains(point):
            return "mic"
        if self._lock_rect().contains(point):
            return "lock"
        if self._close_rect().contains(point):
            return "close"
        if self._body().contains(point):
            return "grip"
        return ""

    # State --------------------------------------------------------------

    def set_state(self, state, mode="record"):
        self.state = state
        self.mode = mode
        if state != "recording":
            self.level = 0.0
            self.countdown = None
        self._sync_timer()
        self.update()

    def set_target(self, language):
        self.target = (language or "en").split("-")[0].upper()[:2]
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
            _mac_panel(int(self.winId()))

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
                if not self._dragging and desktop.wayland():
                    # Wayland ignores move(); the compositor moves the window instead.
                    handle = self.windowHandle()
                    if handle is not None and handle.startSystemMove():
                        self._press = None
                        return
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
        elif part == "translate":
            self.translate_toggled.emit()
        elif part == "lock":
            self.set_locked(not self.locked)
            self.lock_changed.emit(self.locked)
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
            return tr("Stop") if self.state == "recording" else tr("Start dictation")
        if part == "translate":
            if self.state == "recording":
                return tr("Stop")
            return tr("Translate into %s") % self.target
        if part == "lock":
            return tr("Keep listening until I stop") if not self.locked else tr("Locked: auto-stop is off")
        if part == "close":
            return tr("Hide until the next dictation")
        return ""

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
        self._draw_lock(painter)
        self._draw_close(painter)
        self._draw_mic(painter)
        self._draw_badge(painter)

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

    def _draw_badge(self, painter):
        rect = self._badge_rect()
        active = self.state == "recording" and self.mode == "translate"
        if active:
            fill = BUSY
        elif self._hover == "translate":
            fill = QColor(78, 86, 102)
        else:
            fill = QColor(58, 64, 76)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawEllipse(rect)
        _draw_badge_ring(painter, rect)
        font = QFont(self.font())
        font.setPixelSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255) if active else GLYPH)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.target)

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


def _draw_badge_ring(painter, rect):
    # A dark rim cuts the badge out of the microphone circle under it.
    painter.setPen(QPen(QColor(24, 26, 31, 235), 2.2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(rect.adjusted(-1.1, -1.1, 1.1, 1.1))


def _mac_panel(view):
    # Qt makes a Tool window an NSPanel. Clicking a panel still brings the
    # app to the front unless it is non-activating, and then the paste would
    # land in this app instead of the one you were typing in.
    if sys.platform != "darwin" or not view:
        return
    try:
        import ctypes
        import ctypes.util
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc") or "/usr/lib/libobjc.A.dylib")
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = objc.objc_msgSend

        def call(obj, name, restype=ctypes.c_void_p, argtypes=(), *args):
            send.restype = restype
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p] + list(argtypes)
            return send(obj, objc.sel_registerName(name), *args)

        def can(obj, name):
            return call(obj, b"respondsToSelector:", ctypes.c_bool, [ctypes.c_void_p],
                        objc.sel_registerName(name))

        window = call(view, b"window")
        if not window:
            return
        NONACTIVATING = 1 << 7
        mask = call(window, b"styleMask", ctypes.c_ulong)
        call(window, b"setStyleMask:", None, [ctypes.c_ulong], mask | NONACTIVATING)
        # A mask changed after creation does not always reach the window
        # server; this private call makes it stick where it exists.
        if can(window, b"_setPreventsActivation:"):
            call(window, b"_setPreventsActivation:", None, [ctypes.c_bool], True)
        call(window, b"setHidesOnDeactivate:", None, [ctypes.c_bool], False)
        if can(window, b"setBecomesKeyOnlyIfNeeded:"):
            call(window, b"setBecomesKeyOnlyIfNeeded:", None, [ctypes.c_bool], True)
        if can(window, b"setFloatingPanel:"):
            call(window, b"setFloatingPanel:", None, [ctypes.c_bool], True)
        # Every Space, and over full-screen apps too.
        JOIN_ALL_SPACES = 1 << 0
        STATIONARY = 1 << 4
        FULL_SCREEN_AUXILIARY = 1 << 8
        call(window, b"setCollectionBehavior:", None, [ctypes.c_ulong],
             JOIN_ALL_SPACES | STATIONARY | FULL_SCREEN_AUXILIARY)
    except Exception as exc:
        from .crashlog import note
        note("mac panel: %s" % exc)


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
