# Spider-Web FX

Real-time, webcam-driven Spider-Man-style web-shooter VFX. Point your hand at
the camera, make the web-shooter gesture, and a procedurally animated,
glowing web launches from your hand in the direction you're pointing.

This is a real-time computer-vision + procedural graphics project, not a
static overlay: webs are generated frame-by-frame from curves, branches, a
particle system, and a glow pipeline — no image assets.

## Project Overview

The app tracks your hand with MediaPipe, recognizes a specific web-shooter
hand pose using multiple geometric conditions (not a single landmark check),
and drives a small real-time VFX engine that spawns, animates, and retires
"web projectiles." Each web has its own procedural curved trajectory, branch
geometry, glow, particles, and a full lifecycle (travel → impact → attached →
retract).

## Features

- Real-time hand tracking (up to two hands) via MediaPipe Hands
- Dedicated gesture recognizer with debouncing, confidence accumulation, and
  cooldown — supports rapid-fire shots and a **hold-to-charge power shot**
- Procedural web geometry: curved (Bezier) main strand, branching secondary
  strands, thin fibers, and an attachment burst — all seeded per shot so the
  shape is stable across frames but different every time
- Layered glow pipeline (blur at reduced resolution + additive blend + sharp
  core on top) for a soft cinematic look without killing performance
- Vectorized NumPy particle system (dust while traveling, sparks on impact)
- Subtle screen shake on impact and a fading motion trail
- Five selectable web styles (classic, silver, electric, dark, venom)
- Two-hand support with independent gesture state per hand
- Minimal HUD (status, hand/gesture state, active web count, FPS) + optional
  debug overlay (landmarks, confidence, frame time)
- Optional sound effects (works perfectly with no audio files present)
- Recording (`.mp4`) and screenshot (`.png`) capture
- Config-driven: every threshold, color, speed, and limit lives in `config.py`

## Tech Stack

- Python 3.10–3.12
- OpenCV (`opencv-python`) — capture, drawing, compositing, glow, video I/O
- MediaPipe Hands — 21-point hand landmark tracking
- NumPy — vectorized particle simulation and curve math
- pygame (optional) — sound effects

## Installation

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

## Requirements

- A working webcam
- Python 3.10–3.12 (MediaPipe's legacy `solutions` API, used here, is not
  available on newer MediaPipe releases — see the note in
  `requirements.txt`; pip will install a compatible version automatically)
- See `requirements.txt` for pinned package versions

## How to Run

```bash
python main.py
```

On launch you'll see a short startup log, then the camera window opens.
Perform the gesture described below to shoot webs.

## Controls

| Key | Action |
|---|---|
| `Q` / `Esc` | Quit |
| `R` | Reset — clear all active webs |
| `Space` | Manual web shot (no gesture needed, for quick testing) |
| `M` | Toggle mirror |
| `G` | Toggle gesture visualization ("WEB READY" / "WEB SHOOT!" text) |
| `H` | Toggle HUD |
| `1` | Classic white web |
| `2` | Electric web |
| `3` | Dark web |
| `T` | Toggle motion trails |
| `S` | Toggle sound |
| `F` | Toggle fullscreen |
| `V` | Start/stop recording to `recordings/` |
| `P` | Save a screenshot to `screenshots/` |

## Gesture Instructions

The default gesture is a relaxed **"rock on" pose**: thumb, index finger, and
pinky extended, with the middle and ring fingers folded into the palm. It's
recognized using several independent geometric checks (finger extension
ratios for each finger, and thumb distance from the palm) rather than a
single landmark distance, so it's fairly robust to hand size and small
tracking jitter.

- Hold the pose steadily for a few frames to fire a web
- Keep holding to rapid-fire additional webs
- **Hold for over a second, then release**, to trigger a bigger, faster
  **power shot**
- The web travels in the direction from your wrist toward your index
  fingertip — point where you want it to go
- Works with either hand, and both hands at once

If detection feels too strict or too loose for your hand/camera, adjust the
thresholds in `config.py` (see below).

## Configuration

All tunable values live in `config.py` — nothing is hard-coded elsewhere.
Notable groups:

- **Camera**: `CAMERA_INDEX`, `CAMERA_WIDTH/HEIGHT`, fallback resolution
- **Gesture thresholds**: `INDEX_EXTENSION_THRESHOLD`, `FINGER_FOLD_THRESHOLD`,
  `THUMB_POSITION_THRESHOLD`, `GESTURE_CONFIDENCE_THRESHOLD`,
  `GESTURE_HOLD_FRAMES`, `GESTURE_COOLDOWN_SECONDS`, `POWER_SHOT_HOLD_SECONDS`
- **Web behavior**: `MAX_ACTIVE_WEBS`, `WEB_BASE_SPEED`, distance range,
  lifetime, retraction duration, branch count range, thickness
- **Glow**: `GLOW_DOWNSCALE`, `GLOW_BLUR_KERNEL`, `GLOW_INTENSITY`
- **Particles**: `MAX_PARTICLES`, `IMPACT_PARTICLES`
- **Screen shake / trails**: enable flags + strength/decay
- **Styles**: `WEB_STYLES` dict — add your own by adding a `{"core": ..., "glow": ...}` entry
- **Audio / HUD / Debug**: default enabled states

## Troubleshooting

- **"Could not open webcam"** — make sure no other app (Zoom, Teams, another
  Python process) is holding the camera, and that `CAMERA_INDEX` in
  `config.py` matches your device (try `0`, `1`, `2`...).
- **"Hand tracking unavailable"** — MediaPipe failed to import/initialize.
  Reinstall with `pip install -r requirements.txt` inside your virtual
  environment. The app still runs and shows the camera feed without this,
  it just won't detect gestures.
- **Gesture won't trigger** — try better lighting and keep your hand fully
  in frame; loosen `GESTURE_CONFIDENCE_THRESHOLD` or the per-finger
  thresholds in `config.py`. Turn on debug mode (see below) to watch the
  live confidence score.
- **Low FPS** — lower `CAMERA_WIDTH/HEIGHT`, reduce `GLOW_BLUR_KERNEL`,
  lower `MAX_PARTICLES`/`MAX_ACTIVE_WEBS`.
- **No sound** — this is expected out of the box. Sound is fully optional;
  drop `web_shoot.wav`, `web_impact.wav`, and `web_retract.wav` (any
  royalty-free `.wav` files — e.g. from freesound.org or opengameart.org)
  into `assets/sounds/` to enable it.
- **Recording fails to start** — check that `recordings/` is writable and
  that OpenCV's `mp4v` codec is available on your platform; if not, edit
  the fourcc in `main.py`'s `_toggle_recording`.

To enable the debug overlay (landmarks, per-finger confidence, frame time),
set `DEBUG_MODE_DEFAULT = True` in `config.py`.

## Architecture

```
spider_web_fx/
├── main.py                  # Application class: main loop, input, wiring
├── config.py                # All tunables in one place
│
├── camera/
│   └── camera_manager.py    # Webcam open/read/mirror/fallback/FPS
│
├── tracking/
│   ├── hand_tracker.py      # MediaPipe wrapper -> HandState per hand
│   ├── gesture_detector.py  # Pose scoring, debouncing, power-shot timing
│   └── landmark_utils.py    # Geometry helpers, landmark index constants
│
├── vfx/
│   ├── web_engine.py        # Owns all active webs + shared particle system
│   ├── web.py                # WebProjectile: curve, branches, state machine
│   ├── web_branch.py        # Branch dataclass (re-exported from web.py)
│   ├── particles.py         # Vectorized NumPy particle system
│   ├── impact.py            # Impact burst helper
│   └── glow.py               # Blur + additive-blend glow compositing
│
├── rendering/
│   ├── renderer.py          # Orchestrates VFX -> screen shake -> HUD
│   ├── compositing.py       # Alpha-blend helper
│   └── effects.py           # Screen shake + motion trail
│
├── audio/
│   └── sound_manager.py     # Optional pygame.mixer wrapper
│
├── ui/
│   └── hud.py                # HUD + debug overlay drawing
│
├── assets/sounds/           # Drop your own .wav files here (optional)
├── recordings/               # .mp4 output from the V key
├── screenshots/              # .png output from the P key
├── tests/test_core.py        # Plain-assert tests for the non-visual logic
├── requirements.txt
└── .gitignore
```

## Future Improvements

- Scene-aware targeting (attach webs to detected edges/corners instead of a
  fixed pseudo-depth distance)
- Full web-swing simulation with simple physics on the attachment point
- GPU-accelerated glow via OpenGL/shader compositing for higher resolutions
- On-screen gesture calibration wizard instead of editing `config.py` by hand
- Combo/achievement system beyond the current simple combo counter

## Notes on Assets

No copyrighted movie footage, logos, character art, or soundtracks are used
or required. Every visual is generated procedurally with OpenCV/NumPy; audio
is optional and expects your own royalty-free `.wav` files.
