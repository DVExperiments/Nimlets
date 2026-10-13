"""The Living Pet System - and a small experiment in artificial life.

A lightweight "mind" layered on top of the care simulation. It decides what
the pet *does*; it barely touches the care rules. Nothing here is machine
learning or a language model: just hidden numbers, counters and a few
hand-written rules - which is exactly the point of the experiment. The
question the game wants you to ask is: "Is it following instructions, or is
it deciding?"

 1. Awareness    cursor, window focus, inactivity and clicks - only the game's
                 own window. No camera, microphone, keylogging or other apps.
 2. Memory       routines, wariness after neglect, affection, associations.
 3. Autonomy     its own agenda; it avoids you if it doesn't trust you,
                 refuses suggestions, rearranges its room, guards its spot.
 4. Emotions     hidden, temporary and fluid.
 5. Quirks and behavioural mutations that emerge days after hatching.
 6. Creations    a wall drawing, a collection, a nest, invented games - kept
                 in the persistent World, so later generations find them.
 7. Beliefs      learned associations it tests with small experiments.
 8. Signals      an emergent shared language built from your responses.
 9. The Frontier it slowly discovers the edges of its world, presses on the
                 screen, climbs out across the interface, and (only if you
                 allow it) roams your desktop.
"""
import math
import time
from collections import deque

from . import learning
from .behaviour import act, chase, move, weighted
from .config import FLOOR_Y, X_MAX, X_MIN
from .genetics import BEHAVIOURS
from .personality import has_quirk
from . import shop
from . import wall
from .episodes import Episodes
from .existential import Existential
from .observation import Trace
from .observer import Observer
from .reciprocity import Reciprocity
from .rituals import Rituals
from .skills import Skills
from .sprites import hsv
from .uncanny import Uncanny
from .world_model import WorldModel
from .world import BED_RANGE, ITEM_KINDS, MURAL_RECT, World

BED_X, BOWL_X, WINDOW_X, HIDE_X, PEEK_X, FRONT_X = 30, 64, 124, 152, 141, 80
BALL_MIN, BALL_MAX = 8.0, 155.0
GIFTS = {"flower": "a little flower", "leaf": "a pretty leaf",
         "drawing": "a tiny drawing", "pebble": "a shiny pebble"}
STRANGE_DREAMS = ("fishlegs", "moon", "ghost")
TRANSIENT = ("excited", "affectionate", "grumpy", "curious", "lonely", "mischievous")
WATCH_IDLE = 45.0
INVENTIONS = {"wall_bounce": "bouncing the ball off the wall and catching it",
              "ball_bowl": "trying to get the ball into the food bowl"}
EMERGENCE_TEXT = {
    "nocturnal": "has started staying up at night and napping through the day. None of your pets has done that before.",
    "mimic": "has started copying the way your cursor moves.",
    "wanderer": "keeps staring at the edges of its room, as if wondering what is beyond them.",
    "collector": "has started gathering little things into a pile.",
    "dreamer": "dreams more vividly than any pet before it.",
    "shapeshifter": "briefly looked... different. Did its ears just change?",
    "echo": "repeated a sound back to you.",
    "inventor": "keeps pushing things together just to see what happens.",
    "trickster": "seems to really enjoy fooling you.",
}
SOUVENIRS = ("a stray pixel", "a crumb of taskbar", "a scrap of wallpaper", "a tiny lost window",
             "a cursor sparkle", "a speck of desktop dust")
SLOW_COOLDOWNS = ("surprise", "frontier", "bed", "invent", "signal", "shape", "draw", "experiment")


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


class Mind:
    def __init__(self, rng, effects=None, say=None, play=None, log=None, rare=None):
        self.rng = rng
        self.effects = effects
        self._say = say or (lambda text: None)
        self._play = play or (lambda name: None)
        self._log = log or (lambda kind, text, icon=None, important=False: None)
        self._rare = rare or (lambda label: None)
        self._coins = lambda n, why: None       # set by the app: coins for games won
        self.is_bedtime = lambda hour: False
        self.weather_at = lambda wt: "clear"
        self.allow_roam = False
        self.c = None
        self.beh = None
        self.world = World()
        self.clock = 0.0
        self.pace = 1.0
        self.world_time = time.time()
        self.hour = 12.0
        self.weather = "clear"
        # awareness
        self.focused = True
        self.mouse_in = True
        self.idle_t = 0.0
        self.away_t = 0.0
        self.cursor = None
        self.prev_cursor = None
        self.last_cursor = None
        self.cursor_speed = 0.0
        self.cursor_dx = 0.0
        self.still_t = 0.0
        self.near_still_t = 0.0
        self.dir_changes = deque()
        self.last_sign = 0
        self.hover_pet = False
        self.hover_button = None
        self.last_hover = None
        self.last_feed_hover = -99.0
        self.look_on = False
        self.look_t = 2.0
        self.coy_t = 0.0
        self.sound_t = 0.0
        self.sound_x = None
        self.clicks = deque()
        self.sleep_clicks = deque()
        self.actions = deque()
        self.stir_t = 0.0
        self.peek_t = 0.0
        self.cd = {"notice": 0.0, "tilt": 0.0, "hover": 0.0, "greet": 0.0, "trick": 0.0,
                   "surprise": 120.0, "click": 0.0, "leave": 0.0, "frontier": 150.0, "bed": 400.0,
                   "invent": 120.0, "signal": 25.0, "shape": 200.0, "draw": 90.0, "experiment": 60.0,
                   "mimic": 0.0, "brave": 0.0, "reminisce": 300.0}
        self.emo = {k: 0.0 for k in TRANSIENT}
        self.mood_name = "neutral"
        self.recent = deque(maxlen=6)
        self.dream = None
        self.dream_t = 6.0
        self.gift = None
        self.gift_clock = 0.0
        self.wait_reason = None
        self.trick_told = False
        self._pending_gift = None
        # artificial-life state
        self.pending_signal = None      # {"intent", "signal", "t"}
        self.experiment = None          # {"name", "t"}
        self.carrying = None
        self.shape_id = None
        self.shape_t = 0.0
        self.echo_q = []
        self.drag_dir = 1
        self.smudges = []               # [x, y, life] fingerprints on the "glass"
        self.floor_marks = []           # [x, life] temporary symbols on the floor
        self.escape_request = None      # set when it climbs out; the app runs the trip
        self.ball_rot = 0.0
        self.ball_vx = 0.0
        self.offline_wt = None          # timestamp override while simulating offline life
        self.bowl_wobble = 0.0
        self.trace_log = Trace()        # reasoning trace for Observation Mode
        self.experimental_on = True     # Settings -> Experimental behaviours
        self.mirror_on = False          # Settings -> Mirror
        self.species_db = {}
        self.pet_ritual_pending = None
        self.ball_hidden = False
        self.episodes = Episodes(self)
        self.prituals = Rituals(self)
        self.recip = Reciprocity(self)  # the reciprocal intelligence system
        self.observer = Observer(self)  # the observer update
        self.worldmodel = WorldModel(self)
        self.skills = Skills(self)
        self.existential = Existential(self)
        self.uncanny = Uncanny(self)

    # ---- setup / persistence --------------------------------------------------------
    def attach(self, c, beh, world=None):
        self.c = c
        self.beh = beh
        if world is not None:
            self.world = world
        beh.mind = self

    def reset_for(self, c):
        self.emo = {k: 0.0 for k in TRANSIENT}
        self.gift = None
        self.dream = None
        self.recent.clear()
        self.wait_reason = None
        self.pending_signal = self.experiment = self.carrying = None
        self.shape_id = None
        self.escape_request = None
        self.c = c
        self.recip.reset()
        self.observer.reset()
        self.skills.trial = None
        self.prituals.log.clear()
        self.worldmodel.learn_room()          # a new creature learns the room as it finds it

    def to_dict(self):
        return {"gift": self.gift}

    def load(self, data):
        data = data or {}
        gift = data.get("gift")
        self.gift = gift if isinstance(gift, dict) and gift.get("kind") in GIFTS else None
        if "ball_x" in data:                       # older saves kept the ball here
            self.world.ball_x = float(data["ball_x"])

    @property
    def ball_x(self):
        return self.world.ball_x

    @ball_x.setter
    def ball_x(self, value):
        self.world.ball_x = value

    def log(self, kind, text, icon=None, important=False):
        if self.c is not None:
            self._log(kind, f"{self.c.name} {text}", icon or kind, important)

    def trace(self, chain, kind="decision"):
        self.trace_log.add(self.offline_wt or self.world_time, chain, kind)

    def experimental(self):
        return self.experimental_on

    def species_name(self, sid):
        return self.species_db.get(sid, {}).get("name", sid)

    def drag_bed_plan(self, target):
        w = self.world
        target = max(BED_RANGE[0], min(BED_RANGE[1], target))
        self.drag_dir = 1 if target > w.bed_x else -1
        return [move(w.bed_x + self.drag_dir * 12, speed=1.2, tag="create"),
                act("push", 0.6, face=self.drag_dir, tag="create"),
                move(target + self.drag_dir * 12, speed=0.55, walk="drag", tag="drag"),
                act("proud", 1.2, fx="bed_moved", tag="create")]

    def drawing_plan(self, kind):
        mx, my, mw, mh = MURAL_RECT
        if kind == "ancestral":
            gens = [p for p in self.world.mural if 1 <= p[3] < self.c.generation]
            x = gens[-1][0] if gens else 80
        elif kind == "collab":
            mine = [p for p in self.world.mural if p[3] == 0]
            x = mine[-1][0] if mine else 80
        else:
            x = self.rng.uniform(mx + 12, mx + mw - 12)
        x = max(X_MIN, min(X_MAX, x))
        if kind == "collab":
            return [move(x, z=0.0, tag="create"), act("draw", 2.0, gaze="u", fx="collab_reply", tag="create")]
        return [move(x, z=0.0, tag="create"), act("ponder", 1.2, gaze="u", tag="create"),
                act("draw", 3.0, gaze="u", fx="symbol:" + kind, tag="create"),
                act("watch", 1.4, gaze="", tag="create")]

    def on_step_begin(self, step):
        pass

    def on_sleep_arrive(self, x):
        if abs(x - self.worldmodel.expect("bed")) < 8:
            return self.worldmodel.on_arrive("bed", x)
        return None

    def first(self, key):
        """True the first time `key` happens for this pet."""
        if key in self.c.firsts:
            return False
        self.c.firsts.append(key)
        return True

    # ---- derived feelings ----------------------------------------------------------------
    @property
    def watched(self):
        return self.focused and self.idle_t < WATCH_IDLE

    def q(self, name):
        return has_quirk(self.c, name)

    def mut(self, name):
        return self.c.bmut() == name

    def shyness(self):
        c = self.c
        att = c.memory.attachment / 100.0
        s = (1 - c.personality["sociability"]) * 0.6 * (1 - att) + c.wariness * 0.6
        if self.q("shy"):
            s += 0.5 * (1 - att)
        return _clamp(s)

    def sleepy(self):
        return _clamp((35 - self.c.energy) / 35.0)

    def content(self):
        c = self.c
        return 0.6 if (c.hunger > 60 and c.happiness > 60 and not c.sick and c.hygiene > 50) else 0.0

    def playful(self):
        return self.c.happiness / 100.0 * self.c.personality["playfulness"]

    def trust(self):
        return learning.belief(self.c, "touch")

    def fearful(self):
        return self.trust() < -0.15 or (self.shyness() > 0.55 and self.trust() < 0.3)

    def mood(self):
        values = dict(self.emo)
        values.update(shy=self.shyness() * 0.8, sleepy=self.sleepy(), content=self.content(),
                      playful=self.playful() * 0.8)
        best, score = "neutral", 0.3
        for k, v in values.items():
            v += self.rng.uniform(0, 0.12)
            if v > score:
                best, score = k, v
        self.mood_name = best
        return best

    def grumpy_refuse(self):
        return self.emo["grumpy"] > 0.5

    def learn(self, name, outcome, rate=0.15):
        text = learning.update_belief(self.c, name, outcome, rate)
        if text:
            self.log("belief", text + ".", "belief", important=True)
        return text

    # ---- routines --------------------------------------------------------------------
    def record_routine(self):
        c = self.c
        lt = time.localtime(self.world_time)
        day = lt.tm_year * 400 + lt.tm_yday
        if c.routine_day != day:
            if c.routine_day:
                c.routine = [v * 0.93 for v in c.routine]
            c.routine_day = day
        key = f"{day}-{lt.tm_hour}"
        if key != c.routine_mark:
            c.routine[lt.tm_hour] += 1.0
            c.routine_mark = key

    def routine_expected(self):
        r = self.c.routine
        h = int(self.hour) % 24
        mean = max(0.2, sum(r) / 24.0)
        hours = [h] + ([(h + 1) % 24] if (self.hour % 1) > 0.6 else [])
        return any(r[hh] >= 3 and r[hh] >= 2.5 * mean for hh in hours)

    # ---- inputs from the app ---------------------------------------------------------------
    def on_input(self):
        away = self.idle_t
        self.idle_t = 0.0
        if away >= WATCH_IDLE and self.focused:
            self.on_return(away)

    def on_focus(self, gained):
        if gained:
            away = self.away_t
            self.focused = True
            self.away_t = 0.0
            self.idle_t = 0.0
            if away >= 15:
                self.on_return(away)
        else:
            self.focused = False
            self.away_t = 0.0

    def on_mouse_window(self, inside):
        self.mouse_in = inside
        c, beh = self.c, self.beh
        if c is None or c.stage == "egg" or c.asleep or beh.reaction or beh.tag == "outside":
            return
        if not inside and self.cd["leave"] == 0 and (self.q("observer") or self.q("clingy")):
            self.cd["leave"] = 20
            side = 1 if (self.last_cursor and self.last_cursor[0] > beh.x) else -1
            beh.interject([act("look", 0.3, face=side), act("sad", 1.4, face=side)])
        elif inside and self.cd["leave"] > 12 and self.q("clingy"):
            beh.interject([act("happy", 1.0)])

    def on_player_sound(self, name):
        """Echo / Mimic pets repeat sounds they hear."""
        if self.c and (self.mut("echo") or self.mut("mimic")) and not self.c.asleep:
            if name not in ("select", "button") or self.rng.random() < 0.3:
                self.echo_q.append([self.clock + self.rng.uniform(1.2, 2.6), name])

    def note_action(self, kind, detail=None):
        """Any care action by the player."""
        c = self.c
        if c is None:
            return
        self.record_routine()
        self.actions.append(self.clock)
        while self.actions and self.clock - self.actions[0] > 20:
            self.actions.popleft()
        e = self.emo
        if kind == "feed":
            self.recent.append(detail)
            c.assoc["food"] = min(5.0, c.assoc.get("food", 0) + 0.3)
            e["affectionate"] = _clamp(e["affectionate"] + 0.15)
            if detail and detail == c.memory.favourite_food():
                e["excited"] = _clamp(e["excited"] + 0.6)
            self.learn("cursor_food", 1.0 if self.clock - self.last_feed_hover < 8 else -0.2, 0.12)
            if self.experiment and self.experiment["name"] == "bowl_summons":
                self.experiment = None
                self.learn("bowl_summons", 1.0, 0.3)
            self.world.ball_in_bowl = False
        elif kind == "game":
            self.recent.append("ball")
            c.assoc["ball"] = min(5.0, c.assoc.get("ball", 0) + 0.3)
            self.learn("toy_fun", 1.0 if detail else 0.3, 0.1)
            if detail:
                e["excited"] = _clamp(e["excited"] + 0.3)
        elif kind == "pet":
            self.recent.append("heart")
            e["affectionate"] = _clamp(e["affectionate"] + 0.2)
            self.learn("touch", 1.0, 0.12)
        elif kind == "praise":
            self.recent.append("star")
            e["affectionate"] = _clamp(e["affectionate"] + 0.25)
        elif kind == "scold":
            e["affectionate"] = _clamp(e["affectionate"] - 0.2)
            e["grumpy"] = _clamp(e["grumpy"] + 0.15)
        elif kind == "medicine":
            self.recent.append("pill")
            c.assoc["medicine"] = min(5.0, c.assoc.get("medicine", 0) + 1.0)
        elif kind == "lights_on_asleep":
            e["grumpy"] = _clamp(e["grumpy"] + 0.3)
        self.recip.on_player_action(kind, detail)
        if self.pet_ritual_pending is not None and self.clock - self.pet_ritual_pending < 8:
            self.pet_ritual_pending = None
            n = self.prituals.data.setdefault("answered", 0) + 1
            self.prituals.data["answered"] = n
            if n >= 3 and self.first("shared_pet_ritual"):
                self.uncanny.record("strange_ritual", "a greeting it invented is now one you share")
                self.log("ritual", "greets you with a ritual it invented - and you have started answering it.",
                         "heart", important=True)
        if len(self.actions) >= 6:
            e["grumpy"] = _clamp(e["grumpy"] + 0.15)
        if self.beh and self.beh.tag == "waiting":
            self.on_return(0, force=True)

    def on_mistake(self):
        if self.c:
            self.c.wariness = min(1.0, self.c.wariness + 0.3)

    def on_wake(self):
        if self.emo["grumpy"] > 0.4:
            self.beh.plan.append(act("sulk", 2.0, tag="reaction"))
        if abs(self.beh.x - self.world.bed_x) < 6 and not self.c.napping:
            self.learn("bed_safe", 1.0, 0.2)
            self.worldmodel.rested()

    # ---- the return greeting ---------------------------------------------------------------
    def on_return(self, away, force=False):
        c, beh, rng = self.c, self.beh, self.rng
        if c is None or c.stage == "egg" or c.departed or (self.cd["greet"] > 0 and not force):
            return
        if beh.tag == "outside":
            return
        self.cd["greet"] = 12.0
        if self.gift and not self.gift.get("seen"):
            self.gift["seen"] = True
            self._say(f"There's {GIFTS[self.gift['kind']]} on the floor... a gift from {c.name}?")
        if c.asleep:
            if rng.random() < 0.6:
                self.peek_t = 1.3
            return
        tag = beh.tag
        if tag == "secret":
            beh.interject([act("caught", 1.1, gaze="", tag="reaction")], resume=rng.random() < 0.5)
            return
        if tag == "window" and rng.random() < 0.7:
            return
        if tag == "waiting" or force:
            reason = self.wait_reason
            self.wait_reason = None
            beh.interject([act("excited", 1.0, gaze="", tag="greet"), act("wave", 1.2, tag="greet")],
                          resume=False)
            if self.effects:
                self.effects.hearts(beh.x, FLOOR_Y - 30, 3)
            self._play("happy")
            if reason == "routine":
                self._say(f"{c.name} seems to have been expecting you!")
            elif reason == "lonely":
                self._say(f"{c.name} missed you!")
            self.emo["lonely"] = 0.0
            return
        self.prituals.credit("return")
        if self.recip.on_return(away):          # your shared greeting, initiated by the pet
            self.emo["lonely"] *= 0.3
            return
        own = self.prituals.steps_for("return") if self.experimental() else []
        if own:                                  # a greeting ritual it invented itself
            beh.interject(own + [act("wave", 1.0, gaze="", tag="greet")])
            self.pet_ritual_pending = self.clock
            self.emo["lonely"] *= 0.3
            return
        p = c.personality
        att = c.memory.attachment / 100.0
        lonely = self.emo["lonely"]
        shy = self.shyness()
        busy = tag in ("activity", "doze", "create") or bool(beh.step and beh.step["kind"] == "chase")
        w = {
            "run": 0.3 + self.emo["affectionate"] * 2 + p["sociability"] + att + lonely * 1.5
                   + (1.2 if self.q("clingy") else 0) - c.wariness - shy - (1.0 if self.fearful() else 0),
            "wave": 0.5 + p["sociability"] * 0.5,
            "peek": shy * 2 + c.wariness * 1.5 + (1.0 if self.q("shy") else 0) + (1.0 if self.fearful() else 0),
            "glance": 0.6 + p["independence"] + (1.2 if self.q("independent") else 0) + (0.8 if busy else 0),
            "yawn": self.sleepy() * 2 + (0.6 if tag == "doze" else 0),
        }
        choice = weighted(rng, {k: max(0.05, v) for k, v in w.items()})
        if choice == "run":
            beh.interject([move(FRONT_X + rng.uniform(-8, 8), z=1.0, speed=2.2, walk="zoom", tag="greet"),
                           act("happy", 1.1, gaze="", tag="greet"), act("wave", 1.2, tag="greet")])
            if (lonely > 0.4 or att > 0.6) and self.effects:
                self.effects.hearts(beh.x, FLOOR_Y - 30, 2)
            self._play("happy")
        elif choice == "wave":
            beh.interject([act("notice", 0.6, gaze="", tag="greet"), act("wave", 1.4, tag="greet")])
        elif choice == "peek":
            beh.interject(self._peekaboo(tag="greet", wave=True))
        elif choice == "glance":
            beh.interject([act("notice", 0.9, gaze="", tag="greet")])
        else:
            beh.interject([act("yawn", 1.6, tag="greet"), act("notice", 0.6, gaze="", tag="greet")])
        self.emo["lonely"] *= 0.3

    # ---- clicks -------------------------------------------------------------------------
    def on_click_room(self, lx, ly):
        c, beh = self.c, self.beh
        if c is None or c.stage == "egg" or c.asleep or beh.tag == "outside":
            return
        if self.recip.on_click_room(lx, ly):
            return
        self.clicks.append(self.clock)
        while self.clicks and self.clock - self.clicks[0] > 3.0:
            self.clicks.popleft()
        self.sound_x, self.sound_t = lx, 1.4
        if beh.state in ("idle", "sit", "look", "ponder", "hum", "wait"):
            beh.facing = 1 if lx > beh.x else -1
        spot = c.memory.favourite_spot()
        if (spot is not None and abs(beh.x - spot) < 10 and abs(lx - beh.x) < 20
                and beh.state in ("sit", "hum", "doze", "idle") and self.cd["click"] == 0):
            self.cd["click"] = 6.0
            self.emo["grumpy"] = _clamp(self.emo["grumpy"] + 0.3)
            beh.interject([act("refuse", 1.2, tag="reaction")])
            self._say(f"{c.name} guards its favourite spot. Hmph!")
            return
        if len(self.clicks) >= 4 and self.cd["click"] == 0:
            self.cd["click"] = 8.0
            self.clicks.clear()
            self.learn("touch", -0.6, 0.1)
            if self.fearful():
                beh.interject([move(HIDE_X, speed=2.4, walk="zoom", tag="reaction"), act("hide", 2.0)])
                self._say(f"{c.name} runs and hides from the noise.")
            elif c.personality["stubbornness"] > 0.5 or self.emo["grumpy"] > 0.3:
                self.emo["grumpy"] = _clamp(self.emo["grumpy"] + 0.4)
                beh.interject([act("refuse", 1.3, tag="reaction")])
                self._say(f"{c.name} covers its ears. Too noisy!")
            else:
                self.emo["curious"] = _clamp(self.emo["curious"] + 0.4)
                beh.interject([move(lx, speed=1.4), act("inspect", 1.5), act("look", 0.8)])
                self._say(f"{c.name} goes to investigate the noise.")
        elif self.rng.random() < 0.35 and not beh.reaction and beh.state not in ("walk", "zoom"):
            beh.interject([act("notice", 0.7)])

    def on_click_ball(self, lx):
        c, beh, rng = self.c, self.beh, self.rng
        if self.recip.ball_touched():             # passing the ball back in a game of catch
            return
        direction = 1 if self.ball_x >= lx else -1
        self.kick_ball(direction, 1.6)
        if c is None or c.stage == "egg" or c.asleep or c.sick or beh.reaction or beh.tag == "outside":
            return
        self.learn("objects_respond", 1.0, 0.15)
        self.recip.on_player_action("ball")
        keen = c.personality["playfulness"] + self.emo["excited"] + learning.belief(c, "toy_fun") * 0.4
        refuse = (keen < 0.45 or self.emo["grumpy"] > 0.4
                  or (self.q("independent") and rng.random() < 0.3) or rng.random() < 0.12)
        if refuse or self.recip.insist:
            beh.interject(self.recip.ball_refusal(), resume=False)
            if self.recip.insist:
                self._say(f"{c.name} looks at the ball, looks at you... and goes somewhere else.")
            self.log("refuse", "ignored the ball you kicked to it.", "ball")
            return
        beh.interject([chase(kicks=rng.randint(1, 3), tag="activity"), act("happy", 1.0)], resume=False)
        self.emo["excited"] = _clamp(self.emo["excited"] + 0.2)

    def on_wall_wiped(self, removed, all_at_once=False):
        """You wiped (part of) the wall drawing. See wall.py."""
        if self.c is not None and removed:
            self.observer.on_action("wipe")
        return wall.on_wiped(self, removed, all_at_once)

    def on_click_sleeping(self):
        c = self.c
        self.sleep_clicks.append(self.clock)
        while self.sleep_clicks and self.clock - self.sleep_clicks[0] > 5:
            self.sleep_clicks.popleft()
        self.emo["grumpy"] = _clamp(self.emo["grumpy"] + 0.35)
        if len(self.sleep_clicks) >= 2:
            self.stir_t = 1.2
            self.sleep_clicks.clear()
            return f"{c.name} grumbles in its sleep. Let it rest!"
        return None

    def collect_gift(self):
        gift, self.gift = self.gift, None
        if gift and self.beh and not self.c.asleep:
            self.beh.react("love")
            self.c.memory.attachment = min(100.0, self.c.memory.attachment + 2)
        return gift["kind"] if gift else None

    # ---- ball ------------------------------------------------------------------------------
    def kick_ball(self, direction, power=1.0):
        self.world.ball_in_bowl = False
        self.ball_vx = direction * self.rng.uniform(35, 60) * power

    def kick_ball_to(self, target_x):
        self.world.ball_in_bowl = False
        self.ball_vx = (target_x - self.ball_x) * 1.3

    def _ball(self, dt):
        w = self.world
        if w.ball_in_bowl:
            w.ball_x = BOWL_X
            self.ball_vx = 0.0
            return
        old = w.ball_x
        if abs(self.ball_vx) > 0.5:
            w.ball_x += self.ball_vx * dt
            self.ball_rot += self.ball_vx * dt * 0.4
            self.ball_vx *= math.exp(-dt * 1.3)
            if (min(old, w.ball_x) <= BOWL_X <= max(old, w.ball_x) and abs(self.ball_vx) < 40
                    and w.bowl_food is None):
                w.ball_in_bowl = True        # it can drop into the bowl if it rolls slowly
                self.skills.on_ball_event("bowl")
                return
            if w.ball_x < BALL_MIN:
                w.ball_x, self.ball_vx = BALL_MIN, -self.ball_vx * 0.6
                self.skills.on_ball_event("wall")
            elif w.ball_x > BALL_MAX:
                w.ball_x, self.ball_vx = BALL_MAX, -self.ball_vx * 0.6
                self.skills.on_ball_event("wall")
        else:
            self.ball_vx = 0.0
        hidden = w.ball_x > 144
        if hidden and not self.ball_hidden:
            self.skills.on_ball_event("plant")
        self.ball_hidden = hidden
        if w.loose:
            self.ball_vx = self.skills.physics(dt, old, w.ball_x, self.ball_vx)

    # ---- per-frame ----------------------------------------------------------------------------
    def update(self, dt, cursor=None, hover_button=None, hover_pet=False, hour=12.0,
               weather="clear", world_time=None, pressed=False, zone=None, heading=None):
        c, beh = self.c, self.beh
        self.clock += dt
        self.hour, self.weather = hour, weather
        if world_time is not None:
            self.world_time = world_time
        self.world.now = self.world_time
        for k in self.cd:
            self.cd[k] = max(0.0, self.cd[k] - dt * (self.pace if k in SLOW_COOLDOWNS else 1.0))
        for name in ("coy_t", "sound_t", "stir_t", "peek_t", "shape_t"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))
        if self.shape_t == 0:
            self.shape_id = None
        if not self.focused:
            self.away_t += dt
        self.idle_t += dt
        self._ball(dt)
        self.smudges = [[x, y, life - dt] for x, y, life in self.smudges if life - dt > 0]
        self.floor_marks = [[x, life - dt] for x, life in self.floor_marks if life - dt > 0]
        if c is None or c.stage == "egg" or c.departed:
            self.cursor = None
            return
        decay = math.exp(-dt / 40.0)
        for k in ("excited", "affectionate", "grumpy", "curious", "mischievous"):
            self.emo[k] *= decay
        if not self.watched and not c.asleep:
            rate = (0.5 + c.personality["sociability"]) * (1.5 if self.q("clingy") else 1.0) / 240.0
            self.emo["lonely"] = _clamp(self.emo["lonely"] + rate * dt)
        else:
            self.emo["lonely"] *= math.exp(-dt / 20.0)
        mis_rate = c.personality["stubbornness"] * c.personality["playfulness"] * 2 / 120.0
        if self.mut("trickster"):
            mis_rate *= 3
        if self.rng.random() < mis_rate * dt:
            self.emo["mischievous"] = _clamp(self.emo["mischievous"] + 0.5)

        self.hover_pet = hover_pet
        if hover_button == "feed":
            self.last_feed_hover = self.clock
        self._track_cursor(dt, cursor)
        self._timers(dt)
        self.bowl_wobble = max(0.0, self.bowl_wobble - dt)
        self.hover_button = hover_button
        self.recip.update(dt, self.cursor, pressed)
        self.observer.day_tick()
        self.episodes.day_tick()
        self.prituals.day_tick()
        if c is not None and c.stage != "egg" and not c.departed:
            self.observer.observe(dt, zone, heading)
            self.skills.tick()
            self.existential.figure_tick(dt)
            shop.toy_tick(self, dt)
            self.uncanny.tick(dt)

        if beh.tag == "outside":
            return
        if beh.state in ("sleep", "sleepwalk"):
            self._dreams(dt)
            return
        self.dream = None
        if c.asleep:
            return
        if beh.state == "drag":
            self.world.bed_x = max(BED_RANGE[0], min(BED_RANGE[1], beh.x - self.drag_dir * 12))
        if self.experimental():
            self.skills.private_guard(dt)
            self.worldmodel.survey(dt)
        self._cursor_reactions()
        self._hover_reactions(hover_button)
        self.recip.maybe_initiate()
        self._mutation_moments()

    def _timers(self, dt):
        while self.echo_q and self.echo_q[0][0] <= self.clock:
            _, name = self.echo_q.pop(0)
            self._play(name)
            if self.effects and self.beh:
                self.effects.notes(self.beh.x, FLOOR_Y - 26, 1)
            if self.first("echo_heard"):
                self.log("echo", "repeated a sound back to you.", "note")
        if self.experiment:
            self.experiment["t"] += dt
            if self.experiment["t"] > 14.0:
                self.experiment = None
                self.learn("bowl_summons", -1.0, 0.3)

    def _track_cursor(self, dt, cursor):
        c, beh = self.c, self.beh
        if cursor is None or not self.focused:
            self.cursor = None
            self.prev_cursor = None
            self.cursor_speed *= 0.8
            self.near_still_t = 0.0
            return
        if self.prev_cursor:
            dx = cursor[0] - self.prev_cursor[0]
            dy = cursor[1] - self.prev_cursor[1]
            d = math.hypot(dx, dy)
            self.cursor_speed = 0.7 * self.cursor_speed + 0.3 * (d / max(dt, 1e-3))
            self.cursor_dx = 0.8 * self.cursor_dx + 0.2 * (dx / max(dt, 1e-3))
            self.still_t = 0.0 if d > 0.5 else self.still_t + dt
            sign = 1 if dx > 1 else (-1 if dx < -1 else 0)
            if sign and self.last_sign and sign != self.last_sign:
                self.dir_changes.append(self.clock)
            if sign:
                self.last_sign = sign
        while self.dir_changes and self.clock - self.dir_changes[0] > 1.2:
            self.dir_changes.popleft()
        self.prev_cursor = cursor
        self.cursor = self.last_cursor = cursor
        near = abs(cursor[0] - beh.x) < 30 and cursor[1] > FLOOR_Y - 60
        self.near_still_t = self.near_still_t + dt if (near and self.cursor_speed < 25) else 0.0
        if self.near_still_t > 4 and self.cd["brave"] == 0 and not c.asleep:
            self.cd["brave"] = 20.0          # gentle presence builds trust (bravery)
            before = self.fearful()
            self.learn("touch", 0.4, 0.06)
            if before and not self.fearful() and self.first("brave"):
                self.log("brave", "crept a little closer to your cursor. It seems less afraid now.", "heart",
                         important=True)
        self.look_t -= dt
        if self.look_t <= 0:
            observer = self.q("observer")
            self.look_on = not self.look_on
            if self.look_on:
                self.look_t = self.rng.uniform(4, 8) if observer else self.rng.uniform(2, 4)
            else:
                lo, hi = (1, 3) if observer else ((6, 14) if self.q("independent") else (3, 9))
                self.look_t = self.rng.uniform(lo, hi)
        if self.cursor_speed > 120:
            self.look_on = True
            self.look_t = max(self.look_t, 1.5)
        if beh.tag == "outside":
            return
        if len(self.dir_changes) >= 4 and self.cd["tilt"] == 0 and not c.asleep and not beh.reaction:
            self.cd["tilt"] = 8.0
            self.dir_changes.clear()
            self.emo["curious"] = _clamp(self.emo["curious"] + 0.5)
            beh.interject([act("tilt", 1.4)])
        if self.look_on and beh.state in ("idle", "sit", "wait", "notice", "hum", "ponder"):
            dx = cursor[0] - beh.x
            if abs(dx) > 14:
                beh.facing = 1 if dx > 0 else -1

    def _cursor_reactions(self):
        c, beh, rng = self.c, self.beh, self.rng
        if not (self.watched and self.cursor) or beh.reaction:
            return
        cx, cy = self.cursor
        near = abs(cx - beh.x) < 26 and cy > FLOOR_Y - 55
        if self.mut("mimic") and abs(self.cursor_dx) > 40 and self.cd["mimic"] == 0 \
                and beh.tag not in ("greet", "signal", "drag", "game"):
            self.cd["mimic"] = 2.5             # copies the cursor's movement
            step = 18 if self.cursor_dx > 0 else -18
            beh.interject([move(max(X_MIN, min(X_MAX, beh.x + step)), speed=1.8)])
            return
        if (not near or self.cursor_speed < 15 or beh.tag in ("greet", "signal", "drag", "game")
                or self.cd["notice"] > 0):
            return
        self.cd["notice"] = 12.0
        if self.fearful() and self.cursor_speed > 60:
            away = beh.x - (35 if cx > beh.x else -35)
            beh.interject([move(max(X_MIN, min(X_MAX, away)), speed=2.4, walk="zoom", tag="reaction"),
                           act("peek", 1.4, gaze="", tag="reaction")])
            self.recip.on_retreat()
            self.log("avoid", "backed away from your cursor.", "ghost")
        elif (self.q("observer") or self.q("shy")) and rng.random() < 0.35:
            self.coy_t = 1.6
        elif self.q("showoff") and self.cd["trick"] == 0 and rng.random() < 0.55:
            beh.interject(self._plan("trick", c, beh))
        elif beh.tag in ("activity", "doze", "create") and rng.random() < 0.6:
            beh.interject([act("notice", 1.0)])
        elif beh.tag == "activity" and (self.q("troublemaker") or self.mut("trickster")) and rng.random() < 0.3:
            beh.interject([act("fakesleep", 3.0, tag="activity")])

    def _hover_reactions(self, hover_button):
        c, beh = self.c, self.beh
        changed = hover_button != self.last_hover
        self.last_hover = hover_button
        if not changed or not hover_button or self.cd["hover"] > 0 or beh.reaction or c.sick \
                or beh.tag in ("drag", "game", "signal"):
            return
        if hover_button == "medicine" and c.assoc.get("medicine", 0) >= 2:
            self.cd["hover"] = 6.0
            back = 9 if beh.x < 120 else -9
            beh.interject([move(beh.x + back, speed=2.0), act("nervous", 1.3, tag="reaction")])
        elif hover_button == "feed" and learning.belief(c, "cursor_food") > 0.45 and c.hunger < 85:
            self.cd["hover"] = 8.0             # it has learned what that button means
            side = -1 if beh.x < BOWL_X else 1
            beh.interject([move(BOWL_X + side * 10, speed=1.8, tag="reaction"),
                           act("excited", 1.4, face=-side, tag="reaction")])
        elif hover_button == "feed" and (c.hunger < 75 or c.assoc.get("food", 0) >= 2):
            self.cd["hover"] = 6.0
            beh.interject([act("excited", 1.2, face=1 if BOWL_X > beh.x else -1, tag="reaction")])
        elif hover_button == "play" and self.playful() > 0.3:
            self.cd["hover"] = 6.0
            beh.interject([act("excited", 1.0, face=1 if self.ball_x > beh.x else -1, tag="reaction")])

    def _dreams(self, dt):
        if self.dream:
            self.dream["t"] += dt
            if self.dream["t"] > 4.0:
                self.dream = None
            return
        self.dream_t -= dt
        if self.dream_t <= 0:
            dreamer = self.mut("dreamer")
            self.dream_t = self.rng.uniform(4, 8) if dreamer else self.rng.uniform(9, 16)
            if self.recent and self.rng.random() < 0.85:
                icon = self.rng.choice(list(self.recent))
            else:
                icon = self.rng.choice(STRANGE_DREAMS)
            self.dream = {"icon": icon, "t": 0.0}
            if icon in STRANGE_DREAMS and self.rng.random() < 0.5:
                self.log("dream", "had a strange dream.", icon)
            if dreamer and self.beh.state == "sleep" and self.rng.random() < 0.18:
                self.beh.sleepwalk_to = self.rng.uniform(X_MIN, X_MAX)
                self.log("sleepwalk", "sleepwalked across the room.", "moon")

    def _mutation_moments(self):
        c, beh, rng = self.c, self.beh, self.rng
        if self.mut("shapeshifter") and self.cd["shape"] == 0 and rng.random() < 0.002:
            self.cd["shape"] = rng.uniform(150, 300)
            options = [s for s in ("frolicat", "hootle", "luminelle", "thornback", "zippit", "sprouty")
                       if s != c.species]
            self.shape_id = rng.choice(options)
            self.shape_t = rng.uniform(15, 30)
            if self.effects:
                self.effects.sparkles(beh.x, FLOOR_Y - 16, 6, 16)
            self.log("shape", "briefly changed shape!", "star")

    # ---- simulated-time memory ---------------------------------------------------------
    def update_sim(self, sim_dt):
        c = self.c
        if c is None or c.stage == "egg":
            return
        h = sim_dt / 3600.0
        c.wariness = max(0.0, c.wariness - 0.03 * h)
        for k in c.assoc:
            c.assoc[k] = max(0.0, c.assoc[k] - 0.02 * h)
        self.gift_clock += sim_dt
        while self.gift_clock >= 3600.0:
            self.gift_clock -= 3600.0
            self._hourly()

    def _hourly(self):
        c, rng = self.c, self.rng
        b = c.genome.get("bmut")
        if (b and not c.bmut_active and c.age_days >= b.get("emerge_days", 2)
                and c.stage not in ("egg", "baby")):
            c.bmut_active = True
            self._log("mutation", f"Something new: {c.name} " + EMERGENCE_TEXT.get(b["id"], "is behaving strangely."),
                      "star", True)
            self._rare(BEHAVIOURS.get(b["id"], b["id"]).split(" - ")[0] + " behaviour")
        if c.stage in ("egg", "baby") or c.asleep or c.sick:
            return
        if self.q("explorer") and rng.random() < 0.04:
            c.memory.spots = [v // 2 for v in c.memory.spots]
        if (self.gift is None and c.memory.attachment >= 60 and c.wariness < 0.2
                and c.age - c.last_gift_age >= 2 * 86400 and c.hunger > 25 and rng.random() < 0.08):
            self.spawn_gift()

    def spawn_gift(self):
        c, beh, rng = self.c, self.beh, self.rng
        p = c.personality
        kind = weighted(rng, {"flower": 0.6 + p["sociability"], "leaf": 0.4 + p["curiosity"],
                              "drawing": 0.4 + p["playfulness"], "pebble": 0.3 + p["independence"]})
        c.last_gift_age = c.age
        self.log("gift", f"left you {GIFTS[kind]}.", "flower", important=True)
        if self.watched and not beh.reaction and beh.tag != "outside":
            self._pending_gift = kind
            beh.interject([move(70 + rng.uniform(-6, 6), z=1.0, speed=1.2, tag="greet"),
                           act("present", 2.0, fx="gift", tag="greet")])
        elif self.watched:
            self.gift = {"kind": kind, "x": rng.uniform(40, 110), "seen": True}
            self._say(f"{c.name} quietly leaves {GIFTS[kind]} for you. Click it to keep it.")
        else:
            self.gift = {"kind": kind, "x": rng.uniform(40, 110), "seen": False}

    # ---- decisions ---------------------------------------------------------------------
    def sleep_spot(self, c, beh):
        p_bed = 0.45 if self.q("sleepyhead") else 0.8
        p_bed += learning.belief(c, "bed_safe") * 0.15
        if c.napping:
            p_bed *= 0.5
        if self.rng.random() < p_bed:
            return self.worldmodel.expect("bed")      # where it *remembers* the bed
        spot = self.rng.choice([beh.x, WINDOW_X, BOWL_X + 16, 108.0])
        self.log("sleep_spot", "fell asleep somewhere unusual.", "moon")
        return spot

    def bedtime_ritual(self, c):
        lt = time.localtime(self.world_time)
        day = lt.tm_year * 400 + lt.tm_yday
        if c.napping or c.ritual_day == day or c.stage in ("egg", "baby"):
            return []
        c.ritual_day = day
        self.prituals.credit("sleep")
        learned = self.prituals.data["known"].get("sleep")
        moves = [a for a in learned["seq"].split(">") if not a.startswith("at:")] if learned else list(c.ritual)
        if self.first("ritual") or self.rng.random() < 0.2:
            self.log("ritual", f"did its little bedtime ritual: {', '.join(moves)}.", "moon")
        return self.recip.bedtime(moves)

    def walk_check(self, c, beh):
        tag = beh.tag
        if tag in ("reaction", "greet", "waiting", "signal", "drag", "create", "outside", "frontier",
                   "game") or c.sick:
            return False
        remaining = abs((beh.target or beh.x) - beh.x)
        rng = self.rng
        distract = 0.035 * (0.5 + c.personality["curiosity"]) * (2.0 if self.q("explorer") else 1.0)
        if remaining > 14 and rng.random() < distract:
            beh.interject([act("inspect", 1.4, tag="activity", fx="sparkle_floor"), act("look", 0.8)])
            return True
        if remaining > 25 and rng.random() < 0.025:
            new = beh.x - (beh.target - beh.x) * rng.uniform(0.3, 0.8)
            beh.start_plan([act("look", 1.2), move(max(X_MIN, min(X_MAX, new)))])
            return True
        return False

    def pick(self, c, sp, beh):
        """Choose the next plan, or None for the plain idle FSM."""
        if c.stage == "egg" or c.sick:
            return None
        rng = self.rng
        p = c.personality
        watched = self.watched
        if not watched:
            reason = "routine" if self.routine_expected() else (
                "lonely" if self.emo["lonely"] > 0.6 else None)
            if reason and rng.random() < 0.55:
                self.wait_reason = reason
                if reason == "routine" and self.first(f"wait:{int(self.hour)}"):
                    self.log("wait", "waited at the front of the room around the time you usually visit.",
                             "heart", important=True)
                else:
                    self.log("wait", "sat watching the front of the screen for a while.", "heart")
                return [move(FRONT_X + rng.uniform(-10, 10), z=1.0, speed=0.9, tag="waiting"),
                        act("wait", rng.uniform(10, 18), gaze="", tag="waiting")]
        if (self.world.mural and self._old_mural_artist() and "studied_mural" not in c.firsts
                and c.stage != "baby" and rng.random() < 0.5):
            return self._plan("study_mural", c, beh)
        if self.cd["surprise"] == 0 and rng.random() < 0.15:
            plan = self._surprise(c, watched)
            if plan:
                self.cd["surprise"] = rng.uniform(150, 320)
                return plan
        mood = self.mood()
        sleepy = self.sleepy()
        grown = c.stage != "baby"
        w = {
            "basic": 3.0,
            "bowl": 0.5 + p["curiosity"] * 0.6 + (1.0 if self.q("explorer") else 0) + (0.8 if c.hunger < 50 else 0),
            "ball": (self.playful() * 1.6 + min(1.0, c.assoc.get("ball", 0)) * 0.4
                     + (0.4 if c.memory.favourite_game() else 0) + self.emo["excited"]
                     + learning.belief(c, "toy_fun") * 0.6),
            "window": 0.35 + p["curiosity"] * 0.4 + (0.9 if self.weather in ("rain", "snow") else 0)
                      + (0.5 if self.q("observer") else 0),
            "ponder": 0.3 + p["independence"] * 0.5,
            "bed": sleepy * 2.5 + (0.8 if self.q("sleepyhead") else 0),
            "hum": self.content() * 1.2 + (0.3 if mood == "content" else 0),
            "yawn": sleepy * 1.5,
            "zoom": self.emo["excited"] * 1.5,
            "sulk": self.emo["grumpy"] * 2,
            "solitary": p["independence"] * 0.5 + (0.6 if self.q("independent") else 0),
        }
        if grown:
            w["draw"] = ((0.2 + p["playfulness"] * 0.2 + (0.6 if self.mut("inventor") else 0))
                         * wall.draw_factor(learning.belief(c, "wall_ok"), self.watched)
                         if self.cd["draw"] == 0 else 0)
            w["collect"] = ((0.15 + (1.5 if self.mut("collector") else 0) + p["curiosity"] * 0.1)
                            if not self.carrying else 0)
            w["move_bed"] = ((0.05 + (0.15 if self.q("explorer") else 0) + (0.1 if self.mut("inventor") else 0))
                             if self.cd["bed"] == 0 else 0)
            w["nest"] = 0.4 if (self._nest_ready() and not self.world.nest) else 0
            w["invent"] = ((0.12 + self.playful() * 0.2 + (1.2 if self.mut("inventor") else 0)
                            + (0.3 if self.world.inventions else 0)) if self.cd["invent"] == 0 else 0)
            w["frontier"] = ((0.12 + p["curiosity"] * 0.25 + (1.2 if self.mut("wanderer") else 0))
                             if self.cd["frontier"] == 0 else 0)
            if (watched and self.cd["experiment"] == 0 and abs(learning.belief(c, "bowl_summons")) < 0.45
                    and p["curiosity"] > 0.4 and c.hunger < 80):
                w["experiment"] = 0.5
        else:
            w["window"] *= 0.3
            w["ponder"] *= 0.3
        if watched and self.cursor:
            w["approach"] = (self.emo["affectionate"] * 2 + (1.4 if self.q("clingy") else 0)
                             + max(0.0, self.recip.b["player"]["respects"])
                             + c.memory.attachment / 100.0 - self.shyness() * 1.5
                             - (1.0 if self.q("independent") else 0) - (2.0 if self.fearful() else 0))
            if self.q("showoff") and self.cd["trick"] == 0:
                w["trick"] = 1.6
            if self.q("troublemaker") or self.emo["mischievous"] > 0.3 or self.mut("trickster"):
                w["fakesleep"] = 0.4 + self.emo["mischievous"] + (0.6 if self.mut("trickster") else 0)
        if not watched:
            alone = self.idle_t > 90 or not self.focused
            w["doze"] = (0.6 + (1.2 if self.q("sleepyhead") else 0) + sleepy) if alone else 0
            mis = (self.emo["mischievous"] + (0.6 if self.q("troublemaker") else 0) + p["playfulness"] * 0.3
                   + (1.0 if self.mut("trickster") else 0))
            w["silly"] = mis * 0.6
            w["balance"] = mis * 0.4
            w["hide_ball"] = mis * 0.5 if self.ball_x < 140 else 0.0
            w["ball"] += 0.5
        if (self.q("shy") or self.fearful()) and watched and self.shyness() > 0.4:
            w["hide"] = self.shyness() * 1.2
        if w and self.world.frame_tilt and (p["stubbornness"] > 0.45 or self.world.pile.get("style") == "sorted"):
            w["straighten"] = 0.8
        if self.experimental() and grown:
            if self.mirror_on:
                stage = self.existential.mr["stage"]
                w["mirror"] = 0.25 + p["curiosity"] * 0.4 + (0.3 if stage < 2 else 0)
            if len(c.forms) >= 2 and self.cd["reminisce"] == 0:
                w["reminisce"] = 0.12 + p["curiosity"] * 0.1
            if self.world.figure:
                w["teach"] = 0.25 + p["sociability"] * 0.3
            far = [it for it in self.world.loose if it["x"] > 147]
            if far and "hit_item" not in self.skills.s["known"]:
                w["reach"] = 0.3 + p["curiosity"] * 0.3
            near = [it for it in self.world.loose if it["x"] <= 147]
            if near:
                w["pickup"] = 0.6
        choice = weighted(rng, w)
        return None if choice == "basic" else self._plan(choice, c, beh)

    def _plan(self, choice, c, beh):
        rng = self.rng
        alone = not self.watched
        if choice == "bowl":
            side = -1 if beh.x < BOWL_X else 1
            return [move(BOWL_X + side * 10, tag="activity"),
                    act("inspect", 1.8, face=-side, tag="activity"), act("look", 1.0, tag="activity")]
        if choice == "ball":
            if alone:
                self.log("ball", "played with its ball by itself.", "ball")
            return [chase(kicks=rng.randint(2, 4), tag="activity"),
                    act("happy", 1.0, tag="activity", fx="toy_fun")]
        if choice == "window":
            if alone:
                what = {"rain": "watched the rain", "snow": "watched the snow fall"}.get(
                    self.weather, "gazed out of the window")
                self.log("window", f"{what} for a while.", "moon")
            return [move(WINDOW_X + rng.uniform(-6, 6), z=0.0, tag="window"),
                    act("window", rng.uniform(6, 12), tag="window")]
        if choice == "ponder":
            return [act("ponder", rng.uniform(3, 5), tag="activity")]
        if choice == "bed":
            return [move(self.world.bed_x, tag="activity"), act("sit", rng.uniform(6, 10), tag="activity")]
        if choice == "hum":
            return [act("hum", rng.uniform(4, 6), tag="activity", fx="hum")]
        if choice == "yawn":
            return [act("yawn", 1.6)]
        if choice == "zoom":
            return [move(X_MIN + 4, speed=3, walk="zoom", tag="activity"),
                    move(X_MAX - 4, speed=3, walk="zoom", tag="activity"),
                    move(FRONT_X, speed=2.5, walk="zoom", tag="activity"), act("happy", 1.0)]
        if choice == "sulk":
            return [act("sulk", 3.0)]
        if choice == "solitary":
            corner = 26 if (self.cursor or (FRONT_X, 0))[0] > 80 else 118
            return [move(corner, z=0.0, tag="activity"), act("sit", rng.uniform(8, 14), tag="activity")]
        if choice == "approach" and self.cursor:
            cx, cy = self.cursor
            target = cx - 12 if cx > beh.x else cx + 12
            z = 1.0 if cy > FLOOR_Y - 20 else 0.6
            return [move(max(X_MIN, min(X_MAX, target)), z=z, speed=1.3, tag="activity"),
                    act("notice", 1.5, tag="activity"), act("happy", 1.0, fx="chirp")]
        if choice == "trick":
            self.cd["trick"] = 50.0
            trick = rng.choice(["spin", "dance", "jump"])
            return [act(trick, 2.4 if trick == "dance" else 1.4, fx="trick", tag="activity"),
                    act("present", 1.2, gaze="", tag="activity")]
        if choice == "fakesleep":
            return [act("fakesleep", rng.uniform(4, 7), tag="activity"), act("silly", 1.2)]
        if choice == "doze":
            if alone:
                self.log("doze", "dozed off for a bit.", "moon")
            steps = [move(self.world.bed_x, speed=0.7, tag="doze")] if rng.random() < 0.5 else []
            return steps + [act("doze", rng.uniform(12, 25), tag="doze")]
        if choice == "silly":
            if alone:
                self.log("silly", "pulled silly faces when it thought nobody was looking.", "star")
            return [act("silly", 2.5, tag="secret")]
        if choice == "balance":
            if alone:
                self.log("balance", "tried to balance on its food bowl... and fell off.", "star")
            return [move(BOWL_X, tag="secret"), act("balance", 2.4, tag="secret"),
                    act("fall", 0.8, tag="secret"), act("happy" if self.playful() > 0.3 else "sulk", 1.0)]
        if choice == "hide_ball":
            self.log("hide_ball", "hid its ball behind the plant.", "ball")
            return [move(self.ball_x - 8, tag="secret"), act("push", 0.4, fx="kick_hard", tag="secret"),
                    act("silly", 1.6, tag="secret")]
        if choice == "hide":
            return self._peekaboo()
        # ---- creations -------------------------------------------------------------
        if choice == "draw":
            self.cd["draw"] = rng.uniform(180, 420)
            mx, my, mw, mh = MURAL_RECT
            x = rng.uniform(mx + 6, mx + mw - 6)
            if self.world.mural and rng.random() < 0.6:          # keeps adding to its work
                x = rng.choice(self.world.mural)[0] + rng.uniform(-8, 8)
            x = max(X_MIN, min(X_MAX, x))
            return [move(x, z=0.0, tag="create"), act("draw", 3.0, gaze="u", fx="mural", tag="create"),
                    act("proud", 1.0, tag="create")]
        if choice == "study_mural":
            gen = self._old_mural_artist()
            xs = [pt[0] for pt in self.world.mural if pt[3] == gen[0]] or [80]
            x = max(X_MIN, min(X_MAX, sum(xs) / len(xs)))
            return [move(x, z=0.0, tag="create"), act("ponder", 3.5, gaze="u", fx="study_mural", tag="create"),
                    act("look", 1.0, tag="create")]
        if choice == "collect":
            x = rng.uniform(X_MIN, X_MAX)
            return [move(x, tag="create"), act("inspect", 1.5, fx="find_item", tag="create"),
                    move(self.world.pile["x"], speed=1.1, tag="create"),
                    act("drop", 0.7, fx="drop_item", tag="create")]
        if choice == "move_bed":
            self.cd["bed"] = rng.uniform(900, 1800)
            w = self.world
            spot = c.memory.favourite_spot()
            target = spot if spot is not None and abs(spot - w.bed_x) > 25 else (
                BED_RANGE[1] - 6 if w.bed_x < 70 else BED_RANGE[0] + 4)
            if abs(target - BOWL_X) < 18:
                target = BOWL_X + (20 if target > BOWL_X else -20)
            target = max(BED_RANGE[0], min(BED_RANGE[1], target))
            self.drag_dir = 1 if target > w.bed_x else -1
            start = w.bed_x + self.drag_dir * 12
            return [move(start, speed=1.2, tag="create"),
                    act("push", 0.6, face=self.drag_dir, tag="create"),
                    move(target + self.drag_dir * 12, speed=0.55, walk="drag", tag="drag"),
                    act("proud", 1.2, fx="bed_moved", tag="create")]
        if choice == "nest":
            w = self.world
            return [move(self.ball_x + (8 if self.ball_x > w.bed_x else -8), tag="create"),
                    act("push", 0.5, fx="ball_to_bed", tag="create"),
                    move(w.pile["x"], tag="create"), act("inspect", 1.2, fx="pile_to_bed", tag="create"),
                    move(w.bed_x, tag="create"), act("sit", 2.0, fx="nest_check", tag="create")]
        if choice == "invent":
            self.cd["invent"] = rng.uniform(240, 480)
            return self.skills.explore_plan()
        if choice == "straighten":
            return [move(26, z=0.0, speed=1.2), act("look", 0.8, gaze="ul"),
                    act("jump", 0.7, fx="frame_fix"), act("proud", 1.0)]
        if choice == "mirror":
            return self.existential.mirror_plan()
        if choice == "reminisce":
            self.cd["reminisce"] = rng.uniform(900, 1800)
            return self.existential.reminisce_plan()
        if choice == "teach":
            return self.existential.teach_plan()
        if choice == "reach":
            return self.skills.reach_attempt_plan()
        if choice == "pickup":
            it = [it for it in self.world.loose if it["x"] <= 147][0]
            return [move(max(X_MIN, min(X_MAX, it["x"])), tag="create"), act("inspect", 1.0, fx="tool:pick", tag="create"),
                    move(self.world.pile["x"], speed=1.1, tag="create"), act("drop", 0.6, fx="drop_item", tag="create")]
        if choice == "invent_old":
            known = [i["id"] for i in self.world.inventions]
            idea = rng.choice(known) if known and rng.random() < 0.6 else rng.choice(list(INVENTIONS))
            if idea == "wall_bounce":
                return [move(min(X_MAX, self.ball_x + 8), tag="create"),
                        act("push", 0.4, face=-1, fx="kick_left_hard", tag="create"),
                        act("look", 1.2, tag="create"), chase(kicks=1, tag="create"),
                        act("happy", 1.0, fx="invention:wall_bounce", tag="create")]
            side = 1 if self.ball_x > BOWL_X else -1
            return [move(self.ball_x + side * 8, tag="create"),
                    act("push", 0.4, face=-side, fx="kick_to_bowl", tag="create"),
                    act("look", 1.6, face=-side, gaze="d", tag="create"),
                    act("dance", 1.6, fx="invention:ball_bowl", tag="create")]
        if choice == "experiment":
            self.cd["experiment"] = 200.0
            side = -1 if beh.x < BOWL_X else 1
            if self.first("experiment"):
                self.log("experiment", "tapped its food bowl and stared at you, as if testing something.",
                         "belief", important=True)
            return [move(BOWL_X + side * 10, tag="experiment"),
                    act("tap", 0.8, face=-side, fx="snd:tap", tag="experiment"),
                    act("notice", 1.2, gaze="", tag="experiment"),
                    act("wait", 6.0, gaze="", fx="experiment", tag="experiment")]
        if choice == "frontier":
            return self._frontier(c)
        return None

    def _nest_ready(self):
        w = self.world
        return len(w.pile["items"]) >= 3 and (self.q("sleepyhead") or self.mut("collector")
                                              or len(w.pile["items"]) >= 6)

    def _old_mural_artist(self):
        gens = [g for g in self.world.mural_generations() if g < self.c.generation]
        if not gens:
            return None
        g = gens[-1]
        return g, self.world.mural_artists.get(str(g), "a pet from long ago")

    def _peekaboo(self, tag="hide", wave=False):
        steps = [move(HIDE_X, speed=1.4, tag=tag), act("hide", 2.5 if not wave else 1.0, tag=tag),
                 move(PEEK_X, speed=0.7, walk="sneak", tag=tag), act("peek", 1.4, gaze="", tag=tag),
                 move(HIDE_X, speed=1.2, tag=tag), act("hide", 1.0, tag=tag),
                 move(PEEK_X, speed=0.7, walk="sneak", tag=tag), act("peek", 1.0, gaze="", tag=tag),
                 move(PEEK_X - 14, speed=0.8, tag=tag)]
        return steps + [act("wave" if wave else "happy", 1.0, tag=tag)]

    def _surprise(self, c, watched):
        rng = self.rng
        options = {
            "peekaboo": 1.0 if watched else 0.0,
            "window": 1.0 + (1.0 if self.weather in ("rain", "snow") else 0.0),
            "find": 1.0,
            "zoomies": self.playful() * 2.0,
            "balance": 0.6,
        }
        choice = weighted(rng, options)
        if choice == "peekaboo":
            return self._peekaboo()
        if choice == "window":
            if not watched:
                self.log("window", "spent a long time staring out of the window.", "moon")
            return [move(WINDOW_X, z=0.0, tag="window"), act("window", rng.uniform(15, 25), tag="window")]
        if choice == "find":
            x = rng.uniform(30, 130)
            return [move(x, tag="activity"), act("inspect", 1.5, tag="activity", fx="sparkle_floor"),
                    act("caught", 0.7, tag="activity"), act("happy", 1.2)]
        if choice == "zoomies":
            if not watched:
                self.log("zoomies", "had a sudden burst of energy and raced around the room.", "star")
            laps = [move(X_MIN + 2 if i % 2 == 0 else X_MAX - 2, speed=3.2, walk="zoom", tag="activity")
                    for i in range(4)]
            return laps + [move(FRONT_X, speed=2, walk="zoom"), act("happy", 1.0)]
        return [move(BOWL_X, tag="activity"), act("balance", 2.4, tag="activity"),
                act("fall", 0.8, tag="activity"), act("happy", 1.0)]

    # ---- the frontier: discovering the edges of its world ------------------------------------
    def _frontier(self, c):
        rng, fr = self.rng, c.frontier
        self.cd["frontier"] = rng.uniform(240, 480) / (3.0 if self.mut("wanderer") else 1.0)
        stage = fr["stage"]
        old_enough = c.stage in ("teen", "adult", "elder")
        if stage >= 2 and old_enough and rng.random() < 0.6:
            roam = self.allow_roam and stage >= 3 and rng.random() < 0.35
            return [move(14, speed=1.4, tag="frontier"),
                    act("climb", 2.2, face=-1, fx="escape:" + ("roam" if roam else "ui"), tag="frontier")]
        if stage == 0:
            if rng.random() < 0.5:
                return [move(FRONT_X + rng.uniform(-12, 12), z=1.0, tag="frontier"),
                        act("press", 3.0, gaze="", fx="press", tag="frontier"),
                        act("notice", 1.2, gaze="", tag="frontier")]
            return [move(10, tag="frontier"), act("push_wall", 2.2, face=-1, fx="edge", tag="frontier"),
                    act("notice", 1.2, gaze="", tag="frontier")]
        choice = rng.choice(["climb", "knock", "push"])
        if choice == "climb":
            return [move(10, tag="frontier"), act("climb", 3.0, face=-1, fx="climb", tag="frontier"),
                    act("fall", 0.8, tag="frontier"), act("look", 1.0, gaze="u", tag="frontier")]
        if choice == "knock":
            return [move(FRONT_X + rng.uniform(-15, 15), z=1.0, tag="frontier"),
                    act("knock", 1.8, gaze="", fx="knock", tag="frontier"),
                    act("notice", 1.0, gaze="", tag="frontier")]
        return [move(10, tag="frontier"), act("push_wall", 2.4, face=-1, fx="edge", tag="frontier"),
                act("look", 1.0, gaze="u", tag="frontier")]

    def _frontier_progress(self, kind):
        c = self.c
        fr = c.frontier
        fr["progress"] += 1
        self.learn("room_edge", 1.0, 0.25)
        if fr["stage"] == 0 and fr["progress"] >= 3:
            fr["stage"] = 1
            self.log("frontier", "is testing the edges of its world - pushing, climbing, knocking on the glass.",
                     "ghost", important=True)
        elif fr["stage"] == 1 and fr["progress"] >= 7:
            fr["stage"] = 2
        texts = {"press": "pressed its face against the screen and stared straight at you.",
                 "edge": "touched the edge of its room, very carefully.",
                 "climb": "tried to climb the wall of its room.",
                 "knock": "knocked on the inside of the screen."}
        self.log("edge", texts[kind], "ghost", important=fr["progress"] == 1)

    def escape_started(self, roam):
        """Called by the app when the pet actually climbs out."""
        c = self.c
        fr = c.frontier
        fr["escapes"] += 1
        if fr["escapes"] >= 2:
            fr["stage"] = max(fr["stage"], 3)
        self.learn("edge_passable", 1.0, 0.35)
        if fr["escapes"] == 1:
            self.log("escape", "climbed OUT of its room and explored the screen around it!", "star",
                     important=True)
            self._rare("A pet that left its room")
        else:
            self.log("escape", "slipped out of its room to explore again.", "star")

    def roam_returned(self, souvenir, seconds):
        c = self.c
        c.frontier["roams"] += 1
        self.world.souvenirs.append(souvenir)
        self.world.souvenirs = self.world.souvenirs[-12:]
        self.log("roam", f"came back from {int(seconds)} seconds on your desktop, carrying {souvenir}.",
                 "star", important=True)
        if c.frontier["roams"] == 1:
            self._rare("A pet that visited the desktop")

    # ---- step side effects ---------------------------------------------------------------
    def step_fx(self, step, beh):
        fx = step.get("fx")
        if fx in self.recip.FX:
            self.recip.step_fx(fx, step, beh)
            return
        if fx and self._observer_fx(fx, beh):
            return
        c, w, rng = self.c, self.world, self.rng
        top = FLOOR_Y - 26
        if fx == "gift":
            kind = self._pending_gift or "flower"
            self._pending_gift = None
            gx = beh.x + (12 if beh.x < 100 else -12)
            self.gift = {"kind": kind, "x": gx, "seen": True}
            self._say(f"{c.name} brought you {GIFTS[kind]}! Click it to keep it.")
            self._play("happy")
        elif fx == "trick":
            c.good_window = 7.0
            if self.effects:
                self.effects.notes(beh.x, top, 2)
            if not self.trick_told:
                self.trick_told = True
                self._say(f"{c.name} shows off a little trick for you!")
        elif fx == "sparkle_floor" and self.effects:
            self.effects.sparkles(beh.x + beh.facing * 8, FLOOR_Y - 2, 4, 10)
        elif fx == "hum" and self.effects:
            self.effects.notes(beh.x, top, 2)
        elif fx == "chirp":
            self._play("select")
            if self.effects:
                self.effects.hearts(beh.x, top, 1)
        elif fx == "kick_hard":
            self.kick_ball(1 if self.ball_x >= beh.x else -1, 2.5)
        elif fx == "toy_fun":
            self.learn("toy_fun", 0.6, 0.08)
        elif fx and fx.startswith("snd:"):
            self._play(fx[4:])
            if self.effects and fx[4:] in ("chirp", "trill"):
                self.effects.notes(beh.x, top, 1)
        elif fx == "nudge_ball":
            self.kick_ball_to(self.cursor[0] if self.cursor else FRONT_X)
        elif fx == "floor_symbol":
            self.floor_marks.append([beh.x + beh.facing * 9, 25.0])
        elif fx == "experiment":
            self.experiment = {"name": "bowl_summons", "t": 0.0}
        elif fx == "mural":
            if wall.survived(w, c.generation, self.world_time) >= 6:    # its last drawing was left up
                self.learn("wall_ok", 1.0, 0.06)
            if w.add_mural(self._motif(beh.x), c.generation, c.name):
                if not self.watched and learning.belief(c, "wall_ok") < wall.SECRET_BELIEF:
                    if self.first("secret_drawing"):
                        self.log("draw", "drew on the wall while you weren't looking.", "drawing", important=True)
                    else:
                        self.log("draw", "added to its drawing while nobody was watching.", "drawing")
                elif self.first("first_drawing"):
                    self.log("draw", "started a drawing on the wall. Nobody asked it to.", "drawing",
                             important=True)
                else:
                    self.log("draw", "added a little more to its drawing on the wall.", "drawing")
        elif fx == "study_mural":
            gen = self._old_mural_artist()
            if gen and self.first("studied_mural"):
                self.log("culture", f"studied the old drawing left on the wall by {gen[1]}.", "drawing",
                         important=True)
                if rng.random() < 0.6 and self.recip.copy_old_fragment():
                    self.log("culture", "copied part of the old drawing into a picture of its own.", "drawing")
        elif fx == "find_item":
            self.carrying = rng.choice(ITEM_KINDS)
            if self.experimental() and rng.random() < 0.3 and len(w.loose) < 3:
                self.skills.drop_loose(self.carrying, under_plant=True)
                self.log("collect", f"found a {self.carrying}, but it rolled away under the plant.", "pebble")
                self.carrying = None
        elif fx == "drop_item":
            if self.carrying:
                w.add_item(self.carrying)
                if self.first("collection"):
                    self.log("collect", f"found a little {self.carrying} and started a collection.",
                             "pebble", important=True)
                else:
                    self.log("collect", f"added a {self.carrying} to its collection.", "pebble")
                self.carrying = None
                self.skills.arrange()
        elif fx == "bed_moved":
            self.log("bed", "dragged its bed to a new spot. It seems to prefer it there.", "moon",
                     important=True)
        elif fx == "ball_to_bed":
            self.kick_ball_to(w.bed_x + 14)
        elif fx == "pile_to_bed":
            w.pile["x"] = max(X_MIN, min(X_MAX, w.bed_x + 18))
        elif fx == "nest_check":
            if abs(self.ball_x - w.bed_x) < 26 and abs(w.pile["x"] - w.bed_x) < 26 and not w.nest:
                w.nest = True
                self.log("nest", "built a cozy nest around its bed out of its treasures.", "moon", important=True)
        elif fx == "kick_left_hard":
            self.kick_ball(-1, 2.6)
        elif fx == "kick_to_bowl":
            self.kick_ball_to(BOWL_X)
        elif fx and fx.startswith("invention:"):
            idea = fx.split(":", 1)[1]
            if idea == "ball_bowl" and not w.ball_in_bowl:
                return
            if not w.knows(idea):
                w.inventions.append({"id": idea, "by": c.name, "gen": c.generation})
                self.log("invent", f"invented a new game: {INVENTIONS[idea]}!", "ball", important=True)
                self._rare("An invented game")
            else:
                inv = w.inventor_of(idea)
                if inv["gen"] != c.generation and self.first("culture:" + idea):
                    self.log("culture", f"played {inv['by']}'s old game - {INVENTIONS[idea]}. "
                             "It must have picked it up from the room.", "ball", important=True)
        elif fx in ("press", "edge", "climb", "knock"):
            if fx == "press":
                w.marks["glass"] = w.marks.get("glass", 0) + 1
                for _ in range(3):
                    self.smudges.append([beh.x + rng.uniform(-6, 6), FLOOR_Y - 18 + rng.uniform(-5, 5), 30.0])
            elif fx == "knock":
                self._play("tap")
                if self.effects:
                    self.effects.sparkles(beh.x, FLOOR_Y - 18, 3, 8)
            else:
                w.marks["left"] = w.marks.get("left", 0) + 1
            self._frontier_progress(fx)
        elif fx and fx.startswith("escape:"):
            self.escape_request = {"roam": fx.endswith("roam")}

    def award(self, n, why):
        self._coins(n, why)

    def on_room_poke(self, obj, room=None):
        """You clicked something in the room. Reactions depend on who your pet is."""
        c, beh, rng, w = self.c, self.beh, self.rng, self.world
        self.observer.on_action("poke")
        if c is None or c.stage == "egg" or c.asleep or beh.tag in ("outside", "game", "toy") or beh.reaction:
            return None
        p = c.personality
        msg = None
        if obj == "plant":
            under = [it for it in w.loose if it["x"] > 147]
            if under and rng.random() < 0.6:
                it = under[0]
                it["vx"] = -rng.uniform(35, 55)          # shaken loose!
                msg = f"A little {it['kind']} tumbled out from under the plant."
                beh.interject([act("notice", 0.6, face=1), move(max(X_MIN, it["x"] - 30), speed=1.6),
                               act("excited", 1.0, face=1)])
            elif w.stash["items"] and rng.random() < 0.4:
                beh.interject([move(147, speed=2.4, walk="zoom", tag="reaction"),
                               act("refuse", 1.4, face=1, tag="reaction")])
                msg = f"{c.name} rushes over to guard its secret stash!"
                self.trace(["You shook the plant", "Its stash is hidden there", "Rushed over to guard it"], "private")
            elif self.fearful() or self.shyness() > 0.6:
                beh.interject([act("nervous", 1.2, tag="reaction")])
            elif p["curiosity"] > 0.45:
                beh.interject([move(132, speed=1.4), act("look", 1.2, face=1, gaze="u")])
            else:
                beh.interject([act("notice", 0.8, face=1)])
        elif obj == "window":
            if p["curiosity"] + p["playfulness"] > 0.7 or rng.random() < 0.5:
                beh.interject([move(WINDOW_X, z=0.0, speed=1.5, tag="window"), act("window", 4.0, tag="window")])
        elif obj == "lamp":
            beh.interject([act("watch", 1.8, gaze="u")])
        elif obj == "clock":
            beh.interject([act("watch", 1.0, gaze="u"), act("tilt", 0.8)])
        elif obj == "frame":
            beh.interject([act("notice", 0.8, face=-1, gaze="ul")])
        elif obj == "bowl":
            if c.hunger < 70:
                side = -1 if beh.x < BOWL_X else 1
                beh.interject([move(BOWL_X + side * 10, speed=2.0), act("excited", 1.2, face=-side)])
            else:
                beh.interject([act("look", 0.8, face=1 if BOWL_X > beh.x else -1, gaze="d")])
        elif obj == "bed":
            if self.sleepy() > 0.3:
                beh.interject([move(w.bed_x, speed=1.0), act("sit", 3.0)])
            else:
                beh.interject([act("notice", 0.6, face=1 if w.bed_x > beh.x else -1)])
        elif obj in ("pumpkin", "mirror"):
            beh.interject([act("jump" if p["playfulness"] > 0.5 else "look", 0.8)])
        return msg

    def _observer_fx(self, fx, beh):
        """Effects for the observer-update systems. Returns True if handled."""
        if fx.startswith("toy:"):
            shop.toy_fx(self, fx.split(":", 1)[1])
            return True
        if fx == "frame_fix":
            self.world.frame_tilt = 0
            if self.first("straightened"):
                self.log("tidy", "straightened the picture you knocked crooked.", "heart", important=True)
            return True
        if fx == "tool:cantreach":
            if self.first("cant_reach"):
                self.log("skill", "stretched for a trinket under the plant, but couldn't reach it.", "pebble")
            self.trace(["Wanted the trinket under the plant", "Too far to reach", "Remembered it"], "skill")
            return True
        if fx.startswith("tool:"):
            self.skills.step_fx(fx)
            return True
        if fx.startswith("stash:"):
            self.skills.stash_fx(fx.split(":", 1)[1])
            return True
        if fx.startswith("mirror:"):
            self.existential.mirror_done(int(fx.split(":")[1]))
            return True
        if fx == "reminisce":
            self.existential.reminisced()
            return True
        if fx == "figure:build":
            self.existential.build()
            return True
        if fx.startswith("figure:try:"):
            self.existential.figure_try(fx.split(":")[2])
            return True
        if fx.startswith("spatial:"):
            self.worldmodel.found(fx.split(":", 1)[1])
            return True
        if fx.startswith("symbol:"):
            self._draw_symbol(fx.split(":", 1)[1], beh)
            return True
        return False

    def _draw_symbol(self, kind, beh):
        """Symbolic drawings: the cursor, and drawings built on older generations' work."""
        c, w, rng = self.c, self.world, self.rng
        mx, my, mw, mh = MURAL_RECT
        col = hsv(c.genome.get("hue", 0), 0.65, 0.5)
        x0 = int(max(mx + 2, min(mx + mw - 14, beh.x - 4 + rng.uniform(-4, 4))))
        y0 = int(rng.uniform(my + 2, my + mh - 9))
        arrow = [(0, 0), (0, 1), (1, 1), (0, 2), (1, 2), (2, 2), (0, 3), (1, 3), (2, 3), (3, 3),
                 (0, 4), (1, 4), (0, 5), (2, 5), (2, 6)]
        pts = [(x0 + dx, y0 + dy, col) for dx, dy in arrow]
        o = self.observer.o
        if kind == "cursor":
            larger = o["symbols"] >= 1 and self.observer.stage() >= 5
            if larger:                          # the cursor, next to the thing it associates with it
                top = None
                for key, table in o["assoc"].items():
                    if key.startswith("to:") or key.startswith("z:"):
                        a = max(table, key=table.get)
                        if top is None or table[a] > top[1]:
                            top = (a, table[a])
                glyph = {"feed": [(0, 1), (1, 2), (2, 2), (3, 2), (4, 1)],
                         "play": [(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2)],
                         "pet": [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)]}.get(top[0] if top else "", [])
                pts += [(x0 + 6 + dx, y0 + 3 + dy, col) for dx, dy in glyph]
            w.add_mural(pts, c.generation, c.name)
            o["symbols"] += 1
            self.observer.stage()
            self.episodes.add("discovery", "drew_cursor", "drew the cursor", 0.8)
            if o["symbols"] == 1:
                self.log("draw", "drew an arrow shape on the wall - it looks a lot like your cursor.", "drawing",
                         important=True)
            elif larger and self.first("cursor_scene"):
                self.log("draw", "drew your cursor again, this time next to something it connects with you.",
                         "drawing", important=True)
            self.trace(["Model of you at stage " + str(self.observer.stage()),
                        "Represented the cursor as a drawing"], "symbol")
        elif kind == "ancestral":
            copied = self.recip.copy_old_fragment()
            w.add_mural(self._motif(beh.x + 8), c.generation, c.name)
            if o["symbols"]:
                w.add_mural([(x + 10, y, cc) for x, y, cc in pts], c.generation, c.name)
            if copied:
                self.log("culture", "worked part of an old drawing from a past generation into a new picture "
                         "of its own.", "drawing", important=True)
                self.episodes.add("collaboration", "ancestral", "built on an old drawing", 0.8)

    def observation_snapshot(self):
        """Everything Observation Mode shows, as (title, rows)."""
        from . import language
        c, beh = self.c, self.beh
        obs = self.observer.summary()
        r = self.recip
        lang = r.b["lang"]
        step = beh.step or {}
        now = [f"Doing: {beh.state} ({beh.tag or 'free'})",
               f"Next planned: {', '.join(s.get('state', s['kind']) for s in beh.plan[:4]) or '-'}",
               f"Mood: {self.mood_name}; watched by you: {self.watched}",
               f"Request: {r.request['intent'] + ' via ' + language.describe(r.request['sig'], r.request['intent']) if r.request else '-'}",
               f"Game: {r.game['kind'] + ' (' + r.game.get('phase', '') + ')' if r.game else '-'}",
               f"Predicting: {obs['prediction']}",
               f"Last decision: {r.b['last_decision'] or '-'}"]
        _ = step
        player = [f"Stage {obs['stage']}", f"Predictions: {obs['accuracy']}",
                  "Most visited: " + (", ".join(obs["zones"]) or "-")] + obs["assoc"] +                  ["Confidence: " + (", ".join(obs["conf"]) or "-"), obs["time"]]
        mem = [f"{e['text']} (strength {e['strength']:.2f}, x{e['n']})"
               for e in sorted(self.episodes.items, key=lambda e: -e["strength"])[:10]]
        rit = [f"before {k}: {v['seq'].replace('>', ' then ')} ({v['strength']:.2f})"
               for k, v in self.prituals.data["known"].items()]
        rit += [f"{k} ritual with you: {v['gesture']} ({v['strength']:.2f})" for k, v in r.b["rituals"].items()
                if v["gesture"]]
        learn = []
        for intent, table in lang["stats"].items():
            for sig, st in sorted(table.items(), key=lambda kv: -language.estimate(kv[1]))[:2]:
                if st["n"]:
                    learn.append(f"{intent}: {language.describe(sig, intent)} {st['s']:.1f}/{st['n']:.0f} "
                                 f"({st['m']} misread)")
        beliefs = [f"{k}: {v['v']:+.2f} ({v['n']} experiences)" for k, v in c.beliefs.items() if v["n"]]
        events, eligible = self.uncanny.summary()
        return [("Now", now), ("Model of you", player), ("Memories", mem or ["none yet"]),
                ("Rituals", rit or ["none yet"]), ("Signals and experiments", learn or ["none yet"]),
                ("Object skills", self.skills.summary()), ("Beliefs", beliefs or ["none yet"]),
                ("Room as it remembers it", self.worldmodel.summary() or ["-"]),
                ("Rare events", events), ("Eligible right now", eligible),
                ("Mirror", [f"stage {self.existential.mr['stage']}, sessions {self.existential.mr['sessions']}"
                            if self.mirror_on else "mirror is off"])]

    def _motif(self, x):
        """A little picture in this pet's own style."""
        c, rng = self.c, self.rng
        mx, my, mw, mh = MURAL_RECT
        styles = ("dots", "zigzag", "spiral", "sun", "heart", "eye", "wave", "stick")
        if rng.random() < 0.5:
            style = styles[sum(map(ord, c.name)) % len(styles)]      # its own signature style
        else:
            style = weighted(rng, self.recip.style_weights())        # styles you responded to
        self.recip.note_pet_style(style)
        col = hsv(c.genome.get("hue", 0) + rng.choice((0, 0, 40, 180)), 0.6, 0.6)
        cx = int(max(mx + 3, min(mx + mw - 4, x + rng.uniform(-6, 6))))
        cy = int(rng.uniform(my + 3, my + mh - 4))
        pts = {
            "dots": [(-2, 0), (0, -1), (2, 0), (0, 1)],
            "zigzag": [(-3, 0), (-2, -1), (-1, 0), (0, -1), (1, 0), (2, -1), (3, 0)],
            "spiral": [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1),
                       (2, -1), (2, 0), (2, 1), (2, 2)],
            "sun": [(0, 0), (1, 0), (0, 1), (1, 1), (-1, -1), (2, -1), (-1, 2), (2, 2), (0, -2), (3, 0),
                    (0, 3), (-2, 1)],
            "heart": [(-1, -1), (1, -1), (-2, 0), (0, 0), (2, 0), (-1, 1), (1, 1), (0, 2)],
            "eye": [(-2, 0), (-1, -1), (0, -1), (1, -1), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 0)],
            "wave": [(-3, 0), (-2, -1), (-1, -1), (0, 0), (1, 1), (2, 1), (3, 0)],
            "stick": [(0, -2), (0, -1), (0, 0), (-1, 0), (1, 0), (0, 1), (-1, 2), (1, 2), (0, -3)],
        }[style]
        return [(cx + dx, cy + dy, col) for dx, dy in pts]

    # ---- offline life: what it got up to while the game was closed --------------------------
    def offline_agenda(self, start_wt, sim_seconds):
        """Simulate (cheaply) what the pet did while the game was closed.

        The diary entries are real in the sense that the world changes to
        match them: drawings appear, collections grow, the bed moves."""
        c, rng, w = self.c, self.rng, self.world
        if c is None or c.stage == "egg":
            return 0
        logs = 0
        hours = int(sim_seconds // 3600)
        for h in range(hours):
            wt = start_wt + h * 3600 + rng.uniform(0, 3600)
            self.offline_wt = wt
            w.now = wt
            hour = time.localtime(wt).tm_hour
            if self.is_bedtime(hour):
                if rng.random() < 0.25:
                    icon = (rng.choice(list(self.recent)) if self.recent and rng.random() < 0.8
                            else rng.choice(STRANGE_DREAMS))
                    self.log("dream", "talked in its sleep, dreaming.", icon)
                    logs += 1
            elif rng.random() < 0.4 and c.stage != "baby":
                p = c.personality
                weather = self.weather_at(wt)
                choice = weighted(rng, {
                    "ball": 0.6 + p["playfulness"], "window": 0.5 + (1.0 if weather in ("rain", "snow") else 0),
                    "draw": (0.3 + (0.6 if self.mut("inventor") else 0))
                            * wall.draw_factor(learning.belief(c, "wall_ok"), False),
                    "collect": 0.25 + (1.5 if self.mut("collector") else 0),
                    "bed": 0.04 + (0.1 if self.q("explorer") else 0),
                    "frontier": 0.1 + (1.0 if self.mut("wanderer") else 0),
                    "invent": 0.08 + (1.0 if self.mut("inventor") else 0), "doze": 0.5, "silly": 0.3,
                })
                if choice == "ball":
                    self.ball_x = rng.uniform(BALL_MIN + 4, BALL_MAX - 12)
                    self.log("ball", "played with its ball by itself.", "ball")
                elif choice == "window":
                    what = {"rain": "watched the rain", "snow": "watched the snow fall"}.get(
                        weather, "gazed out of the window")
                    self.log("window", f"{what} for a while.", "moon")
                elif choice == "draw":
                    if w.add_mural(self._motif(rng.uniform(20, 120)), c.generation, c.name):
                        self.log("draw", "added a little more to its drawing on the wall.", "drawing")
                elif choice == "collect":
                    kind = rng.choice(ITEM_KINDS)
                    w.add_item(kind)
                    self.log("collect", f"added a {kind} to its collection.", "pebble")
                elif choice == "bed":
                    w.bed_x = rng.uniform(*BED_RANGE)
                    if abs(w.bed_x - BOWL_X) < 18:
                        w.bed_x = BOWL_X + 22
                    self.log("bed", "dragged its bed to a new spot. It seems to prefer it there.", "moon",
                             important=True)
                elif choice == "frontier":
                    self._frontier_progress(rng.choice(["edge", "press"] if c.frontier["stage"] == 0
                                                       else ["climb", "knock", "edge"]))
                elif choice == "invent":
                    idea = rng.choice(list(INVENTIONS))
                    if not w.knows(idea):
                        w.inventions.append({"id": idea, "by": c.name, "gen": c.generation})
                        self.log("invent", f"invented a new game: {INVENTIONS[idea]}!", "ball", important=True)
                    else:
                        self.log("ball", f"played its game of {INVENTIONS[idea]}.", "ball")
                elif choice == "doze":
                    self.log("doze", "dozed off for a bit.", "moon")
                else:
                    self.log("silly", "pulled silly faces when it thought nobody was looking.", "star")
                logs += 1
            if logs >= 10:
                break
        self.offline_wt = None
        return logs

    # ---- for drawing --------------------------------------------------------------------
    def gaze(self):
        c, beh = self.c, self.beh
        if c is None or c.stage == "egg" or c.asleep:
            return None
        st = beh.state
        if st == "window":
            return "ur" if WINDOW_X >= beh.x + 2 else ("ul" if WINDOW_X < beh.x - 2 else "u")
        if st in ("inspect", "ponder", "sleep", "doze", "fakesleep", "draw", "tap", "draw_floor"):
            return None
        if self.coy_t > 0 and self.cursor:
            return "l" if self.cursor[0] > beh.x else "r"
        if self.sound_t > 0 and self.sound_x is not None:
            return self._dir_to(self.sound_x, FLOOR_Y - 10)
        if self.hover_pet:
            return "u"
        if self.cursor and (self.look_on or st in ("notice", "wait", "tilt", "present", "happy",
                                                     "press", "knock", "chirp")):
            return self._dir_to(*self.cursor)
        return None

    def _dir_to(self, tx, ty):
        beh = self.beh
        dx = tx - beh.x
        dy = ty - (FLOOR_Y - 18 + beh.z * 6)
        h = "l" if dx < -8 else ("r" if dx > 8 else "")
        if dy > 14:
            return "d" if not h else h
        if dy < -10:
            return "u" + h
        return h


__all__ = ["Mind", "GIFTS", "BED_X", "BOWL_X", "WINDOW_X", "HIDE_X", "PEEK_X", "SOUVENIRS"]
