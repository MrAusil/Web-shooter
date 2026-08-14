"""Lightweight vectorized particle system (NumPy-backed for performance)."""
from __future__ import annotations
from enum import Enum, auto
import numpy as np
import cv2

import config


class ParticleType(Enum):
    WEB_DUST = auto()
    IMPACT_SPARK = auto()
    FIBER = auto()
    GLOW_PARTICLE = auto()


class ParticleSystem:
    """Stores all particles in flat numpy arrays and updates/renders them in bulk."""

    def __init__(self, max_particles: int = config.MAX_PARTICLES):
        self.max_particles = max_particles
        self.positions = np.zeros((max_particles, 2), dtype=np.float32)
        self.velocities = np.zeros((max_particles, 2), dtype=np.float32)
        self.accel = np.zeros((max_particles, 2), dtype=np.float32)
        self.life = np.zeros(max_particles, dtype=np.float32)
        self.max_life = np.zeros(max_particles, dtype=np.float32)
        self.size = np.zeros(max_particles, dtype=np.float32)
        self.color = np.zeros((max_particles, 3), dtype=np.float32)
        self.alive = np.zeros(max_particles, dtype=bool)

    def emit(self, position, count, color, speed_range=(40, 160),
              size_range=(1.5, 3.5), life_range=(0.3, 0.8), spread=np.pi * 2,
              base_angle=0.0, gravity=(0, 60)):
        free_idx = np.where(~self.alive)[0]
        n = min(count, len(free_idx))
        if n <= 0:
            return
        idx = free_idx[:n]
        angles = base_angle + (np.random.rand(n) - 0.5) * spread
        speeds = np.random.uniform(speed_range[0], speed_range[1], size=n)
        self.positions[idx] = position
        self.velocities[idx, 0] = np.cos(angles) * speeds
        self.velocities[idx, 1] = np.sin(angles) * speeds
        self.accel[idx] = gravity
        life = np.random.uniform(life_range[0], life_range[1], size=n)
        self.life[idx] = life
        self.max_life[idx] = life
        self.size[idx] = np.random.uniform(size_range[0], size_range[1], size=n)
        self.color[idx] = color
        self.alive[idx] = True

    def update(self, dt: float):
        active = self.alive
        if not np.any(active):
            return
        self.velocities[active] += self.accel[active] * dt
        self.positions[active] += self.velocities[active] * dt
        self.life[active] -= dt
        expired = active & (self.life <= 0)
        self.alive[expired] = False

    def render(self, layer: np.ndarray):
        active = np.where(self.alive)[0]
        for i in active:
            alpha = max(0.0, min(1.0, self.life[i] / self.max_life[i]))
            pos = (int(self.positions[i, 0]), int(self.positions[i, 1]))
            r = max(1, int(self.size[i] * alpha + 1))
            color = tuple(int(c) for c in self.color[i])
            cv2.circle(layer, pos, r, color, -1, lineType=cv2.LINE_AA)

    def count(self) -> int:
        return int(np.sum(self.alive))
