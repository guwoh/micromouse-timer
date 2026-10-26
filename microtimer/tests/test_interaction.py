import numpy as np
from PyQt6 import QtCore, QtTest, QtWidgets

from ui.components.detection_settings import DetectionSettingsDialog
from ui.components.interaction import DialogBackdrop


def test_popup_keeps_video_running_and_closes_with_escape_without_moving_it(window, qapp):
    window.camera_panel.source_combo.setCurrentText("mock")
    window.on_connect()
    QtTest.QTest.qWait(180)
    preview = window.preview_label
    geometry = QtCore.QRect(preview.geometry())
    origin = preview.mapTo(window, QtCore.QPoint())
    image_rect = QtCore.QRect(preview.image_rect())
    with window.shared_state.lock:
        frame_before = window.shared_state.latest.frame_index
    dialog = window.camera_dialog
    rejected = QtTest.QSignalSpy(dialog.rejected)
    finished = QtTest.QSignalSpy(dialog.finished)
    window.video_panel.configure_btn.click()
    assert dialog.isVisible() and dialog.isModal()
    assert dialog._backdrop.isVisible()
    QtTest.QTest.qWait(230)
    with window.shared_state.lock:
        assert window.shared_state.latest.frame_index > frame_before
    assert dialog._backdrop.strength == 0.30
    assert not dialog._opacity.isEnabled()
    assert preview.geometry() == geometry
    assert preview.mapTo(window, QtCore.QPoint()) == origin
    assert preview.image_rect() == image_rect
    QtTest.QTest.keyClick(dialog, QtCore.Qt.Key.Key_Escape)
    assert dialog.isVisible()  # Modal until the closing animation completes.
    QtTest.QTest.qWait(170)
    assert not dialog.isVisible()
    assert dialog._backdrop is None
    assert len(rejected) == len(finished) == 1
    dialog.open()
    QtTest.QTest.qWait(35)
    window.close()
    QtTest.QTest.qWait(35)
    assert not dialog.isVisible()
    assert dialog._backdrop is None
    assert len(rejected) == len(finished) == 2
    assert window.video_panel.configure_btn.isEnabled()
    assert preview.geometry() == geometry


def test_popup_result_is_emitted_once_when_closed_during_opening_and_can_reopen(window):
    dialog = DetectionSettingsDialog({}, window)
    accepted = QtTest.QSignalSpy(dialog.accepted)
    rejected = QtTest.QSignalSpy(dialog.rejected)

    def apply_during_opening():
        dialog.sample_ms.setValue(80)
        buttons = dialog.findChild(QtWidgets.QDialogButtonBox)
        apply_button = next(button for button in buttons.buttons() if buttons.buttonRole(button) == QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        apply_button.click()
        dialog.accept()
        dialog.reject()

    QtCore.QTimer.singleShot(35, apply_during_opening)
    assert dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.values()[0] == 80
    assert len(accepted) == 1 and len(rejected) == 0
    assert not dialog.isVisible() and dialog._backdrop is None
    cancel = next(button for button in dialog.findChild(QtWidgets.QDialogButtonBox).buttons() if button.text() == "Cancel")
    QtCore.QTimer.singleShot(35, cancel.click)
    assert dialog.exec() == QtWidgets.QDialog.DialogCode.Rejected
    assert len(accepted) == len(rejected) == 1
    assert dialog._backdrop is None
    assert window.isEnabled()


def test_hiding_a_popup_cleans_up_backdrop_and_resize_tracks_parent(window, qapp):
    dialog = window.camera_dialog
    dialog.open()
    QtTest.QTest.qWait(40)
    window.resize(1024, 640)
    qapp.processEvents()
    assert dialog._backdrop.geometry() == window.rect()
    dialog.hide()
    QtTest.QTest.qWait(30)
    assert dialog._backdrop is None
    assert not any(widget.isVisible() for widget in window.findChildren(DialogBackdrop))
    dialog.open()
    QtTest.QTest.qWait(180)
    dialog.close()
    QtTest.QTest.qWait(160)
    assert not dialog.isVisible()
    assert dialog._backdrop is None


def test_pointer_and_keyboard_feedback_do_not_move_or_repeat_button_actions(window, qapp):
    window.ui_timer.stop()
    window.preview_label.set_frame(np.zeros((720, 1280, 3), np.uint8))
    qapp.processEvents()
    button = window.control_panel.arm_btn
    geometry = QtCore.QRect(button.geometry())
    video_geometry = QtCore.QRect(window.preview_label.geometry())
    clicked = QtTest.QSignalSpy(button.clicked)
    QtTest.QTest.mousePress(button, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(18, 18))
    QtTest.QTest.qWait(35)
    assert button.isDown()
    assert 0 < button._pulse < 1
    QtTest.QTest.mouseRelease(button, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(18, 18))
    assert len(clicked) == 1
    button.setFocus()
    QtTest.QTest.keyClick(button, QtCore.Qt.Key.Key_Space)
    assert len(clicked) == 2
    button.setEnabled(False)
    QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    assert len(clicked) == 2
    QtTest.QTest.qWait(270)
    assert button.geometry() == geometry
    assert window.preview_label.geometry() == video_geometry
    assert button._animation.state() == QtCore.QAbstractAnimation.State.Stopped
