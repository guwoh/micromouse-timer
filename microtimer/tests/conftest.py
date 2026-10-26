import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6 import QtWidgets


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def window(qapp, monkeypatch, tmp_path):
    from app.config_loader import load_config
    from app.paths import resource_root
    from ui.main_window import MainWindow

    monkeypatch.setattr("ui.main_window.data_root", lambda: tmp_path)
    monkeypatch.setattr("app.preferences.data_root", lambda: tmp_path)
    win = MainWindow(load_config(resource_root() / "config" / "default.yaml"))
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    qapp.processEvents()


@pytest.fixture
def test_video(tmp_path):
    from scripts.create_mock_video import create_synthetic_run

    path = tmp_path / "test_run.mp4"
    create_synthetic_run(str(path))
    return path
