"""Small input widgets shared by the Settings and Usage windows."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QPushButton, QWidget,
)


class Combo(QComboBox):
    """A drop-down that the mouse wheel does not change while it is closed.

    The wheel goes to the window instead, so scrolling past a drop-down
    scrolls the page rather than picking another option by accident.
    """

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        event.ignore()


class _Amount(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class AmountField(QWidget):
    """A dollar amount with its own - and + buttons; 0 shows as off_text.

    The spin box's built-in arrows do not line up with the dark style on
    Windows, so a click on the drawn arrow can miss it.
    """

    changed = pyqtSignal(float)

    def __init__(self, off_text, step=1.0, maximum=10000.0):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.box = _Amount()
        self.box.setRange(0, maximum)
        self.box.setDecimals(2)
        self.box.setSingleStep(step)
        self.box.setPrefix("$")
        self.box.setSpecialValueText(off_text)
        self.box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.box.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.box.valueChanged.connect(self._changed)
        layout.addWidget(self.box, 1)
        self.minus = self._button("−", -1)
        self.plus = self._button("+", 1)
        layout.addWidget(self.minus)
        layout.addWidget(self.plus)
        self._changed(self.box.value())

    def _button(self, text, direction):
        button = QPushButton(text)
        button.setAutoDefault(False)
        button.setFixedWidth(38)
        button.setAutoRepeat(True)
        button.setStyleSheet("QPushButton { background: #2a2f39; border: 1px solid #3c4250; font-size: 15px;"
                             " padding: 6px 0; }"
                             "QPushButton:hover { background: #343a46; }"
                             "QPushButton:disabled { color: #5c6370; }")
        button.clicked.connect(lambda: self.box.stepBy(direction))
        return button

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # The window's style sets the field's height only once it is laid out.
        for button in (self.minus, self.plus):
            button.setFixedHeight(self.box.height())

    def _changed(self, value):
        self.minus.setEnabled(value > self.box.minimum())
        self.plus.setEnabled(value < self.box.maximum())
        self.changed.emit(value)

    def value(self):
        return self.box.value()

    def setValue(self, value):
        self.box.setValue(value)

    def setToolTip(self, text):
        super().setToolTip(text)
        self.box.setToolTip(text)
