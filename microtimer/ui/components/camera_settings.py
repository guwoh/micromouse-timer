from PyQt6 import QtWidgets

from ui.components.interaction import AnimatedDialog, FeedbackButton

from ui.components.dashboard import label
from ui.panels.camera_panel import CameraPanel


class CameraSettingsDialog(AnimatedDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera configuration")
        self.setMinimumWidth(490)
        self.resize(540, 440)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(label("Camera source", title=True))
        self.camera_panel = CameraPanel(config)
        layout.addWidget(self.camera_panel)
        group = QtWidgets.QGroupBox("Live detection diagnostics")
        form = QtWidgets.QFormLayout(group)
        self.vision_label = QtWidgets.QLabel("Not connected")
        self.comparison_label = QtWidgets.QLabel("—")
        self.sampling_label = QtWidgets.QLabel("—")
        self.goal_label = QtWidgets.QLabel("—")
        for title, widget in (("Vision", self.vision_label), ("Goal gate", self.goal_label), ("Zones", self.comparison_label), ("Sampling", self.sampling_label)):
            widget.setWordWrap(True)
            form.addRow(title, widget)
        layout.addWidget(group)
        buttons = QtWidgets.QDialogButtonBox()
        buttons.addButton(FeedbackButton("Close"), QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
