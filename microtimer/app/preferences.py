import json
import math

from app.paths import data_root


LIMITS = {
    "sample_interval_ms": (5, 250),
    "goal_hold_ms": (0, 1000),
    "transition_timeout_ms": (100, 5000),
}


def load_processing_preferences():
    try:
        data = json.loads((data_root() / "preferences.json").read_text(encoding="utf-8"))
        return {
            key: int(data[key]) for key, (low, high) in LIMITS.items()
            if isinstance(data, dict) and type(data.get(key)) in (int, float)
            and math.isfinite(data[key]) and low <= data[key] <= high
        }
    except (OSError, ValueError, TypeError):
        return {}


def save_processing_preferences(processing):
    path = data_root() / "preferences.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({key: processing[key] for key in LIMITS}, indent=2), encoding="utf-8")
    temporary.replace(path)
