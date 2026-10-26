from __future__ import annotations

import cv2
import numpy as np

from vision.camera.base import CameraSource


class UsbCameraSource(CameraSource):
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720, fps: int = 30):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(self.index, backend)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            ok, _ = cap.read()
            if ok:
                self.cap = cap
                return True
            cap.release()
        return False

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.cap is None:
            return False, None
        ok, frame = self.cap.read()
        return ok, frame

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
