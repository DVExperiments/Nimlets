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


class WebStartupTests(unittest.TestCase):
    def test_main_py_runs_without___file__(self):
        """pygbag may run main.py without __file__ set; the web branch must still start the game."""
        import game.app as app
        started = []

        async def fake_main(argv=None):
            started.append(argv)

        with open(os.path.join(ROOT, "main.py"), encoding="utf-8") as f:
            code = compile(f.read(), "main.py", "exec")
        with mock.patch.object(sys, "platform", "emscripten"), mock.patch.object(app, "main_async", fake_main), \
                mock.patch("builtins.print"):
            exec(code, {"__name__": "__main__"})                 # note: no __file__ here
        self.assertEqual(started, [[]])

    def test_main_py_has_pygbags_standard_shape_and_does_nothing_when_imported(self):
        with open(os.path.join(ROOT, "main.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("async def main():", src)
        self.assertTrue(src.rstrip().endswith("asyncio.run(main())"))            # pygbag looks for this
        code = compile(src, "main.py", "exec")
        import game.app as app
        with mock.patch.object(app, "main", lambda *a: self.fail("started on import")):
            exec(code, {"__name__": "main"})                                     # imported, not run

    def test_a_failure_loading_the_game_code_is_shown(self):
        with open(os.path.join(ROOT, "main.py"), encoding="utf-8") as f:
            code = compile(f.read(), "main.py", "exec")
        import builtins
        real_import = builtins.__import__
        shown = []

        def broken_import(name, *a, **k):
            if name == "game.app":
                raise ImportError("pretend the game's code is broken")
            return real_import(name, *a, **k)

        async def fast_sleep(*a):
            raise asyncio.CancelledError                 # stop the "keep it on screen" loop at once

        g = {"__name__": "__main__"}
        with mock.patch.object(sys, "platform", "emscripten"), mock.patch("builtins.__import__", broken_import), \
                mock.patch("builtins.print", lambda *a, **k: shown.append(a)), \
                mock.patch("asyncio.sleep", fast_sleep):
            with self.assertRaises(asyncio.CancelledError):
                exec(code, g)
        self.assertTrue(any("[nimlets] the game" in str(a) and "code" in str(a) for a in shown), shown)
        screen = pygame.display.get_surface()
        self.assertIsNotNone(screen)
        self.assertEqual(screen.get_at((2, 2))[:3], (43, 34, 64))               # the error page, not grey
        pygame.quit()

    def test_a_startup_crash_is_shown_on_screen(self):
        import game.app as app

        def boom(*a, **k):
            raise RuntimeError("pretend startup crash")

        with mock.patch.object(app, "Game", boom), mock.patch("builtins.print"):
            asyncio.run(app.main_async([], error_frames=2))
        screen = pygame.display.get_surface()
        self.assertIsNotNone(screen)
        self.assertNotEqual(screen.get_at((5, 5))[:3], (128, 128, 128))   # not a blank grey page
        colours = {tuple(screen.get_at((x, 40))[:3]) for x in range(20, 400)}
        self.assertGreater(len(colours), 1)                               # some text was drawn
        pygame.quit()


class FakeConsole:
    def __init__(self):
        self.lines = []

    def log(self, msg):
        self.lines.append(("log", str(msg)))

    def error(self, msg):
        self.lines.append(("error", str(msg)))


class FakeWindow:
    def __init__(self):
        self.console = FakeConsole()
        self.localStorage = FakeLocalStorage()


class WebStartupPathTests(unittest.TestCase):
    def test_the_whole_web_start_up_reports_progress_to_the_console(self):
        import platform
        import game.app as app
        win = FakeWindow()
        with mock.patch.object(platform, "window", win, create=True), mock.patch.object(config, "WEB", True), \
                mock.patch.object(save, "WEB", True), mock.patch.object(save, "STORE", None):
            asyncio.run(app.main_async(["--save", "/data/savegame.json", "--smoke-test", "12"]))
        said = [m for kind, m in win.console.lines]
        for step in ("[nimlets] starting", "window ready", "sound ready", "new egg", "game ready",
                     "first frame drawn", "running: 1 frames"):
            self.assertTrue(any(step in m for m in said), step)
        self.assertFalse([m for kind, m in win.console.lines if kind == "error"])
        self.assertIn("nimlets:savegame.json", win.localStorage.items)      # saved to the browser

    def test_web_start_up_reuses_the_canvas_and_makes_sounds_lazily(self):
        import platform
        from game.app import Game
        with mock.patch.object(platform, "window", FakeWindow(), create=True), mock.patch.object(config, "WEB", True):
            pygame.init()
            canvas = pygame.display.set_mode((960, 760))
            g = Game(["--save", "/data/savegame.json"])
            self.assertIs(pygame.display.get_surface(), canvas)                # not replaced
            self.assertTrue(g.audio.lazy)
            if g.audio.ok:
                self.assertEqual(g.audio.sounds, {})                         # nothing made up front
                g.audio.play("page")
                self.assertIn("page", g.audio.sounds)                         # made when first needed
            pygame.quit()

    def test_desktop_still_makes_all_sounds_up_front(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json")])
            self.assertFalse(g.audio.lazy)
            if g.audio.ok:
                self.assertGreaterEqual(len(g.audio.sounds), 20)
            pygame.quit()
