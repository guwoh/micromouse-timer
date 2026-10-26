from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Alignment:
    gray: np.ndarray
    transform: np.ndarray
    valid: bool
    message: str
    shift: tuple[float, float] = (0.0, 0.0)


class MotionCompensator:
    """Align analysis frames to a fixed reference using static background corners."""

    def __init__(self, max_shift_px: float = 24.0):
        self.max_shift_px = max_shift_px
        self.reset()

    def reset(self):
        self.reference = None
        self.small_reference = None
        self.points = None
        self.background_mask = None
        self.scale = None

    def update(self, gray: np.ndarray, excluded: list[tuple[int, int, int, int]]) -> Alignment:
        identity = np.float32([[1, 0, 0], [0, 1, 0]])
        height, width = gray.shape
        small_w = min(720, width)
        small_h = max(1, round(height * small_w / width))
        small = cv2.resize(gray, (small_w, small_h), interpolation=cv2.INTER_AREA)
        if self.reference is None or self.reference.shape != gray.shape:
            self.reference = gray.copy()
            self.small_reference = small
            self.window = cv2.createHanningWindow((small_w, small_h), cv2.CV_32F)
            self.scale = np.array([small_w / width, small_h / height], dtype=np.float64)
            mask = np.full(gray.shape, 255, np.uint8)
            margin = max(2, round(min(width, height) * 0.03))
            mask[:margin] = mask[-margin:] = 0
            mask[:, :margin] = mask[:, -margin:] = 0
            for x, y, w, h in excluded:
                mask[max(0, y):min(height, y + h), max(0, x):min(width, x + w)] = 0
            self.background_mask = mask[::6, ::6] != 0
            small_mask = cv2.resize(mask, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
            self.points = cv2.goodFeaturesToTrack(
                small, maxCorners=240, qualityLevel=0.015, minDistance=8,
                mask=small_mask, blockSize=7,
            )
            valid = self.points is not None and len(self.points) >= 8
            return Alignment(gray, identity, valid, "Calibrating" if valid else "Need visible background details")

        if self.points is None or len(self.points) < 8:
            return Alignment(gray, identity, False, "Need visible background details")
        tracked, status, _ = cv2.calcOpticalFlowPyrLK(
            self.small_reference, small, self.points, None,
            winSize=(21, 21), maxLevel=3,
        )
        if tracked is None or status is None:
            return Alignment(gray, identity, False, "Cannot align camera — check view")
        good = (status.ravel() != 0) & np.isfinite(tracked.reshape(-1, 2)).all(axis=1)
        if np.count_nonzero(good) < 8:
            return Alignment(gray, identity, False, "Cannot align camera — check view")
        matrix, inliers = cv2.estimateAffinePartial2D(
            self.points.reshape(-1, 2)[good], tracked.reshape(-1, 2)[good],
            method=cv2.RANSAC, ransacReprojThreshold=1.5, maxIters=1000, confidence=0.99,
        )
        if matrix is None or inliers is None or np.count_nonzero(inliers) < 8 or np.mean(inliers) < 0.6:
            return Alignment(gray, identity, False, "Camera alignment uncertain")
        sx, sy = self.scale
        transform = matrix.copy()
        transform[0, 1] *= sy / sx
        transform[1, 0] *= sx / sy
        transform[0, 2] /= sx
        transform[1, 2] /= sy
        center = np.array([width / 2, height / 2, 1])
        displacement = transform @ center - center[:2]
        # Repeated maze walls can make optical flow slip by one cell. A global
        # frequency-based estimate must agree before measurement is allowed.
        phase_shift, response = cv2.phaseCorrelate(
            self.small_reference.astype(np.float32), small.astype(np.float32), self.window,
        )
        phase_shift = np.array(phase_shift) / self.scale
        if response > 0.25 and np.linalg.norm(phase_shift - displacement) > 3.0:
            return Alignment(gray, transform, False, "Camera alignment uncertain")
        angle = abs(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))
        zoom = np.hypot(matrix[0, 0], matrix[1, 0])
        shift = tuple(float(value) for value in displacement)
        if np.linalg.norm(displacement) > self.max_shift_px or angle > 2 or abs(zoom - 1) > 0.025:
            return Alignment(gray, transform, False, "Camera moved — recheck ROIs", shift)
        aligned = cv2.warpAffine(
            gray, transform, (width, height),
            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT,
        )
        # Normalize common brightness drift using pixels outside the measurement zones.
        samples = aligned[::6, ::6].astype(np.int16)
        reference_samples = self.reference[::6, ::6].astype(np.int16)
        background = self.background_mask
        if not np.any(background):
            return Alignment(gray, transform, False, "Leave background outside ROIs", shift)
        offset = float(np.median((samples - reference_samples)[background]))
        normalized = np.clip(aligned.astype(np.float32) - offset, 0, 255).astype(np.uint8)
        change = np.abs(normalized[::6, ::6].astype(np.int16) - reference_samples)
        if np.mean(change[background] > 28) > 0.22:
            return Alignment(normalized, transform, False, "Scene changed — check camera and lighting", shift)
        return Alignment(normalized, transform, True, "Stable", shift)
