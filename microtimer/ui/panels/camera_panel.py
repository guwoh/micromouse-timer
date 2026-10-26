from PyQt6 import QtCore, QtWidgets
from app.paths import resource_root
from ui.components.interaction import FeedbackButton


class CameraPanel(QtWidgets.QWidget):
    def __init__(self, config: dict | None = None):
        super().__init__()
        config = config or {}
        self._values = {
            "usb": str(config.get("usb_index", 0)),
            "ip": config.get("ip_url", ""),
            "mock": config.get("mock_video") or str(resource_root() / "samples" / "mock_run_real.mp4"),
        }
        self._source = config.get("source_type", "usb")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.source_combo = QtWidgets.QComboBox()
        self.source_combo.addItems(["usb", "ip", "mock"])
        self.source_combo.setCurrentText(self._source)
        self.input_edit = QtWidgets.QLineEdit()
        self.browse_btn = FeedbackButton("Browse")
        self.browse_btn.setFixedWidth(78)
        self.browse_btn.setMinimumHeight(32)
        self.browse_btn.clicked.connect(self._browse_video)
        input_row = QtWidgets.QHBoxLayout()
        input_row.addWidget(self.input_edit, 1)
        input_row.addWidget(self.browse_btn)
        self.input_label = QtWidgets.QLabel("Index / URL:")
        form.addRow("Source:", self.source_combo)
        form.addRow(self.input_label, input_row)
        layout.addLayout(form)
        buttons = QtWidgets.QHBoxLayout()
        self.connect_btn = FeedbackButton("Connect")
        self.disconnect_btn = FeedbackButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        for button in (self.connect_btn, self.disconnect_btn):
            button.setMinimumHeight(32)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.hint_label = QtWidgets.QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet("color: #65738a; font-size: 11px;")
        self.hint_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        layout.addWidget(self.hint_label)
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        self._show_source(self._source)

    def _on_source_changed(self, source: str):
        if self._source in self._values:
            self._values[self._source] = self.input_edit.text()
        self._source = source
        self._show_source(source)

    def _show_source(self, source: str):
        self.input_edit.setEnabled(True)
        self.input_edit.setText(self._values.get(source, ""))
        self.input_label.setText("Video:" if source == "mock" else "Index / URL:")
        self.browse_btn.setVisible(source in ("ip", "mock"))
        self.input_edit.setPlaceholderText("0" if source == "usb" else "rtsp://... or video path")
        hints = {
            "usb": "Use the camera index, for example 0 or 1.",
            "ip": "Enter a stream URL or the full path to a video.",
            "mock": "Test video · Set Start/Goal, then Next Run to replay.",
        }
        self.hint_label.setText(hints.get(source, ""))

    def _browse_video(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose a test video", self.input_edit.text(),
            "Videos (*.mp4 *.avi *.mkv *.mov *.m4v);;All files (*)",
        )
        if path:
            self.input_edit.setText(path)
