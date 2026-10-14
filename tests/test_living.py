"""Tests for the Living Pet System, settings/themes and resets.

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

from game import config, evolution, genetics  # noqa: E402
from game.behaviour import Behaviour, act, move  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.living import BED_X, Mind  # noqa: E402
from game.personality import EXCLUSIVE, Personality, assign_quirks, has_quirk  # noqa: E402
from game.save import load_prefs, save_prefs  # noqa: E402

SPECIES = config.load_species()


def setup(seed=3, stage="adult", species="frolicat"):
    rng = random.Random(seed)
    c = Creature("Liv", genetics.random_genome(rng), 1, rng)
    evolution.apply(c, species, stage, SPECIES)
    c.hunger = c.happiness = c.energy = 90
    beh = Behaviour(rng)
    said = []
    mind = Mind(rng, None, said.append, lambda n: None)
    mind.attach(c, beh)
    return c, beh, mind, said


def tick(c, beh, mind, seconds, cursor=None, dt=1 / 30):
    sp = SPECIES[c.species]
    for _ in range(int(seconds / dt)):
        mind.update(dt, cursor, None, False, 14.0, "clear")
        beh.update(dt, c, sp)


class QuirkTests(unittest.TestCase):
    def test_three_quirks_respecting_exclusions(self):
        for seed in range(200):
            rng = random.Random(seed)
            p = Personality({t: rng.random() for t in ("playfulness", "sociability", "curiosity",
                                                      "independence", "stubbornness")})
            q = [x["id"] for x in assign_quirks(p, rng)]
            self.assertEqual(len(set(q)), 3)
            for a, b in EXCLUSIVE:
                self.assertFalse(a in q and b in q)

    def test_quirks_unlock_with_age(self):
        c, *_ = setup()
        c.quirks = [{"id": "observer", "from": "baby"}, {"id": "explorer", "from": "teen"}]
        c.stage = "child"
        self.assertTrue(has_quirk(c, "observer"))
        self.assertFalse(has_quirk(c, "explorer"))
        c.stage = "adult"
        self.assertTrue(has_quirk(c, "explorer"))

    def test_old_saves_get_quirks(self):
        c, *_ = setup()
        data = c.to_dict()
        del data["quirks"], data["routine"]
        c2 = Creature.from_dict(data)
        self.assertEqual(len(c2.quirks), 3)
        self.assertEqual(len(c2.routine), 24)


class BehaviourPlanTests(unittest.TestCase):
    def test_interrupted_activity_resumes(self):
        c, beh, mind, _ = setup()
        beh._c, beh._sp = c, SPECIES[c.species]
        beh.start_plan([act("window", 10.0, tag="window")])
        tick(c, beh, mind, 2.0)
        beh.interject([act("notice", 1.0)])
        self.assertEqual(beh.state, "notice")
        tick(c, beh, mind, 1.2)
        self.assertEqual(beh.state, "window")       # carried on, didn't reset to idle

    def test_moves_reach_target_and_depth(self):
        c, beh, mind, _ = setup()
        beh._c, beh._sp = c, SPECIES[c.species]
        beh.start_plan([move(120, z=1.0, speed=2), act("idle", 5)])
        tick(c, beh, mind, 6)
        self.assertAlmostEqual(beh.x, 120, delta=1)
        self.assertGreater(beh.z, 0.9)

    def test_sleeps_in_bed(self):
        c, beh, mind, _ = setup()
        mind.rng = random.Random(0)
        mind.sleep_spot = lambda c, beh: BED_X
        c.asleep = True
        tick(c, beh, mind, 15)
        self.assertEqual(beh.state, "sleep")
        self.assertAlmostEqual(beh.x, BED_X, delta=1.5)

    def test_long_autonomous_run_is_stable_and_varied(self):
        c, beh, mind, _ = setup()
        mind.idle_t = 100          # alone: secret activities allowed
        seen = set()
        for _ in range(30 * 400):
            mind.update(1 / 30, None, None, False, 14.0, "rain")
            beh.update(1 / 30, c, SPECIES[c.species])
            seen.add(beh.state)
            self.assertTrue(4 <= beh.x <= 160)
        self.assertGreaterEqual(len(seen), 10, seen)


class AwarenessTests(unittest.TestCase):
    def test_eyes_follow_cursor(self):
        c, beh, mind, _ = setup()
        beh.x = 80
        mind.look_on, mind.look_t = True, 99
        tick(c, beh, mind, 0.2, cursor=(20, 95))
        self.assertIn(mind.gaze(), ("l", "ul"))
        mind.hover_pet = True
        self.assertEqual(mind.gaze(), "u")

    def test_return_after_absence_triggers_greeting(self):
        c, beh, mind, _ = setup()
        tick(c, beh, mind, 1)
        mind.on_focus(False)
        mind.away_t = 120
        mind.on_focus(True)
        self.assertEqual(beh.tag, "greet")

    def test_secret_activity_gets_caught(self):
        c, beh, mind, _ = setup()
        beh._c, beh._sp = c, SPECIES[c.species]
        beh.start_plan([act("silly", 10, tag="secret")])
        mind.on_return(120)
        self.assertEqual(beh.state, "caught")

    def test_click_spam_annoys_stubborn_pet(self):
        c, beh, mind, said = setup()
        c.personality.traits["stubbornness"] = 0.9
        for _ in range(4):
            mind.on_click_room(40, 95)
        self.assertGreater(mind.emo["grumpy"], 0.3)
        self.assertTrue(any("ears" in s for s in said))

    def test_lonely_when_left_alone(self):
        c, beh, mind, _ = setup()
        mind.focused = False
        tick(c, beh, mind, 200, dt=0.5)
        self.assertGreater(mind.emo["lonely"], 0.4)


class MemoryTests(unittest.TestCase):
    def test_routine_recognition(self):
        c, beh, mind, _ = setup()
        base = 1_760_000_000
        for day in range(5):
            mind.world_time = base + day * 86400
            mind.record_routine()
        import time as _t
        mind.hour = _t.localtime(base).tm_hour + 0.1
        self.assertTrue(mind.routine_expected())
        mind.hour = (mind.hour + 6) % 24
        self.assertFalse(mind.routine_expected())

    def test_neglect_makes_wary_and_fades(self):
        c, beh, mind, _ = setup()
        mind.on_mistake()
        mind.on_mistake()
        self.assertGreater(c.wariness, 0.5)
        mind.update_sim(48 * 3600)
        self.assertLess(c.wariness, 0.1)

    def test_medicine_association(self):
        c, beh, mind, _ = setup()
        for _ in range(3):
            mind.note_action("medicine")
        self.assertGreaterEqual(c.assoc["medicine"], 2)
        beh._c, beh._sp = c, SPECIES[c.species]
        beh.start_plan([act("idle", 5)])
        mind.update(0.1, None, "medicine", False, 14.0, "clear")
        tick(c, beh, mind, 0.6)
        self.assertIn(beh.state, ("walk", "nervous"))

    def test_gift_after_good_care(self):
        c, beh, mind, said = setup()
        c.memory.attachment = 90
        c.wariness = 0
        c.last_gift_age = -1e9
        mind.focused = False
        for _ in range(500):
            mind._hourly()
            if mind.gift:
                break
        self.assertIsNotNone(mind.gift)
        self.assertEqual(mind.collect_gift() in ("flower", "leaf", "drawing", "pebble"), True)
        self.assertIsNone(mind.gift)


class PrefsAndResetTests(unittest.TestCase):
    def test_prefs_roundtrip_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.json")
            self.assertEqual(load_prefs(path)["theme_hue"], "pet")
            save_prefs(path, {"theme_hue": 262, "dark": True})
            self.assertEqual(load_prefs(path), {"theme_hue": 262, "dark": True, "wander": True,
                                                "experimental": True, "mirror": False})

    def test_reset_from_the_game(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            save = os.path.join(d, "s.json")
            g = Game(["--save", save, "--mute"])
            g.records.discover("bobbit", SPECIES)
            g.records.gifts["leaf"] = 2
            g.save()
            g.set_pref("dark", True)
            g.ask("reset_soft")
            g.confirm_answer(True)
            self.assertIn("bobbit", g.records.discovered)
            self.assertEqual(g.c.stage, "egg")
            g.ask("reset_hard")
            g.confirm_answer(True)
            self.assertEqual(g.records.discovered, [])
            self.assertEqual(g.records.gifts["leaf"], 0)
            self.assertTrue(load_prefs(os.path.join(d, "preferences.json"))["dark"])  # theme survives
            self.assertTrue(os.path.exists(save + ".reset-backup"))
            g.draw()   # all themes/panels draw without errors
            for panel in ("settings", "status", "records"):
                g.panel = panel
                g.draw()
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
