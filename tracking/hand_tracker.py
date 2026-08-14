"""MediaPipe-based hand tracking wrapper."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import time
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

from . import landmark_utils as lu
import config


@dataclass
class HandState:
    """Snapshot of a single tracked hand for the current frame (normalized coords)."""
    landmarks: np.ndarray                 # (21,3) normalized coords
    handedness: str                       # "Left" / "Right"
    confidence: float
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float32))
    wrist: np.ndarray = field(init=False)
    palm_center: np.ndarray = field(init=False)
    index_direction: np.ndarray = field(init=False)
    scale: float = field(init=False)

    def __post_init__(self):
        self.wrist = self.landmarks[lu.WRIST][:2]
        self.palm_center = self.landmarks[[lu.WRIST, lu.INDEX_MCP, lu.PINKY_MCP]][:, :2].mean(axis=0)
        tip = self.landmarks[lu.INDEX_TIP][:2]
        self.index_direction = lu.normalize(tip - self.wrist)
        self.scale = lu.hand_scale(self.landmarks)


class HandTracker:
    """Wraps MediaPipe Hands and produces HandState objects per frame."""

    def __init__(self):
        self.available = MEDIAPIPE_AVAILABLE
        self._prev_states: Dict[str, HandState] = {}
        self._prev_time: Optional[float] = None
        self._hands = None

        if self.available:
            try:
                self._mp_hands = mp.solutions.hands
                self._hands = self._mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=config.MAX_NUM_HANDS,
                    min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                    min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
                )
            except Exception as exc:
                print(f"[tracking] MediaPipe Hands failed to initialize: {exc}")
                self.available = False
                self._hands = None

    def process(self, frame_rgb: np.ndarray, frame_w: int, frame_h: int) -> List[HandState]:
        """Run detection on an RGB frame and return a list of HandState."""
        if not self.available or self._hands is None:
            return []

        results = self._hands.process(frame_rgb)
        states: List[HandState] = []
        now = time.time()
        dt = (now - self._prev_time) if self._prev_time else (1.0 / 30.0)
        dt = max(dt, 1e-3)
        self._prev_time = now

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness_info in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                pts = lu.to_array(hand_landmarks.landmark)
                label = handedness_info.classification[0].label
                confidence = handedness_info.classification[0].score
                state = HandState(landmarks=pts, handedness=label, confidence=confidence)

                prev = self._prev_states.get(label)
                current_px = state.palm_center * np.array([frame_w, frame_h])
                if prev is not None:
                    prev_px = prev.palm_center * np.array([frame_w, frame_h])
                    state.velocity = (current_px - prev_px) / dt
                self._prev_states[label] = state
                states.append(state)

        return states

    def close(self):
        if self.available and self._hands is not None:
            self._hands.close()
