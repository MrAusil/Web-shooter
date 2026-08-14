"""
Central configuration for Spider-Web FX.
Tune every knob here instead of scattering magic numbers through the code.
"""
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SOUND_DIR = ASSETS_DIR / "sounds"
RECORDINGS_DIR = BASE_DIR / "recordings"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# --- Camera ---
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FALLBACK_WIDTH = 640
CAMERA_FALLBACK_HEIGHT = 480
TARGET_FPS = 30
MIRROR_DEFAULT = True

# --- Hand tracking ---
MAX_NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.6
MIN_TRACKING_CONFIDENCE = 0.5

# --- Gesture thresholds ---
INDEX_EXTENSION_THRESHOLD = 0.55
FINGER_FOLD_THRESHOLD = 0.35
THUMB_POSITION_THRESHOLD = 0.4
GESTURE_CONFIDENCE_THRESHOLD = 0.75
GESTURE_HOLD_FRAMES = 4               # consecutive frames required to trigger
GESTURE_COOLDOWN_SECONDS = 0.18
POWER_SHOT_HOLD_SECONDS = 1.0
DOUBLE_SHOT_WINDOW_SECONDS = 0.5

# --- Smoothing ---
ORIGIN_SMOOTHING = 0.5
DIRECTION_SMOOTHING = 0.4

# --- Web behaviour ---
MAX_ACTIVE_WEBS = 20
WEB_BASE_SPEED = 2200.0        # px/sec
WEB_MAX_DISTANCE = 1400.0
WEB_MIN_DISTANCE = 250.0
WEB_LIFETIME_ATTACHED = 1.4
WEB_RETRACT_DURATION = 0.35
WEB_IMPACT_DURATION = 0.35
WEB_BRANCH_COUNT_RANGE = (3, 6)
WEB_THICKNESS = 3
WEB_ORIGIN_OFFSET = (0, 10)

# --- Glow ---
GLOW_DOWNSCALE = 0.35
GLOW_BLUR_KERNEL = 21
GLOW_INTENSITY = 0.55

# --- Particles ---
MAX_PARTICLES = 400
IMPACT_PARTICLES = 26

# --- Screen shake ---
SCREEN_SHAKE_ENABLED = True
SCREEN_SHAKE_STRENGTH = 4  # pixels

# --- Trails ---
TRAIL_ENABLED = True
TRAIL_DECAY = 0.85

# --- Colors (BGR) ---
STYLE_CLASSIC_WHITE = {"core": (255, 255, 255), "glow": (255, 250, 235)}
STYLE_SILVER        = {"core": (220, 220, 210), "glow": (200, 200, 190)}
STYLE_ELECTRIC      = {"core": (255, 235, 80),  "glow": (255, 180, 40)}
STYLE_DARK_WEB      = {"core": (90, 90, 90),    "glow": (40, 40, 40)}
STYLE_VENOM         = {"core": (60, 20, 90),    "glow": (120, 10, 160)}

WEB_STYLES = {
    "classic": STYLE_CLASSIC_WHITE,
    "silver": STYLE_SILVER,
    "electric": STYLE_ELECTRIC,
    "dark": STYLE_DARK_WEB,
    "venom": STYLE_VENOM,
}
DEFAULT_STYLE = "classic"

# --- Audio ---
SOUND_ENABLED_DEFAULT = True
SOUND_SHOOT = "web_shoot.wav"
SOUND_IMPACT = "web_impact.wav"
SOUND_RETRACT = "web_retract.wav"

# --- HUD ---
HUD_ENABLED_DEFAULT = True
HUD_FONT_SCALE = 0.55
HUD_COLOR = (255, 255, 255)

# --- Debug ---
DEBUG_MODE_DEFAULT = False
