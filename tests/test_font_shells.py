"""Tests for v1.9: the pixel font, the eight new shells, and every screen
drawing cleanly in both text styles at several window sizes.
Run:  python -m unittest discover -s tests -v
"""
import os
import random
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NIMLETS_SKIP_WELCOME", "1")   # tests start lots of new games

import pygame  # noqa: E402

from game import config, evolution, genetics, shells  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.pixelfont import GLYPHS, ROWS, PixelFont, normalise, scale_for  # noqa: E402
from game.records import Records  # noqa: E402

SPECIES = config.load_species()


class PixelFontTests(unittest.TestCase):
    def setUp(self):
        pygame.init()

    def test_every_glyph_is_well_formed(self):
        for ch, g in GLYPHS.items():
            with self.subTest(ch=ch):
                self.assertEqual(len(g), ROWS)
                self.assertEqual(len({len(row) for row in g}), 1)       # rectangular
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?:;'\"-+=()/%&*<>_\u00b7\u00d7":
            self.assertIn(ch, GLYPHS, ch)

    def test_size_matches_render_at_every_scale(self):
        text = "Luri ate the Fish \u00b7 x2!"
        for size in (9, 12, 16, 22, 32):
            for bold in (False, True):
                f = PixelFont(size, bold)
                img = f.render(text, True, (10, 20, 30))
                self.assertEqual(img.get_size(), f.size(text))
                self.assertEqual(img.get_height(), f.get_height())
        self.assertEqual([scale_for(s) for s in (8, 12, 16, 24)], [1, 2, 2, 3])

    def test_unknown_characters_are_stood_in_for(self):
        self.assertEqual(normalise("\u201cHi\u201d\u2014ok\u2026"), '"Hi"-ok...')
        self.assertEqual(normalise("caf\u00e9 \u2603"), "caf? ?")
        PixelFont(16).render("\u00e9\u2603 \u4e2d", True, (0, 0, 0))          # never raises

    def test_pixels_are_crisp(self):
        img = PixelFont(16).render("I", True, (255, 0, 0))
        colours = {tuple(img.get_at((x, y))) for x in range(img.get_width()) for y in range(img.get_height())}
        self.assertTrue(colours <= {(255, 0, 0, 255), (0, 0, 0, 0)})        # no blended edges


class NewShellTests(unittest.TestCase):
    def records(self, gens=1, rare=()):
        r = Records()
        r.lineage = [{"generation": i, "name": "X", "forms": [], "final": "bobbit", "final_name": "Bobbit",
                      "days": 3, "care_mistakes": 0, "reason": "elder", "hue": 0, "mutation": None}
                     for i in range(1, gens)]
        for m in rare:
            r.note_mutation(m)
        return r

    def test_generation_milestones(self):
        self.assertNotIn("patchwork", shells.unlocked(self.records(2)))
        self.assertIn("patchwork", shells.unlocked(self.records(3)))
        have = shells.unlocked(self.records(5))
        self.assertIn("heirloom", have)
        self.assertNotIn("familytree", have)
        self.assertIn("familytree", shells.unlocked(self.records(10)))

    def test_rare_eggs(self):
        have = shells.unlocked(self.records(rare=("shiny", "midnight", "chimera", "pastel", "glitch")))
        for sid in ("golden", "void", "chimera", "pastel", "static"):
            self.assertIn(sid, have)
        self.assertNotIn("golden", shells.unlocked(self.records(rare=("pastel",))))

    def test_match_my_pet_for_rare_eggs_and_secrets(self):
        rng = random.Random(2)
        c = Creature("Ari", genetics.random_genome(rng), 1, rng)
        c.genome.update(line="water", mutation="shiny")
        evolution.apply(c, "dewdrop", "baby", SPECIES)
        self.assertEqual(shells.match_for(c), "golden")
        evolution.apply(c, "aurora", "adult", SPECIES)
        self.assertEqual(shells.match_for(c), "starlight")              # a secret form wins
        r = Records()
        r.discover("dewdrop", SPECIES)                                  # neither rare shell unlocked yet:
        self.assertEqual(shells.current({"shell": "match"}, r, c), "tide")   # fall back to its line

    def test_fourteen_shells_all_draw(self):
        self.assertEqual(len(shells.ORDER), 14)
        for sid in shells.ORDER:
            for dark in (False, True):
                surf = shells.shell_surface(sid, (400, 320), (64, 38), 200, dark)
                self.assertEqual(surf.get_size(), (400, 320))


class EveryScreenTests(unittest.TestCase):
    """Draws every screen in both text styles at three window sizes. Any crash fails."""

    def test_every_screen_draws(self):
        from game.app import Game
        from game.book import SECTIONS
        from game.minigames import GAME_CLASSES
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "3"])
            for _ in range(30 * 30):
                if g.c.stage == "adult" and not g.blocked():
                    break
                if not g.blocked():
                    g.c.stage_age = 1e9
                g.update(1 / 30)
            g.c.asleep = False
            g.records.coins = 50
            g.journal.add("note", "did something memorable.", g.world_time, important=True)
            for pixel in (True, False):
                g.prefs["pixel_text"] = pixel
                for size in ((640, 520), (960, 760), (1600, 900)):
                    pygame.display.set_mode(size, pygame.RESIZABLE)
                    with self.subTest(pixel=pixel, size=size):
                        g.menu = g.panel = g.minigame = None
                        g.draw()
                        for idx in (0, 1, 2, 4):                   # the action menus
                            g.menu = None
                            g.do_action(idx)
                            g.draw()
                        g.menu = None
                        for panel in ("status", "settings", "shop"):
                            g.panel = panel
                            g.draw()
                        g.shop_tab = "toy"
                        g.draw()
                        g.panel = "records"
                        for tab in range(5):
                            g.records_tab = tab
                            g.draw()
                        g.open_book(0)
                        for tab in range(len(SECTIONS)):
                            g.book_tab = tab
                            g.draw()
                        g.panel = None
                        g.ask("reset_hard")
                        g.draw()
                        g.confirm_answer(False)
                        g.panel = None
                        for name, cls in GAME_CLASSES.items():
                            g.minigame = cls(g.c, g.rng)
                            g.draw()
                        g.minigame = None
            pygame.quit()

    def test_settings_switches_text_style(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            g.toggle("settings")
            g.draw()
            self.assertTrue(g.ui.pixel)
            g.on_click(g.ui.hit["text_btn"].center)
            self.assertFalse(g.prefs["pixel_text"])
            g.draw()
            self.assertFalse(g.ui.pixel)
            self.assertNotIsInstance(g.ui.font(16), PixelFont)
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
