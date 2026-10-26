from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

import numpy as np


class TimerState(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"


@dataclass
class FramePacket:
    frame: np.ndarray
    capture_ts: float
    frame_index: int


@dataclass
class RoiBundle:
    start_line: Tuple[int, int, int, int]
    goal_area: Tuple[int, int, int, int]
    start_before: Optional[Tuple[int, int, int, int]] = None
    start_after: Optional[Tuple[int, int, int, int]] = None
    goal_outer: Optional[Tuple[int, int, int, int]] = None


@dataclass
class DetectionResult:
    rois: Optional[RoiBundle] = None
    start_crossed: bool = False
    goal_changed_ratio: float = 0.0
    mouse_in_goal: bool = False
    latency_ms: float = 0.0
    debug_messages: list[str] = field(default_factory=list)
    start_outside_roi: Optional[Tuple[int, int, int, int]] = None
    goal_outside_roi: Optional[Tuple[int, int, int, int]] = None
    start_inside_ratio: float = 0.0
    start_outside_ratio: float = 0.0
    goal_outside_ratio: float = 0.0
    vision_status: str = "Calibrating"
    vision_ready: bool = False
    camera_transform: Optional[np.ndarray] = None
    start_inside_roi: Optional[Tuple[int, int, int, int]] = None
    goal_status: str = "Waiting for OUT -> IN"
    sample_dt_ms: float = 0.0
