"""JSON save/load with atomic writes and corruption fallback.

On a computer, saves are files (written atomically, with a .bak copy). In the web
version (v2.2, running in a browser via pygbag) there are no real files that
survive a reload, so the same functions read and write the browser's own
storage instead, under keys named after the file. Everything above this module
works the same either way.
"""
import json
import os
import shutil
import sys
import time

WEB = sys.platform == "emscripten"
STORE = None          # tests can put a dict-like object here to stand in for browser storage


def _browser_store():
    if STORE is not None:
        return STORE
    if WEB:
        try:
            import platform as _p                  # pygbag exposes the page's window here
            return _p.window.localStorage
        except Exception:
            return None
    return None


def _key(path):
    return "nimlets:" + os.path.basename(path)


def _read(path):
    store = _browser_store()
    if store is not None:
        value = store.getItem(_key(path))
        return None if value is None else str(value)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path, text):
    """Write text, keeping the previous version as path + '.bak'."""
    store = _browser_store()
    if store is not None:
        old = store.getItem(_key(path))
        if old is not None:
            store.setItem(_key(path + ".bak"), old)
        store.setItem(_key(path), text)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")
    os.replace(tmp, path)

SAVE_VERSION = 1


def save_game(path, data):
    data = dict(data)
    data["version"] = SAVE_VERSION
    data["saved_at"] = time.time()
    _write(path, json.dumps(data, indent=1))
    return True


def load_game(path):
    """Returns the save dict, or None. Falls back to the .bak file if corrupt."""
    for candidate in (path, path + ".bak"):
        try:
            text = _read(candidate)
            if text is None:
                continue
            data = json.loads(text)
            if isinstance(data, dict) and "creature" in data:
                return data
        except (OSError, ValueError) as exc:
            print(f"[save] could not read {candidate}: {exc}")
            if _browser_store() is None:
                try:
                    shutil.copyfile(candidate, candidate + ".corrupt")
                except OSError:
                    pass
    return None


# Every preference the game keeps. load_prefs() only keeps keys listed here, so a new
# preference MUST be added here or it is quietly forgotten on the next launch.
DEFAULT_PREFS = {"theme_hue": "pet", "dark": False, "wander": True, "experimental": True, "mirror": False,
                 "shell": "match", "pixel_text": True, "welcomed": False, "hints": False, "hints_seen": []}


def load_prefs(path):
    prefs = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_PREFS.items()}
    try:
        text = _read(path)
        data = json.loads(text) if text else None
        if isinstance(data, dict):
            prefs.update({k: v for k, v in data.items() if k in DEFAULT_PREFS})
    except (OSError, ValueError):
        pass
    return prefs


def save_prefs(path, prefs):
    try:
        _write(path, json.dumps({k: v for k, v in prefs.items() if not k.startswith("_")}, indent=1))
    except OSError as exc:
        print(f"[prefs] could not save: {exc}")
