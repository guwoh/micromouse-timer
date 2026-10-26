from PyQt6 import QtCore, QtGui, QtWidgets

from ui.components.dashboard import Card, label


class StatusPanel(Card):
    def __init__(self, controls):
        super().__init__()
        self._clock_family = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont).family()
        self.title = label("Timing", self, title=True)
        self.state_label = QtWidgets.QLabel("IDLE", self)
        self.state_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("background: #dcf6ef; color: #087e64; border-radius: 6px; font-size: 11px; font-weight: bold;")
        self.remaining_box, self.countdown_label = self._clock("SESSION REMAINING", "00:00", "#f0f5fa")
        self.elapsed_box, self.elapsed_label = self._clock("CURRENT RUN", "0.000 s", "#e1f7f1")
        self._state = None
        self.set_state("IDLE")
        self.controls = controls
        for widget in (controls.arm_btn, controls.reset_btn, controls.next_run_btn):
            widget.setParent(self)
        self.best_title = label("Best", self)
        self.best_label = QtWidgets.QLabel("—", self)
        self.best_label.setStyleSheet("font-weight: bold;")
        self.runs_title = label("Runs", self)
        self.run_count_label = QtWidgets.QLabel("0", self)
        for widget in (self.best_label, self.run_count_label):
            widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)

    def set_state(self, state):
        if state == self._state:
            return
        self._state = state
        self.state_label.setText(state)
        background, foreground = {
            "IDLE": ("#edf2f8", "#657d99"),
            "ARMED": ("#fff3d8", "#93600c"),
            "RUNNING": ("#dcf6ef", "#087e64"),
            "FINISHED": ("#e3edf9", "#234d7b"),
        }.get(state, ("#edf2f8", "#657d99"))
        self.state_label.setStyleSheet(f"background: {background}; color: {foreground}; border-radius: 6px; font-size: 11px; font-weight: bold;")

    def _clock(self, title, text, color):
        box = QtWidgets.QFrame(self)
        box.setStyleSheet(f"QFrame {{ background: {color}; border-radius: 8px; }}")
        caption = label(title, box)
        caption.setStyleSheet("font-size: 11px; color: #526e8e; font-weight: bold;")
        value = QtWidgets.QLabel(text, box)
        value.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        value.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        value.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Ignored)
        box.caption, box.value = caption, value
        return box, value

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h, m, gap = self.width(), self.height(), 16, 10
        self.title.setGeometry(m, 12, w - 150, 28)
        self.state_label.setGeometry(w - m - 106, 12, 106, 28)
        # The smallest supported body leaves 326px for this card.
        controls_height = 38 if h < 380 else 46
        box_height = (h - 52 - 3 * gap - controls_height * 2 - 32 - m) // 2
        for index, box in enumerate((self.remaining_box, self.elapsed_box)):
            box.setGeometry(m, 52 + index * (box_height + gap), w - m * 2, box_height)
            box.caption.setGeometry(16, 9, w - 2 * m - 32, 17)
            box.value.setGeometry(16, 28, w - 2 * m - 32, box_height - 31)
            available = box.value.width()
            # Size the font for the longest supported 180-minute value, independent of live text.
            pixels = min(box_height - 38, available // (5 if index == 0 else 7))
            box.value.setStyleSheet(f"color: #09263d; font-family: '{self._clock_family}'; font-size: {max(23, pixels)}px; font-weight: bold;")
        y = 52 + 2 * (box_height + gap)
        half = (w - 2 * m - gap) // 2
        self.controls.arm_btn.setGeometry(m, y, half, controls_height)
        self.controls.next_run_btn.setGeometry(m + half + gap, y, half, controls_height)
        self.controls.reset_btn.setGeometry(m, y + controls_height + gap, w - 2 * m, controls_height)
        y = h - 35
        self.best_title.setGeometry(m, y, 34, 24)
        self.best_label.setGeometry(m + 40, y, w - 160, 24)
        self.runs_title.setGeometry(w - 105, y, 38, 24)
        self.run_count_label.setGeometry(w - 62, y, 46, 24)
