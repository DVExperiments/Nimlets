"""Tests for v2.6's home page: the site that GitHub Pages serves, with the game in play/.
The game itself is built by pygbag, which needs the internet, so a small stand-in
"built game" is used here; everything this project adds around it is real.
Run:  python -m unittest discover -s tests -v
"""
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import build_web  # noqa: E402
from game import config, save  # noqa: E402
from game.config import load_species  # noqa: E402
from game.version import VERSION  # noqa: E402

FAKE_GAME_PAGE = """<!doctype html>
<html><HEAD><title>Nimlets</title><link rel="icon" href="favicon.png"></HEAD>
<body><canvas id="canvas"></canvas></body></html>
"""


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        game = os.path.join(cls.tmp.name, "game_build")
        os.makedirs(game)
        for name, text in (("index.html", FAKE_GAME_PAGE), ("nimlets.apk", "apk"), ("favicon.png", "png")):
            with open(os.path.join(game, name), "w", encoding="utf-8") as f:
                f.write(text)
        cls.out = build_web.assemble(game, os.path.join(cls.tmp.name, "web"))
        with open(os.path.join(cls.out, "index.html"), encoding="utf-8") as f:
            cls.home = f.read()
        with open(os.path.join(cls.out, "play", "index.html"), encoding="utf-8") as f:
            cls.play = f.read()
        with open(os.path.join(cls.out, "manifest.webmanifest"), encoding="utf-8") as f:
            cls.manifest = json.load(f)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        cls.tmp.cleanup()

    def test_home_page_on_top_and_the_game_in_play(self):
        self.assertEqual(sorted(os.listdir(self.out)), ["img", "index.html", "manifest.webmanifest", "play"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.out, "play"))), ["favicon.png", "index.html", "nimlets.apk"])
        self.assertIn('href="play/"', self.home)
        self.assertNotIn("{{", self.home)
        self.assertIn(f"v{VERSION}", self.home)
        self.assertIn('<svg class="wordmark-art"', self.home)

    def test_every_local_file_the_home_page_uses_exists(self):
        refs = re.findall(r'(?:src|href)="([^"#]+)"', self.home)
        local = [r for r in refs if not r.startswith(("http:", "https:", "mailto:"))]
        self.assertGreater(len(local), 30)
        for ref in local:
            path = os.path.join(self.out, ref)
            if ref.endswith("/"):
                path = os.path.join(path, "index.html")
            self.assertTrue(os.path.exists(path), ref)
        for ref in refs:                              # nothing loaded from elsewhere, like the game itself
            if ref.startswith("http"):
                self.assertTrue(ref.startswith("https://github.com/DVExperiments/Nimlets"), ref)

    def test_the_collection_shows_every_form_with_secrets_kept_secret(self):
        db = load_species()
        tiles = re.findall(r'<li class="(found|unknown|secret)"><img src="img/([^"]+)" alt="([^"]*)"', self.home)
        self.assertEqual(len(tiles), len(db))
        self.assertEqual(sum(1 for t in tiles if t[0] == "secret"), sum(1 for s in db.values() if s.get("secret")))
        found = [t for t in tiles if t[0] == "found"]
        self.assertEqual(len(found), len(build_web.GROWTH) - 1)              # every growth stage but the egg
        for kind, src, alt in tiles:
            if kind != "found":
                self.assertNotIn(alt.lower(), {s.get("name", "").lower() for s in db.values()})
        self.assertIn(f"{len(db)} forms to find", self.home)
        self.assertNotIn(">celestine<", self.home.lower())                   # no secret names on the page

    def test_pictures_are_drawn_at_the_right_sizes(self):
        img = os.path.join(self.out, "img")
        for size in build_web.ICON_SIZES:
            self.assertEqual(pygame.image.load(os.path.join(img, f"icon-{size}.png")).get_size(), (size, size))
        for sid in build_web.GROWTH:
            self.assertEqual(pygame.image.load(os.path.join(img, f"grow-{sid}.png")).get_size(), (32, 32))
        self.assertEqual(pygame.image.load(os.path.join(img, "secret.png")).get_size(), (32, 32))

    def test_the_manifest_makes_it_an_installable_app_that_opens_the_game(self):
        m = self.manifest
        self.assertEqual((m["name"], m["start_url"], m["scope"], m["display"]), ("Nimlets", "./play/", "./", "standalone"))
        sizes = {i["sizes"] for i in m["icons"]}
        self.assertTrue({"192x192", "512x512"} <= sizes)                     # what Chrome asks for
        for icon in m["icons"]:
            self.assertTrue(os.path.exists(os.path.join(self.out, icon["src"])), icon["src"])
        self.assertIn('rel="manifest" href="manifest.webmanifest"', self.home)
        self.assertIn('rel="apple-touch-icon" href="img/icon-180.png"', self.home)

    def test_the_game_page_gets_the_app_extras_inside_its_head(self):
        self.assertEqual(self.play.count(build_web.HEAD_MARK), 1)
        head_end = self.play.lower().index("</head>")
        self.assertLess(self.play.index(build_web.HEAD_MARK), head_end)
        self.assertIn('href="../manifest.webmanifest"', self.play)
        self.assertTrue(os.path.exists(os.path.join(self.out, "play", "..", "img", "icon-180.png")))
        self.assertIn("navigator.storage", self.play)
        self.assertIn("pointerdown", self.play)                              # asked on the first tap, not on load
        self.assertIn('<canvas id="canvas">', self.play)                     # the game's own page is otherwise unchanged

    def test_the_home_page_reads_the_same_save_the_game_writes(self):
        key = save._key(config.SAVE_PATH)
        self.assertIn(f'getItem("{key}")', self.home)


class AssemblyTests(unittest.TestCase):
    def tearDown(self):
        pygame.quit()

    def test_app_head_goes_in_once_even_without_a_head(self):
        once = build_web.add_app_head("<html><head></head><body></body></html>")
        self.assertEqual(build_web.add_app_head(once), once)
        self.assertTrue(once.index(build_web.HEAD_MARK) < once.index("</head>"))
        bare = build_web.add_app_head("<canvas></canvas>")
        self.assertTrue(bare.startswith(build_web.HEAD_MARK))

    def test_an_unfilled_placeholder_stops_the_build(self):
        self.assertEqual(build_web.render_page("v{{VERSION}}", {"VERSION": "1"}), "v1")
        with self.assertRaises(ValueError):
            build_web.render_page("{{VERSION}} {{MYSTERY}}", {"VERSION": "1"})

    def test_site_only_needs_no_pygbag(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(build_web, "OUT", os.path.join(d, "web")), \
                mock.patch.object(build_web.subprocess, "run", side_effect=AssertionError("pygbag ran")), \
                mock.patch("builtins.print"):
            out = build_web.assemble(None, os.path.join(d, "web"))
            with open(os.path.join(out, "play", "index.html"), encoding="utf-8") as f:
                stand_in = f.read()
            self.assertIn("stand-in", stand_in)
            self.assertIn(build_web.HEAD_MARK, stand_in)

    def test_the_workflow_publishes_what_the_build_makes(self):
        with open(os.path.join(ROOT, ".github", "workflows", "build-web.yml"), encoding="utf-8") as f:
            wf = f.read()
        self.assertIn("python tools/build_web.py", wf)
        self.assertIn("path: dist/web", wf)
        self.assertEqual(os.path.relpath(build_web.OUT, ROOT).replace(os.sep, "/"), "dist/web")


if __name__ == "__main__":
    unittest.main()
