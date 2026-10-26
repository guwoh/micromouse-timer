import time

import numpy as np

from core.fsm import TimerFSM
from core.models import FramePacket
from pipeline.process_worker import ProcessWorker
from pipeline.shared_state import SharedFrameState
from vision.roi_builder import build_rois


def test_raw_frame_rois_follow_camera_resolution():
    shared = SharedFrameState()
    worker = ProcessWorker(
        shared, {"processing": {"start_corner": "bottom_left"}}, TimerFSM()
    )
    worker.start()
    capture_start = time.perf_counter()
    try:
        for index, (width, height) in enumerate(((640, 480), (800, 600))):
            with shared.lock:
                shared.latest = FramePacket(
                    np.zeros((height, width, 3), dtype=np.uint8),
                    capture_start + index * 0.05,
                    index,
                )
            deadline = time.monotonic() + 2
            while (worker._last_frame_index != index or
                   worker.latest_output.result.rois != build_rois((width, height), "bottom_left")):
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert worker.latest_output.overlay_frame.shape[:2] == (height, width)
            assert worker.latest_output.overlay_frame is shared.latest.frame
    finally:
        worker.stop()


def test_roi_editor_keeps_the_other_regions_aligned_to_the_raw_camera():
    from core.models import RoiBundle

    worker = ProcessWorker(SharedFrameState(), {}, TimerFSM())
    worker._frame_size = (640, 480)
    worker.rois = RoiBundle((20, 300, 40, 10), (250, 150, 80, 80),
                           start_before=(15, 310, 50, 50), start_after=(15, 240, 50, 50))
    worker.detector.transform = np.float32([[1, 0, 3], [0, 1, 2]])
    worker.set_roi("goal_outer", (220, 120, 140, 140))
    assert worker.rois.start_line == (23, 302, 40, 10)
    assert worker.rois.start_before == (18, 312, 50, 50)
    assert worker.rois.start_after == (18, 242, 50, 50)
    assert worker.rois.goal_outer == (220, 120, 140, 140)
    assert worker.detector.motion.reference is None
