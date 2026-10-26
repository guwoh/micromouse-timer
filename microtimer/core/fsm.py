from __future__ import annotations

from dataclasses import dataclass, replace

import logging
import threading
import time
try:
    import winsound
except ImportError:
    winsound = None

from core.models import TimerState
from core.timing import now_s


def play_beep(freq: int, duration: int, repeats: int = 1) -> None:
    if winsound is not None:
        def _beep():
            for i in range(repeats):
                try:
                    winsound.Beep(freq, duration)
                except RuntimeError:
                    logging.debug("Audible notification unavailable on this machine")
                    return
                if i < repeats - 1:
                    time.sleep(0.05)
        threading.Thread(target=_beep, daemon=True).start()

@dataclass
class TimerSnapshot:
    state: TimerState = TimerState.IDLE
    start_ts: float | None = None
    finish_ts: float | None = None
    elapsed_s: float = 0.0


class TimerFSM:
    def __init__(self, debounce_ms: int = 80, min_run_ms: int = 200):
        self._lock = threading.RLock()
        self.snapshot = TimerSnapshot()
        self.debounce_ms = debounce_ms
        self.min_run_ms = min_run_ms
        self._last_transition_s = 0.0

    def arm(self) -> None:
        with self._lock:
            if self.snapshot.state in (TimerState.IDLE, TimerState.FINISHED):
                self.snapshot = TimerSnapshot(state=TimerState.ARMED)
                self._last_transition_s = now_s()

    def reset(self) -> None:
        with self._lock:
            self.snapshot = TimerSnapshot(state=TimerState.IDLE)
            self._last_transition_s = now_s()

    def on_start_trigger(self, timestamp_s: float | None = None) -> None:
        with self._lock:
            t = now_s() if timestamp_s is None else timestamp_s
            if self.snapshot.state != TimerState.ARMED:
                return
            if (t - self._last_transition_s) * 1000.0 < self.debounce_ms:
                return
            self.snapshot.state = TimerState.RUNNING
            self.snapshot.start_ts = t
            self.snapshot.finish_ts = None
            self.snapshot.elapsed_s = 0.0
            self._last_transition_s = t
        play_beep(1000, 150)

    def on_finish_trigger(self, timestamp_s: float | None = None) -> None:
        with self._lock:
            t = now_s() if timestamp_s is None else timestamp_s
            if self.snapshot.state != TimerState.RUNNING or self.snapshot.start_ts is None:
                return
            run_ms = (t - self.snapshot.start_ts) * 1000.0
            if run_ms < self.min_run_ms:
                return
            if (t - self._last_transition_s) * 1000.0 < self.debounce_ms:
                return
            self.snapshot.finish_ts = t
            self.snapshot.elapsed_s = t - self.snapshot.start_ts
            self.snapshot.state = TimerState.FINISHED
            self._last_transition_s = t
        play_beep(1500, 200, repeats=3)

    def tick(self) -> TimerSnapshot:
        with self._lock:
            if self.snapshot.state == TimerState.RUNNING and self.snapshot.start_ts is not None:
                self.snapshot.elapsed_s = now_s() - self.snapshot.start_ts
            return replace(self.snapshot)
