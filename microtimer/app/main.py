from __future__ import annotations

from app.config_loader import load_config
from app.paths import data_root, resource_root
from app.preferences import load_processing_preferences
from core.logger import setup_logging
from ui.qt_app import run_qt_app


def main() -> int:
    setup_logging(data_root() / "logs" / "app.log")
    cfg_path = resource_root() / "config" / "default.yaml"
    config = load_config(cfg_path)
    config.setdefault("processing", {}).update(load_processing_preferences())
    return run_qt_app(config)


if __name__ == "__main__":
    raise SystemExit(main())
