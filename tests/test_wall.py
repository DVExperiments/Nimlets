"""Tests for cleaning the wall (v1.6): timestamps on drawings, the sponge,
wiping everything, and what the pet learns depending on how fresh the
drawing was.  Run:  python -m unittest discover -s tests -v
"""
import json
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

from game import config, evolution, genetics, learning, wall  # noqa: E402
from game.behaviour import Behaviour  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.living import Mind  # noqa: E402
from game.world import MURAL_RECT, World  # noqa: E402

SPECIES = config.load_species()
HOUR = 3600.0
NOW = 1_800_000_000.0


def setup(seed=5, stubborn=0.3):
    rng = random.Random(seed)
    c = Creature("Ari", genetics.random_genome(rng), 1, rng)
    evolution.apply(c, "frolicat", "adult", SPECIES)
    c.hunger = c.happiness = c.energy = 90
    c.personality.traits["stubbornness"] = stubborn
    beh = Behaviour(rng)
    log = []
    mind = Mind(rng, None, lambda t: None, lambda n: None,
                lambda kind, text, icon=None, important=False: log.append((kind, text, important)))
    mind.attach(c, beh, World())
    beh._c, beh._sp = c, SPECIES[c.species]
    mind.world_time = NOW
    mind.world.now = NOW
    return c, beh, mind, log


def scribble(world, gen, t, x0=30, n=14):
    mx, my, mw, mh = MURAL_RECT
    return world.add_mural([(x0 + i, my + 5, (10, 20, 30)) for i in range(n)], gen, "Ari", t=t)


class WallDataTests(unittest.TestCase):
    def test_drawings_are_timestamped_and_wiped_by_radius(self):
        w = World()
        w.now = NOW
        scribble(w, 1, None)
        self.assertTrue(all(len(p) == 5 and p[4] == NOW for p in w.mural))
        mx, my, mw, mh = MURAL_RECT
        gone = w.wipe(33, my + 5, 2.0)
        self.assertEqual(len(gone), 5)                      # x = 31..35
        self.assertEqual(len(w.mural), 9)
        self.assertEqual(len(w.wipe_all()), 9)
        self.assertEqual(w.mural, [])

    def test_old_saves_without_timestamps_load_render_and_count_as_old(self):
        import pygame
        from game.room import Room
        w = World.from_dict({"mural": [[20, 55, [1, 2, 3], 1], [21, 55, [1, 2, 3], 0]]})
        k = wall.classify(w.wipe_all(), 1, NOW)
        self.assertEqual((k["old"], k["yours"], k["fresh"]), (1, 1, 0))
        w = World.from_dict({"mural": [[20, 55, [1, 2, 3], 1]]})
        pygame.init()
        surf = pygame.Surface((160, 100))
        c, beh, mind, _ = setup()
        mind.world = w
        Room(config.load_settings()).draw_objects(surf, mind, c, 0.0, 0)         # 4-element pixels still draw
        pygame.quit()

    def test_now_is_not_saved_but_timestamps_are(self):
        w = World()
        w.now = NOW
        scribble(w, 2, None)
        data = json.loads(json.dumps(w.to_dict()))
        self.assertNotIn("now", data)
        self.assertEqual(World.from_dict(data).mural[0][4], NOW)

    def test_classify_by_owner_and_age(self):
        w = World()
        scribble(w, 3, NOW - 10 * 60, x0=10, n=4)           # fresh
        scribble(w, 3, NOW - 5 * HOUR, x0=20, n=3)          # recent
        scribble(w, 3, NOW - 50 * HOUR, x0=30, n=2)         # old
        scribble(w, 0, NOW, x0=40, n=5)                     # yours
        scribble(w, 1, NOW - 99 * HOUR, x0=50, n=6)         # an ancestor's
        k = wall.classify(w.mural, 3, NOW)
        self.assertEqual((k["fresh"], k["recent"], k["old"], k["yours"]), (4, 3, 2, 5))
        self.assertEqual(k["ancestors"], {1: 6})


class WallLearningTests(unittest.TestCase):
    def test_wiping_fresh_drawings_teaches_it_drawing_is_unwelcome(self):
        c, beh, mind, log = setup()
        for i in range(4):
            scribble(mind.world, 1, NOW - 5 * 60, x0=20 + i)
            mind.on_wall_wiped(mind.world.wipe_all())
        self.assertLess(learning.belief(c, "wall_ok"), wall.SECRET_BELIEF)
        texts = " ".join(t for _, t, _ in log)
        self.assertIn("don't want it drawing", texts)
        self.assertIn("only just made", texts)
        self.assertIsNotNone(mind.episodes.get("wall_wiped"))

    def test_wiping_old_drawings_or_your_own_teaches_nothing(self):
        c, beh, mind, _ = setup()
        scribble(mind.world, 1, NOW - 48 * HOUR)
        scribble(mind.world, 0, NOW, x0=60)
        mind.on_wall_wiped(mind.world.wipe_all())
        self.assertEqual(learning.belief(c, "wall_ok"), 0.0)

    def test_recent_is_a_milder_lesson_than_fresh(self):
        c1, _, m1, _ = setup()
        c2, _, m2, _ = setup()
        scribble(m1.world, 1, NOW - 10 * 60)
        scribble(m2.world, 1, NOW - 6 * HOUR)
        m1.on_wall_wiped(m1.world.wipe_all())
        m2.on_wall_wiped(m2.world.wipe_all())
        self.assertLess(learning.belief(c1, "wall_ok"), learning.belief(c2, "wall_ok"))
        self.assertLess(learning.belief(c2, "wall_ok"), 0.0)

    def test_stubborn_pets_shrug_it_off_and_sleepers_learn_less(self):
        soft, _, m1, _ = setup(stubborn=0.1)
        tough, _, m2, _ = setup(stubborn=0.95)
        asleep, _, m3, _ = setup(stubborn=0.1)
        asleep.asleep = True
        for m in (m1, m2, m3):
            scribble(m.world, 1, NOW - 60)
            m.on_wall_wiped(m.world.wipe_all())
        b = [learning.belief(x, "wall_ok") for x in (soft, tough, asleep)]
        self.assertLess(b[0], b[1])
        self.assertLess(b[0], b[2])

    def test_it_reacts_when_it_sees_and_not_when_asleep(self):
        c, beh, mind, _ = setup()
        scribble(mind.world, 1, NOW - 60)
        msg = mind.on_wall_wiped(mind.world.wipe_all())
        self.assertTrue(msg and c.name in msg)
        c2, beh2, m2, _ = setup()
        c2.asleep = True
        scribble(m2.world, 1, NOW - 60)
        self.assertIsNone(m2.on_wall_wiped(m2.world.wipe_all()))

    def test_losing_the_last_of_an_ancestors_drawing_is_noted(self):
        c, beh, mind, log = setup()
        c.generation = 2
        scribble(mind.world, 1, NOW - 100 * HOUR)
        mind.world.mural_artists["1"] = "Grandpip"
        mind.on_wall_wiped(mind.world.wipe_all())
        self.assertTrue(any("Grandpip" in t for _, t, _ in log))

    def test_draw_factor_means_secret_drawing(self):
        self.assertEqual(wall.draw_factor(0.0, True), 1.0)
        self.assertLess(wall.draw_factor(-0.6, True), 0.35)
        self.assertGreater(wall.draw_factor(-0.6, False), 1.3)
        self.assertGreater(wall.draw_factor(0.6, True), 1.0)

    def test_drawings_left_up_and_your_drawing_rebuild_the_belief(self):
        c, beh, mind, _ = setup()
        c.beliefs["wall_ok"] = {"v": -0.6, "n": 5, "a": "neg"}
        scribble(mind.world, 1, NOW - 10 * HOUR)
        self.assertGreaterEqual(wall.survived(mind.world, 1, NOW), 6)
        from game.behaviour import act
        mind.step_fx(act("draw", 1.0, fx="mural"), beh)
        after_survival = learning.belief(c, "wall_ok")
        self.assertGreater(after_survival, -0.6)
        mind.recip.on_wall_stroke([(20, 55), (21, 55)])
        self.assertGreater(learning.belief(c, "wall_ok"), after_survival)

    def test_belief_survives_save_and_load(self):
        c, _, mind, _ = setup()
        scribble(mind.world, 1, NOW - 60)
        mind.on_wall_wiped(mind.world.wipe_all())
        c2 = Creature.from_dict(json.loads(json.dumps(c.to_dict())))
        self.assertAlmostEqual(learning.belief(c2, "wall_ok"), learning.belief(c, "wall_ok"))


class WallAppTests(unittest.TestCase):
    def game(self, d):
        from game.app import Game
        g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "4"])
        for _ in range(30 * 40):                             # hatch and grow up to an adult
            if g.c.stage == "adult" and not g.blocked():
                break
            if not g.blocked():
                g.c.stage_age = 1e9
            g.update(1 / 30)
        self.assertEqual(g.c.stage, "adult")
        g.c.asleep, g.c.poops, g.c.hygiene = False, 0, 100.0
        g.menu = g.panel = None
        g.world.mural = []
        return g

    def test_clean_flushes_mess_first_then_offers_the_wall(self):
        import pygame
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            g.do_action(2)
            self.assertIsNone(g.menu)                        # blank wall: plain clean
            scribble(g.world, g.c.generation, g.world_time)
            g.c.poops = 2
            g.do_action(2)
            self.assertEqual(g.c.poops, 0)                   # mess comes first
            self.assertIsNone(g.menu)
            self.assertIn("wipe the wall", g.message)
            g.do_action(2)
            self.assertEqual(g.menu.kind, "clean")           # tidy room: the wall menu
            pygame.quit()

    def test_sponge_wipes_where_you_drag_and_the_pet_reacts(self):
        import pygame
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            mx, my, mw, mh = MURAL_RECT
            scribble(g.world, g.c.generation, g.world_time, x0=30, n=14)
            scribble(g.world, g.c.generation, g.world_time, x0=100, n=6)
            g.do_action(2)
            g.menu_select(0)                                 # Sponge
            self.assertIsNotNone(g.sponge)
            g.click_lcd(30, my + 5)
            for x in range(30, 46):
                g.move_sponge((x, my + 5))
            g.finish_stroke()
            left = sorted(p[0] for p in g.world.mural)
            self.assertEqual(left, list(range(100, 106)))    # only the dragged part is gone
            self.assertLess(learning.belief(g.c, "wall_ok"), 0.0)
            g.draw()                                         # sponge cursor renders
            g.on_key(pygame.K_ESCAPE)
            self.assertIsNone(g.sponge)
            pygame.quit()

    def test_clicking_elsewhere_or_other_buttons_puts_the_sponge_away(self):
        import pygame
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            scribble(g.world, g.c.generation, g.world_time)
            g.do_action(2)
            g.menu_select(0)
            g.click_lcd(80, 20)                              # up on the wall, away from the drawing
            self.assertIsNone(g.sponge)
            g.do_action(2)
            g.menu_select(0)
            g.do_action(6)                                   # Status
            self.assertIsNone(g.sponge)
            self.assertEqual(len(g.world.mural), 14)         # nothing was wiped
            pygame.quit()

    def test_wipe_it_all_asks_first(self):
        import pygame
        with tempfile.TemporaryDirectory() as d:
            g = self.game(d)
            scribble(g.world, g.c.generation, g.world_time)
            g.do_action(2)
            g.menu_select(1)                                 # Wipe it all
            self.assertEqual(g.panel, "confirm")
            g.confirm_answer(False)
            self.assertEqual(len(g.world.mural), 14)
            g.do_action(2)
            g.menu_select(1)
            g.draw()
            g.confirm_answer(True)
            self.assertEqual(g.world.mural, [])
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
