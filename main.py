"""
Spider-Web VFX — Real-Time Hand Gesture Web Shooter
Entry point. Coordinates the camera, hand tracking, gesture detection, VFX
engine, renderer, audio, and HUD into a single real-time application.

Run with:
    python main.py
"""
from __future__ import annotations
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

import config
from camera.camera_manager import CameraManager, CameraError
from tracking.hand_tracker import HandTracker
from tracking.gesture_detector import GestureDetector, Gesture
from vfx.web_engine import WebEngine
from rendering.renderer import Renderer
from audio.sound_manager import SoundManager
from ui.hud import HUD

WINDOW_NAME = "Spider-Web FX"
STYLE_KEYS = {ord('1'): "classic", ord('2'): "electric", ord('3'): "dark"}


class Application:
    """Top-level coordinator for every subsystem and the main loop."""

    def __init__(self):
        config.RECORDINGS_DIR.mkdir(exist_ok=True)
        config.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        config.SOUND_DIR.mkdir(parents=True, exist_ok=True)

        self._print_startup_banner()

        try:
            self.camera = CameraManager()
        except CameraError as exc:
            print(f"[error] {exc}")
            sys.exit(1)

        self.hand_tracker = HandTracker()
        if not self.hand_tracker.available:
            print(
                "[error] Hand tracking unavailable: the 'mediapipe' package is not "
                "installed or failed to initialize. Install it with:\n"
                "    pip install mediapipe\n"
                "The application will still run and show the camera feed, but "
                "gestures will not be detected."
            )

        self.gesture_detector = GestureDetector()
        self.web_engine = WebEngine()
        self.renderer = Renderer()
        self.sound = SoundManager()
        self.hud = HUD()

        self.mirror = config.MIRROR_DEFAULT
        self.hud_enabled = config.HUD_ENABLED_DEFAULT
        self.debug_mode = config.DEBUG_MODE_DEFAULT
        self.gesture_viz = True
        self.running = True

        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording = False

        self._last_frame_time = time.time()
        self._gesture_indicator: Optional[Tuple[str, Tuple[int, int]]] = None
        self._gesture_indicator_expires = 0.0
        self._last_rendered_frame: Optional[np.ndarray] = None

        print(
            "CAMERA READY\n\n"
            "Perform the web-shooter gesture (thumb, index, and pinky extended,\n"
            "middle and ring folded — a relaxed 'rock on' pose) to shoot a web.\n"
            "Point your hand in the direction you want the web to travel.\n"
            "Hold the pose for over a second and release for a POWER SHOT.\n"
            "Press Q to quit, H to toggle the HUD.\n"
        )

    # -------------------------------------------------------------- lifecycle
    def _print_startup_banner(self):
        print("=" * 50)
        print("SPIDER-WEB FX")
        print("=" * 50)
        print("Initializing camera...")
        print("Initializing hand tracking...")
        print("Loading VFX engine...")

    def run(self):
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        try:
            while self.running:
                self._tick()
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

    def _shutdown(self):
        print("\nWEB SYSTEM OFFLINE\nThanks for testing Spider-Web FX.\n")
        self.camera.release()
        self.hand_tracker.close()
        self.sound.close()
        if self.video_writer is not None:
            self.video_writer.release()
        cv2.destroyAllWindows()

    # ------------------------------------------------------------------ tick
    def _tick(self):
        frame_start = time.time()
        dt = frame_start - self._last_frame_time
        self._last_frame_time = frame_start
        dt = min(dt, 0.05)  # clamp so a stall doesn't cause a huge simulation jump

        ok, frame = self.camera.read(mirror=self.mirror)
        if not ok:
            print("[warning] Camera frame unavailable — attempting to continue.")
            time.sleep(0.05)
            return

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = self.hand_tracker.process(rgb, w, h)

        hand_status = "NOT DETECTED"
        gesture_status = "IDLE"
        combo = 0

        for hand in hands:
            hand_status = "DETECTED"
            key = hand.handedness

            result = self.gesture_detector.detect(hand, w, h)

            raw_origin_px = hand.wrist * np.array([w, h], dtype=np.float32) + np.array(
                config.WEB_ORIGIN_OFFSET, dtype=np.float32
            )
            origin_px = self.gesture_detector.smoothed_origin(key, raw_origin_px)

            if result.gesture == Gesture.WEB_SHOOT:
                gesture_status = "READY"
                if self.gesture_viz and not result.triggered:
                    self._set_indicator("WEB READY", origin_px)

            if result.triggered:
                gesture_status = "SHOOTING"
                self._fire_web(origin_px, result.direction, power=result.is_power)
                label = "POWER SHOT!" if result.is_power else "WEB SHOOT!"
                self._set_indicator(label, origin_px)
                combo = self.web_engine.combo_count()

            if self.debug_mode:
                self._draw_debug_hand(frame, hand, result)

        self.web_engine.update(dt)
        self.renderer.update(dt)

        rendered = self.renderer.render_frame(
            frame, self.web_engine, self.hud,
            hud_data=self._build_hud_data(hand_status, gesture_status, combo),
            debug_data=self._build_debug_data(dt) if self.debug_mode else None,
        )
        self._last_rendered_frame = rendered

        if self.recording and self.video_writer is not None:
            self.video_writer.write(rendered)

        cv2.imshow(WINDOW_NAME, rendered)
        self._handle_keys()

    # --------------------------------------------------------------- helpers
    def _fire_web(self, origin_px, direction, power: bool = False):
        style = self.web_engine.current_style_key
        seed = int(time.time() * 1000) % (2 ** 31)
        self.web_engine.shoot(origin_px, direction, style=style, power=power, seed=seed)
        self.sound.play("shoot")

    def _set_indicator(self, text: str, pos):
        self._gesture_indicator = (text, (int(pos[0]) + 20, int(pos[1]) - 20))
        self._gesture_indicator_expires = time.time() + 0.6

    def _build_hud_data(self, hand_status: str, gesture_status: str, combo: int) -> Dict:
        indicator = None
        if self._gesture_indicator and time.time() < self._gesture_indicator_expires:
            indicator = self._gesture_indicator
        return {
            "status": "READY",
            "hand_status": hand_status,
            "gesture_status": gesture_status,
            "web_count": self.web_engine.active_count(),
            "fps": self.camera.fps(),
            "recording": self.recording,
            "gesture_indicator": indicator,
            "combo": combo,
            "hud_enabled": self.hud_enabled,
        }

    def _build_debug_data(self, dt: float) -> Dict:
        return {
            "confidence": 0.0,
            "velocity": 0.0,
            "active_webs": self.web_engine.active_count(),
            "frame_ms": dt * 1000,
        }

    def _draw_debug_hand(self, frame, hand, result):
        h, w = frame.shape[:2]
        for pt in hand.landmarks:
            x, y = int(pt[0] * w), int(pt[1] * h)
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1, cv2.LINE_AA)
        wrist_px = (hand.wrist * np.array([w, h])).astype(int)
        cv2.putText(frame, f"{result.confidence:.2f}", tuple(wrist_px + [10, -10]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

    # -------------------------------------------------------------- controls
    def _handle_keys(self):
        key = cv2.waitKey(1) & 0xFF
        if key == 255:
            return

        if key in (ord('q'), 27):  # Q or ESC
            self.running = False
        elif key == ord('r'):
            self.web_engine.webs.clear()
        elif key == ord(' '):
            w, h = self.camera.frame_size()
            self._fire_web(np.array([w / 2, h / 2]), np.array([1.0, -0.3]))
        elif key == ord('m'):
            self.mirror = not self.mirror
        elif key == ord('g'):
            self.gesture_viz = not self.gesture_viz
        elif key == ord('h'):
            self.hud_enabled = not self.hud_enabled
        elif key in STYLE_KEYS:
            self.web_engine.set_style(STYLE_KEYS[key])
        elif key == ord('t'):
            config.TRAIL_ENABLED = not config.TRAIL_ENABLED
        elif key == ord('s'):
            self.sound.toggle()
        elif key == ord('f'):
            self._toggle_fullscreen()
        elif key == ord('v'):
            self._toggle_recording()
        elif key == ord('p'):
            self._take_screenshot()

    def _toggle_fullscreen(self):
        try:
            prop = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
            new_state = cv2.WINDOW_NORMAL if prop == cv2.WINDOW_FULLSCREEN else cv2.WINDOW_FULLSCREEN
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, new_state)
        except cv2.error:
            pass  # fullscreen toggling isn't supported on every platform/backend

    def _toggle_recording(self):
        if self.recording:
            self.recording = False
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
            print("[recording] Stopped.")
            return

        w, h = self.camera.frame_size()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.RECORDINGS_DIR / f"web_fx_{timestamp}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(path), fourcc, config.TARGET_FPS, (w, h))
        if not writer.isOpened():
            print(f"[error] Could not start recording to {path}.")
            return
        self.video_writer = writer
        self.recording = True
        print(f"[recording] Started: {path}")

    def _take_screenshot(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.SCREENSHOTS_DIR / f"screenshot_{timestamp}.png"
        if self._last_rendered_frame is not None:
            cv2.imwrite(str(path), self._last_rendered_frame)
            print(f"[screenshot] Saved: {path}")
        else:
            print("[screenshot] No frame available yet.")


def main():
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
