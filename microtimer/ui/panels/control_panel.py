from PyQt6 import QtWidgets

from ui.components.dashboard import Card, button, label


class ControlPanel(Card):
    """Session setup; run controls are mounted in the timing card."""
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(9)
        layout.addWidget(label("Session setup", title=True))
        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(8)
        self.team_name_edit = QtWidgets.QLineEdit()
        self.team_name_edit.setPlaceholderText("Team name")
        self.duration_spin = QtWidgets.QSpinBox()
        self.duration_spin.setRange(1, 180)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" min")
        form.addWidget(QtWidgets.QLabel("Team"), 0, 0)
        form.addWidget(self.team_name_edit, 0, 1)
        form.addWidget(QtWidgets.QLabel("Duration"), 1, 0)
        form.addWidget(self.duration_spin, 1, 1)
        layout.addLayout(form)
        row = QtWidgets.QHBoxLayout()
        self.start_session_btn = button("Start Session", "primary")
        self.stop_session_btn = button("Stop Session", "danger")
        row.addWidget(self.start_session_btn)
        row.addWidget(self.stop_session_btn)
        layout.addLayout(row)
        self.settings_btn = button("Sampling / Detection…")
        layout.addWidget(self.settings_btn)
        self.arm_btn = button("Arm", "primary")
        self.reset_btn = button("Reset")
        self.next_run_btn = button("Next Run")
