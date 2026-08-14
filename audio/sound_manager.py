"""Optional sound effects. The app must run fine without any audio files."""
from __future__ import annotations
from pathlib import Path

import config

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class SoundManager:
    """Thin wrapper around pygame.mixer. Fails silently (with a printed note)
    if pygame or the sound files are missing — audio is always optional."""

    def __init__(self, enabled: bool = config.SOUND_ENABLED_DEFAULT):
        self.enabled = enabled and PYGAME_AVAILABLE
        self._sounds = {}

        if enabled and not PYGAME_AVAILABLE:
            print("[audio] 'pygame' is not installed — running without sound. "
                  "Install it with: pip install pygame")

        if self.enabled:
            try:
                pygame.mixer.init()
                self._load("shoot", config.SOUND_SHOOT)
                self._load("impact", config.SOUND_IMPACT)
                self._load("retract", config.SOUND_RETRACT)
            except Exception as exc:
                print(f"[audio] Failed to initialize audio: {exc}. Continuing without sound.")
                self.enabled = False

    def _load(self, key: str, filename: str):
        path = Path(config.SOUND_DIR) / filename
        if path.exists():
            try:
                self._sounds[key] = pygame.mixer.Sound(str(path))
            except Exception as exc:
                print(f"[audio] Could not load {filename}: {exc}")
        else:
            print(f"[audio] Optional sound file not found: {path} "
                  f"(place a royalty-free .wav there to enable it)")

    def play(self, key: str):
        if not self.enabled:
            return
        sound = self._sounds.get(key)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def toggle(self):
        self.enabled = (not self.enabled) and PYGAME_AVAILABLE

    def close(self):
        if self.enabled:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
