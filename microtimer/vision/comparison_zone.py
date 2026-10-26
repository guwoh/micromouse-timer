from __future__ import annotations

import cv2
import numpy as np


def clip_rect(rect, frame_size):
    x, y, w, h = (int(value) for value in rect)
    fw, fh = frame_size
    left, top = max(0, min(x, fw)), max(0, min(y, fh))
    right, bottom = max(left, min(x + w, fw)), max(top, min(y + h, fh))
    return left, top, right - left, bottom - top


def project_rect(rect, transform, frame_size):
    x, y, w, h = rect
    corners = np.float32([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])
    points = cv2.transform(corners[None], transform)[0]
    left, top = np.floor(points.min(axis=0)).astype(int)
    right, bottom = np.ceil(points.max(axis=0)).astype(int)
    return clip_rect((left, top, right - left, bottom - top), frame_size)


def comparison_rect(inner, frame_size, goal=None, after=False):
    x, y, w, h = inner
    margin = max(12, round(min(w, h) * 0.35))
    if goal is None:
        return clip_rect((x - margin, y - margin, w + margin * 2, h + margin * 2), frame_size)
    gx, gy, gw, gh = goal
    depth = max(16, min(120, round(max(w, h) * 1.5)))
    if w >= h:
        below = (gy + gh / 2 < y + h / 2) != after
        before_y = y + h if below else y - depth
        return clip_rect((x - 6, before_y, w + 12, depth), frame_size)
    left = (gx + gw / 2 > x + w / 2) != after
    before_x = x - depth if left else x + w
    return clip_rect((before_x, y - 6, depth, h + 12), frame_size)


class ComparisonZone:
    """Confirm ordered movement between two zones using capture timestamps."""

    def __init__(self, inner, outside, threshold, hold_ms, diff_threshold=30,
                 outside_threshold=0.01, transition_timeout_ms=1500, frame_size=None):
        self.inner, self.outside = inner, outside
        ix, iy, iw, ih = inner
        ox, oy, ow, oh = outside
        x, y = min(ix, ox), min(iy, oy)
        w, h = max(ix + iw, ox + ow) - x, max(iy + ih, oy + oh) - y
        # Tracking needs image context beyond the measurement rectangle. Without
        # it, a fast robot is cropped at the OUT border and forward/backward LK
        # cannot match it when the next sample is already partly inside IN.
        # Only the masks below contribute to the measured change ratios.
        if frame_size is not None:
            padding = max(24, min(80, max(iw, ih) // 2))
            x, y, w, h = clip_rect((x - padding, y - padding, w + padding * 2, h + padding * 2), frame_size)
        self.patch = (x, y, w, h)
        self.inner_mask = np.zeros((h, w), np.uint8)
        self.outer_mask = np.zeros((h, w), np.uint8)
        self.inner_mask[iy - y:iy - y + ih, ix - x:ix - x + iw] = 1
        self.outer_mask[oy - y:oy - y + oh, ox - x:ox - x + ow] = 1
        self.outer_mask[self.inner_mask != 0] = 0
        self.valid = bool(np.any(self.inner_mask) and np.any(self.outer_mask))
        self.threshold = threshold
        self.hold_s = hold_ms / 1000.0
        self.outside_threshold = outside_threshold
        self.transition_timeout_s = transition_timeout_ms / 1000.0
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=diff_threshold, detectShadows=False,
        )
        self.inside_ratio = self.outside_ratio = 0.0
        self.previous_patch = None
        self.previous_timestamp = None
        self.clear_gate()

    def clear_gate(self):
        self.approach_at_s = None
        self.inside_since_s = None
        self.event_timestamp_s = None
        self.hit_streak = 0
        self.latched = False
        self.status = "Waiting for OUT -> IN"

    def clear_history(self):
        self.clear_gate()
        self.previous_patch = None
        self.previous_timestamp = None
        self.inside_ratio = self.outside_ratio = 0.0

    def _incoming_flow(self, previous, current):
        points = cv2.goodFeaturesToTrack(
            previous, maxCorners=80, qualityLevel=0.01, minDistance=2,
            mask=self.outer_mask * 255,
        )
        if points is None or len(points) < 2:
            return False
        tracked, status, error = cv2.calcOpticalFlowPyrLK(
            previous, current, points, None, winSize=(21, 21), maxLevel=3,
        )
        if tracked is None or status is None:
            return False
        start, end = points.reshape(-1, 2), tracked.reshape(-1, 2)
        good = (status.ravel() != 0) & np.isfinite(end).all(axis=1)
        if error is not None:
            good &= error.ravel() < 35
        good &= np.linalg.norm(end - start, axis=1) >= 3
        hits = []
        for index in np.flatnonzero(good):
            px, py = np.rint(end[index]).astype(int)
            if 0 <= py < current.shape[0] and 0 <= px < current.shape[1] and self.inner_mask[py, px]:
                hits.append(index)
        if len(hits) < 2:
            return False
        back, back_status, _ = cv2.calcOpticalFlowPyrLK(
            current, previous, tracked[hits], None, winSize=(21, 21), maxLevel=3,
        )
        if back is None or back_status is None:
            return False
        consistent = (back_status.ravel() != 0) & (np.linalg.norm(back.reshape(-1, 2) - start[hits], axis=1) < 1.5)
        hits = list(np.array(hits)[consistent])
        if len(hits) < 2:
            return False
        # The moving points must agree in direction, not be unrelated noisy matches.
        vectors = end[hits] - start[hits]
        median = np.median(vectors, axis=0)
        return np.count_nonzero(np.linalg.norm(vectors - median, axis=1) < max(3, np.linalg.norm(median) * 0.5)) >= 2

    def update(self, gray, timestamp_s, active=True, warming_up=False):
        x, y, w, h = self.patch
        if w <= 0 or h <= 0 or not self.valid:
            self.clear_gate()
            self.status = "Invalid comparison regions"
            return False
        patch = cv2.GaussianBlur(gray[y:y + h, x:x + w], (3, 3), 0)
        previous, previous_timestamp = self.previous_patch, self.previous_timestamp
        self.previous_patch, self.previous_timestamp = patch.copy(), timestamp_s
        mask = self.subtractor.apply(patch, learningRate=0.1 if warming_up else 0.002)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        # Drop tiny speckles and long, thin wall edges left by imperfect alignment.
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        clean = np.zeros_like(mask)
        for label in range(1, count):
            bx, by, bw, bh, area = stats[label]
            if area >= 8 and min(bw, bh) >= 2 and max(bw, bh) / min(bw, bh) <= 12:
                clean[labels == label] = 1
        self.inside_ratio = float(np.sum(clean * self.inner_mask)) / max(1, int(np.sum(self.inner_mask)))
        self.outside_ratio = float(np.sum(clean * self.outer_mask)) / max(1, int(np.sum(self.outer_mask)))
        if warming_up or not active:
            self.clear_gate()
            self.status = "Calibrating" if warming_up else "Inactive"
            return False
        # A robot may span both zones, or leave a foreground ghost where it
        # was initially parked. Direction/order is stronger evidence than
        # demanding the inside density exceed the outside density.
        inside_hit = self.inside_ratio >= self.threshold
        outside_hit = self.outside_ratio >= self.outside_threshold
        if self.outside_ratio > 0.55 and self.inside_ratio > 0.55:
            self.clear_gate()
            self.status = "Shared change rejected"
            return False
        # Simultaneous inside/outside changes alone never create an approach.
        if outside_hit and self.inside_ratio < self.threshold:
            self.approach_at_s = timestamp_s
        recent = self.approach_at_s is not None and 0 < timestamp_s - self.approach_at_s <= self.transition_timeout_s
        # A fast robot can cross both zones between two camera samples.
        if inside_hit and not recent and previous is not None:
            if 0 < timestamp_s - previous_timestamp <= self.transition_timeout_s and self._incoming_flow(previous, patch):
                self.approach_at_s = previous_timestamp
                recent = True
        if inside_hit and recent:
            self.hit_streak += 1
            if self.inside_since_s is None:
                self.inside_since_s = timestamp_s
        else:
            self.hit_streak = 0
            self.inside_since_s = None
        if self.latched:
            self.status = "Entry confirmed"
        elif self.inside_since_s is not None:
            elapsed_ms = max(0, (timestamp_s - self.inside_since_s) * 1000)
            self.status = f"Confirming entry: {elapsed_ms:.0f}/{self.hold_s * 1000:g} ms"
        elif inside_hit:
            self.status = "IN changed; OUT -> IN not confirmed"
        elif recent:
            self.status = "Approach seen; waiting for IN"
        else:
            self.status = "Waiting for OUT -> IN"
        if self.inside_since_s is not None and timestamp_s - self.inside_since_s + 1e-9 >= self.hold_s and not self.latched:
            self.latched = True
            self.event_timestamp_s = self.inside_since_s
            self.status = "Entry confirmed"
            return True
        return False
