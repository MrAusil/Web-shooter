"""Impact burst effect helper — spawns particles and reports screen-shake strength."""
import numpy as np
import config
from vfx.particles import ParticleSystem


class ImpactEffect:
    """Stateless helper: triggers a particle burst at an impact point."""

    @staticmethod
    def trigger(particle_system: ParticleSystem, position: np.ndarray, style: dict,
                 power: bool = False) -> float:
        count = config.IMPACT_PARTICLES * (2 if power else 1)
        particle_system.emit(
            position, count, style["glow"],
            speed_range=(60, 220) if not power else (120, 340),
            size_range=(1.5, 4.0) if not power else (2.5, 6.0),
            life_range=(0.25, 0.55),
            spread=np.pi * 2,
            gravity=(0, 40),
        )
        return config.SCREEN_SHAKE_STRENGTH * (2.0 if power else 1.0)
