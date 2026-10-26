from __future__ import annotations

from vision.camera.base import CameraSource
from vision.camera.ip_camera import IpCameraSource
from app.paths import resource_root
from vision.camera.video_file import VideoFileSource
from vision.camera.usb_camera import UsbCameraSource


def build_camera_source(config: dict) -> CameraSource:
    camera_cfg = config.get("camera", {})
    source_type = camera_cfg.get("source_type", "usb").lower()
    if source_type == "mock":
        path = camera_cfg.get("mock_video") or str(resource_root() / "samples" / "mock_run_real.mp4")
        return VideoFileSource(path)
    if source_type == "ip":
        return IpCameraSource(
            url=camera_cfg.get("ip_url", ""),
            reconnect_ms=int(camera_cfg.get("reconnect_ms", 1500)),
        )
    return UsbCameraSource(
        index=int(camera_cfg.get("usb_index", 0)),
        width=int(camera_cfg.get("width", 1280)),
        height=int(camera_cfg.get("height", 720)),
        fps=int(camera_cfg.get("fps", 30)),
    )
