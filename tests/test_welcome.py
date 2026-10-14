"""Tests for the first-time welcome tour and one-time hints (v2.1).
Run:  python -m unittest discover -s tests -v
"""
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

from game import welcome  # noqa: E402

NEW_PLAYER = {k: v for k, v in os.environ.items() if k != "NIMLETS_SKIP_WELCOME"}


def new_game(d, **kw):
    from game.app import Game
    with mock.patch.dict(os.environ, NEW_PLAYER, clear=True):
        return Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "5"])


class WelcomeTests(unittest.TestCase):
    def test_a_new_player_gets_the_tour_and_time_holds_still(self):
        with tempfile.TemporaryDirectory() as d:
            g = new_game(d)
            self.assertEqual(g.panel, "welcome")
            age = g.c.age
            g.c.stage_age = 1e9                              # the egg is ready to hatch...
            for _ in range(60):
                g.update(1 / 30)
                g.draw()
            self.assertEqual(g.c.age, age)                   # ...but nothing moves during the tour
            self.assertEqual(g.c.stage, "egg")
            self.assertFalse(g.evolving)
            self.assertFalse(g.paused)                       # the player's own pause isn't touched
            pygame.quit()

    def test_turning_pages_and_finishing(self):
        with tempfile.TemporaryDirectory() as d:
            g = new_game(d)
            g.on_key(pygame.K_RIGHT)
            g.press_abc("b")
            self.assertEqual(g.welcome_page, 2)
            g.on_key(pygame.K_LEFT)
            g.press_abc("c")
            self.assertEqual(g.welcome_page, 0)
            g.press_abc("c")                                 # can't go back past the first page
            self.assertEqual((g.panel, g.welcome_page), ("welcome", 0))
            for _ in range(len(welcome.PAGES) - 1):
                g.draw()
                g.on_click(g.ui.hit["welcome_next"].center)
            self.assertEqual(g.welcome_page, len(welcome.PAGES) - 1)
            g.draw()
            self.assertIsNone(g.ui.hit["welcome_skip"])      # no "skip" on the last page
            g.on_key(pygame.K_RETURN)                        # "Let's begin!"
            self.assertIsNone(g.panel)
            self.assertTrue(g.prefs["welcomed"])
            self.assertTrue(g.prefs["hints"])
            g.save()
            pygame.quit()
            g2 = new_game(d)                                 # same player, next time: no tour
            self.assertIsNone(g2.panel if g2.panel != "away" else None)
            pygame.quit()

    def test_skipping(self):
        with tempfile.TemporaryDirectory() as d:
            g = new_game(d)
            g.draw()
            g.on_click(g.ui.hit["welcome_skip"].center)
            self.assertIsNone(g.panel)
            self.assertTrue(g.prefs["welcomed"])
            g.open_welcome()
            g.on_key(pygame.K_ESCAPE)
            self.assertIsNone(g.panel)
            pygame.quit()

    def test_existing_players_never_see_it_unless_they_ask(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])   # an existing player's save
            g.save()
            os.remove(os.path.join(d, "preferences.json"))             # from before the tour existed
            pygame.quit()
            g = new_game(d)
            self.assertNotEqual(g.panel, "welcome")
            self.assertTrue(g.prefs["welcomed"])
            self.assertFalse(g.prefs.get("hints"))
            g.panel = None
            g.toggle("settings")
            g.draw()
            g.on_click(g.ui.hit["tour_btn"].center)                    # Settings, Welcome tour
            self.assertEqual((g.panel, g.welcome_page), ("welcome", 0))
            g.close_welcome()
            self.assertFalse(g.prefs.get("hints"))                     # replaying it adds no hints
            pygame.quit()

    def test_every_page_draws_in_both_text_styles_and_sizes(self):
        with tempfile.TemporaryDirectory() as d:
            g = new_game(d)
            for pixel in (True, False):
                g.prefs["pixel_text"] = pixel
                for size in ((640, 520), (960, 760), (1920, 1080)):
                    pygame.display.set_mode(size, pygame.RESIZABLE)
                    for page in range(len(welcome.PAGES)):
                        g.welcome_page = page
                        g.draw()
                        self.assertTrue(pygame.Rect(0, 0, *size).contains(g.ui.hit["welcome_next"]))
            pygame.quit()


class HintTests(unittest.TestCase):
    def hatched(self, d):
        g = new_game(d)
        g.close_welcome()
        for _ in range(30 * 20):
            if g.c.stage != "egg" and not g.blocked():
                break
            if not g.blocked():
                g.c.stage_age = 1e9
            g.update(1 / 30)
        import time as _t
        lt = _t.localtime(g.world_time)                 # afternoon, wide awake, so it doesn't nod off
        g.world_time += ((14 - lt.tm_hour) % 24) * 3600
        g.c.energy = 100.0
        g.c.attention, g.c.poops, g.c.asleep = None, 0, False
        g.world.mural = []
        g.msg_t = 0
        g.prefs["hints_seen"] = []
        return g

    def tick(self, g, seconds=1.2):
        for _ in range(int(seconds * 30)):
            g.update(1 / 30)

    def test_each_hint_shows_once(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.hatched(d)
            g.c.poops = 1
            self.tick(g)
            self.assertEqual(g.message, welcome.HINTS["mess"])
            self.assertIn("mess", g.prefs["hints_seen"])
            g.msg_t = 0
            g.message = ""
            self.tick(g)
            self.assertNotEqual(g.message, welcome.HINTS["mess"])     # never twice
            pygame.quit()

    def test_hints_wait_for_other_messages_and_respect_existing_players(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.hatched(d)
            g.say("Something else is happening!")
            g.c.poops = 1
            self.tick(g, 0.5)
            self.assertEqual(g.message, "Something else is happening!")   # not interrupted
            g.prefs["hints"] = False                                      # an existing player
            g.msg_t = 0
            self.tick(g)
            self.assertNotIn("mess", g.prefs.get("hints_seen", []))
            pygame.quit()

    def test_what_triggers_each_hint(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.hatched(d)
            self.assertIsNone(welcome.hint_due(g))
            g.c.attention = "hunger"
            self.assertEqual(welcome.hint_due(g), "attention")
            g.c.attention = None
            g.c.asleep, g.c.lights_on = True, True
            self.assertEqual(welcome.hint_due(g), "sleep")
            g.c.asleep = False
            g.world.add_mural([(30, 55, (1, 2, 3))], g.c.generation, g.c.name)
            self.assertEqual(welcome.hint_due(g), "drawing")
            g.world.mural = []
            g.c.stage = "child"
            self.assertEqual(welcome.hint_due(g), "grown")
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
