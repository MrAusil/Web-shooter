"""Cinematic glow post-processing."""
import cv2
import numpy as np
import config


def apply_glow(base_bgr: np.ndarray, web_layer: np.ndarray) -> np.ndarray:
    """
    Render web_layer at reduced resolution, blur it, and additively blend it
    back onto base_bgr for a soft cinematic glow, then composite the sharp
    web_layer on top so cores stay crisp. Rendering the blur at reduced
    resolution keeps this cheap enough for real time.
    """
    h, w = base_bgr.shape[:2]
    small_w = max(1, int(w * config.GLOW_DOWNSCALE))
    small_h = max(1, int(h * config.GLOW_DOWNSCALE))

    small = cv2.resize(web_layer, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    k = config.GLOW_BLUR_KERNEL | 1  # ensure odd kernel size
    blurred = cv2.GaussianBlur(small, (k, k), 0)
    glow = cv2.resize(blurred, (w, h), interpolation=cv2.INTER_LINEAR)

    out = cv2.addWeighted(base_bgr, 1.0, glow, config.GLOW_INTENSITY, 0)

    mask = cv2.cvtColor(web_layer, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(mask, 10, 255, cv2.THRESH_BINARY)
    mask_3 = cv2.merge([mask, mask, mask]).astype(np.float32) / 255.0
    out = (out.astype(np.float32) * (1 - mask_3) + web_layer.astype(np.float32) * mask_3).astype(np.uint8)
    return out
