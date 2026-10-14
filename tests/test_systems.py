"""Tests for the core gameplay systems.

Run from the project folder:   python -m unittest discover -s tests -v
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

from game import care, config, evolution, genetics  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.minigames import GAME_CLASSES  # noqa: E402
from game.records import Records  # noqa: E402
from game.save import save_game, load_game  # noqa: E402

SETTINGS = config.load_settings()
SPECIES = config.load_species()
NOON = 12.0


def hatched(seed=1, stage="baby", species="pipling"):
    rng = random.Random(seed)
    c = Creature("Testy", genetics.random_genome(rng), 1, rng)
    evolution.apply(c, species, stage, SPECIES)
    return c, rng


def obedient(c):
    """Remove randomness from refusals for deterministic tests."""
    for t in c.personality.traits:
        c.personality.traits[t] = 0.3
    c.personality.traits["playfulness"] = 0.9
    c.discipline = 100
    for f in c.memory.food_likes:
        c.memory.food_likes[f] = 0.0


class NeedsTests(unittest.TestCase):
    def test_needs_decay_over_time(self):
        c, rng = hatched(stage="child", species="bobbit")
        care.tick(c, 3600, NOON, SETTINGS, rng)
        self.assertLess(c.hunger, 80)
        self.assertLess(c.happiness, 80)
        self.assertGreaterEqual(c.hunger, 0)

    def test_hearts_mapping(self):
        self.assertEqual(Creature.hearts(100), 4)
        self.assertEqual(Creature.hearts(75), 3)
        self.assertEqual(Creature.hearts(1), 1)
        self.assertEqual(Creature.hearts(0), 0)

    def test_feeding_restores_hunger_and_adds_weight(self):
        c, rng = hatched()
        obedient(c)
        c.hunger, w = 20, c.weight
        fb = care.feed(c, "rice", rng)
        self.assertEqual(c.hunger, 50)
        self.assertGreater(c.weight, w)
        self.assertEqual(fb.reaction, "eat")

    def test_full_creature_refuses_meal(self):
        c, rng = hatched()
        c.hunger = 100
        fb = care.feed(c, "fish", rng)
        self.assertEqual(fb.reaction, "refuse")

    def test_ignored_hunger_is_a_care_mistake(self):
        c, rng = hatched(stage="child", species="bobbit")
        c.hunger = 0
        care.tick(c, 30, NOON, SETTINGS, rng)
        self.assertEqual(c.attention, "hungry")
        for _ in range(40):
            care.tick(c, 30, NOON, SETTINGS, rng)
        self.assertEqual(c.care_mistakes, 1)

    def test_answering_call_avoids_mistake(self):
        c, rng = hatched(stage="child", species="bobbit")
        obedient(c)
        c.hunger = 0
        care.tick(c, 30, NOON, SETTINGS, rng)
        care.feed(c, "fish", rng)
        for _ in range(40):
            care.tick(c, 30, NOON, SETTINGS, rng)
        self.assertEqual(c.care_mistakes, 0)

    def test_clean_and_medicine(self):
        c, rng = hatched()
        c.poops, c.hygiene = 3, 20
        care.clean(c)
        self.assertEqual((c.poops, c.hygiene), (0, 100))
        c.sick, c.doses = True, 2
        care.medicine(c)
        self.assertTrue(c.sick)
        fb = care.medicine(c)
        self.assertFalse(c.sick)
        self.assertEqual(fb.reaction, "recover")

    def test_scold_only_works_on_misbehaviour(self):
        c, rng = hatched(stage="child", species="bobbit")
        c.attention = "fake"
        care.scold(c, rng)
        self.assertGreater(c.discipline, 0)
        before = c.happiness
        care.scold(c, rng)            # unjust scolding
        self.assertLess(c.happiness, before)

    def test_praise_in_good_window_raises_discipline_and_habit(self):
        c, rng = hatched(stage="child", species="bobbit")
        c.good_window = 5
        care.praise(c, "jump")
        self.assertEqual(c.discipline, 10)
        self.assertIn("jump", c.memory.habits)

    def test_sleep_and_lights(self):
        c, rng = hatched(stage="child", species="bobbit")
        events = care.tick(c, 60, 21.0, SETTINGS, rng)
        self.assertIn("sleep", events)
        care.tick(c, 60, 21.0, SETTINGS, rng)
        self.assertEqual(c.attention, "lights")
        care.toggle_lights(c)
        self.assertIsNone(c.attention)
        events = care.tick(c, 60, 9.0, SETTINGS, rng)
        self.assertIn("wake", events)

    def test_health_never_hits_zero(self):
        c, rng = hatched(stage="child", species="bobbit")
        for _ in range(48):
            care.tick(c, 3600, NOON, SETTINGS, rng)
        self.assertGreaterEqual(c.health, 5)


class OfflineTests(unittest.TestCase):
    def test_gentle_offline_caps_mistakes(self):
        c, rng = hatched(stage="child", species="bobbit")
        c.offline_neglect = False
        for _ in range(8 * 60):
            care.tick(c, 60, NOON, SETTINGS, rng, gentle=True)
        self.assertEqual(c.care_mistakes, 0)     # gentle mode only raises a flag
        self.assertLessEqual(c.poops, 3)


class EvolutionTests(unittest.TestCase):
    def test_baby_branches(self):
        c, rng = hatched()
        self.assertEqual(evolution.choose_next(c, rng)[0], "bobbit")
        c.stage_mistakes = 3
        self.assertEqual(evolution.choose_next(c, rng)[0], "grumpkin")

    def test_child_branches(self):
        c, rng = hatched(stage="child", species="bobbit")
        c.discipline = 80
        self.assertEqual(evolution.choose_next(c, rng)[0], "sprouty")

    def test_adult_branches(self):
        c, rng = hatched(stage="teen", species="sprouty")
        c.discipline, c.care_mistakes, c.memory.attachment = 90, 5, 10
        c.genome["mutation"] = None
        results = {evolution.choose_adult(c, random.Random(s)) for s in range(30)}
        self.assertIn("luminelle", results)
        c2, _ = hatched(stage="teen", species="scruff")
        c2.stage_mistakes = 6
        c2.genome["mutation"] = None
        res2 = {evolution.choose_adult(c2, random.Random(s)) for s in range(30)}
        self.assertIn("grumblin", res2)

    def test_secret_celestine_possible(self):
        c, rng = hatched(stage="teen", species="sprouty")
        c.discipline, c.care_mistakes, c.memory.attachment, c.happiness = 95, 0, 90, 90
        c.genome["mutation"] = None
        res = {evolution.choose_adult(c, random.Random(s)) for s in range(60)}
        self.assertIn("celestine", res)

    def test_all_targets_exist(self):
        rng = random.Random(3)
        for _ in range(300):
            c, _ = hatched(seed=rng.randrange(10 ** 6), stage="teen",
                           species=rng.choice(["sprouty", "zippit", "scruff"]))
            c.discipline = rng.uniform(0, 100)
            c.stage_mistakes = c.care_mistakes = rng.randint(0, 9)
            self.assertIn(evolution.choose_adult(c, rng), SPECIES)


class LifecycleTests(unittest.TestCase):
    def test_full_accelerated_lifecycle_and_generations(self):
        """Egg -> elder -> new egg, three generations, with a simple auto-carer."""
        rng = random.Random(7)
        c = Creature("Auto", genetics.random_genome(rng), 1, rng)
        records = Records()
        hour = 10.0
        seen_stages = set()
        generations = 0
        steps = 0
        while generations < 3 and steps < 400000:
            steps += 1
            care.tick(c, 300, hour, SETTINGS, rng)
            hour = (hour + 300 / 3600.0) % 24
            if c.stage != "egg":   # auto-carer
                if c.hunger < 40:
                    care.feed(c, "fish", rng)
                if c.happiness < 40 and not c.asleep and not c.sick:
                    care.apply_game(c, "timing", rng.random() < 0.6, rng)
                if c.poops:
                    care.clean(c)
                if c.sick:
                    care.medicine(c)
                if c.asleep and c.lights_on:
                    care.toggle_lights(c)
                if not c.asleep and not c.lights_on:
                    care.toggle_lights(c)
                if c.attention == "fake":
                    care.scold(c, rng)
            seen_stages.add(c.stage)
            if evolution.is_due(c, SETTINGS):
                target, stage = evolution.choose_next(c, rng)
                if stage == "depart":
                    records.add_lineage(c, SPECIES, "elder")
                    genome, _ = genetics.inherit(c.genome, c.personality.traits, rng)
                    c = Creature("Auto", genome, c.generation + 1, rng)
                    generations += 1
                else:
                    evolution.apply(c, target, stage, SPECIES)
                    records.discover(target, SPECIES)
        self.assertEqual(generations, 3)
        self.assertEqual(seen_stages, {"egg", "baby", "child", "teen", "adult", "elder"})
        self.assertEqual(len(records.lineage), 3)
        self.assertEqual(c.generation, 4)
        self.assertTrue(records.longest)
        self.assertLess(records.lineage[0]["care_mistakes"], 6)


class PersistenceTests(unittest.TestCase):
    def test_save_load_roundtrip(self):
        c, rng = hatched(stage="adult", species="frolicat")
        c.care_mistakes, c.discipline, c.poops = 2, 55, 1
        c.memory.reinforce_habit("dance")
        c.personality.nudge("curiosity", 0.2)
        records = Records()
        records.discover("frolicat", SPECIES)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            save_game(path, {"creature": c.to_dict(), "records": records.to_dict(), "world_time": 5.0})
            data = load_game(path)
        c2 = Creature.from_dict(data["creature"])
        self.assertEqual(c2.to_dict(), json.loads(json.dumps(c.to_dict())))
        self.assertEqual(Records.from_dict(data["records"]).discovered, ["frolicat"])

    def test_corrupt_save_falls_back_to_backup(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            save_game(path, {"creature": {"name": "A"}})
            save_game(path, {"creature": {"name": "B"}})   # A becomes .bak
            with open(path, "w") as f:
                f.write("{not json")
            self.assertEqual(load_game(path)["creature"]["name"], "A")


class GeneticsTests(unittest.TestCase):
    def test_inheritance_is_close_to_parent(self):
        rng = random.Random(2)
        parent = genetics.random_genome(rng)
        traits = {"playfulness": 0.9, "sociability": 0.5, "curiosity": 0.5,
                  "independence": 0.5, "stubbornness": 0.1}
        diffs = []
        for _ in range(100):
            child, _ = genetics.inherit(parent, traits, rng)
            d = abs(child["hue"] - parent["hue"]) % 360
            diffs.append(min(d, 360 - d))
            self.assertGreater(child["tendencies"]["playfulness"], 0.6)
            self.assertLess(child["tendencies"]["stubbornness"], 0.4)
        self.assertLess(sum(diffs) / len(diffs), 25)


class MiniGameTests(unittest.TestCase):
    def test_games_complete(self):
        for gid, cls in GAME_CLASSES.items():
            c, rng = hatched(stage="child", species="bobbit")
            g = cls(c, rng)
            for _ in range(2000):
                g.on_input("action" if gid == "timing" else "left")
                g.update(0.1)
                if g.closed:
                    break
            self.assertTrue(g.closed, gid)
            self.assertEqual(g.won, g.score >= g.need)

    def test_timing_hit_detection(self):
        c, rng = hatched(stage="child", species="bobbit")
        g = GAME_CLASSES["timing"](c, rng)
        g.pos = g.zone
        self.assertEqual(g.on_input("action"), "point")


class SpriteTests(unittest.TestCase):
    def test_every_species_renders_distinctly(self):
        import pygame
        pygame.init()
        pygame.display.set_mode((8, 8))
        from game.sprites import SpriteRenderer
        r = SpriteRenderer(SPECIES)
        genome = {"hue": 120, "sat": 0.6, "marking": "none"}
        seen = set()
        for sid in SPECIES:
            s = r.creature(sid, genome, False, {"eyes": "open", "mouth": "smile"})
            self.assertEqual(s.get_size(), (32, 32))
            mask = pygame.mask.from_surface(s)
            self.assertGreater(mask.count(), 60, sid)
            seen.add(bytes(pygame.image.tobytes(r.silhouette(sid), "RGBA")))
        self.assertEqual(len(seen), len(SPECIES))   # every silhouette is unique


if __name__ == "__main__":
    unittest.main()
