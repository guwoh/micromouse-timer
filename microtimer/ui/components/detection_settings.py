from PyQt6 import QtWidgets

from ui.components.interaction import AnimatedDialog, FeedbackButton


class DetectionSettingsDialog(AnimatedDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sampling and detection")
        self.setMinimumWidth(420)
        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Times use capture timestamps. Actual sampling also depends on camera FPS. "
            "Goal confirmation does not add its hold time to the recorded finish time."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QtWidgets.QFormLayout()
        self.sample_ms = self._spin(config.get("sample_interval_ms", 30), 5, 250)
        self.goal_ms = self._spin(config.get("goal_hold_ms", 80), 0, 1000)
        self.transition_ms = self._spin(config.get("transition_timeout_ms", 1500), 100, 5000)
        form.addRow("Requested sampling period:", self.sample_ms)
        form.addRow("Goal confirmation hold:", self.goal_ms)
        form.addRow("Maximum A → B / outside → inside:", self.transition_ms)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox()
        apply_button = FeedbackButton("Apply")
        apply_button.setProperty("role", "primary")
        apply_button.setDefault(True)
        buttons.addButton(apply_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(FeedbackButton("Cancel"), QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _spin(value, low, high):
        spin = QtWidgets.QSpinBox()
        spin.setRange(low, high)
        spin.setValue(round(value))
        spin.setSuffix(" ms")
        return spin

    def values(self):
        return self.sample_ms.value(), self.goal_ms.value(), self.transition_ms.value()
