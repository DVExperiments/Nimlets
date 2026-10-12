"""Configuration loading and shared constants."""
import copy
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
SAVE_DIR = os.path.join(ROOT_DIR, "saves")
SAVE_PATH = os.path.join(SAVE_DIR, "savegame.json")
PREFS_PATH = os.path.join(SAVE_DIR, "preferences.json")   # survives resets

# The retro "LCD" is drawn at this logical resolution and scaled up by an
# integer factor for pixel-perfect output.
LCD_W, LCD_H = 160, 112
FLOOR_Y = 100          # y of the creature's feet on the LCD
X_MIN, X_MAX = 24, 136  # walkable range for the creature's centre

DEFAULT_SETTINGS = {
    "window_width": 960,
    "window_height": 760,
    "fps": 30,
    "heart_slots": 6,
    "sound_enabled": True,
    "base_time_scale": 1.0,
    "allow_test_speeds": True,
    "test_speeds": [1, 10, 60, 600, 3600],
    "offline_cap_hours": 8.0,
    "autosave_seconds": 60,
    "hemisphere": "north",
    "stage_hours": {"egg": 0.05, "baby": 1.0, "child": 24.0, "teen": 48.0,
                    "adult": 144.0, "elder": 72.0},
    "new_generation_min_adult_hours": 24.0,
    "decay_per_hour": {"hunger": 9.0, "happiness": 7.0, "hygiene": 5.0,
                       "energy_awake": 5.0, "energy_sleep_recover": 15.0},
    "baby_decay_multiplier": 3.0,
    "poop_interval_hours": 3.0,
    "attention_timeout_minutes": 15,
    "lights_timeout_minutes": 30,
    "fake_call_chance_per_hour": 0.35,
    "bedtimes": {"baby": [19, 8], "child": [20, 8], "teen": [21, 8],
                 "adult": [22, 8], "elder": [20, 9]},
}


def _merge(base, override):
    for key, value in override.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_settings(path=None):
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    path = path or os.path.join(CONFIG_DIR, "settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _merge(settings, json.load(f))
    except (OSError, ValueError) as exc:
        print(f"[config] using default settings ({exc})")
    return settings


def load_species(path=None):
    path = path or os.path.join(CONFIG_DIR, "species.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {sp["id"]: sp for sp in data["species"]}
