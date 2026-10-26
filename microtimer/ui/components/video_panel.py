from PyQt6 import QtCore, QtWidgets

from ui.components.dashboard import Card, button, label
from ui.components.interactive_label import InteractiveLabel


class VideoPanel(Card):
    """Camera card whose viewport depends only on its allocated size."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title = label("Live camera", self, title=True)
        self.source_combo = QtWidgets.QComboBox(self)
        for text, source in (("USB camera", "usb"), ("IP stream", "ip"), ("Mock video", "mock")):
            self.source_combo.addItem(text, source)
        self.connect_btn = button("Connect", "primary")
        self.configure_btn = button("Configure")
        self.reset_rois_btn = button("Reset ROIs")
        for widget in (self.connect_btn, self.configure_btn, self.reset_rois_btn):
            widget.setParent(self)
        self.preview = InteractiveLabel("Connect a camera or choose a Mock video in Configure", self)
        self.help = label("Left-drag: Start line   ·   Right-drag: Goal area", self)
        self.roi_target_combo = QtWidgets.QComboBox(self)
        for text, target in (
            ("Quick draw · Start / Goal", None), ("Start · line", "start"),
            ("Start A · before line", "start_before"), ("Start B · after line", "start_after"),
            ("Goal · inner region", "goal"), ("Goal · outer region", "goal_outer"),
        ):
            self.roi_target_combo.addItem(text, target)
        self.roi_target_combo.currentIndexChanged.connect(self._set_target)

    def _set_target(self):
        self.preview.roi_target = self.roi_target_combo.currentData()
        text = "Left-drag: Start line   ·   Right-drag: Goal area" if self.preview.roi_target is None else "Drag to set: " + self.roi_target_combo.currentText()
        self.help.setText(text)
        self.help.setToolTip(text)

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h, m = self.width(), self.height(), 12
        narrow = w < 650
        self.title.setGeometry(m + 4, 10, w - 2 * m if narrow else w - 442, 36)
        # At compact widths controls wrap into a dedicated, fixed-height row.
        y = 50 if narrow else 10
        self.source_combo.setGeometry(m if narrow else w - 408, y, 110 if narrow else 142, 36)
        self.connect_btn.setGeometry(m + 118 if narrow else w - 258, y, 120 if narrow else 124, 36)
        self.configure_btn.setGeometry(m + 246 if narrow else w - 126, y, 114, 36)
        self.configure_btn.setIconSize(QtCore.QSize(0, 0) if narrow else QtCore.QSize(16, 16))
        toolbar_y = y + 44
        self.roi_target_combo.setGeometry(m, toolbar_y, min(286, w - 150), 34)
        self.reset_rois_btn.setGeometry(w - m - 112, toolbar_y, 112, 34)
        preview_y = toolbar_y + 42
        self.preview.setGeometry(m, preview_y, w - 2 * m, max(120, h - preview_y - 34))
        self.help.setGeometry(m + 3, h - 28, w - 2 * m - 6, 22)
