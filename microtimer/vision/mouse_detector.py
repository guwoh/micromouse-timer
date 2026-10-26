from __future__ import annotations

import time

import cv2
import numpy as np

from core.models import RoiBundle, TimerState
from vision.comparison_zone import ComparisonZone, clip_rect, comparison_rect
from vision.motion_compensator import MotionCompensator


class MouseDetector:
    def __init__(self, diff_threshold=30, goal_ratio_threshold=0.02,
                 start_ratio_threshold=0.05, warmup_ms=500, goal_hold_ms=80,
                 outside_ratio_threshold=0.01, transition_timeout_ms=1500,
                 max_camera_shift_px=24.0, sample_interval_ms=30):
        self.diff_threshold = diff_threshold
        self.goal_ratio_threshold = goal_ratio_threshold
        self.start_ratio_threshold = start_ratio_threshold
        self.warmup_ms = warmup_ms
        self.goal_hold_ms = goal_hold_ms
        self.outside_ratio_threshold = outside_ratio_threshold
        self.transition_timeout_ms = transition_timeout_ms
        self.max_sample_gap_s = max(250, sample_interval_ms * 3) / 1000
        self.motion = MotionCompensator(max_camera_shift_px)
        self.reset()

    def _zone(self, inner, outside, threshold, hold_ms, frame_size):
        return ComparisonZone(
            inner, outside, threshold, hold_ms, self.diff_threshold,
            self.outside_ratio_threshold, self.transition_timeout_ms, frame_size,
        )

    def reset(self):
        self.motion.reset()
        self._roi_key = None
        self.start_zone = self.goal_zone = None
        self._first_valid_ts = self._last_ts = None
        self.ready = self.motion_ok = False
        self.message = "Calibrating"
        self.shift = (0.0, 0.0)
        self.transform = np.float32([[1, 0, 0], [0, 1, 0]])
        self.start_event_ts = self.goal_event_ts = None
        self.sample_dt_ms = 0.0
        self._last_state = None

    def update(self, frame, rois: RoiBundle, state: TimerState | None = None, timestamp_s=None):
        height, width = frame.shape[:2]
        fields = (rois.start_line, rois.goal_area, rois.start_before, rois.start_after, rois.goal_outer)
        key = (width, height, *(tuple(rect) if rect is not None else None for rect in fields))
        if key != self._roi_key:
            self.reset()
            self._roi_key = key
            size = (width, height)
            line, goal = clip_rect(rois.start_line, size), clip_rect(rois.goal_area, size)
            before = clip_rect(rois.start_before, size) if rois.start_before else comparison_rect(line, size, goal)
            after = clip_rect(rois.start_after, size) if rois.start_after else comparison_rect(line, size, goal, after=True)
            outer = clip_rect(rois.goal_outer, size) if rois.goal_outer else comparison_rect(goal, size)
            self.start_zone = self._zone(after, before, self.start_ratio_threshold, 0, size)
            self.goal_zone = self._zone(goal, outer, self.goal_ratio_threshold, self.goal_hold_ms, size)

        if not self.start_zone.valid or not self.goal_zone.valid:
            self.ready = False
            self.message = "Leave space outside Start and Goal"
            return False, 0.0, False
        ax, ay, aw, ah = self.start_zone.outside
        bx, by, bw, bh = self.start_zone.inner
        if max(ax, bx) < min(ax + aw, bx + bw) and max(ay, by) < min(ay + ah, by + bh):
            self.ready = False
            self.message = "Separate Start A and Start B"
            return False, 0.0, False
        ix, iy, iw, ih = self.goal_zone.inner
        ox, oy, ow, oh = self.goal_zone.outside
        if not (ox <= ix and oy <= iy and ox + ow >= ix + iw and oy + oh >= iy + ih):
            self.ready = False
            self.message = "Goal outer must contain Goal inner"
            return False, 0.0, False

        timestamp_s = time.perf_counter() if timestamp_s is None else float(timestamp_s)
        if state != self._last_state:
            if state == TimerState.RUNNING:
                self.goal_zone.clear_history()
            elif state == TimerState.ARMED:
                self.start_zone.clear_history()
            self._last_state = state
        self.start_event_ts = self.goal_event_ts = None
        gap = False
        if self._last_ts is not None:
            self.sample_dt_ms = max(0.0, (timestamp_s - self._last_ts) * 1000)
            gap = timestamp_s <= self._last_ts or timestamp_s - self._last_ts > self.max_sample_gap_s
        self._last_ts = timestamp_s
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        alignment = self.motion.update(gray, [self.start_zone.patch, self.goal_zone.patch])
        self.transform, self.shift = alignment.transform, alignment.shift
        self.motion_ok = alignment.valid
        if not alignment.valid:
            self.ready = False
            self.message = alignment.message
            self.clear_gates()
            return False, 0.0, False
        if self._first_valid_ts is None:
            self._first_valid_ts = timestamp_s
        calibrated_ms = (timestamp_s - self._first_valid_ts) * 1000
        warming_up = calibrated_ms < self.warmup_ms
        if gap:
            self.clear_gates()
        self.ready = not warming_up and not gap
        self.message = (
            f"Calibrating {min(self.warmup_ms, round(calibrated_ms))}/{self.warmup_ms} ms"
            if warming_up else "Sampling gap — waiting for approach" if gap else "Ready · Start A → B / Goal outside → inside"
        )
        start = self.start_zone.update(
            alignment.gray, timestamp_s,
            active=state in (None, TimerState.ARMED), warming_up=warming_up or gap,
        )
        goal = self.goal_zone.update(
            alignment.gray, timestamp_s,
            active=state in (None, TimerState.RUNNING), warming_up=warming_up or gap,
        )
        if start:
            self.start_event_ts = self.start_zone.event_timestamp_s
            self.goal_zone.clear_history()
            goal = False
        if goal:
            self.goal_event_ts = self.goal_zone.event_timestamp_s
        return start, self.goal_zone.inside_ratio, goal

    def clear_gates(self):
        for zone in (self.start_zone, self.goal_zone):
            if zone is not None:
                zone.clear_history()
