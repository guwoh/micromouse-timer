from __future__ import annotations

import threading
import time

from core.models import FramePacket
from core.timing import now_s
from pipeline.shared_state import SharedFrameState
from vision.camera.base import CameraSource


class CaptureWorker:
    def __init__(self, camera: CameraSource, shared_state: SharedFrameState):
        self.camera = camera
        self.shared_state = shared_state
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.frame_index = 0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

    def _run(self) -> None:
        if not self.camera.is_opened() and not self.camera.open():
            return
        while not self.stop_event.is_set():
            ok, frame = self.camera.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue
            packet = FramePacket(frame=frame, capture_ts=now_s(), frame_index=self.frame_index)
            self.frame_index += 1
            with self.shared_state.lock:
                self.shared_state.latest = packet
