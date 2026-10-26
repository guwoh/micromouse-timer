import time

import numpy as np
import pytest
from PyQt6 import QtCore, QtGui, QtTest, QtWidgets

from core.fsm import TimerSnapshot
from core.models import TimerState
from vision.camera.video_file import VideoFileSource


@pytest.mark.parametrize("size", [(1280, 840), (1024, 640), (760, 480)])
def test_controls_keep_legible_height_at_small_window_sizes(window, qapp, size):
    window.resize(*size)
    QtTest.QTest.qWait(30)
    for button in window.findChildren(QtWidgets.QPushButton):
        if not button.isVisible():
            continue
        assert button.height() >= 32, button.text()
        assert button.width() > button.fontMetrics().horizontalAdvance(button.text()) + 12, (
            button.text(), button.font().toString(), QtGui.QFontInfo(button.font()).family(),
            button.logicalDpiX(), button.devicePixelRatioF(),
        )
    for field in (
        window.camera_panel.input_edit, window.camera_panel.source_combo,
        window.control_panel.team_name_edit, window.control_panel.duration_spin,
    ):
        if field.isVisible():
            assert field.height() >= field.fontMetrics().height() + 6
    assert window.dashboard.timing.x() > window.video_panel.x() + window.video_panel.width()
    assert window.history_panel.y() > window.video_panel.y() + window.video_panel.height()
    assert not window.club_banner._pixmap.isNull()


def test_recording_runs_and_long_labels_do_not_resize_video(window, qapp, tmp_path):
    window.ui_timer.stop()
    preview = window.preview_label
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    preview.set_frame(frame)
    qapp.processEvents()
    geometry = QtCore.QRect(preview.geometry())
    image_rect = QtCore.QRect(preview.image_rect())
    hint = preview.sizeHint()
    window.competition.start("SRC " * 100, 180, tmp_path)
    window.timer_fsm.snapshot = TimerSnapshot(
        state=TimerState.FINISHED, start_ts=100.0, finish_ts=10900.123, elapsed_s=10800.123,
    )
    window.on_ui_tick()
    for _ in range(10):
        window.on_ui_tick()
    assert len(window.competition.runs) == 1
    assert window.history_panel.table.rowCount() == 1
    assert window.status_panel.run_count_label.text() == "1"
    window.history_panel.sync_runs([10800.123] * 1000)
    window.status_panel.run_count_label.setText("1000")
    qapp.processEvents()
    assert preview.geometry() == geometry
    assert preview.image_rect() == image_rect
    preview.set_frame(np.zeros((800, 800, 3), dtype=np.uint8))
    qapp.processEvents()
    assert preview.geometry() == geometry
    assert preview.sizeHint() == hint


def test_roi_mapping_uses_letterboxed_image_and_clamps_start_line(window, qapp):
    preview = window.preview_label
    preview.set_frame(np.zeros((800, 800, 3), dtype=np.uint8))
    qapp.processEvents()
    rect = preview.image_rect()
    assert preview._map_to_image(rect.center()) == pytest.approx((400, 400), abs=2)
    assert preview._map_to_image(QtCore.QPoint(-1, -1)) is None
    signals = QtTest.QSignalSpy(preview.roi_updated)
    start = rect.topLeft() + QtCore.QPoint(1, 1)
    end = start + QtCore.QPoint(max(30, rect.width() // 3), 0)
    QtTest.QTest.mousePress(preview, QtCore.Qt.MouseButton.LeftButton, pos=start)
    QtTest.QTest.mouseRelease(preview, QtCore.Qt.MouseButton.LeftButton, pos=end)
    assert len(signals) == 1
    mode, (x, y, w, h) = signals[0]
    assert mode == "start"
    assert 0 <= x < 800 and 0 <= y < 800
    assert x + w <= 800 and y + h <= 800


def test_two_video_replays_are_recorded_without_resizing(window, qapp, test_video):
    window.camera_panel.source_combo.setCurrentText("mock")
    assert window.camera_panel.input_edit.isEnabled()
    window.camera_dialog.show()
    assert window.camera_panel.browse_btn.isVisible()
    window.camera_dialog.hide()
    window.camera_panel.input_edit.setText(str(test_video))
    window.on_connect()
    assert isinstance(window.camera, VideoFileSource)
    window.on_start_session()
    QtTest.QTest.qWait(60)
    geometry = QtCore.QRect(window.preview_label.geometry())
    for run in (1, 2):
        window.on_next_run()
        deadline = time.monotonic() + 7
        while len(window.competition.runs) < run:
            assert time.monotonic() < deadline, window.timer_fsm.snapshot
            QtTest.QTest.qWait(30)
        assert window.history_panel.table.rowCount() == run
        assert window.status_panel.run_count_label.text() == str(run)
        assert window.preview_label.geometry() == geometry
        assert window.timer_fsm.snapshot.state == TimerState.FINISHED
    window.on_disconnect()
    assert window.camera is None and window.process_worker is None
    assert window.shared_state.latest is None


def test_actual_video_does_not_move_during_live_status_and_counter_updates(window, qapp):
    window.camera_panel.source_combo.setCurrentText("mock")
    window.on_connect()
    QtTest.QTest.qWait(120)
    preview = window.preview_label
    assert (preview.orig_w, preview.orig_h) == (1920, 1080)
    geometry = QtCore.QRect(preview.geometry())
    origin = preview.mapTo(window, QtCore.QPoint())
    image_rect = QtCore.QRect(preview.image_rect())
    for index, count in enumerate((1, 9, 10, 99, 100, 999, 1000, 9, 0)):
        window.competition.team_name = "SRC " * (index * 20 + 1)
        window.competition.runs = [1000.123] * count
        window.history_panel.sync_runs(window.competition.runs)
        window.timer_fsm.snapshot = TimerSnapshot(
            state=list(TimerState)[index % 4], elapsed_s=10 ** index + 0.123,
        )
        window.on_ui_tick()
        window.statusBar().showMessage("Video playing " * (index * 20 + 1))
        QtTest.QTest.qWait(40)
        assert preview.geometry() == geometry
        assert preview.mapTo(window, QtCore.QPoint()) == origin
        assert preview.image_rect() == image_rect
    assert window.camera.cap.get(1) > 2


def test_browse_selects_a_real_video_and_missing_file_reports_error(window, monkeypatch, test_video):
    window.camera_panel.source_combo.setCurrentText("mock")
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *args: (str(test_video), "Videos (*.mp4)"),
    )
    window.camera_panel.browse_btn.click()
    assert window.camera_panel.input_edit.text() == str(test_video)
    window.on_connect()
    assert window.camera.is_opened()
    window.on_disconnect()
    window.camera_panel.input_edit.setText(str(test_video.parent / "missing.mp4"))
    window.on_connect()
    assert window.camera is None
    assert "Cannot open video" in window.statusBar().currentMessage()


@pytest.mark.parametrize("target", ["start_before", "start_after", "goal_outer"])
def test_each_comparison_zone_can_be_selected_and_drawn(window, qapp, target):
    preview = window.preview_label
    preview.set_frame(np.zeros((800, 800, 3), dtype=np.uint8))
    selector = window.video_panel.roi_target_combo
    selector.setCurrentIndex(selector.findData(target))
    qapp.processEvents()
    geometry = QtCore.QRect(preview.geometry())
    rect = preview.image_rect()
    start = rect.topLeft() + QtCore.QPoint(rect.width() // 4, rect.height() // 4)
    end = start + QtCore.QPoint(rect.width() // 3, rect.height() // 5)
    signals = QtTest.QSignalSpy(preview.roi_updated)
    QtTest.QTest.mousePress(preview, QtCore.Qt.MouseButton.LeftButton, pos=start)
    QtTest.QTest.mouseRelease(preview, QtCore.Qt.MouseButton.LeftButton, pos=end)
    assert len(signals) == 1
    mode, (_, _, w, h) = signals[0]
    assert mode == target and w > 15 and h > 15
    assert preview.geometry() == geometry


def test_sampling_dialog_updates_live_worker_without_moving_video(window, monkeypatch, qapp):
    window.camera_panel.source_combo.setCurrentText("mock")
    window.on_connect()
    QtTest.QTest.qWait(120)
    geometry = QtCore.QRect(window.preview_label.geometry())

    class AcceptedDialog:
        def __init__(self, *args):
            pass
        def exec(self):
            return QtWidgets.QDialog.DialogCode.Accepted
        def values(self):
            return 80, 120, 900

    monkeypatch.setattr("ui.main_window.DetectionSettingsDialog", AcceptedDialog)
    window.on_detection_settings()
    QtTest.QTest.qWait(300)
    assert window.process_worker.sample_interval_ms == 80
    assert window.process_worker.detector.goal_hold_ms == 120
    assert window.process_worker.detector.transition_timeout_ms == 900
    assert window.process_worker.latest_output.result.sample_dt_ms >= 79
    assert window.preview_label.geometry() == geometry
    from app.preferences import load_processing_preferences
    assert load_processing_preferences()["sample_interval_ms"] == 80


def test_finish_during_ui_render_does_not_mix_running_and_finished_labels(window, monkeypatch, tmp_path):
    from core.models import DetectionResult
    from pipeline.process_worker import ProcessWorker, ProcessOutput

    window.ui_timer.stop()
    window.competition.start("SRC", 10, tmp_path)
    began = time.perf_counter() - 2
    window.timer_fsm.snapshot = TimerSnapshot(state=TimerState.RUNNING, start_ts=began)
    worker = ProcessWorker(window.shared_state, window.config, window.timer_fsm)
    worker.latest_output = ProcessOutput(DetectionResult(), np.zeros((240, 320, 3), np.uint8))
    window.process_worker = worker
    rendered_states = []

    def finish_during_draw(frame, result, state, elapsed):
        rendered_states.append(state)
        window.timer_fsm.on_finish_trigger(began + 2)
        return frame

    monkeypatch.setattr("ui.main_window.draw_overlay", finish_during_draw)
    window.on_ui_tick()
    assert rendered_states[-1] == TimerState.RUNNING
    assert window.status_panel.state_label.text() == "RUNNING"
    assert len(window.competition.runs) == 0
    window.on_ui_tick()
    assert rendered_states[-1] == TimerState.FINISHED
    assert window.status_panel.state_label.text() == "FINISHED"
    assert window.competition.runs == pytest.approx([2.0])


def test_dashboard_source_controls_diagnostics_and_session_lock(window, qapp, monkeypatch):
    header_source = window.video_panel.source_combo
    header_source.setCurrentIndex(header_source.findData("mock"))
    assert window.camera_panel.source_combo.currentText() == "mock"
    window.video_panel.configure_btn.click()
    qapp.processEvents()
    assert window.camera_dialog.isVisible()
    for widget in (window.camera_panel.input_edit, window.camera_panel.browse_btn,
                   window.camera_panel.connect_btn, window.camera_panel.disconnect_btn):
        assert widget.isVisible()
        assert widget.height() >= 32
    window.camera_dialog.accept()
    window.video_panel.connect_btn.click()
    QtTest.QTest.qWait(180)
    assert isinstance(window.camera, VideoFileSource)
    assert window.video_panel.connect_btn.text() == "Disconnect"
    assert "Mock video playing" in window.header.connection.text()
    assert window.camera_dialog.vision_label.text() != "Not connected"
    assert "ms requested" in window.camera_dialog.sampling_label.text()
    window.control_panel.team_name_edit.setText("SRC Team 04")
    window.control_panel.start_session_btn.click()
    window.on_ui_tick()
    assert window.active_team.team_label.text() == "SRC Team 04"
    assert not window.video_panel.roi_target_combo.isEnabled()
    assert not window.video_panel.reset_rois_btn.isEnabled()
    assert not window.control_panel.settings_btn.isEnabled()
    assert not window.control_panel.start_session_btn.isEnabled()
    assert window.control_panel.stop_session_btn.isEnabled()
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args: None)
    window.control_panel.stop_session_btn.click()
    window.on_ui_tick()
    assert window.video_panel.roi_target_combo.isEnabled()
    assert window.control_panel.settings_btn.isEnabled()
    window.video_panel.connect_btn.click()
    window.on_ui_tick()
    assert window.camera is None
    assert "Disconnected" in window.header.connection.text()
    assert window.video_panel.connect_btn.text() == "Connect"


def test_history_highlights_fastest_and_new_session_clears_results(window, tmp_path, monkeypatch):
    window.ui_timer.stop()
    window.competition.start("SRC", 10, tmp_path)
    for index, elapsed in enumerate((8.5, 7.25, 9.0)):
        began = 100.0 + index * 20
        snap = TimerSnapshot(state=TimerState.FINISHED, start_ts=began, finish_ts=began + elapsed, elapsed_s=elapsed)
        window._record_finished_run(snap)
        window._record_finished_run(snap)
    table = window.history_panel.table
    assert table.rowCount() == 3
    assert table.item(0, 2).text() == "✓  Valid"
    assert table.item(1, 2).text() == "★  Best"
    assert table.item(1, 1).text() == "7.250 s"
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args: None)
    window.on_stop_session()
    assert table.rowCount() == 3
    assert window.competition.export_done
    window.on_start_session()
    assert table.rowCount() == 0
    assert window.competition.runs == []


def test_footer_fields_and_connection_button_stay_inside_their_cards(window, qapp):
    window.video_panel.connect_btn.setText("Disconnect")
    for size in ((1920, 1080), (1440, 960), (1024, 640), (760, 480)):
        window.resize(*size)
        qapp.processEvents()
        footer = window.footer
        assert footer.rois.geometry().right() < footer.note.geometry().left()
        assert footer.note.geometry().right() < footer.sampling.geometry().left()
        assert footer.sampling.geometry().right() < footer.width()
        button = window.video_panel.connect_btn
        assert button.width() >= button.fontMetrics().horizontalAdvance(button.text()) + 24
        for widget in (window.video_panel.configure_btn, button, window.video_panel.source_combo):
            assert window.video_panel.rect().contains(widget.geometry())
        assert window.dashboard_scroll.horizontalScrollBar().maximum() == 0
    assert window.dashboard_scroll.verticalScrollBar().maximum() > 0


def test_fast_real_robot_finishes_with_tight_goal_roi_and_clock_stays_stopped(window, qapp):
    """Regression: OUT was below 1%, then IN/OUT changed in the same sample."""
    window.camera_panel.source_combo.setCurrentText("mock")
    window.on_connect()
    QtTest.QTest.qWait(180)
    window.on_roi_updated("start", (354, 865, 55, 14))
    window.on_roi_updated("goal", (889, 369, 114, 96))
    window.on_start_session()
    window.on_next_run()
    geometry = QtCore.QRect(window.preview_label.geometry())
    deadline = time.monotonic() + 15
    while not window.competition.runs:
        assert time.monotonic() < deadline, (
            window.timer_fsm.tick(), window.camera_dialog.goal_label.text(),
        )
        QtTest.QTest.qWait(25)
    assert window.timer_fsm.tick().state == TimerState.FINISHED
    assert window.history_panel.table.rowCount() == 1
    assert 7 < window.competition.runs[0] < 9
    clock = window.status_panel.elapsed_label.text()
    QtTest.QTest.qWait(220)
    assert window.status_panel.elapsed_label.text() == clock
    assert window.history_panel.table.rowCount() == 1
    assert window.preview_label.geometry() == geometry
