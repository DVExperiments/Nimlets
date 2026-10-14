"""Tests for v1.5: 28 forms, coins and the shop, and the interactive room.

Run:  python -m unittest discover -s tests -v
"""
import json
import os
import random
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NIMLETS_SKIP_WELCOME", "1")   # tests start lots of new games

import pygame  # noqa: E402

from game import config, evolution, genetics, shop  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.records import Records  # noqa: E402

SPECIES = config.load_species()


def make_game(d, seed=8, stages=4):
    from game.app import Game
    g = Game(["--save", os.path.join(d, "s.json"), "--mute", "--seed", str(seed)])
    g.world_time += ((13 - time.localtime(g.world_time).tm_hour) % 24) * 3600
    for _ in range(stages):
        g.c.stage_age = 1e9
        for _ in range(140):
            g.update(1 / 30)
    g.c.asleep, g.c.sick = False, False
    g.c.hunger = g.c.happiness = g.c.energy = 70
    return g


class CollectionTests(unittest.TestCase):
    def test_28_forms_with_a_full_tree(self):
        self.assertEqual(len(SPECIES), 28)
        by_stage = {}
        for sp in SPECIES.values():
            by_stage.setdefault(sp["stage"], []).append(sp["id"])
        self.assertEqual({k: len(v) for k, v in by_stage.items()}, {"baby": 2, "child": 4, "teen": 6, "adult": 16})
        self.assertEqual(sum(1 for sp in SPECIES.values() if sp.get("secret")), 4)

    def test_every_form_is_reachable(self):
        reached = set()
        rng = random.Random(1)
        for i in range(1500):
            g = genetics.random_genome(rng)
            c = Creature("T", g, 1, rng)
            for t in c.personality.traits:
                c.personality.traits[t] = rng.random()
            perfect = rng.random() < 0.2              # some carers are near-perfect
            while c.stage != "adult":
                c.discipline = rng.uniform(80, 100) if perfect else rng.uniform(0, 100)
                c.stage_mistakes = 0 if perfect else rng.choice([0, 0, 1, 3, 6, 8])
                c.care_mistakes = c.stage_mistakes + (0 if perfect else rng.choice([0, 0, 2, 6]))
                c.memory.attachment = rng.uniform(70, 100) if perfect else rng.uniform(0, 100)
                c.hist = {"hunger": 50.0, "happy": rng.uniform(60, 90) if perfect else rng.uniform(20, 90),
                          "weight": rng.uniform(15, 30), "hours": 1.0}
                if rng.random() < 0.03:
                    c.genome["bmut"] = {"id": "collector", "emerge_days": 1}
                target, stage = evolution.choose_next(c, rng)
                self.assertIn(target, SPECIES)
                evolution.apply(c, target, stage, SPECIES)
                reached.add(target)
        self.assertEqual(reached, set(SPECIES), set(SPECIES) - reached)

    def test_family_line_is_inherited(self):
        rng = random.Random(3)
        parent = genetics.random_genome(rng)
        parent["line"] = "water"
        kids = [genetics.inherit(parent, {}, rng)[0]["line"] for _ in range(200)]
        self.assertGreater(kids.count("water"), 150)
        old = dict(parent)
        old.pop("line")
        c = Creature("Old", old, 1, rng)
        self.assertEqual(evolution.choose_next(c, rng)[0], "pipling")     # old saves keep the old tree


class CoinShopTests(unittest.TestCase):
    def test_winning_a_minigame_earns_coins(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            from game.minigames import GAME_CLASSES
            g.minigame = GAME_CLASSES["timing"](g.c, g.rng)
            g.minigame.score = 3
            g.minigame.finish()
            for _ in range(80):
                g.update(1 / 30)
            self.assertGreaterEqual(g.records.coins, shop.COINS_FOR_WIN)
            self.assertEqual(g.records.coins, g.records.coins_earned)
            pygame.quit()

    def test_shop_entry_at_the_bottom_of_feed_and_play(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            g.do_action(0)
            self.assertEqual(g.menu.items[-1][1], "__shop__")
            g.menu_select(len(g.menu.items) - 1)
            self.assertEqual((g.panel, g.shop_tab), ("shop", "food"))
            g.draw()
            g.panel = None
            g.c.energy = 90
            g.mind.recip.cd["neg"] = 99
            g.do_action(1)
            if g.menu:
                self.assertEqual(g.menu.items[-1][1], "__shop__")
                g.menu_select(len(g.menu.items) - 1)
                self.assertEqual(g.shop_tab, "toy")
            pygame.quit()

    def test_buying_uses_the_item_immediately(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            g.records.coins = 30
            self.assertTrue(g.buy("starfruit"))
            self.assertEqual(g.records.coins, 30 - shop.ITEMS["starfruit"]["price"])
            self.assertEqual(g.world.bowl_food["id"], "starfruit")
            for _ in range(200):
                g.update(1 / 30)
            self.assertTrue(g.buy("music_box"))
            self.assertEqual(g.world.active_toy["id"], "music_box")
            self.assertEqual(g.beh.tag, "toy")
            for _ in range(30 * 20):
                g.update(1 / 30)
            self.assertIsNone(g.world.active_toy)              # one-time use
            self.assertEqual(g.records.bought, {"starfruit": 1, "music_box": 1})
            pygame.quit()

    def test_cannot_buy_without_coins_or_while_asleep(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            g.records.coins = 2
            self.assertFalse(g.buy("golden_apple"))
            self.assertEqual(g.records.coins, 2)
            g.records.coins = 50
            g.c.asleep = True
            self.assertFalse(g.buy("yarn_ball"))
            g.c.asleep, g.c.sick = False, True
            self.assertFalse(g.buy("yarn_ball"))
            self.assertTrue(g.buy("golden_apple"))             # the one treat that helps a sick pet
            self.assertFalse(g.c.sick and shop.ensure(g.c)["like"]["golden_apple"] > -0.2)
            pygame.quit()

    def test_pets_differ_and_learn_preferences(self):
        tastes = []
        for seed in range(12):
            rng = random.Random(seed)
            c = Creature(f"P{seed}", genetics.random_genome(rng), 1, rng)
            tastes.append(shop.taste(c, "fire_pepper"))
        self.assertGreater(max(tastes) - min(tastes), 0.8)       # divisive: some love it, some hate it
        from game.living import Mind
        from game.behaviour import Behaviour
        from game.world import World
        rng = random.Random(4)
        c = Creature("Q", genetics.random_genome(rng), 1, rng)
        evolution.apply(c, "frolicat", "adult", SPECIES)
        m = Mind(rng, None, None, None)
        m.attach(c, Behaviour(rng), World())
        self.assertIsNone(shop.known_preference(c, "plush_buddy"))
        shop.ensure(c)["taste"]["plush_buddy"] = 0.9
        for _ in range(3):
            shop.apply(m, "plush_buddy")
        self.assertEqual(shop.known_preference(c, "plush_buddy"), "loves this")
        shop.ensure(c)["taste"]["yarn_ball"] = -0.8
        for _ in range(3):
            shop.apply(m, "yarn_ball")
        self.assertEqual(shop.known_preference(c, "yarn_ball"), "not keen")

    def test_boredom_with_the_same_toy(self):
        from game.living import Mind
        from game.behaviour import Behaviour
        from game.world import World
        rng = random.Random(5)
        c = Creature("R", genetics.random_genome(rng), 1, rng)
        evolution.apply(c, "frolicat", "adult", SPECIES)
        m = Mind(rng, None, None, None)
        m.attach(c, Behaviour(rng), World())
        shop.ensure(c)["taste"]["bubble_wand"] = 0.3
        first = shop.experience(m, "bubble_wand")[2]
        for _ in range(4):
            shop.apply(m, "bubble_wand")
        later = shop.experience(m, "bubble_wand")[2]
        self.assertGreater(later["boredom"], first["boredom"])
        self.assertEqual(later["novelty"], 0.0)

    def test_coins_persist(self):
        r = Records()
        r.coins, r.coins_earned, r.coins_spent, r.bought = 7, 20, 13, {"yarn_ball": 2}
        r2 = Records.from_dict(json.loads(json.dumps(r.to_dict())))
        self.assertEqual((r2.coins, r2.coins_earned, r2.coins_spent, r2.bought), (7, 20, 13, {"yarn_ball": 2}))

    def test_pet_led_games_pay_a_little(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            r = g.mind.recip
            r.game = {"kind": "catch", "phase": "wait_touch", "t": 0.0, "rally": 3, "touched": False}
            r._end_catch()
            self.assertGreaterEqual(g.records.coins, 1)
            pygame.quit()


class RoomTests(unittest.TestCase):
    def test_objects_can_be_clicked(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            g.draw()
            season = g.room.season(time.localtime(g.world_time).tm_mon)
            for (lx, ly), name in (((150, 80), "plant"), ((120, 25), "window"), ((46, 8), "lamp"),
                                   ((72, 20), "clock"), ((20, 25), "frame"), ((64, 96), "bowl")):
                self.assertEqual(g.room.hit_object(lx, ly, g.mind, season), name)
                g.click_lcd(lx, ly)
                g.update(1 / 30)
                g.draw()
            self.assertNotEqual(g.world.frame_tilt, 0)
            pygame.quit()

    def test_shaking_the_plant_frees_a_trinket(self):
        with tempfile.TemporaryDirectory() as d:
            g = make_game(d)
            g.mind.skills.drop_loose("pebble", under_plant=True)
            freed = False
            for _ in range(6):
                g.beh.start_plan([])
                g.mind.beh.reaction and g.beh.start_plan([])
                g.poke_object("plant")
                for _ in range(90):
                    g.update(1 / 30)
                if g.world.loose and g.world.loose[0]["x"] < 147:
                    freed = True
                    break
            self.assertTrue(freed)
            pygame.quit()

    def test_tidy_pet_straightens_the_picture(self):
        from game.living import Mind
        from game.behaviour import Behaviour
        from game.world import World
        rng = random.Random(6)
        c = Creature("S", genetics.random_genome(rng), 1, rng)
        evolution.apply(c, "frolicat", "adult", SPECIES)
        beh = Behaviour(rng)
        m = Mind(rng, None, None, None)
        m.attach(c, beh, World())
        beh._c, beh._sp = c, SPECIES["frolicat"]
        c.personality.traits["stubbornness"] = 0.9
        m.world.frame_tilt = 8
        beh.start_plan(m._plan("straighten", c, beh))
        for _ in range(30 * 10):
            m.update(1 / 30, None, None, False, 13.0, "clear")
            beh.update(1 / 30, c, SPECIES["frolicat"])
        self.assertEqual(m.world.frame_tilt, 0)


if __name__ == "__main__":
    unittest.main()
