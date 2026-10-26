from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0")
    parser.add_argument("--out", default="sample.mp4")
    parser.add_argument("--seconds", type=int, default=10)
    args = parser.parse_args()

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        print("Cannot open camera/source")
        return 1

    fps = 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    out_path = Path(args.out)
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    max_frames = int(args.seconds * fps)
    count = 0
    while count < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(frame)
        count += 1

    writer.release()
    cap.release()
    print(f"Wrote {count} frames to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
