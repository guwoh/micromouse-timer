from PyQt6 import QtCore, QtGui, QtWidgets

from app.paths import resource_root


class ClubBanner(QtWidgets.QWidget):
    """Draw the original SRC mark from the club banner without modifying the asset."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QtGui.QPixmap(str(resource_root() / "assets" / "branding" / "club_logo.jpg"))
        self.setToolTip("SRC · CLB Sinh viên Nghiên cứu Khoa học · Trường Điện - Điện tử")

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor("#f9fafc"))
        painter.drawRoundedRect(self.rect(), 5, 5)
        if self._pixmap.isNull():
            painter.setPen(QtGui.QColor("#24376a"))
            painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "SRC")
            return
        w, h = self._pixmap.width(), self._pixmap.height()
        source = QtCore.QRectF(.357 * w, .305 * h, .290 * w, .252 * h)
        target = QtCore.QRectF(5, 5, self.width() - 10, self.height() - 10)
        fit = source.size().scaled(target.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        target = QtCore.QRectF(target.center().x() - fit.width() / 2, target.center().y() - fit.height() / 2, fit.width(), fit.height())
        painter.drawPixmap(target, self._pixmap, source)
