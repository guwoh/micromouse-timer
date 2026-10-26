from pathlib import Path

import cv2
import numpy as np


def create_synthetic_run(output_path: str = "mock_run.mp4", duration_sec: int = 5, fps: int = 30) -> None:
    width = height = 800
    writer = cv2.VideoWriter(
        output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create video: {output_path}")

    background = np.full((height, width, 3), 195, dtype=np.uint8)
    for coordinate in range(0, width + 1, 50):
        cv2.line(background, (coordinate, 0), (coordinate, height - 1), (160, 160, 160), 1)
        cv2.line(background, (0, coordinate), (width - 1, coordinate), (160, 160, 160), 1)

    try:
        for frame_index in range(duration_sec * fps):
            t = frame_index / fps
            if t <= 1.0:
                x, y = 25, 780
            elif t < 1.7:
                x, y = 25, int(780 - (t - 1.0) / 0.7 * 130)
            elif t < 3.5:
                progress = (t - 1.7) / 1.8
                x = int(25 + progress * 375)
                y = int(650 - progress * 250)
            else:
                x, y = 400, 400

            frame = background.copy()
            cv2.rectangle(frame, (x - 15, y - 15), (x + 15, y + 15), (0, 0, 255), -1)
            writer.write(frame)
    finally:
        writer.release()
    print(f"Synthetic video saved at: {Path(output_path).resolve()}")


if __name__ == "__main__":
    create_synthetic_run()
