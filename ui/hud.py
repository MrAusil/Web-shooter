"""Minimal cinematic HUD overlay."""
from __future__ import annotations
import cv2
import config


class HUD:
    """Draws a small, clean status readout and optional debug overlay."""

    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def draw(self, frame, data: dict):
        h, w = frame.shape[:2]
        lines = [
            "SPIDER-WEB FX",
            f"STATUS: {data.get('status', 'READY')}",
            f"HAND: {data.get('hand_status', 'NOT DETECTED')}",
            f"GESTURE: {data.get('gesture_status', 'IDLE')}",
            f"WEBS: {data.get('web_count', 0):02d}",
            f"FPS: {data.get('fps', 0):.0f}",
        ]
        y = 28
        for line in lines:
            cv2.putText(frame, line, (16, y), self.font, config.HUD_FONT_SCALE,
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, line, (16, y), self.font, config.HUD_FONT_SCALE,
                        config.HUD_COLOR, 1, cv2.LINE_AA)
            y += 22

        if data.get("recording"):
            cv2.circle(frame, (w - 30, 24), 7, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(frame, "REC", (w - 70, 30), self.font, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        indicator = data.get("gesture_indicator")
        if indicator:
            text, pos = indicator
            cv2.putText(frame, text, pos, self.font, 0.6, (100, 255, 255), 2, cv2.LINE_AA)

        combo = data.get("combo")
        if combo and combo >= 3:
            cv2.putText(frame, f"COMBO x{combo}", (w // 2 - 80, 50), self.font, 0.9,
                        (0, 200, 255), 2, cv2.LINE_AA)

    def draw_debug(self, frame, debug: dict):
        y = frame.shape[0] - 110
        lines = [
            f"Gesture confidence: {debug.get('confidence', 0):.2f}",
            f"Hand velocity: {debug.get('velocity', 0):.1f}",
            f"Active webs: {debug.get('active_webs', 0)}",
            f"Frame time: {debug.get('frame_ms', 0):.1f} ms",
        ]
        for line in lines:
            cv2.putText(frame, line, (16, y), self.font, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
            y += 20
