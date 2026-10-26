from __future__ import annotations

import threading
import time
from pathlib import Path

import cv2

from vision.camera.base import CameraSource


class VideoFileSource(CameraSource):
    """Decode and replay an actual video at its recorded frame rate."""

    def __init__(self, path: str | Path, loop: bool = True):
        self.path = Path(path).expanduser()
        self.loop = loop
        self.cap: cv2.VideoCapture | None = None
        self.fps = 30.0
        self._next_frame_s = 0.0
        self._lock = threading.RLock()
        self._closed = threading.Event()

    def open(self) -> bool:
        self.release()
        with self._lock:
            if not self.path.is_file():
                return False
            cap = cv2.VideoCapture(str(self.path))
            ok, frame = cap.read()
            if not ok or frame is None:
                cap.release()
                return False
            self.cap = cap
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.fps = fps if 0 < fps <= 240 else 30.0
            self._closed.clear()
            self.rewind()
            return True

    def rewind(self) -> None:
        with self._lock:
            if self.cap is not None:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._next_frame_s = time.perf_counter()

    def read(self):
        with self._lock:
            if self.cap is None:
                return False, None
            deadline = self._next_frame_s
        if self._closed.wait(max(0.0, deadline - time.perf_counter())):
            return False, None
        with self._lock:
            if self.cap is None:
                return False, None
            scheduled = self._next_frame_s
            ok, frame = self.cap.read()
            if not ok and self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
            self._next_frame_s = max(scheduled + 1.0 / self.fps, time.perf_counter())
            return (True, frame) if ok else (False, None)

    def release(self) -> None:
        self._closed.set()
        with self._lock:
            if self.cap is not None:
                self.cap.release()
                self.cap = None

    def is_opened(self) -> bool:
        with self._lock:
            return self.cap is not None and self.cap.isOpened()
