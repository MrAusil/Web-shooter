"""Single web projectile: procedural curve, branches, and lifecycle state machine."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import time
import numpy as np
import cv2

import config


class WebState(Enum):
    TRAVELING = auto()
    IMPACT = auto()
    ATTACHED = auto()
    RETRACTING = auto()
    COMPLETE = auto()


@dataclass
class Branch:
    start_t: float
    angle_offset: float
    length: float
    thickness: float
    opacity: float


class WebProjectile:
    """
    A single web shot with a procedural curved (quadratic-Bezier) trajectory,
    branching secondary strands generated from a seeded RNG (stable across
    frames), and a full lifecycle: TRAVELING -> IMPACT -> ATTACHED ->
    RETRACTING -> COMPLETE.
    """

    def __init__(self, origin, direction, target, speed, style, seed=None,
                 power: bool = False, thickness: float | None = None):
        self.origin = np.array(origin, dtype=np.float32)
        self.direction = np.array(direction, dtype=np.float32)
        self.target = np.array(target, dtype=np.float32)
        self.speed = speed * (1.6 if power else 1.0)
        self.style = style
        self.power = power
        self.rng = np.random.default_rng(seed)
        self.thickness = thickness or (config.WEB_THICKNESS * (1.6 if power else 1.0))

        self.state = WebState.TRAVELING
        self.created_at = time.time()
        self.state_elapsed = 0.0   # simulated time spent in the current state
        self.progress = 0.0  # 0..1 travel progress along the curve

        self.distance = float(np.linalg.norm(self.target - self.origin))
        self.duration = max(self.distance / max(self.speed, 1.0), 0.05)

        # Procedural curve control point: a perpendicular offset gives the
        # web a natural arc instead of a perfectly straight line. Deterministic
        # per-shot (seeded), so it doesn't jitter frame to frame.
        mid = (self.origin + self.target) / 2.0
        perp = np.array([-self.direction[1], self.direction[0]], dtype=np.float32)
        curve_strength = self.rng.uniform(0.08, 0.22) * max(self.distance, 1.0)
        curve_side = self.rng.choice([-1.0, 1.0])
        self.control = mid + perp * curve_strength * curve_side

        self.branches: list[Branch] = self._generate_branches()
        self.alive = True

    # ---- procedural generation ---------------------------------------
    def _generate_branches(self) -> list[Branch]:
        n = int(self.rng.integers(config.WEB_BRANCH_COUNT_RANGE[0], config.WEB_BRANCH_COUNT_RANGE[1]))
        branches = []
        for _ in range(n):
            branches.append(Branch(
                start_t=float(self.rng.uniform(0.15, 0.85)),
                angle_offset=float(self.rng.uniform(-0.6, 0.6)),
                length=float(self.rng.uniform(0.05, 0.16) * max(self.distance, 1.0)),
                thickness=float(self.rng.uniform(0.8, 1.6)),
                opacity=float(self.rng.uniform(0.35, 0.7)),
            ))
        return branches

    def _bezier_point(self, t: float) -> np.ndarray:
        one_minus = 1 - t
        return (one_minus ** 2) * self.origin + 2 * one_minus * t * self.control + (t ** 2) * self.target

    def sample_curve(self, t_max: float, n: int = 24) -> np.ndarray:
        t_max = max(0.0, min(1.0, t_max))
        ts = np.linspace(0, max(t_max, 1e-3), n)
        return np.array([self._bezier_point(t) for t in ts], dtype=np.float32)

    def _tangent(self, t: float) -> np.ndarray:
        eps = 0.01
        p1 = self._bezier_point(max(0.0, t - eps))
        p2 = self._bezier_point(min(1.0, t + eps))
        d = p2 - p1
        n = np.linalg.norm(d)
        return d / n if n > 1e-6 else np.array([1.0, 0.0], dtype=np.float32)

    # ---- lifecycle ------------------------------------------------------
    def _set_state(self, state: WebState):
        self.state = state
        self.state_elapsed = 0.0

    def update(self, dt: float, particle_system=None, on_impact=None):
        # Use accumulated simulated time (dt) rather than wall-clock time so
        # behaviour stays deterministic and correct even if frame processing
        # stalls or the caller drives updates faster/slower than real time.
        self.state_elapsed += dt
        elapsed = self.state_elapsed

        if self.state == WebState.TRAVELING:
            self.progress = min(1.0, elapsed / self.duration)
            if particle_system is not None and self.rng.random() < 0.5:
                tip = self._bezier_point(self.progress)
                particle_system.emit(tip, 1, self.style["glow"], speed_range=(10, 40),
                                       size_range=(1, 2), life_range=(0.15, 0.3))
            if self.progress >= 1.0:
                self._set_state(WebState.IMPACT)
                if on_impact:
                    on_impact(self.target, self.power)

        elif self.state == WebState.IMPACT:
            if elapsed >= config.WEB_IMPACT_DURATION:
                self._set_state(WebState.ATTACHED)

        elif self.state == WebState.ATTACHED:
            if elapsed >= config.WEB_LIFETIME_ATTACHED:
                self._set_state(WebState.RETRACTING)

        elif self.state == WebState.RETRACTING:
            t = min(1.0, elapsed / config.WEB_RETRACT_DURATION)
            self.progress = 1.0 - t
            if t >= 1.0:
                self._set_state(WebState.COMPLETE)
                self.alive = False

    def request_retract(self):
        if self.state == WebState.ATTACHED:
            self._set_state(WebState.RETRACTING)

    def is_alive(self) -> bool:
        return self.alive

    # ---- rendering --------------------------------------------------------
    def render(self, web_layer: np.ndarray):
        """Draw main strand + branches/fibers + attachment marker onto a BGR layer."""
        core = self.style["core"]
        glow_color = self.style["glow"]
        t_max = 1.0 if self.state == WebState.IMPACT else self.progress

        curve_pts = self.sample_curve(t_max)
        pts_i = curve_pts.astype(np.int32)

        # thick semi-transparent strand (drawn with the glow color to read soft)
        thick = max(1, int(self.thickness * 2))
        for i in range(len(pts_i) - 1):
            cv2.line(web_layer, tuple(pts_i[i]), tuple(pts_i[i + 1]), glow_color, thick, cv2.LINE_AA)
        # thin bright core
        for i in range(len(pts_i) - 1):
            cv2.line(web_layer, tuple(pts_i[i]), tuple(pts_i[i + 1]), core, max(1, int(self.thickness)), cv2.LINE_AA)

        # branches / fibers, revealed progressively as the main strand travels
        for b in self.branches:
            if b.start_t > t_max:
                continue
            base = self._bezier_point(b.start_t)
            tangent = self._tangent(b.start_t)
            angle = np.arctan2(tangent[1], tangent[0]) + b.angle_offset
            end = base + np.array([np.cos(angle), np.sin(angle)], dtype=np.float32) * b.length
            color = tuple(int(c * b.opacity) for c in core)
            cv2.line(web_layer, tuple(base.astype(np.int32)), tuple(end.astype(np.int32)),
                      color, max(1, int(b.thickness)), cv2.LINE_AA)

        if self.state in (WebState.IMPACT, WebState.ATTACHED):
            self._render_attachment(web_layer, self.target, core, glow_color)

    def _render_attachment(self, layer, point, core, glow_color):
        p = point.astype(np.int32)
        cv2.circle(layer, tuple(p), 4, core, -1, cv2.LINE_AA)
        n_spokes = 6
        for i in range(n_spokes):
            angle = (2 * np.pi / n_spokes) * i
            end = (p + (np.array([np.cos(angle), np.sin(angle)]) * 14)).astype(np.int32)
            cv2.line(layer, tuple(p), tuple(end), glow_color, 1, cv2.LINE_AA)
