"""Gesture recognition for the Spider-Man-style web-shooter pose."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from collections import deque
from typing import Dict, Optional
import time
import numpy as np

from tracking.hand_tracker import HandState
from tracking import landmark_utils as lu
import config


class Gesture(Enum):
    NONE = auto()
    WEB_SHOOT = auto()


@dataclass
class GestureResult:
    gesture: Gesture
    confidence: float
    direction: np.ndarray
    triggered: bool          # a shot should fire this frame
    holding: bool            # gesture currently held
    hold_duration: float
    is_power: bool = False   # True if this trigger is a released power shot


class GestureDetector:
    """
    Detects the web-shooter pose per-hand using multiple geometric conditions
    (not a single landmark check):
      - index finger extended
      - pinky extended
      - thumb reasonably away from the palm
      - middle + ring folded
    This resembles a relaxed "rock on" / web-shooter pose. Debounces with a
    rolling frame history + cooldown, and supports holding for a power shot.
    """

    def __init__(self):
        self._history: Dict[str, deque] = {}
        self._last_shot_time: Dict[str, float] = {}
        self._hold_start: Dict[str, float] = {}
        self._was_holding: Dict[str, bool] = {}
        self._smoothed_direction: Dict[str, np.ndarray] = {}
        self._smoothed_origin: Dict[str, np.ndarray] = {}

    def _pose_confidence(self, hand: HandState) -> float:
        pts = hand.landmarks
        index_ratio = lu.finger_extension_ratio(pts, lu.INDEX_TIP, lu.INDEX_MCP)
        middle_ratio = lu.finger_extension_ratio(pts, lu.MIDDLE_TIP, lu.MIDDLE_MCP)
        ring_ratio = lu.finger_extension_ratio(pts, lu.RING_TIP, lu.RING_MCP)
        pinky_ratio = lu.finger_extension_ratio(pts, lu.PINKY_TIP, lu.PINKY_MCP)
        thumb_dist = lu.distance(pts[lu.THUMB_TIP], pts[lu.INDEX_MCP])

        index_ok = index_ratio > (1.0 + config.INDEX_EXTENSION_THRESHOLD * 0.5)
        pinky_ok = pinky_ratio > (1.0 + config.INDEX_EXTENSION_THRESHOLD * 0.4)
        middle_folded = middle_ratio < (1.0 + config.FINGER_FOLD_THRESHOLD * 0.3)
        ring_folded = ring_ratio < (1.0 + config.FINGER_FOLD_THRESHOLD * 0.3)
        thumb_ok = thumb_dist > config.THUMB_POSITION_THRESHOLD * hand.scale

        # The four finger-state conditions are mandatory: a plain pointing
        # finger or an open palm must NOT be able to pass just because it
        # scores well on the others. Thumb position only fine-tunes the
        # confidence once the mandatory shape is already correct.
        mandatory = [index_ok, pinky_ok, middle_folded, ring_folded]
        if not all(mandatory):
            # Cap well below the trigger threshold even if 3/4 mandatory checks pass.
            return 0.6 * (sum(1.0 for c in mandatory if c) / len(mandatory))

        return 0.8 + (0.2 if thumb_ok else 0.0)

    def detect(self, hand: HandState, frame_w: int, frame_h: int) -> GestureResult:
        key = hand.handedness
        confidence = self._pose_confidence(hand)
        history = self._history.setdefault(key, deque(maxlen=config.GESTURE_HOLD_FRAMES))
        history.append(confidence >= config.GESTURE_CONFIDENCE_THRESHOLD)

        now = time.time()
        is_pose_now = len(history) == history.maxlen and all(history)

        # direction smoothing (EMA) so the aim vector doesn't jitter frame to frame
        raw_dir = hand.index_direction.astype(np.float32)
        prev_dir = self._smoothed_direction.get(key)
        smoothed_dir = lu.normalize(lu.ema(prev_dir, raw_dir, config.DIRECTION_SMOOTHING))
        self._smoothed_direction[key] = smoothed_dir

        triggered = False
        is_power = False
        holding = False
        hold_duration = 0.0

        if is_pose_now:
            holding = True
            if key not in self._hold_start:
                self._hold_start[key] = now
            hold_duration = now - self._hold_start[key]

            # Rapid-fire while held, but stop normal shots once charging a power shot.
            if hold_duration < config.POWER_SHOT_HOLD_SECONDS:
                last_shot = self._last_shot_time.get(key, 0.0)
                if now - last_shot >= config.GESTURE_COOLDOWN_SECONDS:
                    triggered = True
                    self._last_shot_time[key] = now
            self._was_holding[key] = True
        else:
            # Detect release after a long hold -> fire a power shot.
            if self._was_holding.get(key, False):
                prev_hold_start = self._hold_start.get(key)
                if prev_hold_start is not None:
                    prev_hold_duration = now - prev_hold_start
                    if prev_hold_duration >= config.POWER_SHOT_HOLD_SECONDS:
                        triggered = True
                        is_power = True
                        self._last_shot_time[key] = now
            self._hold_start.pop(key, None)
            self._was_holding[key] = False

        gesture = Gesture.WEB_SHOOT if (is_pose_now or is_power) else Gesture.NONE
        return GestureResult(
            gesture=gesture,
            confidence=confidence,
            direction=smoothed_dir,
            triggered=triggered,
            holding=holding,
            hold_duration=hold_duration,
            is_power=is_power,
        )

    def smoothed_origin(self, key: str, raw_origin: np.ndarray) -> np.ndarray:
        """Smooth the web-launch origin point (wrist position) to avoid jitter."""
        prev = self._smoothed_origin.get(key)
        smoothed = lu.ema(prev, raw_origin, config.ORIGIN_SMOOTHING)
        self._smoothed_origin[key] = smoothed
        return smoothed
