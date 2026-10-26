from __future__ import annotations

import time

import cv2
import numpy as np

from vision.camera.base import CameraSource


class IpCameraSource(CameraSource):
    def __init__(self, url: str, reconnect_ms: int = 1500):
        self.url = url
        self.reconnect_ms = reconnect_ms
        self.cap: cv2.VideoCapture | None = None
        self._last_try_s = 0.0
        self._is_local_file = False
        self._frame_delay_s = 0.033
        self._last_read_s = 0.0

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.url)
        if self.cap.isOpened():
            url_str = str(self.url).lower()
            self._is_local_file = not url_str.startswith(('http://', 'https://', 'rtsp://', 'rtmp://', 'tcp://', 'udp://'))
            if self._is_local_file:
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                if fps > 0 and fps < 240:
                    self._frame_delay_s = 1.0 / fps
            self._last_read_s = time.perf_counter()
        return self.cap is not None and self.cap.isOpened()

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.cap is None or not self.cap.isOpened():
            now = time.perf_counter()
            if (now - self._last_try_s) * 1000.0 >= self.reconnect_ms:
                self._last_try_s = now
                self.open()
            return False, None

        if self._is_local_file:
            now = time.perf_counter()
            elapsed = now - self._last_read_s
            if elapsed < self._frame_delay_s:
                time.sleep(self._frame_delay_s - elapsed)
            self._last_read_s = time.perf_counter()

        ok, frame = self.cap.read()
        if not ok:
            return False, None
        return True, frame

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
