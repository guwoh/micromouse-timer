from __future__ import annotations

import sys

from PyQt6 import QtWidgets, QtCore

from ui.main_window import MainWindow


def run_qt_app(config: dict) -> int:
    # Enable high DPI scaling for multi-monitor projection setups
    QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(config)
    win.showMaximized()
    return app.exec()
