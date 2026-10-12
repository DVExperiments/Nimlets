"""JSON save/load with atomic writes and corruption fallback."""
import json
import os
import shutil
import time

SAVE_VERSION = 1


def save_game(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = dict(data)
    data["version"] = SAVE_VERSION
    data["saved_at"] = time.time()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")
    os.replace(tmp, path)
    return True


def load_game(path):
    """Returns the save dict, or None. Falls back to the .bak file if corrupt."""
    for candidate in (path, path + ".bak"):
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "creature" in data:
                return data
        except (OSError, ValueError) as exc:
            print(f"[save] could not read {candidate}: {exc}")
            try:
                shutil.copyfile(candidate, candidate + ".corrupt")
            except OSError:
                pass
    return None


DEFAULT_PREFS = {"theme_hue": "pet", "dark": False, "roam": False, "experimental": True, "mirror": False}


def load_prefs(path):
    prefs = dict(DEFAULT_PREFS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            prefs.update({k: v for k, v in data.items() if k in DEFAULT_PREFS})
    except (OSError, ValueError):
        pass
    return prefs


def save_prefs(path, prefs):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=1)
    except OSError as exc:
        print(f"[prefs] could not save: {exc}")
