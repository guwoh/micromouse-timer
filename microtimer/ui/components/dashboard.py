"""Dashboard chrome. Live text never participates in allocating the video area."""
from PyQt6 import QtCore, QtGui, QtWidgets

from ui.components.club_banner import ClubBanner
from ui.components.interaction import FeedbackButton

NAVY = "#102b48"
MUTED = "#657d99"

STYLE = """
QMainWindow, QScrollArea, QWidget#dashboard { background: #f4f7fc; }
QWidget { color: #102b48; font-size: 13px; }
QFrame#card { background: white; border: 1px solid #dce6f2; border-radius: 10px; }
QLabel { background: transparent; border: none; }
QLabel#sectionTitle { font-size: 16px; font-weight: bold; }
QLabel#muted { color: #657d99; font-size: 11px; }
QPushButton { min-height: 30px; padding: 3px 12px; background: #edf3fa; border: 1px solid #d3dff0; border-radius: 6px; font-weight: bold; }
QPushButton:hover { background: #dfeaf7; border-color: #9db7d4; }
QPushButton:pressed { background: #ccdcee; }
QPushButton[role="primary"] { background: #132f4e; color: white; border-color: #132f4e; }
QPushButton[role="primary"]:hover { background: #21496d; border-color: #386387; }
QPushButton[role="primary"]:pressed { background: #0a2037; border-color: #41c9b0; }
QPushButton[role="danger"] { background: #dc273b; color: white; border-color: #dc273b; }
QPushButton[role="danger"]:hover { background: #ed3d50; border-color: #ed3d50; }
QPushButton[role="danger"]:pressed { background: #b71e30; border-color: #9c1b2a; }
QPushButton:focus { border-color: #209eaa; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #209eaa; background: white; }
QPushButton:disabled, QPushButton[role="primary"]:disabled, QPushButton[role="danger"]:disabled { color: #96a5b6; background: #f1f4f8; border-color: #e3e9f0; }
QLineEdit, QSpinBox, QComboBox { min-height: 26px; padding: 3px 8px; border: 1px solid #d4e0ef; border-radius: 6px; background: #fbfcfe; selection-background-color: #c8eee8; selection-color: #102b48; }
QComboBox QAbstractItemView { background: white; color: #102b48; selection-background-color: #dcf5ef; }
QTableWidget { border: 1px solid #dce6f2; border-radius: 6px; background: white; gridline-color: #e6edf6; selection-background-color: #e0f5f0; selection-color: #102b48; }
QHeaderView::section { background: #edf3f9; border: none; border-bottom: 1px solid #dce6f2; padding: 7px; font-weight: bold; }
QScrollBar:vertical { background: #f1f5fa; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #c4d1e1; min-height: 24px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QDialog { background: #f4f7fc; }
QGroupBox { border: 1px solid #dce6f2; border-radius: 8px; margin-top: 14px; padding: 12px; font-weight: bold; background: white; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
"""



def icon(kind, color=NAVY):
    pixmap = QtGui.QPixmap(22, 22)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setPen(QtGui.QPen(QtGui.QColor(color), 1.8, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap, QtCore.Qt.PenJoinStyle.RoundJoin))
    if kind == "camera":
        painter.drawRoundedRect(QtCore.QRectF(2, 5, 13, 12), 2, 2)
        painter.drawEllipse(QtCore.QRectF(6, 8, 5, 5))
        painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(15, 9), QtCore.QPointF(20, 6), QtCore.QPointF(20, 16), QtCore.QPointF(15, 13)]))
    elif kind == "team":
        painter.drawEllipse(QtCore.QRectF(7, 2, 7, 7))
        painter.drawArc(QtCore.QRectF(3, 11, 15, 13), 0, 180 * 16)
        painter.drawEllipse(QtCore.QRectF(1, 5, 4, 4))
        painter.drawEllipse(QtCore.QRectF(17, 5, 4, 4))
    elif kind == "clock":
        painter.drawEllipse(QtCore.QRectF(2, 2, 18, 18))
        painter.drawLine(11, 5, 11, 11)
        painter.drawLine(11, 11, 15, 14)
    elif kind == "list":
        for y in (5, 11, 17):
            painter.drawPoint(3, y)
            painter.drawLine(8, y, 20, y)
    elif kind == "settings":
        painter.drawEllipse(QtCore.QRectF(5, 5, 12, 12))
        painter.drawEllipse(QtCore.QRectF(9, 9, 4, 4))
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(11, 11)
            painter.rotate(angle)
            painter.drawLine(0, -8, 0, -10)
            painter.restore()
    elif kind == "reset":
        painter.drawArc(QtCore.QRectF(3, 3, 16, 16), -45 * 16, 290 * 16)
        painter.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(2, 3), QtCore.QPointF(3, 9), QtCore.QPointF(9, 8)]))
    else:
        painter.setBrush(QtGui.QColor(color))
        painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(5, 3), QtCore.QPointF(16, 11), QtCore.QPointF(5, 19)]))
        if kind == "next":
            painter.drawLine(19, 3, 19, 19)
    painter.end()
    return QtGui.QIcon(pixmap)


class SectionTitle(QtWidgets.QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        kind = {"Live camera": "camera", "Active team": "team", "Timing": "clock", "Run history": "list", "Session setup": "settings"}.get(text)
        self._icon = icon(kind or "settings").pixmap(20, 20)
        self.setContentsMargins(30, 0, 0, 0)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, (self.height() - 20) // 2, self._icon)


def label(text, parent=None, title=False):
    widget = SectionTitle(text, parent) if title else QtWidgets.QLabel(text, parent)
    widget.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    widget.setObjectName("sectionTitle" if title else "muted")
    widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
    return widget


def button(text, role=None):
    widget = FeedbackButton(text)
    widget.setMinimumHeight(36)
    kind = {"Configure": "settings", "Arm": "play", "Next Run": "next", "Reset": "reset"}.get(text)
    if kind:
        widget.setIcon(icon(kind, "white" if role == "primary" else NAVY))
    if role:
        widget.setProperty("role", role)
    return widget


class Card(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored)


class ElidedLabel(QtWidgets.QLabel):
    """Keep long names/messages within the allocated width, with the full tooltip."""
    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.WindowText))
        painter.setFont(self.font())
        text = self.fontMetrics().elidedText(self.text(), QtCore.Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment() | QtCore.Qt.AlignmentFlag.AlignVCenter, text)


class AppHeader(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(64)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#112b45"))
        self.setPalette(palette)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(22, 8, 22, 8)
        layout.setSpacing(18)
        self.logo = ClubBanner()
        self.logo.setFixedSize(96, 44)
        layout.addWidget(self.logo)
        title = QtWidgets.QLabel("Micromouse Timer")
        title.setStyleSheet("color: white; font-size: 23px; font-weight: bold;")
        layout.addWidget(title)
        self.subtitle = QtWidgets.QLabel("Competition control")
        self.subtitle.setStyleSheet("color: #b8cbdf; font-size: 14px;")
        layout.addWidget(self.subtitle)
        layout.addStretch()
        self.connection = QtWidgets.QLabel("●  Disconnected")
        self.connection.setFixedSize(194, 34)
        self.connection.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection)
        self.set_connection(False)

    def set_connection(self, connected, mock=False):
        text = "Mock video playing" if mock else "Camera connected"
        self.connection.setText("●  " + (text if connected else "Disconnected"))
        color = "#35e6bb" if connected else "#b8cbdf"
        self.connection.setStyleSheet(f"color: {color}; border: 1px solid #32616b; border-radius: 7px; font-weight: bold; font-size: 12px;")

    def resizeEvent(self, event):
        self.subtitle.setVisible(self.width() >= 1000)
        super().resizeEvent(event)


class ActiveTeam(Card):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(label("Active team", title=True))
        row = QtWidgets.QHBoxLayout()
        avatar = QtWidgets.QLabel("SRC")
        avatar.setFixedSize(46, 46)
        avatar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background: #159d9e; color: white; border-radius: 23px; font-weight: bold;")
        row.addWidget(avatar)
        row.addSpacing(8)
        self.team_label = ElidedLabel("No active team")
        self.team_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.team_label.setStyleSheet("font-size: 21px; font-weight: bold;")
        self.team_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        row.addWidget(self.team_label, 1)
        layout.addLayout(row)


class RunHistory(Card):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(label("Run history", title=True), 1)
        self.count = label("0 completed")
        self.count.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.count, 1)
        layout.addLayout(top)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Run", "Time", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        layout.addWidget(self.table)
        self._runs = None
        self.sync_runs([])

    def sync_runs(self, runs):
        values = tuple(runs)
        if values == self._runs:
            return
        self._runs = values
        self.table.setRowCount(len(values))
        best = min(values) if values else None
        for index, seconds in enumerate(values):
            is_best = seconds == best
            for column, value in enumerate((f"{index + 1:02d}", f"{seconds:.3f} s", "★  Best" if is_best else "✓  Valid")):
                item = QtWidgets.QTableWidgetItem(value)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if is_best:
                    item.setBackground(QtGui.QColor("#e5f8f2"))
                    if column == 2:
                        item.setForeground(QtGui.QColor("#07866a"))
                self.table.setItem(index, column, item)
        self.count.setText(f"{len(values)} completed")
        self.table.scrollToBottom()


class DashboardBody(QtWidgets.QWidget):
    def __init__(self, video, history, team, timing, setup):
        super().__init__()
        self.setObjectName("dashboard")
        self.setMinimumSize(751, 760)
        self.video, self.history, self.team, self.timing, self.setup = video, history, team, timing, setup
        for widget in (video, history, team, timing, setup):
            widget.setParent(self)

    def resizeEvent(self, event):
        # Text, history rows and frame dimensions cannot negotiate this geometry.
        gap, margin = 16, 16
        width, height = self.width() - 2 * margin, self.height() - 2 * margin
        right = min(490, max(306, round((width - gap) * .315)))
        left = width - gap - right
        x = margin + left + gap
        history_height, setup_height, team_height = 176, 244, 108
        self.video.setGeometry(margin, margin, left, height - history_height - gap)
        self.history.setGeometry(margin, margin + height - history_height, left, history_height)
        self.team.setGeometry(x, margin, right, team_height)
        self.timing.setGeometry(x, margin + team_height + gap, right, height - team_height - setup_height - 2 * gap)
        self.setup.setGeometry(x, margin + height - setup_height, right, setup_height)
        super().resizeEvent(event)


class DashboardFooter(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(38)
        self.setObjectName("footer")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#footer { background: white; border-top: 1px solid #e0e8f3; }")
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        self.rois = label("○ Start line   ·   ○ Goal area")
        self.rois.setFixedWidth(244)
        self.rois.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        layout.addWidget(self.rois)
        self.note = ElidedLabel("Ready · Select a camera or Mock video")
        self.note.setStyleSheet("color: #657d99; font-size: 11px; border: none;")
        self.note.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        layout.addWidget(self.note, 1)
        self.sampling = label("No source")
        self.sampling.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.sampling.setFixedWidth(265)
        self.sampling.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        layout.addWidget(self.sampling)
