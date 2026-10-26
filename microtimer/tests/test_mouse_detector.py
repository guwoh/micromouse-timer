import cv2
import numpy as np
import pytest

from app.paths import resource_root
from core.models import RoiBundle, TimerState
from vision.mouse_detector import MouseDetector as CameraDetector


class MouseDetector(CameraDetector):
    """Drive prerecorded test frames with an explicit 30 Hz capture clock."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clock = 0.0

    def update(self, frame, rois, state=None, timestamp_s=None):
        self.clock = self.clock + 1 / 30 if timestamp_s is None else timestamp_s
        return super().update(frame, rois, state=state, timestamp_s=self.clock)


@pytest.fixture
def maze():
    rng = np.random.default_rng(9)
    gray = rng.integers(30, 100, (240, 320), dtype=np.uint8)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    for x in range(10, 320, 32):
        cv2.line(gray, (x, 10), (x, 230), 150, 2)
    for y in range(10, 240, 32):
        cv2.line(gray, (10, y), (310, y), 150, 2)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def rois():
    return RoiBundle((30, 170, 50, 12), (130, 80, 50, 50))


def robot(frame, x, y):
    frame = frame.copy()
    cv2.rectangle(frame, (x - 8, y - 8), (x + 8, y + 8), (245, 245, 245), -1)
    return frame


def prime(detector, frame, rois):
    for _ in range(round(detector.warmup_ms * 30 / 1000) + 3):
        assert detector.update(frame, rois) == (False, detector.goal_zone.inside_ratio, False)
    assert detector.ready


def test_start_then_goal_requires_outside_before_inside(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    starts, finishes = [], []
    state = TimerState.ARMED
    path = [(55, y) for y in (201, 195, 190, 180, 175, 160)]
    path += [(x, 105) for x in (115, 120, 121, 132, 140, 145, 146, 147)]
    for index, (x, y) in enumerate(path):
        start, _, finish = detector.update(robot(maze, x, y), rois, state=state)
        if start:
            starts.append(index)
            state = TimerState.RUNNING
        if finish:
            finishes.append(index)
    assert len(starts) == 1
    assert len(finishes) == 1
    assert starts[0] < finishes[0]


def test_inside_only_change_is_not_an_entry(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    assert not any(detector.update(robot(maze, 150, 105), rois)[2] for _ in range(15))


def test_robot_remaining_outside_never_finishes(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    assert not any(detector.update(robot(maze, x, 105), rois)[2] for x in (115, 120, 118, 119) * 4)


def test_leaving_goal_is_not_entering_goal(maze, rois):
    detector = MouseDetector()
    prime(detector, robot(maze, 150, 105), rois)
    for x in (145, 140, 132, 120, 115, 105, 95, 85):
        assert not detector.update(robot(maze, x, 105), rois)[2]


def test_crossing_start_in_reverse_does_not_start(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    for y in (150, 160, 165, 175, 185, 195, 205):
        assert not detector.update(robot(maze, 55, y), rois)[0]


def test_finish_needs_consecutive_frames_and_does_not_accumulate_flicker(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    detector.update(robot(maze, 120, 105), rois)
    for _ in range(4):
        assert not detector.update(robot(maze, 145, 105), rois)[2]
        assert not detector.update(maze, rois)[2]
    assert detector.goal_zone.hit_streak == 0


def test_goal_approach_before_start_is_not_reused(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    detector.update(robot(maze, 120, 105), rois, state=TimerState.ARMED)
    assert not any(
        detector.update(robot(maze, x, 105), rois, state=TimerState.RUNNING)[2]
        for x in (145, 146, 147, 150, 150)
    )


def test_warmup_and_reset_do_not_keep_stale_hits(maze, rois):
    detector = MouseDetector()
    for _ in range(round(detector.warmup_ms * 30 / 1000)):
        assert not detector.update(robot(maze, 150, 105), rois)[2]
        assert detector.goal_zone.hit_streak == 0
    detector.reset()
    prime(detector, maze, rois)
    detector.update(robot(maze, 120, 105), rois)
    detector.clear_gates()
    for _ in range(5):
        assert not detector.update(robot(maze, 150, 105), rois)[2]


@pytest.mark.parametrize("brightness", [0, 12, -12])
def test_camera_jitter_and_common_brightness_changes_do_not_trigger(maze, rois, brightness):
    detector = MouseDetector()
    prime(detector, maze, rois)
    rng = np.random.default_rng(5)
    for _ in range(45):
        dx, dy = rng.integers(-3, 4, 2)
        frame = cv2.warpAffine(maze, np.float32([[1, 0, dx], [0, 1, dy]]), (320, 240),
                               borderMode=cv2.BORDER_REFLECT)
        frame = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
        start, _, finish = detector.update(frame, rois)
        assert not start and not finish


def test_large_camera_move_blocks_detection_then_recovers(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    moved = cv2.warpAffine(maze, np.float32([[1, 0, 35], [0, 1, 0]]), (320, 240),
                           borderMode=cv2.BORDER_REFLECT)
    start, _, finish = detector.update(moved, rois)
    assert not start and not finish and not detector.ready
    assert not detector.motion_ok
    assert detector.goal_zone.approach_at_s is None
    assert detector.update(maze, rois)[0::2] == (False, False)
    assert detector.ready


def test_low_texture_and_roi_at_frame_edge_fail_safely(rois):
    detector = MouseDetector()
    blank = np.zeros((240, 320, 3), np.uint8)
    for _ in range(30):
        assert detector.update(blank, rois)[0::2] == (False, False)
    assert not detector.ready
    assert "background" in detector.message
    edge_rois = RoiBundle((10, 238, 50, 2), (130, 80, 50, 50))
    assert detector.update(blank, edge_rois)[0::2] == (False, False)
    assert "outside" in detector.message


@pytest.mark.parametrize("goal", [(884, 360, 124, 115), (889, 369, 114, 96)])
@pytest.mark.parametrize("stride", [1, 2, 3])
def test_real_recording_has_ordered_crossings_after_calibrating_rois(goal, stride):
    cap = cv2.VideoCapture(str(resource_root() / "samples" / "mock_run_real.mp4"))
    detector = MouseDetector()
    rois = RoiBundle((360, 850, 50, 16), goal)
    starts, finishes = [], []
    state = TimerState.ARMED
    index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % stride:
                index += 1
                continue
            start, _, finish = detector.update(frame, rois, state=state, timestamp_s=index / 30)
            if start:
                starts.append(index)
                state = TimerState.RUNNING
            if finish:
                finishes.append(index)
                state = TimerState.FINISHED
            index += 1
    finally:
        cap.release()
    assert len(starts) == len(finishes) == 1
    assert (finishes[0] - starts[0]) / 30 > 1
    # The finish must occur in this pass, while the robot is in Goal, rather
    # than relying on another loop or on a previously latched approach.
    assert finishes[0] / 30 < 12


@pytest.mark.parametrize("sample_ms", [10, 33, 100])
def test_goal_hold_uses_elapsed_time_and_reports_first_entry_timestamp(maze, rois, sample_ms):
    detector = MouseDetector(goal_hold_ms=80)
    prime(detector, maze, rois)
    detector.update(robot(maze, 120, 105), rois, state=TimerState.RUNNING)
    entry = detector.clock + sample_ms / 1000
    assert not detector.update(robot(maze, 145, 105), rois, state=TimerState.RUNNING, timestamp_s=entry)[2]
    for index in range(1, 20):
        timestamp = entry + index * sample_ms / 1000
        _, _, finish = detector.update(
            robot(maze, 145, 105), rois, state=TimerState.RUNNING, timestamp_s=timestamp,
        )
        if finish:
            assert timestamp - entry >= 0.080 - 1e-9
            assert timestamp - entry < 0.080 + sample_ms / 1000 + 1e-9
            assert detector.goal_event_ts == pytest.approx(entry)
            break
    else:
        pytest.fail("No confirmed goal entry")


def test_a_long_sampling_gap_cannot_complete_a_partial_goal_confirmation(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    detector.update(robot(maze, 120, 105), rois, state=TimerState.RUNNING)
    detector.update(robot(maze, 145, 105), rois, state=TimerState.RUNNING)
    assert not detector.update(
        robot(maze, 145, 105), rois, state=TimerState.RUNNING, timestamp_s=detector.clock + 0.4,
    )[2]
    assert "gap" in detector.message
    for _ in range(5):
        assert not detector.update(robot(maze, 145, 105), rois, state=TimerState.RUNNING)[2]


def test_manually_drawn_start_bands_and_goal_ring_are_used(maze, rois):
    custom = RoiBundle(
        rois.start_line, rois.goal_area,
        start_before=(20, 185, 65, 35), start_after=(20, 130, 65, 35),
        goal_outer=(110, 60, 90, 90),
    )
    detector = MouseDetector()
    prime(detector, maze, custom)
    assert detector.start_zone.outside == custom.start_before
    assert detector.start_zone.inner == custom.start_after
    assert detector.goal_zone.outside == custom.goal_outer
    events = [
        detector.update(robot(maze, 55, y), custom, state=TimerState.ARMED)[0]
        for y in (210, 205, 200, 190, 180, 170, 160, 150)
    ]
    assert sum(events) == 1


def test_real_robot_is_still_detected_with_camera_jitter(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    rng = np.random.default_rng(5)
    starts, goals = 0, 0
    state = TimerState.ARMED
    path = [(55, y) for y in (201, 195, 190, 180, 175, 160)]
    path += [(x, 105) for x in (115, 120, 121, 132, 140, 145, 146, 147, 148)]
    for x, y in path:
        dx, dy = rng.integers(-3, 4, 2)
        frame = cv2.warpAffine(
            robot(maze, x, y), np.float32([[1, 0, dx], [0, 1, dy]]), (320, 240),
            borderMode=cv2.BORDER_REFLECT,
        )
        start, _, goal = detector.update(frame, rois, state=state)
        if start:
            starts += 1
            state = TimerState.RUNNING
        goals += int(goal)
    assert starts == goals == 1


def test_robot_parked_in_start_a_can_cross_while_both_zones_change(maze, rois):
    detector = MouseDetector()
    prime(detector, robot(maze, 55, 201), rois)
    events = [
        detector.update(robot(maze, 55, y), rois, state=TimerState.ARMED)[0]
        for y in (198, 195, 190, 180, 175, 170, 165, 160, 155, 150)
    ]
    assert sum(events) == 1


def test_small_camera_rotation_does_not_create_crossings(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    stable = 0
    for angle in (-0.5, 0.3, 0.5, -0.2, 0.0) * 6:
        matrix = cv2.getRotationMatrix2D((160, 120), angle, 1.0)
        frame = cv2.warpAffine(maze, matrix, (320, 240), borderMode=cv2.BORDER_REFLECT)
        start, _, goal = detector.update(frame, rois)
        assert not start and not goal
        stable += int(detector.ready)
    assert stable >= 24


def test_simultaneous_changes_in_both_zones_are_not_a_crossing(maze, rois):
    detector = MouseDetector()
    prime(detector, maze, rois)
    flashed = maze.copy()
    for zone in (detector.start_zone, detector.goal_zone):
        for x, y, w, h in (zone.inner, zone.outside):
            flashed[y:y + h, x:x + w] = 245
    for frame in [flashed] * 5 + [maze] * 5:
        start, _, goal = detector.update(frame, rois)
        assert not start and not goal


def test_invalid_manual_zone_relationships_block_detection(maze, rois):
    detector = MouseDetector()
    overlapping = RoiBundle(
        rois.start_line, rois.goal_area,
        start_before=(10, 100, 80, 50), start_after=(20, 110, 80, 50),
    )
    assert detector.update(maze, overlapping)[0::2] == (False, False)
    assert not detector.ready and "Separate Start" in detector.message
    bad_outer = RoiBundle(rois.start_line, rois.goal_area, goal_outer=(125, 75, 50, 50))
    assert detector.update(maze, bad_outer)[0::2] == (False, False)
    assert not detector.ready and "contain" in detector.message
