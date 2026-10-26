from __future__ import annotations

import cv2
import numpy as np

from core.models import DetectionResult, TimerState


def draw_overlay(frame: np.ndarray, result: DetectionResult, state: TimerState, elapsed_s: float) -> np.ndarray:
    out = frame.copy()
    transform = result.camera_transform

    def outline(rect, color, thickness, label=""):
        if rect is None:
            return
        x, y, w, h = rect
        points = np.float32([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])
        if transform is not None:
            points = cv2.transform(points[None], transform)[0]
        cv2.polylines(out, [np.rint(points).astype(np.int32)], True, color, thickness)
        if label:
            tx, ty = np.rint(points[0]).astype(int)
            cv2.putText(out, label, (max(2, tx), max(14, ty - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    if result.rois:
        outline(result.start_outside_roi, (230, 170, 80), 1, "A")
        outline(result.start_inside_roi, (120, 220, 120), 1, "B")
        outline(result.goal_outside_roi, (230, 170, 80), 1, "OUT")
        outline(result.rois.start_line, (255, 200, 0), 2)
        outline(result.rois.goal_area, (0, 255, 255), 2, "IN")

    cv2.putText(out, f"State: {state.value}", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(out, f"Elapsed: {elapsed_s:.3f}s", (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(out, f"Goal in/out: {result.goal_changed_ratio:.3f}/{result.goal_outside_ratio:.3f}", (12, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(out, f"Goal: {result.goal_status}", (12, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return out
