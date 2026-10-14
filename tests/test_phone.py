"""Tests for v2.5: portrait and wide phone layouts, the Screen setting, and sizing the
browser canvas to the phone's real pixels.  Run:  python -m unittest discover -s tests -v
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
os.environ.setdefault("NIMLETS_SKIP_WELCOME", "1")

import pygame  # noqa: E402

from game import config, webscreen  # noqa: E402
from game.escape import Trip  # noqa: E402
from game.ui import ACTION_IDS, UI  # noqa: E402

PORTRAIT = [(585, 1266), (540, 1200), (390, 844), (1170, 2532), (820, 1180), (640, 1136), (700, 1000)]
WIDE = [(1266, 585), (2532, 1170), (844, 390), (1200, 540), (2400, 1080)]
DESKTOP = [(640, 520), (960, 760), (1280, 800), (1920, 1080), (1600, 900)]


class PhoneLayoutTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.ui = UI(None, config.load_species())

    def check_fits(self, L, W, H):
        win = pygame.Rect(0, 0, W, H)
        self.assertTrue(win.contains(L.shell))
        self.assertTrue(L.bezel.contains(L.lcd))
        self.assertEqual(L.lcd.size, (160 * L.scale, 112 * L.scale))
        pieces = L.buttons + [L.hearts_rect, L.msg, L.bezel] + list(L.toggles.values()) + list(L.abc.values())
        for r in pieces:
            self.assertTrue(L.shell.contains(r), (W, H, r))
        for i, a in enumerate(pieces):                     # nothing overlaps anything else
            for b in pieces[i + 1:]:
                self.assertFalse(a.colliderect(b), (W, H, a, b))
        self.assertEqual(len(L.buttons), len(ACTION_IDS))
        self.assertEqual(set(L.toggles), {"settings", "sound", "speed", "pause"})
        self.assertEqual(set(L.abc), {"a", "b", "c"})
        for r in L.buttons + list(L.toggles.values()) + list(L.abc.values()):
            self.assertGreaterEqual(min(r.size), 36, (W, H, r))   # comfortable for a finger

    def test_upright_phones_get_the_portrait_layout(self):
        for W, H in PORTRAIT:
            with self.subTest(size=(W, H)):
                L = self.ui.layout(W, H)
                self.assertEqual(L.kind, "portrait")
                self.assertEqual(L.tab_style, "grid")
                self.check_fits(L, W, H)
                self.assertGreaterEqual(L.scale, self.ui._layout_classic(W, H).scale)
                # room, then message, then the tab grid, then A/B/C, then the utility buttons
                self.assertLessEqual(L.hearts_rect.bottom, L.bezel.top)
                self.assertGreaterEqual(L.msg.top, L.bezel.bottom)
                self.assertGreater(min(r.top for r in L.buttons), L.msg.bottom)
                self.assertGreater(L.abc["b"].top, max(r.bottom for r in L.buttons))
                self.assertGreater(L.toggles["settings"].top, L.abc["b"].bottom)
                rows = sorted({r.y for r in L.buttons})
                self.assertEqual(len(rows), 2)              # a 4 x 2 grid, in action order
                self.assertEqual([r.y for r in L.buttons[:4]], [rows[0]] * 4)

    def test_phones_on_their_side_get_the_wide_layout(self):
        for W, H in WIDE:
            with self.subTest(size=(W, H)):
                L = self.ui.layout(W, H)
                self.check_fits(L, W, H)
                self.assertGreaterEqual(L.scale, self.ui._layout_classic(W, H).scale)
                if L.kind == "wide":
                    self.assertTrue(all(r.right < L.bezel.left for r in L.buttons[:4]))
                    self.assertTrue(all(r.left > L.bezel.right for r in L.buttons[4:]))
                    self.assertTrue(L.name_box.right < L.hearts_rect.left < L.hearts_rect.right < L.clock_box.left)
        # the common phone sizes really do get a bigger room than the classic device would
        self.assertEqual(self.ui.layout(1266, 585).kind, "wide")
        self.assertGreater(self.ui.layout(1266, 585).scale, self.ui._layout_classic(1266, 585).scale)

    def test_desktop_windows_keep_the_classic_device(self):
        for W, H in DESKTOP:
            with self.subTest(size=(W, H)):
                self.assertEqual(self.ui.layout(W, H).kind, "classic")

    def test_the_screen_setting(self):
        self.assertEqual(self.ui.layout(960, 760, "portrait").kind, "portrait")
        self.check_fits(self.ui.layout(960, 760, "portrait"), 960, 760)
        self.assertIn(self.ui.layout(585, 1266, "landscape").kind, ("classic", "wide"))
        self.assertEqual(self.ui.layout(1266, 585, "landscape").kind, "wide")
        self.assertEqual(self.ui.layout(1920, 1080, "landscape").kind, "classic")  # a tie keeps the classic device
        self.assertEqual(self.ui.layout(2400, 1080, "landscape").kind, "wide")     # wide wins when it's bigger
        self.assertIsNotNone(self.ui.layout(320, 200, "portrait"))               # never nothing

    def test_long_messages_stay_readable_in_portrait(self):
        W, H = 585, 1266
        L = self.ui.layout(W, H)
        self.assertTrue(L.stack_hearts)
        screen = pygame.Surface((W, H))
        used = []
        real = self.ui.font
        self.ui.font = lambda size, bold=False: used.append(size) or real(size, bold)
        try:
            self.ui.draw_message(screen, L, "Pichan pulled silly faces when it thought nobody was looking, "
                                 "then hid behind the plant.", 1.0)
        finally:
            self.ui.font = real
        self.assertGreaterEqual(used[-1], L.fs - 4)           # wrapped onto two lines, not shrunk away

    def test_escape_trips_stay_on_the_device(self):
        for W, H in PORTRAIT[:3] + WIDE[:2]:
            L = self.ui.layout(W, H)
            win = pygame.Rect(0, 0, W, H)
            for name, frac in (("tabside", 1), ("tabside", 5), ("tabtop", 0), ("tabtop", 4), ("abc", "b"),
                               ("settings", 0), ("msg", 0.5), ("bezel", 0.5), ("hearts", 0), ("edge", 0)):
                with self.subTest(size=(W, H), anchor=name):
                    x, y = Trip.anchor(L, name, frac)
                    self.assertTrue(win.collidepoint(x, y), (W, H, name, x, y))


class CanvasSizeTests(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(webscreen.canvas_size(390, 844, 3), (585, 1266, 2))     # an iPhone held upright
        self.assertEqual(webscreen.canvas_size(844, 390, 3), (1266, 585, 2))     # on its side
        self.assertEqual(webscreen.canvas_size(960, 760, 1), (960, 760, 1))      # a desktop browser window
        self.assertEqual(webscreen.canvas_size(1920, 1080, 1), (960, 540, 2))
        self.assertEqual(webscreen.canvas_size(412, 915, 2.625)[2], 2)           # an Android phone

    def test_within_budget_and_matching_the_window(self):
        for w, h, dpr in ((390, 844, 3), (412, 915, 2.625), (1024, 1366, 2), (1920, 1080, 1.5), (360, 640, 4)):
            cw, ch, k = webscreen.canvas_size(w, h, dpr)
            self.assertLessEqual(cw * ch, webscreen.BUDGET * 1.01)
            self.assertAlmostEqual(cw / ch, w / h, delta=0.01)                  # same shape: nothing squashed
            self.assertAlmostEqual(cw * k, w * dpr, delta=k)                     # whole screen pixels per pixel

    def test_unknown_density_counts_as_one(self):
        self.assertEqual(webscreen.canvas_size(800, 600, 0), (800, 600, 1))


class FakeStyle:
    imageRendering = ""


class FakeCanvas:
    def __init__(self):
        self.style = FakeStyle()


class FakeWindow:
    def __init__(self, w, h, dpr):
        self.innerWidth, self.innerHeight, self.devicePixelRatio = w, h, dpr
        self.canvas = FakeCanvas()
        self.resized = 0

    def window_resize(self):
        self.resized += 1


class WebFitTests(unittest.TestCase):
    def setUp(self):
        import platform
        self.platform = platform

    def test_wanted_size_reads_the_browser(self):
        with mock.patch.object(self.platform, "window", FakeWindow(390, 844, 3), create=True):
            self.assertEqual(webscreen.wanted_size(), (585, 1266))
        with mock.patch.object(self.platform, "window", None, create=True):
            self.assertIsNone(webscreen.wanted_size())

    def test_game_follows_the_phone_round(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            pygame.display.set_mode((960, 760))
            win = FakeWindow(390, 844, 3)
            with mock.patch.object(self.platform, "window", win, create=True), \
                    mock.patch.object(config, "WEB", True), mock.patch("game.app.save_prefs"), \
                    mock.patch("game.app.weblog"):
                g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
                g.web_fit()
                self.assertEqual(g.screen.get_size(), (585, 1266))
                self.assertEqual(win.canvas.style.imageRendering, "pixelated")
                self.assertGreaterEqual(win.resized, 1)
                g.draw()
                self.assertEqual(g.L.kind, "portrait")
                win.innerWidth, win.innerHeight = 844, 390               # turned on its side
                g.web_fit()
                g.draw()
                self.assertEqual(g.screen.get_size(), (1266, 585))
                self.assertEqual(g.L.kind, "wide")

    def test_a_failed_resize_keeps_the_old_canvas(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            pygame.display.set_mode((960, 760))
            with mock.patch.object(self.platform, "window", FakeWindow(390, 844, 3), create=True), \
                    mock.patch.object(config, "WEB", True), mock.patch("game.app.save_prefs"), \
                    mock.patch("game.app.weblog"):
                g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
                with mock.patch("pygame.display.set_mode", side_effect=pygame.error("no")):
                    g.web_fit()
                self.assertTrue(g.web_fit_off)
                self.assertEqual(g.screen.get_size(), (960, 760))
                g.web_fit()                                              # and doesn't keep trying
                g.draw()

    def test_desktop_never_touches_the_window(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            before = g.screen.get_size()
            g.web_fit()
            self.assertEqual(g.screen.get_size(), before)


class ScreenSettingTests(unittest.TestCase):
    def test_choosing_portrait_in_settings(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            pygame.display.set_mode((960, 760))
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            g.prefs["screen"] = "auto"
            g.panel = "settings"
            g.draw()
            rect = next(r for r, v in g.ui.hit["screen_btns"] if v == "portrait")
            g.on_click(rect.center)
            self.assertEqual(g.prefs["screen"], "portrait")
            g.panel = None
            g.draw()
            self.assertEqual(g.L.kind, "portrait")
            g.prefs["screen"] = "auto"


if __name__ == "__main__":
    unittest.main()
