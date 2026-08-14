"""Coordinates the rendering pipeline: VFX -> screen shake -> HUD."""
from __future__ import annotations
from typing import Optional
import numpy as np

from vfx.web_engine import WebEngine
from rendering.effects import ScreenShake, MotionTrail
from ui.hud import HUD


class Renderer:
    """Ties together the VFX composite, screen shake, and HUD into one call."""

    def __init__(self):
        self.screen_shake = ScreenShake()
        self.trail = MotionTrail()

    def render_frame(self, base_frame: np.ndarray, web_engine: WebEngine, hud: HUD,
                       hud_data: dict, debug_data: Optional[dict] = None) -> np.ndarray:
        frame = web_engine.render(base_frame, trail=self.trail)

        if web_engine.pending_shake > 0:
            self.screen_shake.kick(web_engine.pending_shake)
        frame = self.screen_shake.apply(frame)

        if hud_data.get("hud_enabled", True):
            hud.draw(frame, hud_data)
        if debug_data:
            hud.draw_debug(frame, debug_data)

        return frame

    def update(self, dt: float):
        self.screen_shake.update(dt)
