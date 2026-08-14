"""Geometry helpers for hand landmarks."""
from __future__ import annotations
import numpy as np


def to_array(landmarks) -> np.ndarray:
    """Convert a mediapipe landmark list into an (21,3) numpy array (normalized coords)."""
    return np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a[:2] - b[:2]))


def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-6:
        return v
    return v / n


def lerp(a, b, t: float):
    return a + (b - a) * t


def ema(prev, new, factor: float):
    """Exponential moving average smoothing. factor in [0,1], higher = more responsive."""
    if prev is None:
        return new
    return prev + (new - prev) * factor


# MediaPipe hand landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


def finger_extension_ratio(points: np.ndarray, tip: int, mcp: int, wrist: int = WRIST) -> float:
    """Ratio of tip-to-wrist distance over mcp-to-wrist distance. >1 roughly means extended."""
    wrist_to_mcp = distance(points[wrist], points[mcp]) + 1e-6
    wrist_to_tip = distance(points[wrist], points[tip])
    return wrist_to_tip / wrist_to_mcp


def hand_scale(points: np.ndarray) -> float:
    """Rough hand size measure (wrist to middle mcp), used for pseudo-depth / thresholds."""
    return distance(points[WRIST], points[MIDDLE_MCP]) + 1e-6
