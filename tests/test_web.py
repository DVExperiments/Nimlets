"""Tests for v2.2's web-ready changes: the async main loop, saving to the browser's
storage, and the game running in "web mode". A plain dict stands in for the
browser's localStorage, so these run anywhere.
Run:  python -m unittest discover -s tests -v
"""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NIMLETS_SKIP_WELCOME", "1")   # tests start lots of new games

import pygame  # noqa: E402

from game import config, save  # noqa: E402


class FakeLocalStorage:
    """The two calls the game makes on a browser's window.localStorage."""

    def __init__(self):
        self.items = {}

    def getItem(self, key):                      # noqa: N802 (the browser's own name)
        return self.items.get(key)

    def setItem(self, key, value):               # noqa: N802
        self.items[key] = str(value)


class BrowserStorageTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeLocalStorage()
        patcher = mock.patch.object(save, "STORE", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_saves_and_preferences_go_to_browser_storage_not_files(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "savegame.json")
            save.save_game(path, {"creature": {"name": "Ari"}})
            save.save_game(path, {"creature": {"name": "Bo"}})
            self.assertEqual(os.listdir(d), [])                                  # no files at all
            self.assertEqual(save.load_game(path)["creature"]["name"], "Bo")
            self.assertIn("nimlets:savegame.json.bak", self.store.items)        # the previous save is kept
            save.save_prefs(os.path.join(d, "preferences.json"), {"dark": True, "shell": "tide", "_web": True})
            prefs = save.load_prefs(os.path.join(d, "preferences.json"))
            self.assertEqual((prefs["dark"], prefs["shell"]), (True, "tide"))
            self.assertNotIn("_web", json.loads(self.store.items["nimlets:preferences.json"]))

    def test_a_damaged_save_falls_back_to_the_backup(self):
        save.save_game("/data/savegame.json", {"creature": {"name": "Ari"}})
        save.save_game("/data/savegame.json", {"creature": {"name": "Bo"}})
        self.store.items["nimlets:savegame.json"] = "{ not json"
        self.assertEqual(save.load_game("/data/savegame.json")["creature"]["name"], "Ari")
        self.assertIsNone(save.load_game("/data/nothing.json"))


class WebModeGameTests(unittest.TestCase):
    def test_the_game_in_web_mode(self):
        from game.app import Game
        store = FakeLocalStorage()
        with mock.patch.object(save, "STORE", store), mock.patch.object(config, "WEB", True):
            g = Game(["--save", "/data/savegame.json", "--mute"])
            name = g.c.name
            g.save()
            self.assertIn("nimlets:savegame.json", store.items)
            g.toggle("settings")
            g.draw()
            self.assertIsNone(g.ui.hit.get("folder_btn"))                    # no folders in a browser
            self.assertIsNotNone(g.ui.hit.get("tour_btn"))
            g.open_data_folder()
            self.assertIn("browser", g.message)
            g.panel = None
            g.export_observation()
            self.assertIn("browser version", g.message)
            pygame.quit()
            g2 = Game(["--save", "/data/savegame.json", "--mute"])         # reopening the page
            self.assertEqual(g2.c.name, name)
            pygame.quit()

    def test_the_async_loop_runs_frames_and_saves(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            g = Game(["--save", path, "--mute", "--smoke-test", "25"])
            asyncio.run(g.run_async())
            self.assertEqual(g.frames, 25)
            self.assertTrue(os.path.exists(path))

    def test_focus_loss_saves(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            g = Game(["--save", path, "--mute"])
            self.assertFalse(os.path.exists(path))
            g.handle(pygame.event.Event(getattr(pygame, "WINDOWFOCUSLOST")))
            self.assertTrue(os.path.exists(path))
            pygame.quit()

    def test_the_web_build_packs_only_the_game(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import build_web
        with tempfile.TemporaryDirectory() as d, mock.patch.object(build_web, "STAGE", os.path.join(d, "nimlets")):
            pygame.init()
            pygame.display.set_mode((1, 1))
            names = build_web.stage()
            self.assertEqual(names, ["config", "favicon.png", "game", "main.py"])
            packed = os.listdir(os.path.join(d, "nimlets", "game"))
            self.assertIn("app.py", packed)
            self.assertNotIn("__pycache__", packed)
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
