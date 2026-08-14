"""Robust webcam capture wrapper with fallback resolution and FPS tracking."""
from __future__ import annotations
import time
from typing import Optional, Tuple
import cv2

import config


class CameraError(Exception):
    """Raised when the webcam cannot be opened or configured."""


class CameraManager:
    """Owns the cv2.VideoCapture device: opens it, mirrors frames, tracks FPS,
    and releases resources cleanly."""

    def __init__(self, index: int = config.CAMERA_INDEX):
        self.index = index
        self.cap: Optional[cv2.VideoCapture] = None
        self._fps_smoothed = 0.0
        self._last_time = time.time()
        self._open()

    def _open(self):
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            raise CameraError(
                f"Could not open webcam at index {self.index}. "
                f"Check that a camera is connected, drivers are installed, "
                f"and it is not already in use by another application."
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

        actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if actual_w < 640 or actual_h < 360:
            # 720p unavailable on this device -> fall back gracefully
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_FALLBACK_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_FALLBACK_HEIGHT)

    def read(self, mirror: bool = True):
        """Returns (ok, frame). Handles disconnects gracefully by returning ok=False."""
        if self.cap is None or not self.cap.isOpened():
            return False, None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return False, None
        if mirror:
            frame = cv2.flip(frame, 1)

        now = time.time()
        dt = now - self._last_time
        self._last_time = now
        if dt > 0:
            inst_fps = 1.0 / dt
            self._fps_smoothed = (
                self._fps_smoothed * 0.9 + inst_fps * 0.1 if self._fps_smoothed else inst_fps
            )

        return True, frame

    def fps(self) -> float:
        return self._fps_smoothed

    def frame_size(self) -> Tuple[int, int]:
        if self.cap is None:
            return config.CAMERA_WIDTH, config.CAMERA_HEIGHT
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return w, h

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
