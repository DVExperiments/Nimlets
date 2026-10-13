"""Tests for v2.0 "build-ready" changes: saves in a per-user folder with a
one-time copy from the old location, and the test save.
Run:  python -m unittest discover -s tests -v
"""
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

from game import config  # noqa: E402


class DataFolderTests(unittest.TestCase):
    def test_data_folder_per_platform_and_override(self):
        with mock.patch.dict(os.environ, {"NIMLETS_DATA_DIR": "/somewhere/else"}):
            self.assertEqual(config.data_dir(), "/somewhere/else")
        env = {k: v for k, v in os.environ.items() if k != "NIMLETS_DATA_DIR"}
        with mock.patch.dict(os.environ, dict(env, APPDATA="C:\\\\Users\\\\Ari\\\\AppData\\\\Roaming"), clear=True), \
                mock.patch.object(sys, "platform", "win32"):
            self.assertTrue(config.data_dir().endswith("Nimlets"))
            self.assertIn("AppData", config.data_dir())
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "platform", "darwin"):
            self.assertIn(os.path.join("Library", "Application Support", "Nimlets"), config.data_dir())
        with mock.patch.dict(os.environ, dict(env, XDG_DATA_HOME="/xdg"), clear=True), \
                mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(config.data_dir(), os.path.join("/xdg", "Nimlets"))
        self.assertNotEqual(os.path.abspath(config.SAVE_DIR), os.path.abspath(config.LEGACY_SAVE_DIR))

    def test_old_saves_are_copied_once_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as old, tempfile.TemporaryDirectory() as new:
            for name, body in (("savegame.json", {"v": "old"}), ("savegame.json.bak", {}),
                               ("preferences.json", {"dark": True}), ("example_save.json", {})):
                with open(os.path.join(old, name), "w") as f:
                    json.dump(body, f)
            copied = config.migrate_legacy_saves(old, new)
            self.assertEqual(sorted(copied), ["preferences.json", "savegame.json", "savegame.json.bak"])
            self.assertTrue(os.path.exists(os.path.join(old, "savegame.json")))      # originals stay put
            self.assertFalse(os.path.exists(os.path.join(new, "example_save.json")))
            with open(os.path.join(new, "savegame.json"), "w") as f:
                json.dump({"v": "newer"}, f)
            self.assertEqual(config.migrate_legacy_saves(old, new), [])               # only ever once
            with open(os.path.join(new, "savegame.json")) as f:
                self.assertEqual(json.load(f)["v"], "newer")
        with tempfile.TemporaryDirectory() as new:
            self.assertEqual(config.migrate_legacy_saves(os.path.join(new, "missing"), new), [])

    def test_the_game_uses_the_data_folder_and_a_separate_test_save(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d, mock.patch.object(config, "SAVE_DIR", d), \
                mock.patch.object(config, "SAVE_PATH", os.path.join(d, "savegame.json")), \
                mock.patch.object(config, "LEGACY_SAVE_DIR", os.path.join(d, "no-legacy")):
            g = Game(["--mute"])
            self.assertEqual(g.save_path, os.path.join(d, "savegame.json"))
            g.save()
            self.assertTrue(os.path.exists(os.path.join(d, "savegame.json")))
            pygame.quit()
            t = Game(["--mute", "--test-save"])
            self.assertEqual(t.save_path, os.path.join(d, "test_save.json"))
            pygame.quit()


class IconTests(unittest.TestCase):
    def test_icon_draws_at_every_size(self):
        import pygame
        from game.icon import icon_surface
        pygame.init()
        pygame.display.set_mode((1, 1))
        for size in (16, 24, 32, 48, 64, 128, 256):
            img = icon_surface(size)
            self.assertEqual(img.get_size(), (size, size))
            self.assertEqual(img.get_at((0, 0)).a, 0)                       # rounded corners
            self.assertGreaterEqual(img.get_at((size // 2, size // 2)).a, 250)    # solid in the middle
        pygame.quit()

    def test_icon_files_are_valid(self):
        import struct
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import make_icon
        with tempfile.TemporaryDirectory() as d:
            make_icon.main(d)
            with open(os.path.join(d, "icon.ico"), "rb") as f:
                data = f.read()
            reserved, kind, count = struct.unpack("<HHH", data[:6])
            self.assertEqual((reserved, kind, count), (0, 1, len(make_icon.SIZES)))
            for i in range(count):
                w, h, _, _, planes, bits, size, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i: 22 + 16 * i])
                self.assertEqual(data[offset:offset + 8], b"\x89PNG\r\n\x1a\n")     # each entry is a PNG
                self.assertEqual(offset + size <= len(data), True)
            self.assertTrue(os.path.getsize(os.path.join(d, "icon.png")) > 0)
        import pygame
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
