"""Short, local UI animations; never animate or capture the live video widget."""
from PyQt6 import QtCore, QtGui, QtWidgets


class FeedbackButton(QtWidgets.QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._origin = None
        self._pulse = 1.0
        self._animation = QtCore.QVariantAnimation(self)
        self._animation.setDuration(240)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._set_pulse)
        self.pressed.connect(self._begin_pulse)

    def _set_pulse(self, value):
        self._pulse = float(value)
        self.update()

    def _begin_pulse(self):
        if self._origin is None:
            self._origin = QtCore.QPointF(self.rect().center())
        self._animation.stop()
        self._animation.start()

    def mousePressEvent(self, event):
        self._origin = event.position() if event.button() == QtCore.Qt.MouseButton.LeftButton else None
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        self._origin = None
        super().keyPressEvent(event)

    def hideEvent(self, event):
        self._animation.stop()
        self._pulse = 1.0
        self._origin = None
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pulse >= 1 or not self.isEnabled() or self._origin is None:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1), 6, 6)
        painter.setClipPath(clip)
        color = QtGui.QColor("white" if self.property("role") in ("primary", "danger") else "#248f9b")
        color.setAlphaF(0.22 * (1 - self._pulse))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(color)
        radius = (self.width() ** 2 + self.height() ** 2) ** 0.5 * self._pulse
        painter.drawEllipse(self._origin, radius, radius)


class DialogBackdrop(QtWidgets.QWidget):
    def __init__(self, host):
        super().__init__(host)
        self._strength = 0.0
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setGeometry(host.rect())
        host.installEventFilter(self)
        self.animation = QtCore.QPropertyAnimation(self, b"strength", self)
        self.animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def strength(self):
        return self._strength

    @strength.setter
    def strength(self, value):
        self._strength = value
        self.update()

    def animate_to(self, value, duration):
        self.animation.stop()
        self.animation.setDuration(duration)
        self.animation.setStartValue(self.strength)
        self.animation.setEndValue(value)
        self.animation.start()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.Resize:
            self.setGeometry(watched.rect())
        return False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        color = QtGui.QColor("#081b30")
        color.setAlphaF(self.strength)
        painter.fillRect(self.rect(), color)


class AnimatedDialog(QtWidgets.QDialog):
    """Fade a small dialog, retaining native modality, focus and result signals."""
    OPEN_MS = 160
    CLOSE_MS = 110

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backdrop = None
        self._pending_result = None
        self._opacity = QtWidgets.QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1)
        self._opacity.setEnabled(False)
        self.setGraphicsEffect(self._opacity)
        self._fade = QtCore.QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.finished.connect(self._fade_finished)
        self._host = parent.window() if parent is not None else None
        if self._host is not None:
            self._host.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self._host and event.type() in (QtCore.QEvent.Type.Hide, QtCore.QEvent.Type.Close):
            if self.isVisible():
                self._fade.stop()
                self._pending_result = None
                self._remove_backdrop()
                # Exit any nested exec() immediately when the app is closing.
                super().done(int(QtWidgets.QDialog.DialogCode.Rejected))
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        self._fade.stop()
        self._pending_result = None
        self.setEnabled(True)
        super().showEvent(event)
        for button in self.findChildren(QtWidgets.QPushButton):
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        host = self.parentWidget()
        if host is not None:
            self._remove_backdrop()
            self._backdrop = DialogBackdrop(host.window())
            self._backdrop.show()
            self._backdrop.raise_()
            self._backdrop.animate_to(0.30, self.OPEN_MS)
        self._animate(0, 1, self.OPEN_MS)

    def _animate(self, start, end, duration):
        self._fade.stop()
        self._opacity.setEnabled(True)
        self._opacity.setOpacity(start)
        self._fade.setDuration(duration)
        self._fade.setStartValue(start)
        self._fade.setEndValue(end)
        self._fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic if end else QtCore.QEasingCurve.Type.InCubic)
        self._fade.start()

    def done(self, result):
        if not self.isVisible():
            super().done(result)
            return
        if self._pending_result is not None:
            return
        self._pending_result = int(result)
        self.setEnabled(False)
        if self._backdrop is not None:
            self._backdrop.animate_to(0, self.CLOSE_MS)
        self._animate(self._opacity.opacity(), 0, self.CLOSE_MS)

    def _fade_finished(self):
        if self._pending_result is None:
            # Live diagnostics can update without repeatedly compositing the dialog.
            self._opacity.setEnabled(False)
            return
        result = self._pending_result
        self._pending_result = None
        self._remove_backdrop()
        super().done(result)

    def _remove_backdrop(self):
        if self._backdrop is not None:
            self._backdrop.animation.stop()
            self._backdrop.hide()
            self._backdrop.deleteLater()
            self._backdrop = None

    def closeEvent(self, event):
        event.ignore()
        self.reject()

    def hideEvent(self, event):
        self._fade.stop()
        self._pending_result = None
        self._remove_backdrop()
        super().hideEvent(event)
