"""
Basic tests for the core, non-visual logic of Spider-Web FX.

Run with:
    python tests/test_core.py
No test framework is required (plain asserts), so this works even in a
minimal environment. If pytest is installed you can also run:
    python -m pytest tests/test_core.py -v
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import config
from tracking import landmark_utils as lu
from tracking.hand_tracker import HandState
from tracking.gesture_detector import GestureDetector
from vfx.web import WebProjectile
from vfx.particles import ParticleSystem


def _pose(index_ext=True, pinky_ext=True, middle_folded=True, ring_folded=True, thumb_away=True):
    """Build synthetic 21-point landmarks with controllable finger states."""
    pts = np.zeros((21, 3), dtype=np.float32)
    pts[0] = [0.5, 0.8, 0]  # wrist
    pts[1] = [0.42, 0.75, 0]
    pts[2] = [0.38, 0.70, 0]
    pts[3] = [0.34, 0.65, 0]
    pts[4] = [0.30 if thumb_away else 0.47, 0.60 if thumb_away else 0.77, 0]

    pts[5] = [0.50, 0.65, 0]
    pts[6] = [0.50, 0.55, 0]
    pts[7] = [0.50, 0.45, 0]
    pts[8] = [0.50, 0.35 if index_ext else 0.62, 0]

    pts[9]  = [0.54, 0.65, 0]
    pts[10] = [0.54, 0.68, 0]
    pts[11] = [0.53, 0.72, 0]
    pts[12] = [0.53, 0.35 if not middle_folded else 0.75, 0]

    pts[13] = [0.58, 0.65, 0]
    pts[14] = [0.58, 0.68, 0]
    pts[15] = [0.57, 0.72, 0]
    pts[16] = [0.57, 0.35 if not ring_folded else 0.75, 0]

    pts[17] = [0.62, 0.65, 0]
    pts[18] = [0.63, 0.58, 0]
    pts[19] = [0.64, 0.50, 0]
    pts[20] = [0.65, 0.42 if pinky_ext else 0.70, 0]
    return pts


def test_gesture_correct_pose_true():
    detector = GestureDetector()
    hand = HandState(landmarks=_pose(), handedness="Right", confidence=0.9)
    fired = False
    for _ in range(config.GESTURE_HOLD_FRAMES + 2):
        r = detector.detect(hand, 1280, 720)
        fired = fired or r.triggered
    assert fired, "Correct web-shooter pose should trigger a shot"


def test_gesture_fist_false():
    detector = GestureDetector()
    hand = HandState(landmarks=_pose(index_ext=False, pinky_ext=False), handedness="Right", confidence=0.9)
    fired = False
    for _ in range(config.GESTURE_HOLD_FRAMES + 2):
        r = detector.detect(hand, 1280, 720)
        fired = fired or r.triggered
    assert not fired, "A fist should not trigger the web-shooter gesture"


def test_gesture_open_palm_false():
    detector = GestureDetector()
    # everything extended -> fails the middle/ring-folded condition
    hand = HandState(landmarks=_pose(middle_folded=False, ring_folded=False), handedness="Right", confidence=0.9)
    fired = False
    for _ in range(config.GESTURE_HOLD_FRAMES + 2):
        r = detector.detect(hand, 1280, 720)
        fired = fired or r.triggered
    assert not fired, "An open palm should not trigger the web-shooter gesture"


def test_gesture_pointing_finger_false():
    detector = GestureDetector()
    # index only, pinky folded -> should not match (pinky required)
    hand = HandState(landmarks=_pose(pinky_ext=False), handedness="Right", confidence=0.9)
    fired = False
    for _ in range(config.GESTURE_HOLD_FRAMES + 2):
        r = detector.detect(hand, 1280, 720)
        fired = fired or r.triggered
    assert not fired, "A plain pointing finger should not trigger the web-shooter gesture"


def test_two_hands_tracked_independently():
    detector = GestureDetector()
    right = HandState(landmarks=_pose(), handedness="Right", confidence=0.9)
    left = HandState(landmarks=_pose(index_ext=False, pinky_ext=False), handedness="Left", confidence=0.9)
    right_fired, left_fired = False, False
    for _ in range(config.GESTURE_HOLD_FRAMES + 2):
        r_r = detector.detect(right, 1280, 720)
        r_l = detector.detect(left, 1280, 720)
        right_fired = right_fired or r_r.triggered
        left_fired = left_fired or r_l.triggered
    assert right_fired and not left_fired, "Each hand's gesture state must be tracked independently"


def test_vector_normalization():
    v = np.array([3.0, 4.0], dtype=np.float32)
    n = lu.normalize(v)
    assert abs(np.linalg.norm(n) - 1.0) < 1e-5

    zero = np.array([0.0, 0.0], dtype=np.float32)
    assert np.allclose(lu.normalize(zero), zero), "Normalizing a zero vector should not divide by zero"


def test_curve_generation_and_lifecycle():
    origin = np.array([100, 500], dtype=np.float32)
    target = np.array([600, 200], dtype=np.float32)
    web = WebProjectile(origin, np.array([1, -1]), target, speed=3000, style=config.WEB_STYLES["classic"], seed=1)

    pts = web.sample_curve(1.0, n=10)
    assert pts.shape == (10, 2)
    assert np.allclose(pts[0], origin, atol=1e-3)
    assert np.allclose(pts[-1], target, atol=1e-3)

    # deterministic given the same seed
    web2 = WebProjectile(origin, np.array([1, -1]), target, speed=3000, style=config.WEB_STYLES["classic"], seed=1)
    assert np.allclose(web.control, web2.control)
    assert len(web.branches) == len(web2.branches)


def test_web_lifecycle_reaches_completion():
    origin = np.array([0, 0], dtype=np.float32)
    target = np.array([300, 0], dtype=np.float32)
    web = WebProjectile(origin, np.array([1, 0]), target, speed=3000, style=config.WEB_STYLES["classic"], seed=2)
    for _ in range(500):
        web.update(0.05)
        if not web.is_alive():
            break
    assert not web.is_alive(), "Web should eventually complete its full lifecycle and die"


def test_particle_lifecycle():
    ps = ParticleSystem(max_particles=50)
    ps.emit((10, 10), 5, (255, 255, 255), life_range=(0.1, 0.1))
    assert ps.count() == 5
    for _ in range(10):
        ps.update(0.05)
    assert ps.count() == 0, "Particles should expire after their lifetime"


def test_config_loading():
    assert config.MAX_ACTIVE_WEBS > 0
    assert "classic" in config.WEB_STYLES
    assert config.WEB_MIN_DISTANCE < config.WEB_MAX_DISTANCE


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
