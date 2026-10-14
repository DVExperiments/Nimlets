"""Tests for the artificial-life layer: world, diary, beliefs, signals,
anomalies, creations, the frontier, escape trips, wandering the device and
the new UI pieces.  Run:  python -m unittest discover -s tests -v
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

from game import care, config, evolution, genetics, learning  # noqa: E402
from game.behaviour import Behaviour  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.journal import Journal  # noqa: E402
from game.living import BOWL_X, Mind  # noqa: E402
from game.world import MURAL_RECT, PILE_MAX, World  # noqa: E402

SPECIES = config.load_species()
SETTINGS = config.load_settings()


def setup(seed=5, species="frolicat", stage="adult"):
    rng = random.Random(seed)
    c = Creature("Ari", genetics.random_genome(rng), 1, rng)
    evolution.apply(c, species, stage, SPECIES)
    c.hunger = c.happiness = c.energy = 90
    beh = Behaviour(rng)
    log = []
    mind = Mind(rng, None, lambda t: None, lambda n: None,
                lambda kind, text, icon=None, important=False: log.append((kind, text, important)))
    mind.attach(c, beh, World())
    beh._c, beh._sp = c, SPECIES[c.species]
    return c, beh, mind, log


def daytime(g):
    import time as _t
    lt = _t.localtime(g.world_time)
    g.world_time += ((14 - lt.tm_hour) % 24) * 3600


def run(c, beh, mind, seconds, dt=1 / 30, cursor=None):
    for _ in range(int(seconds / dt)):
        mind.update(dt, cursor, None, False, 14.0, "clear")
        beh.update(dt, c, SPECIES[c.species])


class WorldJournalTests(unittest.TestCase):
    def test_world_roundtrip_and_limits(self):
        w = World()
        for _ in range(PILE_MAX + 5):
            w.add_item("pebble")
        self.assertEqual(len(w.pile["items"]), PILE_MAX)
        mx, my, mw, mh = MURAL_RECT
        added = w.add_mural([(mx + 1, my + 1, (1, 2, 3)), (0, 0, (1, 2, 3))], 2, "Ari")
        self.assertEqual(added, 1)                     # off-wall pixel rejected
        w2 = World.from_dict(json.loads(json.dumps(w.to_dict())))
        self.assertEqual(w2.mural, w.mural)
        self.assertEqual(w2.mural_artists, {"2": "Ari"})

    def test_journal_merge_unseen_and_persistence(self):
        j = Journal()
        j.add("ball", "Ari played.", 1000)
        j.add("ball", "Ari played.", 1100)
        self.assertEqual(len(j.entries), 1)
        self.assertEqual(Journal.label(j.entries[0]), "Ari played. (x2)")
        j.mark_seen()
        self.assertEqual(j.unseen(), [])
        j.add("ball", "Ari played.", 1200)              # repeats while away become unseen again
        self.assertEqual(len(j.unseen()), 1)
        j2 = Journal.from_dict(json.loads(json.dumps(j.to_dict())))
        self.assertEqual(len(j2.unseen()), 1)


class BeliefSignalTests(unittest.TestCase):
    def test_belief_forms_and_is_announced_once(self):
        c, *_ = setup()
        texts = [learning.update_belief(c, "bed_safe", 1.0, 0.3) for _ in range(6)]
        self.assertEqual(sum(1 for t in texts if t), 1)
        self.assertGreater(learning.belief(c, "bed_safe"), 0.45)

    def test_bowl_experiment_updates_belief(self):
        c, beh, mind, log = setup()
        mind.experiment = {"name": "bowl_summons", "t": 0}
        mind.note_action("feed", "rice")
        self.assertGreater(learning.belief(c, "bowl_summons"), 0)
        mind.experiment = {"name": "bowl_summons", "t": 13.9}
        run(c, beh, mind, 0.5)
        self.assertIsNone(mind.experiment)

    def test_fearful_pet_avoids_cursor_then_learns_trust(self):
        c, beh, mind, log = setup()
        c.beliefs["touch"]["v"] = -0.5
        self.assertTrue(mind.fearful())
        for _ in range(12):
            mind.cd["brave"] = 0
            mind.near_still_t = 5
            mind._track_cursor(1 / 30, (beh.x + 5, 90))
        self.assertFalse(mind.fearful())


class AnomalyTests(unittest.TestCase):
    def test_chimera_and_egg_types_render(self):
        import pygame
        pygame.init()
        pygame.display.set_mode((8, 8))
        from game.sprites import SpriteRenderer
        r = SpriteRenderer(SPECIES)
        rng = random.Random(1)
        for mut in genetics.MUTATIONS:
            g = genetics.random_genome(rng)
            g["mutation"] = mut
            if mut == "chimera":
                g["chimera"] = genetics.chimera_parts(rng, g["hue"])
            self.assertEqual(r.egg(g).get_size(), (32, 32))
            self.assertTrue(genetics.egg_name(g))
            self.assertEqual(r.creature("hootle", g, False, {"eyes": "open"}).get_size(), (32, 32))
        plain = genetics.random_genome(rng)
        plain["mutation"] = None
        chim = dict(plain, mutation="chimera", chimera={"parts": {"ears": "bunny", "tail": "bolt", "wings": True},
                                                        "hue2": 10})
        a = pygame.image.tobytes(r.creature("bobbit", plain, False, {}), "RGBA")
        b = pygame.image.tobytes(r.creature("bobbit", chim, False, {}), "RGBA")
        self.assertNotEqual(a, b)

    def test_behavioural_mutation_emerges_later(self):
        c, beh, mind, log = setup()
        c.genome["bmut"] = {"id": "nocturnal", "emerge_days": 3}
        c.age = 1 * 86400
        mind._hourly()
        self.assertFalse(c.bmut_active)
        c.age = 3.5 * 86400
        mind._hourly()
        self.assertTrue(c.bmut_active)
        self.assertTrue(any(k == "mutation" for k, *_ in log))
        self.assertTrue(care.is_bedtime(c, 12, SETTINGS))       # nocturnal sleeps by day
        self.assertFalse(care.is_bedtime(c, 23, SETTINGS))

    def test_inheritance_can_pass_behaviour_quietly(self):
        rng = random.Random(4)
        parent = genetics.random_genome(rng)
        parent["bmut"] = {"id": "collector", "emerge_days": 2}
        kept = 0
        for _ in range(200):
            child, notes = genetics.inherit(parent, {}, rng)
            kept += bool(child["bmut"] and child["bmut"]["id"] == "collector")
            self.assertFalse(any("collector" in n for n in notes))   # it must be discovered
        self.assertGreater(kept, 20)


class CreationTests(unittest.TestCase):
    def test_drawing_collection_bed_and_invention(self):
        c, beh, mind, log = setup()
        mind.idle_t = 100
        mind.experimental_on = False      # (no trinkets rolling under the plant in this test)
        for choice in ("draw", "collect", "move_bed", "invent", "invent", "invent"):
            beh.start_plan(mind._plan(choice, c, beh))
            run(c, beh, mind, 16)
        w = mind.world
        self.assertGreater(len(w.mural), 0)
        self.assertGreaterEqual(len(w.pile["items"]), 1)
        self.assertNotAlmostEqual(w.bed_x, 30.0, delta=5)
        kinds = {k for k, *_ in log}
        self.assertTrue({"draw", "collect", "bed"} <= kinds, kinds)

    def test_next_generation_studies_old_drawing(self):
        c, beh, mind, log = setup()
        mind.world.add_mural(mind._motif(60), 1, "Ari")
        child = Creature("Bo", genetics.random_genome(random.Random(9)), 2, random.Random(9))
        evolution.apply(child, "bobbit", "child", SPECIES)
        mind.reset_for(child)
        mind.attach(child, beh)
        beh._c, beh._sp = child, SPECIES["bobbit"]
        beh.start_plan(mind._plan("study_mural", child, beh))
        run(child, beh, mind, 10)
        self.assertTrue(any(k == "culture" and "Ari" in t for k, t, _ in log))

    def test_ball_can_land_in_bowl(self):
        c, beh, mind, log = setup()
        mind.ball_x = BOWL_X + 30
        mind.kick_ball_to(BOWL_X)
        run(c, beh, mind, 3)
        self.assertTrue(mind.world.ball_in_bowl)


class FrontierTests(unittest.TestCase):
    def test_progression_to_escape(self):
        c, beh, mind, log = setup()
        for _ in range(8):
            beh.start_plan(mind._frontier(c))
            run(c, beh, mind, 8)
        self.assertGreaterEqual(c.frontier["stage"], 2)
        mind.rng.seed(2)
        for _ in range(20):
            plan = mind._frontier(c)
            if any((s.get("fx") or "").startswith("escape") for s in plan):
                break
        beh.start_plan(plan)
        run(c, beh, mind, 6)
        self.assertIsNotNone(mind.escape_request)

    def test_trip_through_the_interface(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            for _ in range(4):
                g.c.stage_age = 1e9
                for _ in range(140):
                    g.update(1 / 30)
            daytime(g)
            g.c.asleep, g.c.hunger, g.c.happiness = False, 90, 90
            g.draw()
            g.start_trip(False)
            visited = set()
            for _ in range(30 * 25):
                g.update(1 / 30)
                g.draw()
                if g.trip:
                    visited.add(g.trip.steps[g.trip.i]["at"][0])
                else:
                    break
            self.assertIsNone(g.trip)
            self.assertTrue({"hearts", "clock", "settings"} <= visited, visited)
            self.assertEqual(g.c.frontier["escapes"], 1)
            # pressing a care button mid-trip brings it straight home
            g.start_trip(False)
            for _ in range(60):
                g.update(1 / 30)
                g.draw()
            g.do_action(6)       # status: allowed during a trip
            self.assertIsNotNone(g.trip)
            g.do_action(2)       # clean: it hurries home
            self.assertIsNone(g.trip)
            pygame.quit()

    def test_wander_tours_the_device_and_never_leaves_the_window(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "2"])
            for _ in range(30 * 30):
                if g.c.stage == "adult" and not g.blocked():
                    break
                if not g.blocked():
                    g.c.stage_age = 1e9
                g.update(1 / 30)
            daytime(g)                          # a sleepy pet cuts its trip short, so keep it afternoon
            g.c.energy = 100.0
            g.c.asleep = False
            g.draw()
            g.start_trip(True)
            visited = set()
            W, H = g.L.W, g.L.H
            for _ in range(30 * 120):
                if not g.trip:
                    break
                step = g.trip.steps[g.trip.i]
                visited.add(step["at"][0])
                g.update(1 / 30)
                if g.trip and g.trip.pos:
                    x, y = g.trip.pos
                    self.assertTrue(0 <= x <= W and 0 <= y <= H, (x, y))     # stays inside the app
                g.draw()
            self.assertIsNone(g.trip)
            self.assertTrue({"abc", "msg", "tabtop", "tabside", "hearts", "clock"} <= visited)
            self.assertEqual(g.c.frontier["roams"], 1)
            self.assertTrue(g.world.souvenirs)
            self.assertTrue(any("wander around the whole device" in e["text"] for e in g.journal.entries))
            pygame.quit()


class AppFeatureTests(unittest.TestCase):
    def test_food_goes_in_the_bowl_and_is_eaten(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            for _ in range(3):
                g.c.stage_age = 1e9
                for _ in range(140):
                    g.update(1 / 30)
            daytime(g)
            c = g.c
            c.hunger, c.asleep, c.sick = 30, False, False
            for t in c.personality.traits:
                c.personality.traits[t] = 0.2
            c.discipline = 100
            for f in c.memory.food_likes:
                c.memory.food_likes[f] = 0.0
            g.do_action(0)
            g.menu_select(0)
            self.assertIsNotNone(g.world.bowl_food)
            ate = False
            for _ in range(30 * 8):
                g.update(1 / 30)
                g.draw()
                ate = ate or (g.beh.state == "eat" and abs(g.beh.x - BOWL_X) < 16)
            self.assertTrue(ate)
            self.assertIsNone(g.world.bowl_food)
            pygame.quit()

    def test_offline_life_writes_diary_and_away_summary(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            save = os.path.join(d, "s.json")
            g = Game(["--save", save, "--mute", "--seed", "3"])
            for _ in range(4):
                g.c.stage_age = 1e9
                for _ in range(140):
                    g.update(1 / 30)
            g.save()
            pygame.quit()
            with open(save) as f:
                data = json.load(f)
            # an 8-hour absence ending at 6 pm today, so it's always daytime and the pet is up and
            # about (it used to end "now", and overnight absences were sometimes all sleep)
            import time as _t
            from unittest import mock
            lt = _t.localtime()
            back = _t.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 18, 0, 0, 0, 0, -1))
            data["saved_at"] = data["world_time"] = back - 8 * 3600
            with open(save, "w") as f:
                json.dump(data, f)
            with mock.patch("time.time", return_value=back):
                g2 = Game(["--save", save, "--mute", "--seed", "3"])
            self.assertTrue(g2.journal.unseen())
            self.assertEqual(g2.panel, "away")
            g2.draw()
            g2.close_away(diary=True)
            self.assertEqual((g2.panel, g2.records_tab), ("records", 3))
            self.assertEqual(g2.journal.unseen(), [])
            g2.draw()
            pygame.quit()

    def test_reset_flag_ignores_backup(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            save = os.path.join(d, "s.json")
            g = Game(["--save", save, "--mute"])
            g.c.stage_age = 1e9
            for _ in range(140):
                g.update(1 / 30)
            g.save()
            g.save()                       # creates .bak too
            pygame.quit()
            g2 = Game(["--save", save, "--reset", "--mute"])
            self.assertEqual(g2.c.stage, "egg")
            pygame.quit()

    def test_more_heart_slots(self):
        self.assertEqual(Creature.hearts(100, 6), 6)
        self.assertEqual(Creature.hearts(50, 6), 3)
        self.assertEqual(Creature.hearts(1, 6), 1)


if __name__ == "__main__":
    unittest.main()
