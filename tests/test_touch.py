"""Tests for the v2.4 pointer: a finger is only there while it's touching.
Run:  python -m unittest discover -s tests -v
"""
import os
import shutil
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NIMLETS_SKIP_WELCOME", "1")

import pygame  # noqa: E402

from game import pointer as pointer_mod  # noqa: E402
from game.pointer import AFTERGLOW, NOWHERE, Pointer, POINTER  # noqa: E402
from game.reciprocity import GestureTracker  # noqa: E402

DT = 1 / 30


def touch(kind, pos, **kw):
    """A mouse event as SDL synthesises it from a touch."""
    if kind == "down":
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1, touch=True, **kw)
    if kind == "up":
        return pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1, touch=True, **kw)
    return pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(1, 0, 0), touch=True, **kw)


class PointerTests(unittest.TestCase):
    def test_finger_exists_only_while_down(self):
        p = Pointer()
        self.assertTrue(p.on_event(touch("down", (100, 120))))
        self.assertTrue(p.touch)
        self.assertEqual(p.present(), (100, 120))
        p.on_event(touch("move", (110, 125)))
        self.assertEqual(p.present(), (110, 125))
        p.on_event(touch("up", (110, 125)))
        self.assertIsNone(p.present())                  # gone for zones, tabs and the Observer
        self.assertEqual(p.hover_pos(), NOWHERE)        # nothing stays highlighted
        self.assertFalse(p.pressed())

    def test_afterglow_then_gone(self):
        p = Pointer()
        p.on_event(touch("down", (50, 60)))
        p.on_event(touch("up", (50, 60)))
        self.assertEqual(p.present(afterglow=True), (50, 60))   # its eyes may linger there
        t = 0.0
        while t < AFTERGLOW + 0.1:
            p.tick(DT)
            t += DT
        self.assertIsNone(p.present(afterglow=True))

    def test_finger_events_use_window_size(self):
        p = Pointer()
        p.on_event(pygame.event.Event(pygame.FINGERDOWN, x=0.25, y=0.5, dx=0, dy=0, finger_id=0,
                                      touch_id=0, pressure=1.0), (800, 600))
        self.assertEqual(p.present(), (200, 300))
        p.on_event(pygame.event.Event(pygame.FINGERUP, x=0.25, y=0.5, dx=0, dy=0, finger_id=0,
                                      touch_id=0, pressure=0.0), (800, 600))
        self.assertIsNone(p.present())

    def test_real_mouse_switches_back(self):
        p = Pointer()
        p.on_event(touch("down", (10, 10)))
        p.on_event(touch("up", (10, 10)))
        p.on_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(30, 30), rel=(1, 1), buttons=(0, 0, 0)))
        self.assertEqual(p.mode, "mouse")
        self.assertFalse(p.down)

    def test_lift_ends_a_gesture_without_a_pause(self):
        tr = GestureTracker()
        for i in range(12):                              # a quick swipe right, no pause at the end
            tr.update(DT, i * DT, (40 + i * 4, 50))
        self.assertEqual(tr.pop(), [])
        tr.finish(12 * DT)
        out = tr.pop()
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0][1], "right")
        tr.finish(13 * DT)                               # nothing left to finish
        self.assertEqual(tr.pop(), [])


class TouchInGameTests(unittest.TestCase):
    def setUp(self):
        POINTER.__init__()
        self.tmp = tempfile.mkdtemp()
        save = os.path.join(self.tmp, "s.json")
        shutil.copy(os.path.join(ROOT, "saves", "example_save.json"), save)
        from game.app import Game
        self.g = g = Game(["--save", save, "--mute", "--seed", "4"])
        if g.panel == "away":
            g.close_away()
        lt = time.localtime(g.world_time)
        g.world_time += ((14 - lt.tm_hour) % 24) * 3600      # the afternoon: awake, lights on
        g.c.asleep, g.c.hunger, g.c.happiness, g.c.energy = False, 90, 90, 95
        g.c.attention = None
        g.draw()

    def tearDown(self):
        POINTER.__init__()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def step(self, n=1):
        for _ in range(n):
            self.g.update(DT)
            POINTER.tick(DT)

    def room_pos(self, lx, ly):
        L = self.g.L
        return (int(L.lcd.x + lx * L.scale), int(L.lcd.y + ly * L.scale))

    def test_no_phantom_cursor_after_a_tap(self):
        g = self.g
        pos = self.room_pos(g.beh.x, 85)                 # tap right beside the pet
        g.handle(touch("down", pos))
        self.step(3)
        self.assertIsNotNone(g.lcd_cursor())
        g.handle(touch("up", pos))
        self.step(int(30 * 6))                           # long enough to have built "trust" before v2.4
        self.assertIsNone(g.lcd_cursor())
        self.assertIsNone(g.window_cursor())
        self.assertIsNone(g.mind.cursor)
        self.assertEqual(g.mind.near_still_t, 0.0)
        self.assertEqual(g.cursor_zone(DT), (None, None))

    def test_tab_acts_on_release(self):
        g = self.g
        feed = g.L.buttons[0].center
        g.handle(touch("down", feed))
        self.assertIsNone(g.menu)                        # pressed in, nothing yet
        self.assertEqual(g.hover, 0)
        g.handle(touch("up", feed))
        self.assertIsNotNone(g.menu)                     # lifting on the tab chooses it
        self.assertIsNone(g.hover)

    def test_sliding_off_a_tab_cancels(self):
        g = self.g
        feed = g.L.buttons[0]
        g.handle(touch("down", feed.center))
        away = (feed.right + 60, feed.centery)
        g.handle(touch("move", away))
        self.assertIsNone(g.hover)                       # it pops back out
        g.handle(touch("up", away))
        self.assertIsNone(g.menu)
        self.assertIsNone(g.press_tab)

    def test_mouse_clicks_still_act_at_once(self):
        g = self.g
        g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=g.L.buttons[0].center, button=1))
        self.assertIsNotNone(g.menu)

    def test_finger_drag_is_a_gesture(self):
        g = self.g
        seen = []
        g.mind.recip.on_stroke = lambda gest, centre: seen.append(gest)
        start = self.room_pos(30, 20)                    # the upper wall: not the mural, not the bed
        g.handle(touch("down", start))
        self.step()
        for i in range(1, 13):
            g.handle(touch("move", self.room_pos(30 + i * 5, 20)))
            self.step()
        g.handle(touch("up", self.room_pos(90, 20)))
        self.step()
        self.assertIn("right", seen)

    def test_no_heading_from_a_finger(self):
        g = self.g
        g.handle(touch("down", self.room_pos(120, 30)))
        self.step()
        for i in range(1, 8):                            # a fast drag straight at the right-hand tabs
            g.handle(touch("move", self.room_pos(120 + i * 5, 30)))
            self.step()
            self.assertIsNone(g.cursor_zone(DT)[1])

    def test_ui_hover_ignores_a_lifted_finger(self):
        POINTER.on_event(touch("down", (5, 5)))
        self.assertEqual(pointer_mod.hover_pos(), (5, 5))
        POINTER.on_event(touch("up", (5, 5)))
        self.assertEqual(pointer_mod.hover_pos(), NOWHERE)


if __name__ == "__main__":
    unittest.main()
