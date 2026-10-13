"""Tests for the handheld redesign (v1.7): the layout at many window sizes,
decorated shells and how they unlock, the A/B/C buttons, the Settings shell
picker, and the observer changes the new layout needed.
Run:  python -m unittest discover -s tests -v
"""
import os
import random
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from game import config, evolution, genetics, shells  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.records import Records  # noqa: E402
from game.ui import ACTION_IDS, UI  # noqa: E402

SPECIES = config.load_species()
SIZES = [(640, 520), (800, 600), (960, 760), (1280, 800), (1920, 1080), (700, 1000), (1600, 560)]


def creature(species="pipling", stage="baby", line="land"):
    rng = random.Random(1)
    c = Creature("Ari", genetics.random_genome(rng), 1, rng)
    c.genome["line"] = line
    if species != "egg":
        evolution.apply(c, species, stage, SPECIES)
    return c


class LayoutTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.ui = UI(None, SPECIES)

    def test_everything_fits_and_nothing_overlaps_at_every_size(self):
        for W, H in SIZES:
            L = self.ui.layout(W, H)
            win = pygame.Rect(0, 0, W, H)
            with self.subTest(size=(W, H)):
                self.assertTrue(win.contains(L.shell))
                self.assertTrue(L.bezel.contains(L.lcd))
                self.assertGreaterEqual(L.scale, 2 if min(W, H) >= 520 else 1)
                for r in L.buttons + [L.hearts_rect, L.msg, L.top] + list(L.toggles.values()) + list(L.abc.values()):
                    self.assertTrue(L.shell.contains(r), (W, H, r))
                for i, a in enumerate(L.buttons):
                    self.assertFalse(a.colliderect(L.bezel))
                    for b in L.buttons[i + 1:]:
                        self.assertFalse(a.colliderect(b))
                self.assertLessEqual(L.hearts_rect.bottom, L.bezel.top)
                self.assertGreaterEqual(L.msg.top, L.bezel.bottom)
                controls = list(L.toggles.values()) + list(L.abc.values())
                for i, a in enumerate(controls):
                    self.assertGreaterEqual(a.top, L.msg.bottom)
                    for b in controls[i + 1:]:
                        self.assertFalse(a.colliderect(b))

    def test_tabs_run_down_both_sides_in_action_order(self):
        L = self.ui.layout(960, 760)
        left, right = L.buttons[:4], L.buttons[4:]
        self.assertTrue(all(r.right == L.bezel.left for r in left))
        self.assertTrue(all(r.left == L.bezel.right for r in right))
        self.assertEqual([r.y for r in left], sorted(r.y for r in left))
        self.assertEqual(len(L.buttons), len(ACTION_IDS))
        self.assertEqual(set(L.toggles), {"settings", "sound", "speed", "pause"})
        self.assertLess(L.toggles["sound"].right, L.abc["a"].left)
        self.assertGreater(L.toggles["speed"].left, L.abc["c"].right)

    def test_every_shell_draws_at_every_size_light_and_dark(self):
        for sid in shells.ORDER:
            for W, H in SIZES[:3]:
                L = self.ui.layout(W, H)
                for dark in (False, True):
                    surf = shells.shell_surface(sid, L.shell.size, L.radii, 200, dark)
                    self.assertEqual(surf.get_size(), L.shell.size)
                    self.assertEqual(surf.get_at((0, 0)).a, 0)          # clipped to the rounded corner
                    self.assertEqual(surf.get_at((L.shell.w // 2, L.shell.h // 2)).a, 255)


class ShellRuleTests(unittest.TestCase):
    def test_unlocks_come_from_the_family_history(self):
        r = Records()
        self.assertEqual(shells.unlocked(r), ["classic"])
        for sid in ("pipling", "dewdrop", "glitchling"):
            r.discover(sid, SPECIES)
        self.assertEqual(shells.unlocked(r), ["classic", "tide", "meadow", "glitch"])
        r.discover("aurora", SPECIES)
        self.assertIn("starlight", shells.unlocked(r))
        self.assertEqual(shells.unlocked_by("mycelia"), "spore")
        self.assertIsNone(shells.unlocked_by("bobbit"))

    def test_match_my_pet_follows_line_and_secret_forms(self):
        self.assertEqual(shells.match_for(creature("egg", line="water")), "classic")   # no spoilers
        self.assertEqual(shells.match_for(creature("pipling", line="land")), "meadow")
        self.assertEqual(shells.match_for(creature("dewdrop", line="water")), "tide")
        self.assertEqual(shells.match_for(creature("celestine", "adult")), "starlight")
        self.assertEqual(shells.match_for(creature("mycelia", "adult", line="water")), "spore")

    def test_a_locked_choice_falls_back_to_classic(self):
        r = Records()
        r.discover("pipling", SPECIES)
        c = creature("pipling")
        self.assertEqual(shells.current({"shell": "match"}, r, c), "meadow")
        self.assertEqual(shells.current({"shell": "glitch"}, r, c), "classic")
        self.assertEqual(shells.current({}, r, c), "meadow")
        self.assertEqual(shells.options(r), ["match", "classic", "meadow"])
        self.assertEqual(shells.label("match"), "Match my pet")


class AppTests(unittest.TestCase):
    def game(self, d):
        from game.app import Game
        g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "4"])
        g.draw()
        return g

    def grown(self, g):
        for _ in range(30 * 40):
            if g.c.stage == "adult" and not g.blocked():
                break
            if not g.blocked():
                g.c.stage_age = 1e9
            g.update(1 / 30)
        g.c.asleep, g.c.poops, g.c.hygiene = False, 0, 100.0
        g.menu = g.panel = None
        g.draw()

    def test_hatching_unlocks_and_announces_the_line_shell(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            self.assertEqual(g.ui.shell_id, "classic")
            self.grown(g)
            first = g.c.forms[0]
            expected = "tide" if first == "dewdrop" else "meadow"
            self.assertIn(expected, shells.unlocked(g.records))
            self.assertTrue(any("shell" in e["text"] for e in g.journal.entries))
            self.assertEqual(g.ui.shell_id, shells.match_for(g.c))
            pygame.quit()

    def test_a_b_c_buttons_and_keys(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            self.grown(g)
            g.sel_tab = 5
            g.press_abc("a")
            self.assertEqual(g.sel_tab, 6)                       # A moves along the tabs
            g.press_abc("b")
            self.assertEqual(g.panel, "status")                  # B selects
            g.press_abc("c")
            self.assertIsNone(g.panel)                           # C goes back
            g.on_key(pygame.K_a)
            self.assertEqual(g.sel_tab, 7)
            g.sel_tab = 0
            g.on_key(pygame.K_b)                                 # Feed opens its menu
            self.assertEqual(g.menu.kind, "feed")
            g.press_abc("a")
            self.assertEqual(g.menu.sel, 1)
            g.on_key(pygame.K_c)
            self.assertIsNone(g.menu)
            g.do_action(3)
            self.assertEqual(g.sel_tab, 3)                       # clicking a tab selects it too
            g.panel = "settings"
            L = g.L
            before = g.sel_tab
            g.on_click(L.abc["b"].center)                        # hidden under the panel: B doesn't act
            self.assertIsNone(g.menu)
            self.assertEqual(g.sel_tab, before)
            g.panel = None
            g.on_click(L.abc["a"].center)
            self.assertEqual(g.sel_tab, 4)
            pygame.quit()

    def test_settings_shell_picker_cycles_unlocked_shells_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            self.grown(g)
            g.records.discover("glitchling", SPECIES)
            opts = shells.options(g.records)
            self.assertEqual(g.shell_choice(), "match")
            g.cycle_shell(1)
            self.assertEqual(g.prefs["shell"], opts[1])
            g.cycle_shell(-1)
            g.cycle_shell(-1)
            self.assertEqual(g.prefs["shell"], opts[-1])
            g.toggle("settings")
            g.draw()
            r = g.ui.hit["shell_btn"]
            g.on_click((r.right - 4, r.centery))
            self.assertEqual(g.prefs["shell"], opts[0])
            g.prefs["shell"] = "spore"                          # not unlocked
            self.assertEqual(g.shell_choice(), "match")
            g.draw()
            self.assertNotEqual(g.ui.shell_id, "spore")
            pygame.quit()

    def test_every_shell_renders_in_the_running_game(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            self.grown(g)
            for sid in ("tide", "meadow", "starlight", "glitch", "spore", "classic"):
                for sp in shells.SHELLS[sid]["unlock"]:
                    g.records.discover(sp, SPECIES)
                g.prefs["shell"] = sid
                for size in ((640, 520), (1280, 800)):
                    pygame.display.set_mode(size, pygame.RESIZABLE)
                    g.draw()
                    self.assertEqual(g.ui.shell_id, sid)
            pygame.quit()


class ObserverLayoutTests(unittest.TestCase):
    def test_a_passing_hover_over_the_pet_is_withdrawn_not_scored(self):
        from test_observer import setup
        c, beh, mind, log = setup()
        o = mind.observer
        o.o["assoc"]["z:room:pet"] = {"pet": 9}
        o.observe(0.1, "room:pet", None)
        self.assertEqual(o.prediction["action"], "pet")
        misses = o.o["misses"]
        o.observe(0.1, "feed", None)                            # the cursor moved on to a tab
        self.assertIsNone(o.prediction)
        self.assertEqual(o.o["misses"], misses)

    def test_room_headings_only_count_tabs_on_the_near_side(self):
        with tempfile.TemporaryDirectory() as d:
            from game.app import Game
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            g.draw()
            L = g.L
            start = (L.lcd.right - 20, L.lcd.centery)           # right half of the room, moving left
            g.window_cursor = lambda: start
            g.cursor_prev = (start[0] + 30, start[1])
            g.cursor_vel = (-900.0, 0.0)
            zone, heading = g.cursor_zone(0.0)
            self.assertNotIn(heading, ACTION_IDS[:4])
            start2 = (L.lcd.left + 20, L.buttons[1].centery)    # left half, heading for Play
            g.window_cursor = lambda: start2
            g.cursor_prev = (start2[0] + 30, start2[1])
            zone, heading = g.cursor_zone(0.0)
            self.assertEqual(heading, "play")
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
