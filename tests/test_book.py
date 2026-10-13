"""Tests for the Records book (v1.8): the Expand button on the quick Records
view, the six storybook sections, navigation, and the book's buttons.
Run:  python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import config, shells  # noqa: E402
from game.book import SECTIONS  # noqa: E402

SPECIES = config.load_species()


class BookTests(unittest.TestCase):
    def game(self, d, grow=True):
        from game.app import Game
        g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "4"])
        g.draw()
        if grow:
            for _ in range(30 * 40):
                if g.c.stage == "adult" and not g.blocked():
                    break
                if not g.blocked():
                    g.c.stage_age = 1e9
                g.update(1 / 30)
            g.c.asleep = False
            g.menu = g.panel = None
        g.draw()
        return g

    def lived_in(self, g):
        g.records.lineage = [{"generation": 1, "name": "Pichan", "forms": ["pipling", "bobbit", "sprouty", "luminelle"],
                              "final": "luminelle", "final_name": "Luminelle", "days": 11.2, "care_mistakes": 1,
                              "reason": "journey", "hue": 20, "mutation": None}]
        g.records.longest = dict(g.records.lineage[0])
        g.records.gifts.update(flower=2, pebble=1)
        for i in range(40):
            g.journal.add("note", f"did thing number {i}.", g.world_time + i, important=i % 5 == 0)
        g.world.mural_artists["1"] = "Pichan"

    def test_expand_opens_the_book_on_the_matching_section(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            g.do_action(7)                                   # Records: the quick view
            self.assertEqual(g.panel, "records")
            g.draw()
            self.assertIsNotNone(g.ui.hit.get("expand"))
            g.records_tab = 1
            g.draw()
            g.on_click(g.ui.hit["expand"].center)
            self.assertEqual((g.panel, g.book_tab), ("book", 1))
            g.on_key(pygame.K_ESCAPE)                        # back to the quick view, same section
            self.assertEqual((g.panel, g.records_tab), ("records", 1))
            g.on_key(pygame.K_e)                             # E expands too
            self.assertEqual(g.panel, "book")
            g.press_abc("c")
            self.assertEqual(g.panel, "records")
            g.records_tab = 2                                # the quick view's "Records" tab is the book's Care
            g.open_book()
            self.assertEqual(SECTIONS[g.book_tab], "Care")
            g.draw()
            g.on_click(g.ui.hit["book_close"].center)
            self.assertEqual(g.panel, "records")
            pygame.quit()

    def test_turning_pages_with_keys_buttons_and_tabs(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            g.open_book(0)
            seen = []
            for _ in range(len(SECTIONS)):
                seen.append(g.book_tab)
                g.on_key(pygame.K_RIGHT)
            self.assertEqual(sorted(seen), list(range(len(SECTIONS))))
            self.assertEqual(g.book_tab, 0)
            g.on_key(pygame.K_LEFT)
            self.assertEqual(SECTIONS[g.book_tab], "Shells")
            g.press_abc("a")
            self.assertEqual(g.book_tab, 0)
            g.draw()
            g.on_click(g.ui.hit["book_tabs"][3].center)
            self.assertEqual(SECTIONS[g.book_tab], "Diary")
            pygame.quit()

    def test_every_section_draws_for_an_egg_and_a_lived_in_save_at_any_size(self):
        with tempfile.TemporaryDirectory() as d:
            for grow in (False, True):
                g = self.game(d, grow)
                if grow:
                    self.lived_in(g)
                g.open_book(0)
                for size in ((640, 520), (960, 760), (1920, 1080)):
                    pygame.display.set_mode(size, pygame.RESIZABLE)
                    for tab in range(len(SECTIONS)):
                        g.book_tab = tab
                        g.draw()
                        self.assertEqual(len(g.ui.hit["book_tabs"]), len(SECTIONS))
                        self.assertTrue(pygame.Rect(0, 0, *size).contains(g.ui.hit["book_close"]))
                pygame.quit()

    def test_diary_scrolls_within_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            self.lived_in(g)
            g.open_book(3)
            g.on_key(pygame.K_DOWN)
            self.assertEqual(g.book_scroll, 1)
            g.scroll_book(10_000)
            self.assertEqual(g.book_scroll, len(g.journal.entries) - 3)
            g.scroll_book(-10_000)
            self.assertEqual(g.book_scroll, 0)
            pygame.quit()

    def test_choosing_a_shell_in_the_book(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            g.open_book(5)
            g.draw()
            cells = dict((sid, r) for r, sid in g.ui.hit["book_shells"])
            self.assertEqual(set(cells), set(shells.ORDER))
            g.on_click(cells["glitch"].center)              # locked: you can look, not wear
            self.assertEqual(g.book_shell, "glitch")
            g.draw()
            self.assertIsNone(g.ui.hit["book_use"])
            g.on_click(cells["classic"].center)
            g.draw()
            g.on_click(g.ui.hit["book_use"].center)
            self.assertEqual(g.prefs["shell"], "classic")
            g.draw()
            self.assertEqual(g.ui.shell_id, "classic")
            g.on_click(g.ui.hit["book_match"].center)       # back to following the pet
            self.assertEqual(g.prefs["shell"], "match")
            g.on_click(g.ui.hit["book_match"].center)       # and off again: pins what it's wearing
            self.assertNotEqual(g.prefs["shell"], "match")
            pygame.quit()

    def test_bond_buttons_and_new_generation(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            g.open_book(4)
            g.draw()
            g.on_click(g.ui.hit["book_export"].center)
            self.assertIn("Report saved", g.message)
            g.on_click(g.ui.hit["book_lab"].center)          # the developer lab lives in the quick view
            self.assertEqual((g.panel, g.records_tab, g.lab_open), ("records", 4, True))
            g.can_new_generation = lambda: True
            g.open_book(1)
            g.draw()
            g.on_click(g.ui.hit["book_newgen"].center)
            self.assertEqual(g.panel, "confirm")
            g.confirm_answer(False)
            self.assertEqual(g.panel, "records")
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
