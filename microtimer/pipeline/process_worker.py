from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import numpy as np

from core.fsm import TimerFSM
from core.models import DetectionResult, RoiBundle
from core.timing import elapsed_ms, now_s
from pipeline.shared_state import SharedFrameState
from vision.mouse_detector import MouseDetector
from vision.roi_builder import build_rois
from vision.comparison_zone import project_rect


@dataclass
class ProcessOutput:
    result: DetectionResult
    overlay_frame: np.ndarray | None


class ProcessWorker:
    def __init__(self, shared_state: SharedFrameState, config: dict, timer_fsm: TimerFSM):
        self.shared_state = shared_state
        self.config = config
        self.timer_fsm = timer_fsm
        proc = config.get("processing", {})
        self.sample_interval_ms = float(proc.get("sample_interval_ms", 30))
        self._last_sample_ts = None
        self.rois: RoiBundle | None = None
        self.detector = MouseDetector(
            diff_threshold=int(proc.get("diff_threshold", 30)),
            start_ratio_threshold=float(proc.get("start_ratio_threshold", 0.05)),
            goal_ratio_threshold=float(proc.get("goal_ratio_threshold", 0.02)),
            goal_hold_ms=float(proc.get("goal_hold_ms", 80)),
            warmup_ms=float(proc.get("warmup_ms", 500)),
            outside_ratio_threshold=float(proc.get("outside_ratio_threshold", 0.01)),
            transition_timeout_ms=float(proc.get("transition_timeout_ms", 1500)),
            max_camera_shift_px=float(proc.get("max_camera_shift_px", 24.0)),
            sample_interval_ms=self.sample_interval_ms,
        )
        self.detector_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.latest_output = ProcessOutput(result=DetectionResult(), overlay_frame=None)
        self._last_state = self.timer_fsm.snapshot.state
        self._last_health = None
        self._last_frame_index = -1
        self._frame_size: tuple[int, int] | None = None
        self._rois_user_set = False

    def default_rois(self, frame_size: tuple[int, int]) -> RoiBundle:
        proc = self.config.get("processing", {})
        return build_rois(
            frame_size,
            start_corner=proc.get("start_corner", "top_left"),
            start_line_thickness_pct=float(proc.get("start_line_thickness_pct", 0.03)),
            goal_size_pct=float(proc.get("goal_size_pct", 0.16)),
            inset_pct=float(proc.get("map_inset_pct", 0.0)),
        )

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def reset_detector(self) -> None:
        with self.detector_lock:
            self.detector.clear_gates()

    def set_roi(self, mode, rect):
        with self.detector_lock:
            if self.rois is None or self._frame_size is None:
                return
            transform = self.detector.transform
            mapping = {"start": "start_line", "goal": "goal_area", "start_before": "start_before",
                       "start_after": "start_after", "goal_outer": "goal_outer"}
            if mode not in mapping:
                return
            values = {}
            for field in ("start_line", "goal_area", "start_before", "start_after", "goal_outer"):
                value = getattr(self.rois, field)
                values[field] = project_rect(value, transform, self._frame_size) if value is not None else None
            values[mapping[mode]] = rect
            if mode == "start":
                values["start_before"] = values["start_after"] = None
            self.rois = RoiBundle(**values)
            self._rois_user_set = True
            self.detector.reset()
            logging.info("roi_updated mode=%s rect=%s rois=%s", mode, rect, self.rois)

    def configure_timing(self, sample_ms, goal_hold_ms, transition_ms):
        with self.detector_lock:
            proc = self.config.setdefault("processing", {})
            proc.update(sample_interval_ms=sample_ms, goal_hold_ms=goal_hold_ms, transition_timeout_ms=transition_ms)
            self.sample_interval_ms = sample_ms
            self.detector.goal_hold_ms = goal_hold_ms
            self.detector.transition_timeout_ms = transition_ms
            self.detector.max_sample_gap_s = max(250, sample_ms * 3) / 1000
            for zone in (self.detector.start_zone, self.detector.goal_zone):
                if zone is not None:
                    zone.transition_timeout_s = transition_ms / 1000
            if self.detector.goal_zone is not None:
                self.detector.goal_zone.hold_s = goal_hold_ms / 1000
            self.detector.clear_gates()

    def reset_rois(self):
        with self.detector_lock:
            self.rois = self.default_rois(self._frame_size) if self._frame_size else None
            self._rois_user_set = False
            self.detector.reset()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            with self.shared_state.lock:
                packet = self.shared_state.latest
            if packet is None:
                time.sleep(0.005)
                continue
            if packet.frame_index == self._last_frame_index:
                time.sleep(0.002)
                continue
            self._last_frame_index = packet.frame_index
            if self._last_sample_ts is not None and 0 <= packet.capture_ts - self._last_sample_ts < self.sample_interval_ms / 1000:
                continue
            self._last_sample_ts = packet.capture_ts

            start_s = now_s()
            frame = packet.frame
            h, w = frame.shape[:2]
            frame_size = (w, h)
            with self.detector_lock:
                if self.rois is None or frame_size != self._frame_size:
                    self.rois = self.default_rois(frame_size)
                    self._rois_user_set = False
                self._frame_size = frame_size
                result = DetectionResult(rois=self.rois)
                start_crossed, goal_ratio, in_goal = self.detector.update(
                    frame, self.rois, state=self.timer_fsm.snapshot.state, timestamp_s=packet.capture_ts,
                )
                result.vision_status = self.detector.message
                result.vision_ready = self.detector.ready
                result.camera_transform = self.detector.transform.copy()
                result.sample_dt_ms = self.detector.sample_dt_ms
                health = (self.detector.ready, self.detector.motion_ok,
                          self.detector.message if not self.detector.motion_ok else "")
                if health != self._last_health:
                    logging.info("vision_health ready=%s aligned=%s reason=%s",
                                 self.detector.ready, self.detector.motion_ok, self.detector.message)
                    self._last_health = health
                if self.detector.start_zone is not None:
                    result.start_outside_roi = self.detector.start_zone.outside
                    result.start_inside_roi = self.detector.start_zone.inner
                    result.goal_outside_roi = self.detector.goal_zone.outside
                    result.start_inside_ratio = self.detector.start_zone.inside_ratio
                    result.start_outside_ratio = self.detector.start_zone.outside_ratio
                    result.goal_outside_ratio = self.detector.goal_zone.outside_ratio
                    result.goal_status = self.detector.goal_zone.status if self.detector.ready else self.detector.message
                if start_crossed:
                    self.timer_fsm.on_start_trigger(self.detector.start_event_ts)
                if in_goal:
                    self.timer_fsm.on_finish_trigger(self.detector.goal_event_ts)
            result.start_crossed = start_crossed
            result.goal_changed_ratio = goal_ratio
            result.mouse_in_goal = in_goal

            snapshot = self.timer_fsm.tick()
            if snapshot.state != self._last_state:
                logging.info(
                    "state_transition from=%s to=%s frame=%s goal_ratio=%.4f sample_ms=%.2f "
                    "start_A=%.4f start_B=%.4f goal_out=%.4f capture_ts=%.6f",
                    self._last_state.value,
                    snapshot.state.value,
                    packet.frame_index,
                    result.goal_changed_ratio,
                    result.sample_dt_ms,
                    result.start_outside_ratio,
                    result.start_inside_ratio,
                    result.goal_outside_ratio,
                    packet.capture_ts,
                )
                if snapshot.state.value == "FINISHED":
                    logging.info("run_finished elapsed_ms=%.3f", snapshot.elapsed_s * 1000.0)
                self._last_state = snapshot.state

            end_s = now_s()
            result.latency_ms = elapsed_ms(start_s, end_s)
            self.latest_output = ProcessOutput(result=result, overlay_frame=frame)
