import time


def now_s() -> float:
    return time.perf_counter()


def elapsed_ms(start_s: float, end_s: float) -> float:
    return (end_s - start_s) * 1000.0
