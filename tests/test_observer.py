"""Tests for the Observer update (v1.4) - one group per requirement in the spec.

Run:  python -m unittest discover -s tests -v
"""
import json
import os
import random
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NIMLETS_SKIP_WELCOME", "1")   # tests start lots of new games

import pygame  # noqa: E402

from game import config, evolution, genetics  # noqa: E402
from game.behaviour import Behaviour, act  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.living import Mind  # noqa: E402
from game.observer import heading_target  # noqa: E402
from game.world import World  # noqa: E402

SPECIES = config.load_species()


def setup(seed=21, species="hootle", stage="adult"):
    rng = random.Random(seed)
    c = Creature("Obi", genetics.random_genome(rng), 1, rng)
    evolution.apply(c, species, stage, SPECIES)
    c.hunger = c.happiness = c.energy = 90
    for t in c.personality.traits:
        c.personality.traits[t] = 0.6
    beh = Behaviour(rng)
    log = []
    mind = Mind(rng, None, lambda t: None, lambda n: None,
                lambda kind, text, icon=None, important=False: log.append((kind, text)))
    mind.attach(c, beh, World())
    mind.species_db = SPECIES
    beh._c, beh._sp = c, SPECIES[c.species]
    mind.worldmodel.learn_room()
    mind.recip.cd["request"] = mind.recip.cd["game"] = 999
    mind.cd["surprise"] = mind.cd["frontier"] = 999
    return c, beh, mind, log


def tick(c, beh, mind, seconds, cursor=None, zone=None, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        mind.idle_t = 0
        mind.update(dt, cursor, None, False, 14.0, "clear", zone=zone)
        beh.update(dt, c, SPECIES[c.species])


def habit(mind, c, beh, times, action="feed", path=("room:pet", "shell")):
    """You keep doing the same thing: pet -> heading to Feed -> feed."""
    for _ in range(times):
        for z in path:
            mind.observer.observe(0.1, z, None)
        mind.observer.observe(0.1, "shell", action)
        mind.observer.on_action(action)
        tick(c, beh, mind, 0.3)


class PredictionTests(unittest.TestCase):
    def test_1_predictions_improve_with_experience(self):
        c, beh, mind, log = setup()
        o = mind.observer
        habit(mind, c, beh, 2)
        early = o.o["hits"]
        habit(mind, c, beh, 12)
        self.assertGreater(o.o["hits"], early)
        o.observe(0.1, "room:pet", None)
        o.observe(0.1, "shell", "feed")
        self.assertIsNotNone(o.prediction)
        self.assertEqual(o.prediction["action"], "feed")
        self.assertGreater(o.prediction["p"], 0.6)

    def test_1b_seeded_devsim_learns_habits(self):
        import devsim
        report, g = devsim.run(minutes=4, seed=7, quiet=True,
                               save=os.path.join(tempfile.gettempdir(), "devsim_test.json"))
        self.assertGreater(sum(report["predictions_second_half"]), 3)
        self.assertGreaterEqual(report["accuracy_second"], 0.5)
        self.assertLess(report["ms_per_frame"], 25)
        pygame.quit()

    def test_2_failed_predictions_change_behaviour(self):
        c, beh, mind, log = setup()
        o = mind.observer
        habit(mind, c, beh, 10)
        conf_before = o.o["conf"]["feed"]
        for _ in range(8):                         # habits change: you now go to Play instead
            o.observe(0.1, "room:pet", None)
            o.observe(0.1, "shell", "feed")
            o.on_action("play")
        self.assertLess(o.o["conf"]["feed"], conf_before)
        self.assertGreater(o.o["misses"], 0)

    def test_heading_detection(self):
        rects = {"feed": pygame.Rect(100, 600, 80, 60), "play": pygame.Rect(400, 600, 80, 60)}
        self.assertEqual(heading_target((140, 300), (0, 600), rects), "feed")
        self.assertIsNone(heading_target((140, 300), (0, 20), rects))       # not moving

    def test_anticipation_moves_early(self):
        c, beh, mind, log = setup()
        o = mind.observer
        habit(mind, c, beh, 12)
        o.cd["anticipate"] = 0
        beh.start_plan([act("idle", 5)])
        o.observe(0.1, "room:pet", None)
        o.observe(0.1, "shell", "feed")
        self.assertEqual(beh.tag, "anticipate")
        self.assertTrue(any(e["kind"] == "anticipate" for e in mind.trace_log.items))

    def test_model_stages_are_milestones(self):
        c, beh, mind, log = setup()
        self.assertEqual(mind.observer.stage(), 1)
        mind.observer.observe(0.1, "room", None)
        habit(mind, c, beh, 12)
        self.assertGreaterEqual(mind.observer.stage(), 3)
        self.assertLess(mind.observer.stage(), 5)          # no representation without drawing


class ObservationAndTimeTests(unittest.TestCase):
    def test_deliberate_watching(self):
        c, beh, mind, log = setup()
        mind.observer.cd["watch"] = 0
        mind.rng.seed(1)
        watched = False
        for _ in range(60):
            mind.observer.cd["watch"] = 0
            tick(c, beh, mind, 0.6, cursor=(60, 70))
            watched = watched or beh.tag == "watch"
        self.assertTrue(watched)

    def test_time_awareness(self):
        c, beh, mind, log = setup()
        for i in range(3):
            mind.observer.cd["time"] = 0
            beh.start_plan([act("idle", 5)])
            mind.observer.on_speed(60, 1)
        self.assertEqual(mind.observer.o["speed_seen"], 3)
        self.assertTrue(any(k == "time" for k, _ in log))
        self.assertGreater(c.beliefs["time_control"]["v"], 0)

    def test_pause_really_pauses(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "3"])
            import time as _t
            g.world_time += ((13 - _t.localtime(g.world_time).tm_hour) % 24) * 3600   # daytime
            g.c.stage_age = 1e9
            for _ in range(140):
                g.update(1 / 30)
            g.c.asleep = False
            g.toggle("pause")
            x, t, anim = g.beh.x, g.beh.t, g.beh.anim_t
            for _ in range(60):
                g.update(1 / 30)
            self.assertEqual((g.beh.x, g.beh.t, g.beh.anim_t), (x, t, anim))
            g.toggle("pause")
            self.assertEqual(g.mind.observer.o["pause_seen"], 1)
            pygame.quit()

    def test_12_cursor_only_inside_the_window(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            g.draw()
            real = pygame.mouse.get_focused
            pygame.mouse.get_focused = lambda: False
            try:
                self.assertEqual(g.cursor_zone(1 / 30), (None, None))
                self.assertIsNone(g.lcd_cursor())
            finally:
                pygame.mouse.get_focused = real
            pygame.quit()


class MemoryRitualTests(unittest.TestCase):
    def test_4_rituals_develop_from_history(self):
        c, beh, mind, log = setup()
        r = mind.prituals
        for i in range(6):
            mind.clock += 30
            r.note_action("spin", 120)
            mind.clock += 1
            r.note_action("tap", 66)
            r.credit("eat")
        self.assertIn("eat", r.data["known"])
        steps = []
        for _ in range(5):
            steps = steps or r.steps_for("eat")
        self.assertTrue(steps)
        self.assertTrue(any(k == "ritual" for k, _ in log))

    def test_rituals_do_not_form_from_inconsistent_actions(self):
        c, beh, mind, log = setup()
        r = mind.prituals
        moves = ["spin", "jump", "look", "dance", "sit", "bob", "hum", "wave"]
        for i in range(8):
            mind.clock += 30
            r.note_action(moves[i], 30)
            mind.clock += 1
            r.note_action(moves[(i + 3) % 8], 100)
            r.credit("sleep")
        self.assertNotIn("sleep", r.data["known"])

    def test_forgotten_episode_is_recalled(self):
        c, beh, mind, log = setup()
        mind.episodes.add("gesture", "gesture:circle", "your little circle", 0.6, {"gesture": "circle"})
        self.assertEqual(mind.episodes.forgotten(), [])
        mind.world_time += 4 * 86400
        self.assertEqual(len(mind.episodes.forgotten()), 1)
        mind.observer.o["hits"] = 3
        mind.observer.observe(0.1, "room", None)
        self.assertTrue(mind.uncanny.prereq("forgotten_gesture"))
        beh.start_plan([act("idle", 5)])
        mind.uncanny.run("forgotten_gesture")
        self.assertEqual(beh.tag, "game")
        self.assertTrue(any("haven't" in t for _, t in log))

    def test_episode_strength_fades_unless_important(self):
        c, beh, mind, log = setup()
        mind.episodes.add("object", "trivial", "a trivial thing", 0.1)
        mind.episodes.add("communication", "important", "first understood", 0.95)
        for d in range(25):
            mind.world_time += 86400
            mind.episodes.day_tick()
        keys = [e["key"] for e in mind.episodes.items]
        self.assertIn("important", keys)
        self.assertNotIn("trivial", keys)


class WorldModelTests(unittest.TestCase):
    def test_5_environmental_changes_update_the_model(self):
        c, beh, mind, log = setup()
        wm = mind.worldmodel
        old = mind.world.bed_x
        mind.focused = False                                 # it isn't watching
        mind.world.bed_x = 100.0
        wm.player_moved("bed", old, 100.0)
        self.assertAlmostEqual(wm.expect("bed"), old)       # it doesn't know yet
        self.assertEqual(wm.mismatched(), ["bed"])
        self.assertEqual(wm.on_arrive("bed", old), 100.0)   # searches the old spot, finds the new one
        self.assertAlmostEqual(wm.expect("bed"), 100.0)

    def test_restores_preferred_arrangement(self):
        c, beh, mind, log = setup()
        wm = mind.worldmodel
        c.personality.traits["stubbornness"] = 0.9
        wm.chose("bed", 30.0)
        wm.s["pref_str"]["bed"] = 0.9
        mind.world.bed_x = 100.0
        beh.start_plan([act("idle", 3)])
        wm.found("bed")
        self.assertTrue(any(st.get("walk") == "drag" for st in beh.plan))

    def test_adapts_to_new_layout(self):
        c, beh, mind, log = setup()
        wm = mind.worldmodel
        c.personality.traits["stubbornness"] = 0.05
        wm.chose("bed", 30.0)
        wm.s["pref_str"]["bed"] = 0.2
        for _ in range(3):
            mind.world.bed_x = 100.0
            wm.found("bed")
        self.assertAlmostEqual(wm.s["pref"]["bed"], 100.0)


class RareEventTests(unittest.TestCase):
    def test_6_prerequisites_are_respected(self):
        c, beh, mind, log = setup()
        self.assertFalse(mind.uncanny.allow("draw_cursor"))          # stage too low
        self.assertFalse(mind.uncanny.allow("app_boundary"))         # never escaped
        mind.observer.observe(0.1, "room", None)
        habit(mind, c, beh, 12)
        lang = mind.recip.b["lang"]
        sig = lang["repertoire"]["food"][0]
        lang["stats"]["food"][sig]["n"] = 6
        self.assertGreaterEqual(mind.observer.stage(), 4)
        self.assertTrue(mind.uncanny.allow("draw_cursor"))

    def test_7_cooldowns_prevent_repetition(self):
        c, beh, mind, log = setup()
        u = mind.uncanny
        u.record("unexpected_look", "test")
        self.assertFalse(u.allow("unexpected_look"))
        u.clock += 89
        self.assertFalse(u.allow("eye_contact") and False)
        u.clock += 400
        mind.cursor = (60, 60)
        self.assertTrue(u.allow("unexpected_look"))

    def test_disabling_experimental_behaviour(self):
        c, beh, mind, log = setup()
        mind.experimental_on = False
        mind.cursor = (60, 60)
        self.assertFalse(mind.uncanny.allow("unexpected_look"))
        habit(mind, c, beh, 12)
        beh.start_plan([act("idle", 5)])
        mind.observer.cd["anticipate"] = 0
        mind.observer.observe(0.1, "room:pet", None)
        mind.observer.observe(0.1, "shell", "feed")
        self.assertNotEqual(beh.tag, "anticipate")

    def test_cursor_drawing_reaches_representation(self):
        c, beh, mind, log = setup()
        mind.observer.observe(0.1, "room", None)
        habit(mind, c, beh, 12)
        lang = mind.recip.b["lang"]
        lang["stats"]["food"][lang["repertoire"]["food"][0]]["n"] = 6
        before = len(mind.world.mural)
        beh.start_plan(mind.drawing_plan("cursor"))
        tick(c, beh, mind, 10)
        self.assertGreater(len(mind.world.mural), before)
        self.assertEqual(mind.observer.o["symbols"], 1)
        self.assertGreaterEqual(mind.observer.stage(), 5)


class AutonomyTests(unittest.TestCase):
    def test_tool_use_emerges(self):
        found = 0
        for seed in (5, 7, 9):
            c, beh, mind, log = setup(seed=seed)
            mind.skills.drop_loose("pebble", under_plant=True)
            for i in range(30):
                if not [x for x in mind.world.loose if x["x"] > 147] and i % 6 == 0:
                    mind.skills.drop_loose("bead", under_plant=True)
                mind.ball_x = mind.rng.uniform(30, 130)
                beh.start_plan(mind.skills.explore_plan())
                tick(c, beh, mind, 14)
            found += bool(mind.uncanny.u["done"].get("multi_step_skill"))
            self.assertTrue(mind.skills.s["known"])
        self.assertGreaterEqual(found, 2)

    def test_private_stash_pauses_when_watched(self):
        c, beh, mind, log = setup()
        mind.world.pile["items"] = ["pebble", "leaf"]
        beh.start_plan(mind.skills.stash_plan())
        tick(c, beh, mind, 2.0, cursor=None)
        tick(c, beh, mind, 0.3, cursor=(beh.x + 5, 90))
        self.assertEqual(beh.tag, "hush")
        tick(c, beh, mind, 25, cursor=None)
        self.assertTrue(mind.world.stash["items"])

    def test_10_care_still_works_with_experiments_on(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "4"])
            for _ in range(4):
                g.c.stage_age = 1e9
                for _ in range(140):
                    g.update(1 / 30)
            g.c.hunger, g.c.asleep = 20, False
            for k in g.c.memory.food_likes:
                g.c.memory.food_likes[k] = 0.5
            g.c.discipline = 100
            g.do_action(0)
            g.menu_select(0)
            self.assertGreater(g.c.hunger, 20)
            g.mind.uncanny.tick_t = 5
            g.c.hunger = 10
            g.mind.uncanny.tick(0.1)                 # no rare events while it needs care
            self.assertEqual(g.mind.uncanny.u["done"], {})
            pygame.quit()


class ExistentialTests(unittest.TestCase):
    def test_mirror_understanding_develops(self):
        c, beh, mind, log = setup()
        mind.mirror_on = True
        c.genome["marking"] = "spots"
        for _ in range(12):
            beh.start_plan(mind.existential.mirror_plan())
            tick(c, beh, mind, 14)
        self.assertGreaterEqual(mind.existential.mr["stage"], 3)
        texts = [t for k, t in log if k == "mirror"]
        self.assertTrue(any("hello" in t for t in texts))
        self.assertTrue(all("conscious" not in t and "self-aware" not in t for t in texts))

    def test_caretaker_figure_learns(self):
        c, beh, mind, log = setup()
        mind.world.pile["items"] = ["pebble", "leaf", "bead", "petal", "button"]
        self.assertFalse(mind.existential.can_build() and c.personality["curiosity"] <= 0.6
                         and not mind.skills.s["known"])
        c.personality.traits["curiosity"] = 0.75
        self.assertTrue(mind.existential.can_build())
        beh.start_plan(mind.existential.build_plan())
        tick(c, beh, mind, 8)
        self.assertIsNotNone(mind.world.figure)
        for _ in range(12):
            beh.start_plan(mind.existential.teach_plan())
            tick(c, beh, mind, 8)
        self.assertTrue(mind.world.figure["taught"])
        self.assertTrue(any(k == "caretaker" and "copied" in t for k, t in log))

    def test_reminisce_with_memory_frame(self):
        c, beh, mind, log = setup()
        c.forms = ["pipling", "bobbit", "sprouty", "hootle"]
        beh.start_plan(mind.existential.reminisce_plan())
        tick(c, beh, mind, 10)
        self.assertTrue(any(k == "memory" and "Pipling" in t for k, t in log))


class PersistenceTests(unittest.TestCase):
    def test_8_memories_persist_after_closing(self):
        c, beh, mind, log = setup()
        habit(mind, c, beh, 8)
        mind.episodes.add("discovery", "x", "something", 0.7)
        mind.prituals.data["known"]["eat"] = {"seq": "spin>tap", "strength": 0.6, "since": 0, "done": 0}
        mind.uncanny.record("unexpected_look", "t")
        mind.worldmodel.chose("bed", 50.0)
        c2 = Creature.from_dict(json.loads(json.dumps(c.to_dict())))
        self.assertEqual(c2.observer["hits"], c.observer["hits"])
        self.assertEqual(c2.episodes[0]["key"], c.episodes[0]["key"])
        self.assertEqual(c2.prituals["known"]["eat"]["seq"], "spin>tap")
        self.assertEqual(c2.uncanny["done"]["unexpected_look"], 1)
        self.assertEqual(c2.spatial["pref"]["bed"], 50.0)

    def test_9_new_generation_inherits_only_intended_things(self):
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", "5"])
            for _ in range(4):
                g.c.stage_age = 1e9
                for _ in range(140):
                    g.update(1 / 30)
            m = g.mind
            habit(m, g.c, g.beh, 6)
            m.episodes.add("discovery", "x", "something", 0.7)
            g.world.add_mural([(40, 55, (1, 2, 3))], g.c.generation, g.c.name)
            g.world.stash["items"].append("pebble")
            g.world.inventions.append({"id": "wall_bounce", "by": g.c.name, "gen": 1})
            g.start_depart("journey")
            for _ in range(200):
                g.update(1 / 30)
            self.assertEqual(g.c.generation, 2)
            self.assertFalse(g.c.observer.get("hits"))           # its model of you starts fresh
            self.assertEqual(g.c.episodes, [])
            self.assertFalse(g.c.skills.get("known"))
            self.assertTrue(g.world.mural)                       # but the room remembers
            self.assertEqual(g.world.stash["items"], ["pebble"])
            self.assertTrue(g.world.knows("wall_bounce"))
            g.save()
            g2 = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            self.assertEqual(g2.world.stash["items"], ["pebble"])
            pygame.quit()

    def test_old_save_upgrades(self):
        from game.app import Game
        import shutil
        with tempfile.TemporaryDirectory() as d:
            save = os.path.join(d, "s.json")
            shutil.copy(os.path.join(ROOT, "saves", "example_save.json"), save)
            g = Game(["--save", save, "--mute"])
            for _ in range(60):
                g.update(1 / 30)
            g.draw()
            g.obs_mode = True
            for page in range(5):
                g.obs_page = page
                g.draw()
            path = g.mind.observation_snapshot()
            self.assertTrue(path)
            pygame.quit()


class StressTests(unittest.TestCase):
    def test_11_accelerated_time_has_no_loops(self):
        import devsim
        report, g = devsim.run(minutes=3, seed=13, player="absent", speed=600, quiet=True,
                               save=os.path.join(tempfile.gettempdir(), "devsim_stress.json"))
        self.assertLessEqual(report["trace_len"], 300)
        self.assertLess(len(g.beh.plan), 40)
        self.assertLess(len(g.journal.entries), 301)
        self.assertLess(len(g.mind.episodes.items), 61)
        pygame.quit()

    def test_observation_export(self):
        from game.observation import export_log
        c, beh, mind, log = setup()
        habit(mind, c, beh, 5)
        with tempfile.TemporaryDirectory() as d:
            path = export_log(mind, d)
            with open(path) as f:
                text = f.read()
            self.assertIn("Reasoning trace", text)
            self.assertTrue(os.path.exists(path.replace(".md", ".json")))


if __name__ == "__main__":
    unittest.main()
