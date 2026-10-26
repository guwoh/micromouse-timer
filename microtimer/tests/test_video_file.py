import time

import cv2
import numpy as np

from app.paths import resource_root
from vision.camera.factory import build_camera_source
from vision.camera.video_file import VideoFileSource


def test_default_mock_decodes_original_bundled_video_at_recorded_fps():
    source = build_camera_source({"camera": {"source_type": "mock"}})
    assert isinstance(source, VideoFileSource)
    assert source.path == resource_root() / "samples" / "mock_run_real.mp4"
    decoder = cv2.VideoCapture(str(source.path))
    ok, expected_first = decoder.read()
    assert ok
    decoder.release()
    assert source.open()
    try:
        assert source.fps == 30
        started = time.perf_counter()
        ok, first = source.read()
        assert ok and first.shape == (1080, 1920, 3)
        ok, second = source.read()
        assert ok and second.shape == first.shape
        assert time.perf_counter() - started >= 0.8 / source.fps
        np.testing.assert_array_equal(first, expected_first)
        assert source.cap.get(cv2.CAP_PROP_POS_FRAMES) == 2
        source.rewind()
        ok, replay = source.read()
        assert ok
        np.testing.assert_array_equal(replay, first)
    finally:
        source.release()


def test_custom_video_loops_at_eof_and_rewinds(test_video):
    source = build_camera_source({"camera": {"source_type": "mock", "mock_video": str(test_video)}})
    assert source.open()
    try:
        ok, first = source.read()
        assert ok
        with source._lock:
            source.cap.set(cv2.CAP_PROP_POS_FRAMES, source.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, looped = source.read()
        assert ok
        np.testing.assert_array_equal(looped, first)
    finally:
        source.release()
    assert not source.is_opened()
    assert source.read() == (False, None)


def test_missing_video_is_reported_without_substituting_generated_frames(tmp_path):
    source = VideoFileSource(tmp_path / "missing.mp4")
    assert not source.open()
    assert not source.is_opened()
    assert source.read() == (False, None)
