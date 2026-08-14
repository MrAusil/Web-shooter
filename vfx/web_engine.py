"""Owns all active web projectiles + the shared particle system."""
from __future__ import annotations
import time
from typing import Optional
import numpy as np

import config
from vfx.web import WebProjectile
from vfx.particles import ParticleSystem
from vfx.impact import ImpactEffect
from vfx import glow as glow_mod


class WebEngine:
    """Spawns, updates, and renders every active web + particle."""

    def __init__(self):
        self.webs: list[WebProjectile] = []
        self.particles = ParticleSystem()
        self.pending_shake = 0.0
        self.current_style_key = config.DEFAULT_STYLE
        self._recent_shots: list[float] = []  # for combo detection

    def set_style(self, style_key: str):
        if style_key in config.WEB_STYLES:
            self.current_style_key = style_key

    def shoot(self, origin, direction, style: Optional[str] = None,
              power: bool = False, seed=None) -> WebProjectile:
        if len(self.webs) >= config.MAX_ACTIVE_WEBS:
            self.webs.pop(0)  # drop oldest so shooting never stalls

        style_key = style or self.current_style_key
        style_dict = config.WEB_STYLES.get(style_key, config.WEB_STYLES[config.DEFAULT_STYLE])

        origin = np.array(origin, dtype=np.float32)
        direction = np.array(direction, dtype=np.float32)
        n = np.linalg.norm(direction)
        direction = direction / n if n > 1e-6 else np.array([1.0, 0.0], dtype=np.float32)

        distance = config.WEB_MIN_DISTANCE + np.random.rand() * (
            config.WEB_MAX_DISTANCE - config.WEB_MIN_DISTANCE
        )
        target = origin + direction * distance

        web = WebProjectile(
            origin=origin, direction=direction, target=target,
            speed=config.WEB_BASE_SPEED, style=style_dict,
            seed=seed, power=power,
        )
        self.webs.append(web)

        now = time.time()
        self._recent_shots.append(now)
        self._recent_shots = [t for t in self._recent_shots if now - t < 2.0]
        return web

    def combo_count(self) -> int:
        return len(self._recent_shots)

    def update(self, dt: float):
        self.pending_shake = 0.0

        def on_impact(position, power):
            shake = ImpactEffect.trigger(
                self.particles, position, config.WEB_STYLES[self.current_style_key], power
            )
            self.pending_shake = max(self.pending_shake, shake)

        for web in self.webs:
            web.update(dt, particle_system=self.particles, on_impact=on_impact)

        self.particles.update(dt)
        self.webs = [w for w in self.webs if w.is_alive()]

    def retract_all(self):
        for w in self.webs:
            w.request_retract()

    def render(self, base_frame: np.ndarray, trail=None) -> np.ndarray:
        h, w = base_frame.shape[:2]
        web_layer = np.zeros((h, w, 3), dtype=np.uint8)

        for web in self.webs:
            web.render(web_layer)
        self.particles.render(web_layer)

        frame = base_frame
        if trail is not None:
            frame = trail.update_and_apply(frame, web_layer)

        return glow_mod.apply_glow(frame, web_layer)

    def active_count(self) -> int:
        return len(self.webs)
