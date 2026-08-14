"""Small alpha-blending helpers used by the renderer."""
import numpy as np


def alpha_blend(base: np.ndarray, overlay: np.ndarray, alpha: float) -> np.ndarray:
    """Blend overlay onto base with a uniform alpha in [0, 1]."""
    return (base.astype(np.float32) * (1 - alpha) + overlay.astype(np.float32) * alpha).astype(np.uint8)
