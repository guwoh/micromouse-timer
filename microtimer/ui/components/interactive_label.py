from __future__ import annotations

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets


class InteractiveLabel(QtWidgets.QWidget):
    """Paint frames without making their resolution affect the window layout."""

    roi_updated = QtCore.pyqtSignal(str, tuple)

    def __init__(self, text: str = "No frame", parent=None):
        super().__init__(parent)
        self.placeholder = text
        self.setMinimumSize(200, 120)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self._image = QtGui.QImage()
        self.orig_w = self.orig_h = 0
        self.drag_start_pos: QtCore.QPoint | None = None
        self.drag_end_pos: QtCore.QPoint | None = None
        self.current_mode: str | None = None
        self.roi_target: str | None = None
        self.setToolTip("Left-drag: Start line · Right-drag: Goal area")

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(640, 480)

    def set_frame(self, frame: np.ndarray) -> None:
        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        self.orig_h, self.orig_w = rgb.shape[:2]
        self._image = QtGui.QImage(
            rgb.data, self.orig_w, self.orig_h, rgb.strides[0],
            QtGui.QImage.Format.Format_RGB888,
        ).copy()
        self.update()

    def clear_frame(self) -> None:
        self._image = QtGui.QImage()
        self.orig_w = self.orig_h = 0
        self.drag_start_pos = self.drag_end_pos = self.current_mode = None
        self.update()

    def image_rect(self) -> QtCore.QRect:
        if self._image.isNull():
            return QtCore.QRect()
        size = self._image.size().scaled(self.contentsRect().size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        rect = QtCore.QRect(QtCore.QPoint(), size)
        rect.moveCenter(self.contentsRect().center())
        return rect

    def _map_to_image(self, pos: QtCore.QPoint, clamp: bool = False) -> tuple[int, int] | None:
        rect = self.image_rect()
        if rect.isEmpty() or (not clamp and not rect.contains(pos)):
            return None
        x = int((pos.x() - rect.x()) * self.orig_w / rect.width())
        y = int((pos.y() - rect.y()) * self.orig_h / rect.height())
        return max(0, min(x, self.orig_w - 1)), max(0, min(y, self.orig_h - 1))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        pos = event.position().toPoint()
        if self._map_to_image(pos) is None:
            return
        modes = {QtCore.Qt.MouseButton.LeftButton: "start", QtCore.Qt.MouseButton.RightButton: "goal"}
        self.current_mode = self.roi_target or modes.get(event.button())
        if self.current_mode:
            self.drag_start_pos = self.drag_end_pos = pos
            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.drag_start_pos is not None:
            self.drag_end_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.drag_start_pos is None or self.current_mode is None:
            return
        start = self._map_to_image(self.drag_start_pos, clamp=True)
        end = self._map_to_image(event.position().toPoint(), clamp=True)
        mode = self.current_mode
        self.drag_start_pos = self.drag_end_pos = self.current_mode = None
        self.update()
        if start is None or end is None:
            return
        x1, y1 = start
        x2, y2 = end
        if mode == "start":
            if abs(x2 - x1) > abs(y2 - y1):
                x, y = min(x1, x2), max(0, min(y1 - 7, self.orig_h - 15))
                w, h = max(abs(x2 - x1), 1), min(15, self.orig_h)
            else:
                x, y = max(0, min(x1 - 7, self.orig_w - 15)), min(y1, y2)
                w, h = min(15, self.orig_w), max(abs(y2 - y1), 1)
        else:
            x, y = min(x1, x2), min(y1, y2)
            w, h = max(abs(x2 - x1), 1), max(abs(y2 - y1), 1)
        if max(w, h) > 20:
            self.roi_updated.emit(mode, (x, y, w, h))

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#101c2d"))
        if self._image.isNull():
            painter.setPen(QtGui.QColor("#b8c6d9"))
            painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self.placeholder)
            return
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(self.image_rect(), self._image)
        if self.drag_start_pos is not None and self.drag_end_pos is not None:
            painter.save()
            painter.setClipRect(self.image_rect())
            color = "#38e6ab" if self.current_mode.startswith("start") else "#ffcf5b"
            painter.setPen(QtGui.QPen(QtGui.QColor(color), 2, QtCore.Qt.PenStyle.DashLine))
            start, end = self.drag_start_pos, QtCore.QPoint(self.drag_end_pos)
            if self.current_mode == "start":
                if abs(end.x() - start.x()) > abs(end.y() - start.y()):
                    end.setY(start.y())
                else:
                    end.setX(start.x())
                painter.drawLine(start, end)
            else:
                painter.drawRect(QtCore.QRect(start, end).normalized())
            painter.restore()
