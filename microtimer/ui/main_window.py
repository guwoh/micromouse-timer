from __future__ import annotations

import time

from PyQt6 import QtCore, QtGui, QtWidgets

from app.paths import data_root, resource_root
from app.preferences import save_processing_preferences
from core.competition import CompetitionSession
from core.fsm import TimerFSM
from pipeline.capture_worker import CaptureWorker
from pipeline.process_worker import ProcessWorker
from pipeline.shared_state import SharedFrameState
from ui.panels.control_panel import ControlPanel
from ui.panels.status_panel import StatusPanel
from ui.components.video_panel import VideoPanel
from ui.components.camera_settings import CameraSettingsDialog
from ui.components.dashboard import STYLE, AppHeader, ActiveTeam, DashboardBody, DashboardFooter, RunHistory
from ui.components.detection_settings import DetectionSettingsDialog
from vision.camera.factory import build_camera_source
from vision.camera.video_file import VideoFileSource
from vision.overlay import draw_overlay


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.setWindowTitle("Micromouse Timer 1.2.2")
        self.setWindowIcon(QtGui.QIcon(str(resource_root() / "assets" / "icons" / "micromouse.png")))
        self.resize(1440, 960)
        self.setMinimumSize(760, 480)
        self.config = config
        self.timer_fsm = TimerFSM(
            debounce_ms=int(config.get("processing", {}).get("debounce_ms", 80)),
            min_run_ms=200,
        )
        self.shared_state = SharedFrameState()
        self.capture_worker: CaptureWorker | None = None
        self.process_worker: ProcessWorker | None = None
        self.camera = None
        self.competition = CompetitionSession()
        self.saved_rois = None
        self.saved_frame_size = None
        self._last_recorded_finish = None

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = AppHeader()
        self.club_banner = self.header.logo
        self.camera_dialog = CameraSettingsDialog(config.get("camera", {}), self)
        self.camera_panel = self.camera_dialog.camera_panel
        self.control_panel = ControlPanel()
        self.status_panel = StatusPanel(self.control_panel)
        self.active_team = ActiveTeam()
        self.history_panel = RunHistory()
        self.video_panel = VideoPanel()
        self.preview_label = self.video_panel.preview
        self.preview_label.roi_updated.connect(self.on_roi_updated)
        self.dashboard = DashboardBody(
            self.video_panel, self.history_panel, self.active_team, self.status_panel, self.control_panel,
        )
        self.dashboard_scroll = QtWidgets.QScrollArea()
        self.dashboard_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.dashboard_scroll.setWidgetResizable(True)
        self.dashboard_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.dashboard_scroll.setWidget(self.dashboard)
        self.footer = DashboardFooter()
        layout.addWidget(self.header)
        layout.addWidget(self.dashboard_scroll, 1)
        layout.addWidget(self.footer)
        self.setCentralWidget(central)
        self.setStyleSheet(STYLE)

        self.video_panel.source_combo.setCurrentIndex(self.camera_panel.source_combo.currentIndex())
        self.video_panel.source_combo.currentIndexChanged.connect(self.camera_panel.source_combo.setCurrentIndex)
        self.camera_panel.source_combo.currentIndexChanged.connect(self.video_panel.source_combo.setCurrentIndex)
        self.video_panel.connect_btn.clicked.connect(self.on_toggle_connection)
        self.video_panel.configure_btn.clicked.connect(self.camera_dialog.open)
        self.camera_panel.connect_btn.clicked.connect(self.on_connect)
        self.camera_panel.disconnect_btn.clicked.connect(self.on_disconnect)
        self.control_panel.arm_btn.clicked.connect(self.on_arm)
        self.control_panel.reset_btn.clicked.connect(self.on_reset)
        self.control_panel.next_run_btn.clicked.connect(self.on_next_run)
        self.control_panel.start_session_btn.clicked.connect(self.on_start_session)
        self.control_panel.stop_session_btn.clicked.connect(self.on_stop_session)
        self.video_panel.reset_rois_btn.clicked.connect(self.on_reset_rois)
        self.control_panel.settings_btn.clicked.connect(self.on_detection_settings)
        self.statusBar().hide()
        self.statusBar().messageChanged.connect(self.footer.note.setText)
        self.statusBar().showMessage("Ready · Select USB, IP, or Mock")

        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self.on_ui_tick)
        self.ui_timer.start(33)

    def on_toggle_connection(self):
        if self.camera is None:
            self.on_connect()
        else:
            self.on_disconnect()

    def on_roi_updated(self, mode: str, rect: tuple[int, int, int, int]) -> None:
        if self.competition.active:
            # Ignore edits during an active competition match
            return
        if not self.process_worker:
            return
        if self.process_worker.rois is None:
            return

        self.process_worker.set_roi(mode, rect)
        self.saved_rois = self.process_worker.rois
        self.saved_frame_size = self.process_worker._frame_size

    def on_connect(self) -> None:
        self.on_disconnect()
        source_type = self.camera_panel.source_combo.currentText().strip()
        text = self.camera_panel.input_edit.text().strip()
        self.config.setdefault("camera", {})
        self.config["camera"]["source_type"] = source_type
        if source_type == "ip":
            self.config["camera"]["ip_url"] = text
        elif source_type == "mock":
            self.config["camera"]["mock_video"] = text
        elif source_type == "usb":
            self.config["camera"]["usb_index"] = int(text) if text.isdigit() else 0

        self.camera = build_camera_source(self.config)
        if isinstance(self.camera, VideoFileSource) and not self.camera.open():
            self.statusBar().showMessage(f"Cannot open video: {self.camera.path}")
            self.camera = None
            return
        self.capture_worker = CaptureWorker(self.camera, self.shared_state)
        self.process_worker = ProcessWorker(self.shared_state, self.config, self.timer_fsm)

        if self.saved_rois is not None:
            self.process_worker.rois = self.saved_rois
            self.process_worker._frame_size = self.saved_frame_size
            self.process_worker._rois_user_set = True

        self.capture_worker.start()
        self.process_worker.start()
        self.camera_panel.disconnect_btn.setEnabled(True)
        self.video_panel.connect_btn.setText("Disconnect")
        self.statusBar().showMessage(
            "Mock video playing · Next Run replays from the beginning" if source_type == "mock" else "Camera connection started"
        )

    def on_disconnect(self) -> None:
        if self.capture_worker:
            self.capture_worker.stop()
        if self.process_worker:
            self.process_worker.stop()
        if self.camera:
            self.camera.release()
        self.capture_worker = self.process_worker = self.camera = None
        with self.shared_state.lock:
            self.shared_state.latest = None
        self.preview_label.clear_frame()
        self.camera_panel.disconnect_btn.setEnabled(False)
        self.video_panel.connect_btn.setText("Connect")
        self.header.set_connection(False)
        self.statusBar().showMessage("Disconnected")

    def on_reset(self) -> None:
        self._record_finished_run()
        self.timer_fsm.reset()
        if isinstance(self.camera, VideoFileSource):
            self.camera.rewind()
        if self.process_worker:
            self.process_worker.reset_detector()

    def on_arm(self) -> None:
        if isinstance(self.camera, VideoFileSource):
            self.on_next_run()
        else:
            self._record_finished_run()
            self.timer_fsm.arm()

    def on_next_run(self) -> None:
        self.on_reset()
        self.timer_fsm.arm()

    def on_start_session(self) -> None:
        if self.competition.active:
            return
        team = self.control_panel.team_name_edit.text().strip()
        minutes = int(self.control_panel.duration_spin.value())
        self.competition.start(team_name=team, duration_minutes=minutes, output_dir=data_root() / "exports")
        self.history_panel.sync_runs([])
        self._last_recorded_finish = None
        self.timer_fsm.reset()
        if isinstance(self.camera, VideoFileSource):
            self.camera.rewind()
        if self.process_worker:
            self.process_worker.reset_detector()

    def on_stop_session(self) -> None:
        if self.competition.active:
            self._record_finished_run()
            self.competition.stop()
            if not self.competition.export_done:
                self._export_results()

    def on_reset_rois(self) -> None:
        if self.competition.active:
            # Ignore edits during an active competition match
            return

        self.saved_rois = None
        self.saved_frame_size = None

        # Hot-reload the config so changes to default.yaml apply instantly
        try:
            from app.config_loader import load_config
            new_cfg = load_config(resource_root() / "config" / "default.yaml")
            self.config.update(new_cfg)
        except Exception:
            pass

        if self.process_worker:
            self.process_worker.reset_rois()

    def _format_mmss(self, seconds: float) -> str:
        total = int(max(0, seconds))
        mm = total // 60
        ss = total % 60
        return f"{mm:02d}:{ss:02d}"

    def on_detection_settings(self):
        if self.competition.active:
            self.statusBar().showMessage("Stop the session before changing detection settings")
            return
        dialog = DetectionSettingsDialog(self.config.get("processing", {}), self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            sample_ms, goal_ms, transition_ms = dialog.values()
            self.config.setdefault("processing", {}).update(
                sample_interval_ms=sample_ms, goal_hold_ms=goal_ms, transition_timeout_ms=transition_ms,
            )
            if self.process_worker:
                self.process_worker.configure_timing(sample_ms, goal_ms, transition_ms)
            try:
                save_processing_preferences(self.config["processing"])
            except OSError:
                self.statusBar().showMessage("Applied for this session; settings could not be saved")

    def _export_results(self) -> None:
        output_path = self.competition.export_excel(data_root() / "exports")
        QtWidgets.QMessageBox.information(
            self,
            "Competition ended",
            f"Session results saved:\n{output_path}",
        )

    def on_ui_tick(self) -> None:
        out = self.process_worker.latest_output if self.process_worker else None
        if out is not None:
            self.camera_dialog.vision_label.setText(out.result.vision_status)
            self.camera_dialog.goal_label.setText(out.result.goal_status)
            self.camera_dialog.comparison_label.setText(
                f"Start A/B: {out.result.start_outside_ratio:.3f} / {out.result.start_inside_ratio:.3f}\n"
                f"Goal out/in: {out.result.goal_outside_ratio:.3f} / {out.result.goal_changed_ratio:.3f}"
            )
            requested = float(self.config.get("processing", {}).get("sample_interval_ms", 30))
            measured = out.result.sample_dt_ms
            actual = f"{measured:.1f} ms measured ({1000 / measured:.1f} Hz)" if measured > 0 else "Waiting for next sample"
            self.camera_dialog.sampling_label.setText(f"{requested:g} ms requested\n{actual}")
        else:
            self.camera_dialog.vision_label.setText("Not connected")
            self.camera_dialog.goal_label.setText("-")
            self.camera_dialog.comparison_label.setText("-")
            self.camera_dialog.sampling_label.setText("-")
        self.control_panel.settings_btn.setEnabled(not self.competition.active)
        self.video_panel.roi_target_combo.setEnabled(not self.competition.active)
        self.video_panel.reset_rois_btn.setEnabled(not self.competition.active)
        self.control_panel.start_session_btn.setEnabled(not self.competition.active)
        self.control_panel.stop_session_btn.setEnabled(self.competition.active)
        self.control_panel.team_name_edit.setEnabled(not self.competition.active)
        self.control_panel.duration_spin.setEnabled(not self.competition.active)
        with self.shared_state.lock:
            packet = self.shared_state.latest
        connected = packet is not None and time.perf_counter() - packet.capture_ts < 2
        mock = isinstance(self.camera, VideoFileSource)
        self.header.set_connection(connected, mock)
        source = "Mock video" if mock else self.config.get("camera", {}).get("source_type", "usb").upper()
        measured = out.result.sample_dt_ms if out else 0
        if connected and measured > 0:
            vision = "Ready" if out.result.vision_ready else "Calibrating" if "Calibrat" in out.result.vision_status else "Check vision"
            self.footer.sampling.setText(f"{source} · {vision} · {1000 / measured:.1f} Hz")
            self.footer.sampling.setToolTip(out.result.vision_status)
        else:
            self.footer.sampling.setText("Waiting for frames" if self.camera else "No source")
            self.footer.sampling.setToolTip("")
        rois = self.process_worker.rois if self.process_worker else self.saved_rois
        self.footer.rois.setText("✓ Start line set   ·   ✓ Goal area set" if rois is not None else "○ Start line   ·   ○ Goal area")
        snap = self.timer_fsm.tick()

        frame_to_show = None
        if out is not None and out.overlay_frame is not None:
            frame_to_show = draw_overlay(out.overlay_frame, out.result, snap.state, snap.elapsed_s)
        else:
            with self.shared_state.lock:
                if self.shared_state.latest is not None:
                    frame_to_show = self.shared_state.latest.frame
        if frame_to_show is not None:
            self.preview_label.set_frame(frame_to_show)

        self._record_finished_run(snap)

        if self.competition.active:
            remaining = self.competition.remaining_seconds()
            self.status_panel.countdown_label.setText(self._format_mmss(remaining))
            if self.competition.is_time_up():
                self.competition.stop()
                if not self.competition.export_done:
                    self._export_results()
        else:
            self.status_panel.countdown_label.setText("00:00")

        best = self.competition.best_time_s()
        self.active_team.team_label.setText(self.competition.team_name or self.control_panel.team_name_edit.text().strip() or "No active team")
        self.status_panel.best_label.setText("-" if best is None else f"{best:.3f} s")
        self.status_panel.run_count_label.setText(str(len(self.competition.runs)))

        self.status_panel.set_state(snap.state.value)
        self.status_panel.elapsed_label.setText(f"{snap.elapsed_s:.3f} s")

    def _record_finished_run(self, snap=None) -> None:
        snap = self.timer_fsm.tick() if snap is None else snap
        key = (snap.start_ts, snap.finish_ts)
        if self.competition.active and snap.state.value == "FINISHED" and key != self._last_recorded_finish:
            self._last_recorded_finish = key
            self.competition.add_run(snap.elapsed_s)
            self.history_panel.sync_runs(self.competition.runs)

    def closeEvent(self, event) -> None:
        if self.competition.active:
            self._record_finished_run()
            self.competition.stop()
            if not self.competition.export_done:
                self.competition.export_excel(data_root() / "exports")
        self.on_disconnect()
        super().closeEvent(event)
