from core.fsm import TimerFSM
from core.models import TimerState
import pytest


def test_fsm_flow():
    fsm = TimerFSM(debounce_ms=0, min_run_ms=0)
    fsm.arm()
    assert fsm.snapshot.state == TimerState.ARMED
    fsm.on_start_trigger()
    assert fsm.snapshot.state == TimerState.RUNNING
    fsm.on_finish_trigger()
    assert fsm.snapshot.state == TimerState.FINISHED
    assert fsm.snapshot.elapsed_s >= 0.0


def test_timer_uses_capture_timestamps_instead_of_processing_delay(monkeypatch):
    monkeypatch.setattr("core.fsm.now_s", lambda: 99.0)
    fsm = TimerFSM(debounce_ms=0, min_run_ms=200)
    fsm.arm()
    monkeypatch.setattr("core.fsm.now_s", lambda: 120.0)
    fsm.on_start_trigger(timestamp_s=100.0)
    fsm.on_finish_trigger(timestamp_s=102.125)
    assert fsm.snapshot.state == TimerState.FINISHED
    assert fsm.snapshot.elapsed_s == pytest.approx(2.125)


def test_tick_snapshot_remains_consistent_when_worker_changes_timer():
    fsm = TimerFSM(debounce_ms=0, min_run_ms=0)
    fsm.arm()
    snapshot = fsm.tick()
    fsm.on_start_trigger()
    assert snapshot.state == TimerState.ARMED
    assert snapshot.start_ts is None
    assert fsm.tick().state == TimerState.RUNNING


def test_unavailable_windows_audio_does_not_break_timer_notifications(monkeypatch):
    from types import SimpleNamespace
    from core import fsm

    calls = []

    def unavailable_beep(*args):
        calls.append(args)
        raise RuntimeError("Failed to beep")

    monkeypatch.setattr(fsm, "winsound", SimpleNamespace(Beep=unavailable_beep))
    # Run the notification synchronously so a thread exception cannot escape
    # the test after the assertion has already passed.
    monkeypatch.setattr(fsm.threading.Thread, "start", lambda thread: thread.run())
    fsm.play_beep(1000, 150, repeats=3)
    assert calls == [(1000, 150)]
