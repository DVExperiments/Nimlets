"""Tests for the Reciprocal Intelligence System (v1.3).

Run:  python -m unittest discover -s tests -v
"""
import math
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

from game import config, evolution, genetics, language, learning  # noqa: E402
from game.behaviour import Behaviour  # noqa: E402
from game.creature import Creature  # noqa: E402
from game.living import Mind  # noqa: E402
from game.reciprocity import GestureTracker, classify  # noqa: E402
from game.world import MURAL_RECT, World  # noqa: E402

SPECIES = config.load_species()


def setup(seed=11, species="frolicat", stage="adult"):
    rng = random.Random(seed)
    c = Creature("Echo", genetics.random_genome(rng), 1, rng)
    evolution.apply(c, species, stage, SPECIES)
    c.hunger = c.happiness = c.energy = 90
    for t in c.personality.traits:
        c.personality.traits[t] = 0.6
    beh = Behaviour(rng)
    log, said = [], []
    mind = Mind(rng, None, said.append, lambda n: None,
                lambda kind, text, icon=None, important=False: log.append((kind, text)))
    mind.attach(c, beh, World())
    beh._c, beh._sp = c, SPECIES[c.species]
    mind.recip.cd["request"] = mind.recip.cd["game"] = 999
    mind.cd["surprise"] = mind.cd["frontier"] = 999
    return c, beh, mind, log, said


def tick(c, beh, mind, seconds, cursor=None, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        mind.idle_t = 0
        mind.update(dt, cursor, None, False, 14.0, "clear")
        beh.update(dt, c, SPECIES[c.species])


def path(kind, n=24, cx=80, cy=80):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        if kind == "left":
            x, y = cx + 15 - 30 * t, cy
        elif kind == "right":
            x, y = cx - 15 + 30 * t, cy
        elif kind == "up":
            x, y = cx, cy + 12 - 24 * t
        elif kind == "side":
            x, y = cx + 14 * math.sin(t * 2 * math.pi), cy + (i % 2) * 0.3
        elif kind == "wiggle":
            x, y = cx + 5 * math.sin(t * 6 * math.pi), cy
        elif kind == "circle":
            x, y = cx + 10 * math.cos(t * 2 * math.pi), cy + 10 * math.sin(t * 2 * math.pi)
        pts.append((i * 0.03, x, y))
    return pts


class GestureTests(unittest.TestCase):
    def test_classifier(self):
        for kind in ("left", "right", "up", "side", "wiggle", "circle"):
            self.assertEqual(classify(path(kind)), kind, kind)
        self.assertIsNone(classify(path("left")[:2]))

    def test_tracker_emits_stroke_after_pause(self):
        tr = GestureTracker()
        t = 0.0
        for _, x, y in path("circle"):
            tr.update(1 / 30, t, (x, y))
            t += 1 / 30
        for _ in range(15):
            tr.update(1 / 30, t, (x, y))
            t += 1 / 30
        strokes = tr.pop()
        self.assertEqual([g for _, g, _ in strokes], ["circle"])
        tr.update(1 / 30, t, (x, y), pressed=True)          # drawing on the wall is not a gesture
        self.assertEqual(tr.points, [])


class LanguageTests(unittest.TestCase):
    def test_convention_forms_and_can_change_meaning(self):
        rng = random.Random(1)
        c, *_ = setup()
        lang = language.new_language(rng, c.personality)
        sig = lang["repertoire"]["food"][0]
        events = []
        for _ in range(6):
            events += language.record(lang, "food", sig, 1.0)
        self.assertEqual(lang["conventions"]["food"], sig)
        self.assertGreaterEqual(language.level(lang), 3)
        lang["repertoire"]["play"].append(sig)
        for _ in range(8):
            events += language.record(lang, "play", sig, 1.0)
        self.assertTrue(any(e[0] == "meaning_changed" for e in events))
        self.assertEqual(lang["conventions"].get("play"), sig)

    def test_ambiguous_signal_loses_convention(self):
        lang = language.new_language(random.Random(2), setup()[0].personality)
        sig = lang["repertoire"]["attention"][0]
        for _ in range(5):
            language.record(lang, "attention", sig, 1.0)
        self.assertIn("attention", lang["conventions"])
        for _ in range(8):
            language.record(lang, "attention", sig, 0.0, misunderstood=True)
        self.assertNotIn("attention", lang["conventions"])

    def test_combinatorial_level_combines_signals(self):
        lang = language.new_language(random.Random(3), setup()[0].personality)
        lang["conventions"] = {"attention": "chirp2", "food": lang["repertoire"]["food"][0]}
        self.assertEqual(language.level(lang, 1.0), 4)
        self.assertEqual(language.level(lang, 0.5), 3)     # a young pet hasn't the capacity yet
        self.assertEqual(language.combo_for(lang, "play"), "chirp2+push")

    def test_choice_prefers_what_works_but_explores(self):
        lang = language.new_language(random.Random(4), setup()[0].personality)
        good = lang["repertoire"]["food"][1]
        for _ in range(3):
            language.record(lang, "food", good, 1.0)
        rng = random.Random(5)
        picks = [language.choose(lang, "food", rng, 0.1, {}, 1.0)[0] for _ in range(200)]
        self.assertGreater(picks.count(good), 120)
        self.assertGreater(len(set(picks)), 1)

    def test_memory_decays(self):
        lang = language.new_language(random.Random(6), setup()[0].personality)
        sig = lang["repertoire"]["food"][0]
        language.record(lang, "food", sig, 1.0)
        before = lang["stats"]["food"][sig]["n"]
        language.decay(lang)
        self.assertLess(lang["stats"]["food"][sig]["n"], before)


class RequestTests(unittest.TestCase):
    def start(self, mind, intent="food"):
        r = mind.recip
        sig = r.b["lang"]["repertoire"][intent][0]
        r.request = {"intent": intent, "sig": sig, "t": 0.0, "stage": 0, "test": False,
                     "approached": False, "tried": [sig]}
        return sig

    def test_correct_response_reinforces(self):
        c, beh, mind, log, _ = setup()
        sig = self.start(mind)
        mind.note_action("feed", "rice")
        self.assertIsNone(mind.recip.request)
        st = mind.recip.b["lang"]["stats"]["food"][sig]
        self.assertEqual(st["n"], 1)
        self.assertGreater(st["s"], 0)

    def test_misunderstanding_triggers_repair(self):
        c, beh, mind, log, _ = setup()
        sig = self.start(mind, "play")
        mind.note_action("pet")
        req = mind.recip.request
        self.assertIsNotNone(req)
        self.assertEqual(req["stage"], 1)
        self.assertEqual(mind.recip.b["lang"]["stats"]["play"][sig]["m"], 1)
        self.assertEqual(beh.state, "refuse")                   # it shakes its head first
        mind.note_action("game", True)                          # now you get it
        self.assertTrue(any(m["key"] == "repaired" for m in mind.recip.b["memories"]))

    def test_repairs_are_capped_then_it_gives_up(self):
        c, beh, mind, log, _ = setup()
        self.start(mind, "attention")
        for _ in range(4):
            mind.recip.request and mind.recip.request.update(t=99)
            tick(c, beh, mind, 0.2)
        self.assertIsNone(mind.recip.request)
        self.assertTrue(any("gave up" in t for _, t in log))

    def test_testing_assumptions_sniffs_food(self):
        c, beh, mind, log, _ = setup()
        self.start(mind, "food")
        mind.recip.request["test"] = True
        out = mind.recip.food_check("rice", "meal")
        self.assertIsNotNone(out)
        self.assertIn("sniffs", out[0])
        self.assertIsNone(mind.recip.request)

    def test_initiates_requests_on_its_own(self):
        c, beh, mind, log, _ = setup()
        c.hunger = 30
        mind.recip.cd["request"] = 0
        mind.recip.cd["game"] = 999
        for _ in range(600):
            tick(c, beh, mind, 1 / 30, cursor=(40, 60))
            if mind.recip.request:
                break
        self.assertIsNotNone(mind.recip.request)
        self.assertEqual(mind.recip.request["intent"], "food")
        self.assertTrue(mind.recip.b["last_decision"])


class ImitationGameTests(unittest.TestCase):
    def test_follow_my_lead_success(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r._start_lead(1)
        tick(c, beh, mind, 4, cursor=(40, 60))
        self.assertEqual(r.game["phase"], "wait")
        expected = {"left": "left", "right": "right", "side": "side", "spin": "circle",
                    "jump": "up", "wiggle": "wiggle"}[r.game["pattern"][0]]
        r.b["gest"][expected]["seen"] = 50                      # it perceives you reliably
        r.on_stroke(expected, (80, 60))
        tick(c, beh, mind, 0.2, cursor=(40, 60))
        self.assertEqual(r.b["games"]["lead"]["wins"], 1)
        self.assertTrue(any(m["key"] == "first_imitation" for m in r.b["memories"]))
        self.assertGreater(r.b["player"]["imitates"], 0)

    def test_ignored_invitation_ends_quietly(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r._start_lead(1)
        tick(c, beh, mind, 15, cursor=(40, 60))
        self.assertIsNone(r.game)
        self.assertLess(r.b["player"]["imitates"], 0)

    def test_pet_imitates_you_imperfectly_then_learns(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r.on_stroke("circle", (beh.x, 70))
        self.assertIsNotNone(r.imitating)
        self.assertEqual(beh.tag, "game")
        perceived = [r.perceive("circle") for _ in range(300)]
        self.assertGreater(perceived.count("side"), 5)        # sometimes mistakes a circle for a sway
        r.b["gest"]["circle"] = {"seen": 10, "ok": 5}
        perceived = [r.perceive("circle") for _ in range(300)]
        self.assertGreater(perceived.count("circle"), 270)

    def test_catch_rally(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r._start_catch()
        for _ in range(3):
            for _ in range(200):
                tick(c, beh, mind, 1 / 30, cursor=(20, 30))
                if r.game and r.game["phase"] == "wait_touch":
                    break
            self.assertTrue(r.ball_touched())
        self.assertGreaterEqual(r.game["rally"], 3)
        self.assertTrue(any(m["key"] == "catch" for m in r.b["memories"]))

    def test_echo_rhythm(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r._start_echo(2)
        r.game["gaps"] = [0.3]
        tick(c, beh, mind, 3, cursor=(40, 60))
        self.assertEqual(r.game["phase"], "wait")
        r.on_click_room(40, 90)
        tick(c, beh, mind, 0.3, cursor=(40, 60))
        r.on_click_room(40, 90)
        tick(c, beh, mind, 1.2, cursor=(40, 60))
        self.assertEqual(r.b["games"]["echo"]["wins"], 1)

    def test_follow_the_path_and_you_lead(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r._start_path()
        seq = list(r.game["seq"])
        tick(c, beh, mind, 15, cursor=None)
        self.assertEqual(r.game["phase"], "wait")
        r.game["inputs"] = seq
        tick(c, beh, mind, 0.2)
        self.assertEqual(r.b["games"]["path"]["wins"], 1)
        tick(c, beh, mind, 2)
        from game.behaviour import act
        beh.start_plan([act("idle", 10.0)])                   # attentive (not busy drawing etc.)
        mind.rng.seed(3)
        r.dwells.extend([(mind.clock - 1.0, "bed"), (mind.clock - 0.5, "window")])
        r._maybe_follow_lead()
        self.assertTrue(any(m["key"] == "followed_lead" for m in r.b["memories"]))

    def test_pet_invents_games(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r.cd["game"] = 0
        r.cd["request"] = 999
        started = set()
        for _ in range(40):
            r.game = None
            r.cd["game"] = 0
            beh.start_plan([])
            if r._start_game():
                started.add(r.game["kind"] if r.game else "x")
        self.assertGreaterEqual(len(started), 3)


class RitualTests(unittest.TestCase):
    def test_greeting_ritual_forms_is_initiated_and_can_fade(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        for _ in range(3):
            r.context = {"name": "return", "t": 0.0}
            r.on_stroke("circle", (300, 300))
        rit = r.b["rituals"]["return"]
        self.assertEqual(rit["gesture"], "circle")
        self.assertTrue(any(m["key"] == "ritual_return" for m in r.b["memories"]))
        mind.rng.seed(0)
        tick(c, beh, mind, 1)
        rit["strength"] = 1.0
        self.assertTrue(r.on_return(300))                      # it greets you first
        self.assertEqual(beh.tag, "game")
        r.on_stroke("circle", (80, 60))
        self.assertGreater(rit["strength"], 0.9)
        for _ in range(8):
            r.anticipating = {"ctx": "return", "expect": "circle", "t": 99}
            tick(c, beh, mind, 0.1)
        self.assertIsNone(rit["gesture"])                      # unused rituals fade


class NegotiationBoundaryTests(unittest.TestCase):
    def test_tired_pet_suggests_something_quieter(self):
        c, beh, mind, log, _ = setup()
        c.energy = 20
        mind.rng.seed(1)
        res = None
        for _ in range(10):
            mind.recip.cd["neg"] = 0
            res = mind.recip.play_negotiation()
            if res:
                break
        self.assertTrue(res and res[1])

    def test_insisting_on_the_ball(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        r.ball_refusal()
        self.assertIsNotNone(r.insist)
        plan = r.ball_refusal()
        self.assertEqual(plan[0]["state"], "refuse")
        self.assertGreater(r.ball_later, 0)
        self.assertTrue(any(m["key"] == "first_disagreement" for m in r.b["memories"]))

    def test_snack_declined_when_full(self):
        c, beh, mind, log, _ = setup()
        c.hunger = 95
        results = [mind.recip.food_check("cake", "snack") for _ in range(40)]
        self.assertTrue(any(results))
        self.assertTrue(any(x is None for x in results))     # only sometimes

    def test_respecting_space_vs_chasing(self):
        c, beh, mind, log, _ = setup()
        r = mind.recip
        from game.behaviour import act
        beh.start_plan([act("idle", 30.0)])                 # stays put: we test *your* behaviour
        mind.cursor = (beh.x + 20, 80)
        r.on_retreat()
        tick(c, beh, mind, 4, cursor=(beh.x + 60, 80))
        self.assertGreater(r.b["player"]["respects"], 0)
        mind.cursor = (beh.x + 40, 80)
        r.on_retreat()
        tick(c, beh, mind, 0.7, cursor=(beh.x + 40, 80))
        tick(c, beh, mind, 0.2, cursor=(beh.x + 2, 80))
        self.assertLess(r.b["player"]["respects"], 0.2)


class CollaborationTests(unittest.TestCase):
    def test_pet_answers_your_drawing(self):
        c, beh, mind, log, _ = setup()
        mx, my, mw, mh = MURAL_RECT
        stroke = [(mx + 30 + i, my + 8) for i in range(6)]
        mind.world.add_mural([(x, y, (240, 110, 96)) for x, y in stroke], 0, "you")
        before = len(mind.world.mural)
        mind.recip.on_wall_stroke(stroke)
        tick(c, beh, mind, 8)
        self.assertGreater(len(mind.world.mural), before)
        self.assertTrue(any(m["key"] == "shared_drawing" for m in mind.recip.b["memories"]))
        self.assertGreater(mind.recip.b["player"]["draws"], 0)
        self.assertEqual(mind.world.mural_generations(), [1])          # your marks aren't a "generation"

    def test_learns_styles_you_respond_to(self):
        c, beh, mind, log, _ = setup()
        mind.recip.note_pet_style("spiral")
        mind.recip.cd["collab"] = 99
        mind.recip.on_wall_stroke([(40, 55)])
        self.assertGreater(mind.recip.style_weights()["spiral"], 1.0)


class LabAndAppTests(unittest.TestCase):
    def test_lab_and_report(self):
        c, beh, mind, log, _ = setup()
        secs = dict(mind.recip.lab())
        self.assertIn("Language", secs)
        self.assertIn("How it sees you", secs)
        with tempfile.TemporaryDirectory() as d:
            path = mind.recip.report(d)
            with open(path) as f:
                self.assertTrue(f.read().startswith("# Relationship report"))
        self.assertEqual(learning.phrasebook(c), [])

    def test_app_wall_drawing_bond_tab_and_version(self):
        import pygame
        from game.app import Game
        from game.version import VERSION
        with tempfile.TemporaryDirectory() as d:
            g = Game(["--save", os.path.join(d, "s.json"), "--mute"])
            self.assertIn(VERSION, pygame.display.get_caption()[0])
            for _ in range(3):
                g.c.stage_age = 1e9
                for _ in range(140):
                    g.update(1 / 30)
            g.draw()
            mx, my, mw, mh = MURAL_RECT
            g.stroke = []
            g.extend_stroke((mx + 10, my + 5))
            g.extend_stroke((mx + 20, my + 9))
            g.finish_stroke()
            coral = [p for p in g.world.mural if p[3] == 0]
            self.assertGreaterEqual(len(coral), 10)
            g.panel, g.records_tab = "records", 4
            g.draw()
            g.lab_open = True
            g.draw()
            g.save()
            pygame.quit()

    def test_old_saves_get_a_bond(self):
        import pygame
        from game.app import Game
        with tempfile.TemporaryDirectory() as d:
            save = os.path.join(d, "s.json")
            import shutil
            shutil.copy(os.path.join(ROOT, "saves", "example_save.json"), save)
            g = Game(["--save", save, "--mute"])
            for _ in range(30):
                g.update(1 / 30)
            g.draw()
            self.assertIn("lang", g.c.bond)
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
