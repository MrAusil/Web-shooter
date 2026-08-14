"""Screen shake and motion-trail helpers."""
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
import cv2

import config


class ScreenShake:
    """Subtle camera-shake effect that decays over time."""

    def __init__(self):
        self.strength = 0.0
        self.decay = 8.0  # units per second

    def kick(self, strength: float):
        self.strength = max(self.strength, strength)

    def update(self, dt: float):
        self.strength = max(0.0, self.strength - self.decay * dt)

    def offset(self) -> Tuple[int, int]:
        if self.strength <= 0.1 or not config.SCREEN_SHAKE_ENABLED:
            return 0, 0
        dx = int(np.random.uniform(-1, 1) * self.strength)
        dy = int(np.random.uniform(-1, 1) * self.strength)
        return dx, dy

    def apply(self, frame: np.ndarray) -> np.ndarray:
        dx, dy = self.offset()
        if dx == 0 and dy == 0:
            return frame
        h, w = frame.shape[:2]
        m = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(frame, m, (w, h), borderMode=cv2.BORDER_REFLECT)


class MotionTrail:
    """Simple fading accumulation buffer for a subtle motion trail on the VFX layer."""

    def __init__(self):
        self.buffer: Optional[np.ndarray] = None

    def update_and_apply(self, frame: np.ndarray, web_layer_only: np.ndarray) -> np.ndarray:
        if not config.TRAIL_ENABLED:
            return frame
        if self.buffer is None or self.buffer.shape != frame.shape:
            self.buffer = np.zeros_like(frame, dtype=np.float32)
        self.buffer *= config.TRAIL_DECAY
        self.buffer = np.maximum(self.buffer, web_layer_only.astype(np.float32))
        trail_u8 = np.clip(self.buffer * 0.35, 0, 255).astype(np.uint8)
        return cv2.add(frame, trail_u8)
