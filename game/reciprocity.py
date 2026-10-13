"""The Reciprocal Intelligence System.

Neither you nor the creature starts out understanding the other. Both learn:

    signals -> responses -> interpretation -> learning -> new behaviour

What lives here
  * Cursor gesture recognition inside the pet's room (left, right, side to
    side, circle, up, down, wiggle) - only from this game's own window.
  * Imitation both ways: the pet performs a gesture and waits to see if you
    copy it; you draw a gesture and the pet tries to copy you - imperfectly
    at first (it may mistake a circle for a sway) and better with practice.
  * Games the creature invents and leads: Follow My Lead, Pass the Ball,
    Echo, Follow the Path. Complexity grows from experience and personality.
  * Requests: when it wants something it picks a signal from its private
    language (language.py), watches what you do, and learns. It sometimes
    tests its assumptions, and it repairs misunderstandings (repeat, add a
    gesture, try something else, then give up gracefully - capped).
  * Negotiation: occasional, contextual disagreement that never blocks care.
  * Boundaries: if you chase a retreating pet it learns that retreating is
    needed; if you hold back it grows comfortable and starts approaching you.
  * Mutual rituals: if you keep greeting it with the same cursor gesture it
    learns it - and one day greets you first. Rituals can also fade.
  * Creative collaboration: draw on the wall with the mouse; it answers with
    marks of its own, sometimes imitating yours, and remembers what you liked.
  * A model of *you* (how you tend to respond) that shapes how it interacts.
  * Shared Memories, plus an optional Observation Lab for curious players.

All of it is optional, brief and non-punitive: if you don't respond, the pet
simply goes back to its own life.
"""
import math
import os
import time
from collections import deque

from . import language
from .behaviour import act, chase, move, weighted
from .config import FLOOR_Y, X_MAX, X_MIN
from .sprites import hsv
from .world import MURAL_RECT

BOWL_X, WINDOW_X, FRONT_X = 64, 124, 80
PLAYER_INK = (240, 110, 96)          # your marks on the wall are coral
CAPACITY = {"egg": 0.3, "baby": 0.5, "child": 0.75, "teen": 1.0, "adult": 1.0, "elder": 0.85}
CURSOR_GESTURES = ("left", "right", "side", "circle", "up", "down", "wiggle")
CURSOR_TO_PET = {"left": "left", "right": "right", "side": "side", "circle": "spin",
                 "up": "jump", "down": "jump", "wiggle": "wiggle"}
PET_TO_CURSOR = {"left": "left", "right": "right", "side": "side", "spin": "circle",
                 "jump": "up", "wiggle": "wiggle"}
CONFUSE = {"circle": "side", "side": "wiggle", "wiggle": "side", "up": "down", "down": "up",
           "left": "right", "right": "left"}
SIMILAR = {("side", "wiggle"): 0.6, ("wiggle", "side"): 0.6, ("circle", "side"): 0.4,
           ("side", "circle"): 0.4, ("up", "down"): 0.5, ("down", "up"): 0.5}
CURSOR_WORDS = {"left": "a swipe to the left", "right": "a swipe to the right", "side": "a side-to-side sweep",
                "circle": "a little circle", "up": "a flick upward", "down": "a flick downward",
                "wiggle": "a quick wiggle"}
PET_WORDS = {"left": "a hop to the left", "right": "a hop to the right", "side": "a sway",
             "spin": "a spin", "jump": "a jump", "wiggle": "a wiggle"}
GAMES = {"lead": "Follow My Lead", "catch": "Pass the Ball", "echo": "Echo", "path": "Follow the Path"}
CONTEXTS = {"return": "greeting", "feed": "mealtime", "bedtime": "bedtime", "play": "playtime"}
PLAYER_TRAITS = ("imitates", "sound", "gesture", "ball", "draws", "alone", "respects", "quick")
PLAYER_WORDS = {
    "imitates": "copies its gestures", "sound": "answers its sounds", "gesture": "answers its gestures",
    "ball": "plays with the ball", "draws": "draws with it", "alone": "leaves it to itself",
    "respects": "gives it space when it backs away", "quick": "prefers quick visits",
}
LEVEL_NAMES = {1: "Instinctive", 2: "Associative", 3: "Conventional", 4: "Combinatorial"}
OBJECTS = ("bed", "bowl", "ball", "window", "plant")
STYLES = ("dots", "zigzag", "spiral", "sun", "heart", "eye", "wave", "stick")


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _sgn(v):
    return 1 if v >= 0 else -1


# ---------------------------------------------------------------- gestures
def classify(points):
    """Classify a cursor stroke (list of (t, x, y) in LCD pixels)."""
    if len(points) < 4:
        return None
    xs = [p[1] for p in points]
    ys = [p[2] for p in points]
    length = sum(math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(len(xs) - 1))
    if length < 10:
        return None
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    dx, dy = xs[-1] - xs[0], ys[-1] - ys[0]
    runs = []
    for i in range(1, len(xs)):
        step = xs[i] - xs[i - 1]
        if abs(step) < 0.2:
            continue
        s = 1 if step > 0 else -1
        if runs and runs[-1][0] == s:
            runs[-1][1] += abs(step)
        else:
            runs.append([s, abs(step)])
    filtered = []
    for s, ln in runs:
        if ln < 3:
            continue
        if filtered and filtered[-1][0] == s:
            filtered[-1][1] += ln
        else:
            filtered.append([s, ln])
    reversals = max(0, len(filtered) - 1)
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    sweep, prev = 0.0, None
    for x, y in zip(xs, ys):
        if math.hypot(x - cx, y - cy) < 2:
            continue
        a = math.atan2(y - cy, x - cx)
        if prev is not None:
            d = a - prev
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            sweep += d
        prev = a
    if abs(sweep) > 1.6 * math.pi and w > 8 and h > 6:
        return "circle"
    if reversals >= 4 and w <= 34:
        return "wiggle"
    if reversals >= 1 and w >= 10 and h < max(10, w * 0.9):
        return "side"
    if abs(dy) > abs(dx) * 1.2 and abs(dy) > 10:
        return "up" if dy < 0 else "down"
    if abs(dx) > 12 and h < abs(dx):
        return "left" if dx < 0 else "right"
    return None


def similarity(a, b):
    if a == b:
        return 1.0
    return SIMILAR.get((a, b), 0.0)


class GestureTracker:
    """Turns the cursor path into discrete strokes (a stroke ends on a pause)."""

    def __init__(self):
        self.points = []
        self.still = 0.0
        self.out = []

    def reset(self):
        self.points = []
        self.still = 0.0

    def update(self, dt, t, cursor, pressed=False):
        if cursor is None or pressed:
            self.reset()
            return
        if self.points:
            last = self.points[-1]
            moved = math.hypot(cursor[0] - last[1], cursor[1] - last[2])
            self.still = self.still + dt if moved < 0.6 else 0.0
        self.points.append((t, cursor[0], cursor[1]))
        span = self.points[-1][0] - self.points[0][0]
        if (self.still >= 0.3 and len(self.points) > 4) or span > 2.6:
            moving = [p for p in self.points]
            g = classify(moving)
            if g:
                cx = sum(p[1] for p in moving) / len(moving)
                cy = sum(p[2] for p in moving) / len(moving)
                self.out.append((t, g, (cx, cy)))
            self.points = [self.points[-1]]

    def pop(self):
        out, self.out = self.out, []
        return out


# ---------------------------------------------------------------- bond data
def new_bond(rng, personality):
    return {
        "lang": language.new_language(rng, personality),
        "gest": {g: {"seen": 0, "ok": 0} for g in CURSOR_GESTURES},
        "games": {k: {"played": 0, "wins": 0, "best": 0, "interest": round(rng.uniform(0.35, 0.75), 2),
                      "today": 0} for k in GAMES},
        "rituals": {ctx: {"counts": {}, "gesture": None, "strength": 0.0} for ctx in CONTEXTS},
        "player": {k: 0.0 for k in PLAYER_TRAITS},
        "player_gestures": {},
        "styles": {},
        "memories": [],
        "daily": [],
        "today": {"day": 0, "attempts": 0, "successes": 0},
        "streak": {"intent": None, "n": 0},
        "collab": 0,
        "last_decision": "",
    }


def ensure_bond(c, rng):
    if not getattr(c, "bond", None) or "lang" not in c.bond:
        c.bond = new_bond(rng, c.personality)
    fresh = new_bond(rng, c.personality)
    for k, v in fresh.items():
        c.bond.setdefault(k, v)
    for k in PLAYER_TRAITS:
        c.bond["player"].setdefault(k, 0.0)
    return c.bond


class Reciprocity:
    def __init__(self, mind):
        self.mind = mind
        self.tracker = GestureTracker()
        self.reset()

    def reset(self):
        self.request = None
        self.game = None
        self.cd = {"request": 20.0, "game": 60.0, "imitate": 0.0, "rhythm": 0.0, "lead_follow": 0.0,
                   "neg": 0.0, "collab": 0.0}
        self.clicks = deque()
        self.dwell = {"obj": None, "t": 0.0, "done": False}
        self.dwells = deque()
        self.context = None
        self.anticipating = None
        self.retreat = None
        self.imitating = None
        self.insist = None
        self.ball_later = 0.0
        self.session_start = None
        self.was_watched = False
        self.last_pet_style = None
        self.last_player_stroke = None
        self.tracker.reset()

    # ---- helpers ------------------------------------------------------------------
    @property
    def c(self):
        return self.mind.c

    @property
    def b(self):
        return ensure_bond(self.mind.c, self.mind.rng)

    def capacity(self):
        c = self.c
        return min(1.0, CAPACITY.get(c.stage, 1.0) * (0.8 + 0.4 * c.personality["curiosity"]))

    def nudge(self, trait, target, rate=0.15):
        p = self.b["player"]
        p[trait] = round(_clamp(p.get(trait, 0.0) + rate * (target - p.get(trait, 0.0)), -1.0, 1.0), 3)

    def remember(self, key, text, update=False):
        mems = self.b["memories"]
        for m in mems:
            if m["key"] == key:
                if update:
                    m["text"], m["wt"] = text, self.mind.world_time
                    return True
                return False
        mems.append({"key": key, "text": text, "wt": self.mind.world_time})
        self.mind._log("bond", text, "heart", True)
        kind = ("communication" if key in ("first_convention", "first_recognised", "repaired") else
                "collaboration" if key in ("shared_drawing", "catch", "first_path") else "game")
        self.mind.episodes.add(kind, "mem:" + key, text, None)
        return True

    def attentive(self):
        """Attention limits: a busy pet may simply not notice you."""
        beh = self.mind.beh
        if beh.tag in ("game", "signal", "greet", "outside", "drag", "frontier") or beh.reaction:
            return 0.15
        if beh.tag in ("activity", "create", "window", "doze"):
            return 0.4
        return 0.85

    def busy(self):
        beh = self.mind.beh
        return (beh.reaction or beh.tag in ("game", "signal", "greet", "outside", "drag", "frontier", "waiting")
                or self.c.asleep or self.c.sick or self.c.stage == "egg")

    def obj_rect(self, name):
        w = self.mind.world
        return {
            "bed": (w.bed_x - 15, FLOOR_Y - 9, 30, 12),
            "bowl": (BOWL_X - 8, FLOOR_Y - 8, 16, 9),
            "ball": (self.mind.ball_x - 6, FLOOR_Y - 9, 12, 10),
            "window": (102, 10, 44, 30),
            "plant": (140, FLOOR_Y - 38, 21, 38),
        }[name]

    def obj_at(self, lx, ly):
        for name in ("ball", "bowl", "bed", "plant", "window"):
            x, y, w, h = self.obj_rect(name)
            if x <= lx <= x + w and y <= ly <= y + h:
                return name
        return None

    def obj_x(self, name):
        x, y, w, h = self.obj_rect(name)
        return x + w / 2

    def intent_x(self, intent):
        if intent == "food":
            return BOWL_X
        if intent == "play":
            return self.mind.ball_x
        if intent == "draw":
            mural = self.mind.world.mural
            return sum(p[0] for p in mural[-10:]) / len(mural[-10:]) if mural else 60.0
        return None

    # ---- per frame ------------------------------------------------------------------
    def update(self, dt, cursor, pressed=False):
        m, c = self.mind, self.c
        if c is None:
            return
        for k in self.cd:
            self.cd[k] = max(0.0, self.cd[k] - dt * (m.pace if k in ("request", "game") else 1.0))
        self._day_tick()
        self._session(m.watched)
        if c.stage == "egg" or c.departed:
            return
        if c.asleep or m.beh.tag == "outside":
            self.tracker.reset()
            if self.request or self.game:
                self.request = self.game = None
            return
        self.tracker.update(dt, m.clock, cursor if m.watched else None, pressed)
        for _, g, centre in self.tracker.pop():
            self.on_stroke(g, centre)
        self._dwell_tick(dt, cursor)
        self._clicks_tick()
        self._request_tick(dt, cursor)
        self._game_tick(dt, cursor)
        self._retreat_tick(cursor)
        if self.imitating:
            self.imitating["t"] += dt
            if self.imitating["t"] > 6:
                self.imitating = None
        if self.anticipating:
            self.anticipating["t"] += dt
            if self.anticipating["t"] > 7:
                self._ritual_missed()
        if self.context:
            self.context["t"] += dt
            if self.context["t"] > 7:
                self.context = None
        if self.insist and m.clock - self.insist["t"] > 12:
            self.insist = None
        if self.ball_later > 0:
            self.ball_later -= dt
            if self.ball_later <= 0 and not self.busy():
                m.beh.interject([chase(kicks=3, tag="activity"), act("happy", 1.0)], resume=False)
                m.log("ball", "played with the ball later - on its own terms.", "ball")

    def _day_tick(self):
        lt = time.localtime(self.mind.world_time)
        day = lt.tm_year * 400 + lt.tm_yday
        today = self.b["today"]
        if today["day"] == day:
            return
        if today["day"]:
            daily = self.b["daily"]
            daily.append([today["day"], today["attempts"], round(today["successes"], 2)])
            del daily[:-30]
            language.decay(self.b["lang"])
            for ctx, r in self.b["rituals"].items():
                r["counts"] = {g: round(n * 0.85, 2) for g, n in r["counts"].items() if n * 0.85 > 0.2}
                if r["gesture"]:
                    r["strength"] = round(r["strength"] - 0.05, 3)
                    if r["strength"] < 0.15:
                        self._ritual_fade(ctx)
            for g in self.b["games"].values():
                g["today"] = 0
                g["interest"] = round(g["interest"] + (0.55 - g["interest"]) * 0.05, 3)
        self.b["today"] = {"day": day, "attempts": 0, "successes": 0}

    def _session(self, watched):
        if watched and not self.was_watched:
            self.session_start = self.mind.clock
        elif not watched and self.was_watched and self.session_start is not None:
            dur = self.mind.clock - self.session_start - 45.0      # idle time before "away"
            self.nudge("quick", 1.0 if dur < 120 else -1.0, 0.12)
            self.nudge("alone", 0.3, 0.05)
        self.was_watched = watched

    # ---- strokes: imitation, rituals, games ----------------------------------------------
    def perceive(self, g, expecting=False):
        """Imperfect perception that improves with experience. When it is watching
        for a gesture it just demonstrated, it reads you much more reliably."""
        st = self.b["gest"].setdefault(g, {"seen": 0, "ok": 0})
        p_ok = _clamp(0.5 + 0.12 * st["seen"] + 0.1 * st["ok"] + (0.3 if expecting else 0.0), 0.5, 0.97) \
            * (0.85 + 0.15 * self.capacity())
        if self.mind.rng.random() < p_ok:
            return g
        return CONFUSE.get(g, g)

    def on_stroke(self, g, centre):
        m = self.mind
        pg = self.b["player_gestures"]
        pg[g] = round(pg.get(g, 0) + 1, 2)
        ep = m.episodes.add("gesture", f"gesture:{g}", f"your {CURSOR_WORDS[g]}", 0.6, {"gesture": g})
        if ep and ep["n"] == 1 and m.first("first_player_gesture"):
            m.trace([f"First gesture it recognised from you: {CURSOR_WORDS[g]}"], "observe")
        if self.anticipating and similarity(self.anticipating["expect"], g) >= 0.6:
            self._ritual_success()
            return
        if self.context:
            self._ritual_record(self.context["name"], g)
            self.context = None
        if self.game and self.game["kind"] == "lead" and self.game["phase"] == "wait":
            self.b["gest"].setdefault(g, {"seen": 0, "ok": 0})["seen"] += 1
            self.game["inputs"].append(self.perceive(g, expecting=True))
            self.game["last_input"] = m.clock
            return
        if self.game or self.request or self.busy():
            return
        # correction / confirmation of the pet's last imitation
        if self.imitating and self.imitating["t"] < 6 and g == self.imitating["gesture"]:
            st = self.b["gest"].setdefault(g, {"seen": 0, "ok": 0})
            if self.imitating["perceived"] == g:
                st["ok"] += 1
                m.beh.interject([act("happy", 1.0, tag="reaction")])
                if self.remember("pet_imitated", f"{self.c.name} copied your {CURSOR_WORDS[g]} for the first time."):
                    pass
                self.imitating = None
                return
            st["seen"] += 1            # you showed it again: it tries harder
        if self.cd["imitate"] > 0 or m.rng.random() > self.attentive():
            return
        beh = m.beh
        if abs(centre[0] - beh.x) > 50:
            return
        perceived = self.perceive(g)
        self.b["gest"][g]["seen"] += 1
        self.cd["imitate"] = 3.5
        self.imitating = {"gesture": g, "perceived": perceived, "t": 0.0}
        steps = [act("notice", 0.5, gaze="", tag="game")]
        steps += self.gesture_steps([CURSOR_TO_PET[perceived]], tag="game")
        steps.append(act("notice", 1.0, gaze="", tag="game"))
        beh.interject(steps)
        self._ritual_check_initiation(g)

    def _ritual_check_initiation(self, g):
        """A gesture you use a lot becomes one it repeats on its own."""
        pg = self.b["player_gestures"]
        total = sum(pg.values())
        if total >= 8 and pg.get(g, 0) >= 0.5 * total:
            self.remember("your_gesture", f"{self.c.name} has noticed you often make {CURSOR_WORDS[g]}.")

    # ---- rituals --------------------------------------------------------------------------
    def start_context(self, name):
        r = self.b["rituals"][name]
        if r["gesture"] and self.mind.watched and not self.busy() and \
                self.mind.rng.random() < 0.5 + r["strength"] * 0.5:
            pet_g = CURSOR_TO_PET[r["gesture"]]
            self.anticipating = {"ctx": name, "expect": r["gesture"], "t": 0.0}
            self.mind.beh.interject([act("notice", 0.6, gaze="", tag="game")]
                                    + self.gesture_steps([pet_g], tag="game")
                                    + [act("wait", 4.0, gaze="", tag="game")])
            return True
        self.context = {"name": name, "t": 0.0}
        return False

    def _ritual_record(self, ctx, g):
        r = self.b["rituals"][ctx]
        r["counts"][g] = round(r["counts"].get(g, 0) + 1, 2)
        total = sum(r["counts"].values())
        if not r["gesture"] and r["counts"][g] >= 3 and r["counts"][g] >= 0.6 * total:
            r["gesture"], r["strength"] = g, 0.5
            pet_g = PET_WORDS[CURSOR_TO_PET[g]]
            if ctx == "return":
                self.remember("ritual_return", f"A shared greeting began: you make {CURSOR_WORDS[g]}, "
                              f"{self.c.name} answers with {pet_g}.")
            else:
                self.remember(f"ritual_{ctx}", f"A {CONTEXTS[ctx]} ritual formed around {CURSOR_WORDS[g]}.")

    def _ritual_success(self):
        a, self.anticipating = self.anticipating, None
        r = self.b["rituals"][a["ctx"]]
        r["strength"] = round(min(1.0, r["strength"] + 0.2), 3)
        self.mind.beh.interject([act("excited", 1.2, gaze="", tag="reaction")], resume=False)
        if self.mind.effects:
            self.mind.effects.hearts(self.mind.beh.x, FLOOR_Y - 30, 2)
        if a["ctx"] == "return":
            self.remember("ritual_first_anticipated",
                          f"{self.c.name} greeted you first - and you answered.")

    def _ritual_missed(self):
        a, self.anticipating = self.anticipating, None
        r = self.b["rituals"][a["ctx"]]
        r["strength"] = round(r["strength"] - 0.15, 3)
        if r["strength"] < 0.15:
            self._ritual_fade(a["ctx"])

    def _ritual_fade(self, ctx):
        r = self.b["rituals"][ctx]
        if r["gesture"]:
            self.mind._log("bond", f"The {CONTEXTS[ctx]} ritual with {self.c.name} has faded away.", "moon", False)
        r["gesture"], r["strength"], r["counts"] = None, 0.0, {}

    def on_return(self, away):
        """Returns True if the pet greeted you with your shared ritual."""
        if self.c.asleep or self.c.stage == "egg":
            return False
        return self.start_context("return")

    def bedtime(self, moves):
        r = self.b["rituals"]["bedtime"]
        if not self.mind.watched:
            return moves
        if r["gesture"]:
            self.anticipating = {"ctx": "bedtime", "expect": r["gesture"], "t": 0.0}
            pose = {"wiggle": "bob", "side": "dance", "left": "dance", "right": "dance"}.get(
                CURSOR_TO_PET[r["gesture"]], CURSOR_TO_PET[r["gesture"]])
            return moves + [pose]
        self.context = {"name": "bedtime", "t": 0.0}
        return moves

    # ---- player actions ----------------------------------------------------------------
    def on_player_action(self, kind, detail=None):
        if kind == "ball":
            self.nudge("ball", 1.0, 0.1)
        elif kind == "draw":
            self.nudge("draws", 1.0, 0.12)
        elif kind == "feed" and not self.request:
            self.start_context("feed")
        elif kind == "game":
            self.context = {"name": "play", "t": 0.0}
        req = self.request
        if not req:
            return
        got = {"feed": "food", "game": "play", "ball": "play", "pet": "attention", "praise": "attention",
               "draw": "draw"}.get(kind)
        if got is None:
            return
        if got == req["intent"]:
            self._request_success(req)
        else:
            self._misunderstood(req, got)

    def _request_success(self, req, outcome=1.0):
        c, m = self.c, self.mind
        self.request = None
        m.prituals.credit("signal")
        lang = self.b["lang"]
        events = language.record(lang, req["intent"], req["sig"], outcome, capacity=self.capacity())
        self.b["today"]["attempts"] += 1
        self.b["today"]["successes"] += outcome
        self.nudge("sound" if language.is_vocal(req["sig"]) else "gesture", 1.0, 0.1)
        self.nudge("alone", -1.0, 0.05)
        self._handle_lang_events(events)
        if req.get("misunderstood"):
            self.remember("repaired", f"A misunderstanding was repaired: {c.name} wanted "
                          f"{language.INTENTS[req['intent']]['name']}, and you worked it out.")
        st = self.b["streak"]
        conv = lang["conventions"].get(req["intent"])
        if conv == req["sig"]:
            st["n"] = st["n"] + 1 if st["intent"] == req["intent"] else 1
            st["intent"] = req["intent"]
            if st["n"] >= 3:
                self.remember("first_recognised", f"You answered {c.name}'s "
                              f"{language.describe(conv, req['intent'])} correctly three times in a row.")
        if req["intent"] in ("attention", "draw") and not m.beh.reaction:
            m.beh.interject([act("happy", 1.0, tag="reaction")])

    def _misunderstood(self, req, got):
        m = self.mind
        lang = self.b["lang"]
        events = language.record(lang, req["intent"], req["sig"], 0.0, misunderstood=True,
                                 capacity=self.capacity())
        self._handle_lang_events(events)
        self.b["today"]["attempts"] += 1
        req["misunderstood"] = True
        if m.first("misunderstanding"):
            m.log("bond", f"tried to tell you something, but it wasn't "
                  f"{language.INTENTS[got]['name']}. It shook its head and tried again.", "note")
        self._repair(req, head_shake=True)

    def _handle_lang_events(self, events):
        c = self.c
        for ev in events:
            if ev[0] == "convention":
                _, intent, sig = ev
                self.remember("first_convention", f"{c.name} settled on {language.describe(sig, intent)} "
                              f"when it wants {language.INTENTS[intent]['name']}.")
                self.mind._log("language", f"{c.name} now uses {language.describe(sig, intent)} when it wants "
                               f"{language.INTENTS[intent]['name']}.", "note", True)
            elif ev[0] == "meaning_changed":
                _, old, new, sig = ev
                self.remember(f"meaning_{sig}", f"{language.describe(sig, new)} used to mean "
                              f"{language.INTENTS[old]['name']}; now it means {language.INTENTS[new]['name']}.")

    # ---- negotiation (never blocks essential care) -------------------------------------------
    def food_check(self, food_id, food_kind):
        """Return (message, sound, reaction) if the pet declines this offer, else None."""
        c, m, req = self.c, self.mind, self.request
        if c.asleep or c.sick or c.stage == "egg":
            return None
        if req and req["intent"] == "food" and req.get("test"):
            self._request_success(req)
            m.log("experiment", "tapped for food when it wasn't hungry - and you came. It sniffed the food "
                  "and left it, as if it had only been checking.", "belief")
            return (f"{c.name} sniffs the food... and leaves it. It wasn't really hungry.", "refuse", "look")
        if req and req["intent"] != "food" and c.hunger > 70:
            self._misunderstood(req, "food")
            return (f"{c.name} sniffs it and shakes its head - that's not what it meant.", "refuse", "refuse")
        if food_kind == "snack" and c.hunger > 85 and m.rng.random() < 0.4:
            self._first_disagreement("didn't want a snack")
            return (f"{c.name} sniffs the snack and politely declines.", "refuse", "look")
        return None

    def play_negotiation(self):
        c, m = self.c, self.mind
        if c.stage == "egg" or c.asleep or self.cd["neg"] > 0:
            return None
        if c.energy < 30 and m.rng.random() < 0.5:
            self.cd["neg"] = 30
            m.beh.interject([act("yawn", 1.4, tag="reaction"), move(m.world.bed_x, speed=0.8, tag="activity"),
                             act("hum", 4.0, tag="activity")], resume=False)
            self._first_disagreement("wanted to rest instead of play")
            return f"{c.name} yawns. It seems to want something quieter right now.", True
        if m.beh.state == "draw" and m.rng.random() < 0.6:
            self.cd["neg"] = 30
            m.beh.interject([act("wave", 1.2, gaze="", tag="reaction")])
            return f"{c.name} looks at its drawing, then at you - maybe it wants you to draw with it first.", False
        return None

    def game_choice(self, game_id, favourite):
        c, m = self.c, self.mind
        if not favourite or favourite == game_id or self.cd["neg"] > 0:
            return None
        if m.rng.random() < 0.2 * (c.personality["stubbornness"] + 0.5):
            self.cd["neg"] = 60
            self._first_disagreement("preferred a different game")
            return favourite
        return None

    def ball_refusal(self):
        """Called when the pet declines your ball. Returns the plan it follows instead."""
        c, m = self.c, self.mind
        if self.insist and m.clock - self.insist["t"] < 12:
            self.insist = None
            self.ball_later = m.rng.uniform(90, 200)
            self._first_disagreement("would rather do its own thing than play ball")
            m._say(f"{c.name} shakes its head and settles down. Not now.")
            return [act("refuse", 1.1, tag="reaction"), act("sit", 10.0, tag="activity")]
        if m.sleepy() > 0.3:
            place, end = m.world.bed_x, act("sit", 8.0, tag="activity")
        elif c.personality["curiosity"] > 0.45 or m.weather in ("rain", "snow"):
            place, end = WINDOW_X, act("window", 8.0, tag="window")
        else:
            place, end = m.beh.x - 30 * _sgn(m.ball_x - m.beh.x), act("sit", 6.0, tag="activity")
        self.insist = {"t": m.clock}
        return [act("look", 0.7, face=_sgn(m.ball_x - m.beh.x), gaze="d", tag="reaction"),
                act("notice", 0.7, gaze="", tag="reaction"),
                move(max(X_MIN, min(X_MAX, place)), tag="activity"), end]

    def _first_disagreement(self, what):
        self.remember("first_disagreement", f"First disagreement: {self.c.name} {what}.")

    # ---- boundaries ------------------------------------------------------------------------
    def on_retreat(self):
        m = self.mind
        if m.cursor:
            self.retreat = {"t": m.clock, "d0": abs(m.cursor[0] - m.beh.x) + 30}

    def _retreat_tick(self, cursor):
        r = self.retreat
        if not r:
            return
        m = self.mind
        elapsed = m.clock - r["t"]
        if cursor and 0.6 < elapsed < 3.5 and abs(cursor[0] - m.beh.x) < r["d0"] - 18:
            self.retreat = None
            self.nudge("respects", -1.0, 0.2)
            m.learn("touch", -0.6, 0.1)
            m.log("avoid", "was followed after it backed away. It retreated further.", "ghost")
        elif elapsed >= 3.5:
            self.retreat = None
            self.nudge("respects", 1.0, 0.2)
            m.learn("touch", 0.5, 0.1)
            if self.b["player"]["respects"] > 0.4 and m.first("comfortable"):
                m.log("brave", "seems more comfortable now that you give it space. It came a little closer.",
                      "heart", important=True)

    # ---- clicks & dwells -------------------------------------------------------------------
    def on_click_room(self, lx, ly):
        """Returns True if the click was used by a game."""
        m = self.mind
        self.clicks.append(m.clock)
        while self.clicks and m.clock - self.clicks[0] > 4:
            self.clicks.popleft()
        g = self.game
        if g and g["kind"] == "echo" and g["phase"] == "wait":
            g["inputs"].append(m.clock)
            g["last_input"] = m.clock
            m._play("chirp1")
            return True
        if g and g["kind"] == "path" and g["phase"] == "wait":
            obj = self.obj_at(lx, ly)
            if obj and (not g["inputs"] or g["inputs"][-1] != obj):
                g["inputs"].append(obj)
            return True
        return False

    def _clicks_tick(self):
        """You click a little rhythm; it may echo it back."""
        m = self.mind
        cl = list(self.clicks)
        if (len(cl) < 2 or self.game or self.cd["rhythm"] > 0 or m.clock - cl[-1] < 1.0
                or m.clock - cl[-1] > 1.3):
            return
        gaps = [b - a for a, b in zip(cl, cl[1:])]
        if len(cl) > 4 or max(gaps) > 0.9 or self.busy():
            return
        self.cd["rhythm"] = 8.0
        self.clicks.clear()
        if m.rng.random() < (0.35 + 0.4 * max(0.0, self.b["player"]["sound"]) + (0.4 if m.mut("echo") else 0)) \
                * self.attentive() * 1.4:
            m.beh.interject(self.rhythm_steps(gaps, tag="game") + [act("notice", 0.8, gaze="", tag="game")])
            m.first("echoed_rhythm") and m.log("bond", "echoed a rhythm you clicked.", "note")

    def _dwell_tick(self, dt, cursor):
        d = self.dwell
        obj = self.obj_at(*cursor) if cursor else None
        if obj != d["obj"]:
            self.dwell = {"obj": obj, "t": 0.0, "done": False}
            return
        if obj is None:
            return
        d["t"] += dt
        if d["t"] >= 0.35 and not d["done"]:
            d["done"] = True
            g = self.game
            if g and g["kind"] == "path" and g["phase"] == "wait":
                if not g["inputs"] or g["inputs"][-1] != obj:
                    g["inputs"].append(obj)
            elif d["t"] >= 0.35:
                self.dwells.append((self.mind.clock, obj))
                while len(self.dwells) > 4:
                    self.dwells.popleft()
                self._maybe_follow_lead()
        if self.request:
            ix = self.intent_x(self.request["intent"])
            if ix is not None and obj and abs(self.obj_x(obj) - ix) < 10:
                self.request["approached"] = True

    def _maybe_follow_lead(self):
        """You point out a route of objects; it follows (after it has played Follow the Path)."""
        m = self.mind
        recent = [(t, o) for t, o in self.dwells if m.clock - t < 6]
        seq = []
        for _, o in recent:
            if not seq or seq[-1] != o:
                seq.append(o)
        if (len(seq) < 2 or self.cd["lead_follow"] > 0 or self.game or self.busy()
                or self.b["games"]["path"]["wins"] < 1 or m.rng.random() > self.attentive()):
            return
        self.cd["lead_follow"] = 30.0
        self.dwells.clear()
        steps = []
        for o in seq[:3]:
            x = self.obj_x(o)
            steps += [move(max(X_MIN, min(X_MAX, x + (10 if x < 80 else -10))), speed=1.4, tag="game"),
                      act("look", 0.6, face=_sgn(x - m.beh.x), gaze="u" if o == "window" else "d", tag="game")]
        steps.append(act("happy", 1.0, tag="game"))
        m.beh.interject(steps, resume=False)
        self.remember("followed_lead", f"{self.c.name} followed a path you showed it.")

    # ---- requests: the creature experiments on you ---------------------------------------------
    def _intent(self):
        c, m = self.c, self.mind
        lang = self.b["lang"]
        food_conv = lang["conventions"].get("food")
        threshold = 45 + (15 if food_conv else 0)
        if 0 < c.hunger < threshold:
            return "food", False, "it was getting hungry"
        if c.happiness < 70 and m.playful() > 0.25 and self.b["player"]["alone"] < 0.6:
            return "play", False, "it felt playful"
        if (self.b["player"]["draws"] > 0.15 and self.cd["collab"] == 0 and c.stage != "baby"
                and m.rng.random() < 0.3):
            return "draw", False, "it wanted to draw with you"
        if m.emo["affectionate"] > 0.25 or m.emo["lonely"] > 0.3 or c.personality["sociability"] > 0.7:
            return "attention", False, "it wanted your attention"
        today = self.b["today"]
        if (food_conv and c.hunger > 80 and today.get("tests", 0) < 6
                and m.rng.random() < 0.12 * c.personality["curiosity"] * self.capacity()):
            today["tests"] = today.get("tests", 0) + 1         # bounded experiment budget
            return "food", True, "it wanted to test whether its food signal still works"
        return None, False, ""

    def maybe_initiate(self):
        m = self.mind
        if self.request or self.game or self.busy() or not m.watched or m.beh.tag in ("game",):
            return
        if self.cd["game"] == 0 and m.cursor and m.rng.random() < 0.012:
            if self._start_game():
                return
        if self.cd["request"] == 0 and m.rng.random() < 0.03:
            self._start_request()

    def _start_request(self):
        c, m = self.c, self.mind
        intent, test, why = self._intent()
        self.cd["request"] = m.rng.uniform(25, 45)
        if not intent:
            return
        lang = self.b["lang"]
        explore = 0.06 + 0.2 * c.personality["curiosity"] * self.capacity() + \
            (0.15 if language.level(lang, self.capacity()) <= 1 else 0)
        sig, reason = language.choose(lang, intent, m.rng, explore, self.b["player"], self.capacity())
        est = language.estimate(language._stat(lang, intent, sig))
        self.request = {"intent": intent, "sig": sig, "t": 0.0, "stage": 0, "test": test,
                        "approached": False, "tried": [sig]}
        self.b["last_decision"] = f"Wanted {language.INTENTS[intent]['name']} because {why}; {reason}."
        st = language._stat(lang, intent, sig)
        m.trace([f"Wanted {language.INTENTS[intent]['name']} ({why})",
                 f"Considered {language.describe(sig, intent)}",
                 f"Previously answered {st['s']:.1f} of {st['n']:.0f} times", reason], "signal")
        if test:
            m.uncanny.record("test_signal", "asked for food without needing it, to see if you'd respond")
        m.beh.interject(self.signal_steps(intent, sig, fluent=est > 0.6))
        if m.first("sig:" + sig + ":" + intent):
            m.log("signal", f"tried {language.describe(sig, intent)}, then looked at you. "
                  "Was it trying to tell you something?", "note")

    def _request_tick(self, dt, cursor):
        req = self.request
        if not req:
            return
        m = self.mind
        req["t"] += dt
        if cursor is not None:
            if req["intent"] == "attention" and abs(cursor[0] - m.beh.x) < 20:
                req["approached"] = True
            if req["intent"] == "draw" and MURAL_RECT[1] <= cursor[1] <= MURAL_RECT[1] + MURAL_RECT[3]:
                req["approached"] = True
        if (req["intent"] == "food" and m.hover_button == "feed") or \
                (req["intent"] == "play" and m.hover_button == "play"):
            req["approached"] = True
        if req["t"] < 14.0:
            return
        outcome = 0.35 if req["approached"] else 0.0
        lang = self.b["lang"]
        self._handle_lang_events(language.record(lang, req["intent"], req["sig"], outcome,
                                                 capacity=self.capacity()))
        self.b["today"]["attempts"] += 1
        self.b["today"]["successes"] += outcome
        if not req["approached"]:
            self.nudge("sound" if language.is_vocal(req["sig"]) else "gesture", -0.5, 0.05)
        if m.watched and req["stage"] < 3:
            self._repair(req)
        else:
            self.request = None
            self.nudge("alone", 1.0, 0.08)
            if req["stage"] >= 3:
                m.log("signal", "gave up trying to tell you something and went back to its own things.", "note")

    def _repair(self, req, head_shake=False):
        """Repair a failed or misunderstood signal: repeat, add a gesture, try another; capped."""
        m = self.mind
        req["stage"] += 1
        req["t"] = 0.0
        stage = req["stage"]
        if stage > 3:
            self.request = None
            return
        steps = [act("refuse", 0.9, tag="signal")] if head_shake else []
        intent = req["intent"]
        if stage == 1:
            steps += self.signal_steps(intent, req["sig"], fluent=True)
        elif stage == 2:
            steps += self.signal_steps(intent, req["sig"], fluent=True)[:-1]
            ix = self.intent_x(intent)
            if ix is not None:
                side = -1 if m.beh.x < ix else 1
                steps += [move(max(X_MIN, min(X_MAX, ix + side * 10)), speed=1.5, tag="signal"),
                          act("look", 0.8, face=-side, gaze="u" if intent == "draw" else "d", tag="signal"),
                          act("notice", 1.2, gaze="", tag="signal")]
            else:
                steps += [move(FRONT_X, z=1.0, speed=1.4, tag="signal"), act("notice", 1.2, gaze="", tag="signal")]
        else:
            lang = self.b["lang"]
            options = [s for s in lang["repertoire"].get(intent, []) if s not in req["tried"]]
            if not options:
                self.request = None
                return
            options.sort(key=lambda s: -language.estimate(language._stat(lang, intent, s)))
            req["sig"] = options[0]
            req["tried"].append(options[0])
            steps += self.signal_steps(intent, options[0], fluent=False)
        m.beh.interject(steps)

    def signal_steps(self, intent, sig, fluent, tag="signal"):
        m = self.mind
        beh = m.beh
        obj = language.INTENTS[intent]["obj"]
        ox = self.intent_x(intent)
        steps = []
        if not fluent and ox is not None:          # instinct: look at what it wants first
            steps.append(act("look", 0.7, face=_sgn(ox - beh.x), gaze="u" if obj == "wall" else "d", tag=tag))
        for p in sig.split("+"):
            steps += self.primitive_steps(p, intent, tag)
        steps.append(act("notice", 1.3, gaze="", tag=tag))
        return steps

    def primitive_steps(self, p, intent, tag):
        m = self.mind
        beh = m.beh
        obj = language.INTENTS[intent]["obj"]
        ox = self.intent_x(intent)
        if p == "chirp1":
            return [act("chirp", 0.6, gaze="", fx="snd:chirp1", tag=tag)]
        if p == "chirp2":
            return [act("chirp", 0.9, gaze="", fx="snd:chirp", tag=tag)]
        if p == "trill":
            return [act("chirp", 1.2, gaze="", fx="snd:trill", tag=tag)]
        if p == "coo":
            return [act("hum", 1.0, fx="snd:coo", tag=tag)]
        if p == "spin":
            return [act("spin", 1.0, tag=tag)]
        if p == "hop":
            return [act("jump", 0.7, tag=tag)]
        if p == "pause":
            return [act("wait", 1.4, gaze="", tag=tag)]
        if p == "wiggle":
            return [act("bob", 1.0, tag=tag)]
        if p == "front":
            return [move(max(X_MIN, min(X_MAX, beh.x)), z=1.0, speed=1.4, tag=tag), act("notice", 0.8, gaze="", tag=tag)]
        if p == "point":
            if ox is None:
                return [act("notice", 0.8, gaze="", tag=tag)]
            return [act("point", 1.0, face=_sgn(ox - beh.x), gaze="u" if obj == "wall" else "d", tag=tag)]
        if p == "approach":
            cx = m.cursor[0] if m.cursor else FRONT_X
            tx = cx - 12 if cx > beh.x else cx + 12
            return [move(max(X_MIN, min(X_MAX, tx)), z=1.0, speed=1.4, tag=tag), act("notice", 0.6, gaze="", tag=tag)]
        if p == "look":
            if ox is None:
                return [act("notice", 0.8, gaze="", tag=tag)]
            return [act("look", 0.8, face=_sgn(ox - beh.x), gaze="u" if obj == "wall" else "d", tag=tag)]
        side = -1 if beh.x < (ox or beh.x) else 1
        near = max(X_MIN, min(X_MAX, (ox or beh.x) + side * 10))
        if p == "push":
            if obj == "ball":
                cx = m.cursor[0] if m.cursor else FRONT_X
                s2 = 1 if m.ball_x > cx else -1
                return [move(max(X_MIN, min(X_MAX, m.ball_x + s2 * 8)), speed=1.4, tag=tag),
                        act("push", 0.4, face=-s2, fx="nudge_ball", tag=tag)]
            if obj == "bowl":
                return [move(near, speed=1.4, tag=tag), act("push", 0.5, face=-side, fx="bowl_push", tag=tag)]
        if p == "tap":
            if obj == "wall":
                return [move(near, z=0.0, speed=1.3, tag=tag), act("draw", 1.0, gaze="u", fx="wall_dot", tag=tag)]
            if obj == "you":
                return [act("jump", 0.7, tag=tag)]
            return [move(near, speed=1.4, tag=tag), act("tap", 0.7, face=-side, fx="snd:tap", tag=tag),
                    act("tap", 0.7, face=-side, fx="snd:tap", tag=tag)]
        return [act("notice", 0.6, gaze="", tag=tag)]

    # ---- the creature's own games --------------------------------------------------------
    def _start_game(self):
        c, m = self.c, self.mind
        games = self.b["games"]
        p = self.b["player"]
        if not (m.playful() > 0.2 or m.emo["affectionate"] > 0.2 or m.emo["excited"] > 0.2):
            return False
        weights = {
            "lead": games["lead"]["interest"] * (1 + 1.5 * max(0.0, p["imitates"]) + 0.5),
            "catch": games["catch"]["interest"] * (1 + 1.5 * max(0.0, p["ball"])),
            "echo": games["echo"]["interest"] * (1 + 1.5 * max(0.0, p["sound"])),
            "path": games["path"]["interest"] * (0.6 + c.personality["curiosity"]),
        }
        if c.stage == "baby":
            weights["echo"] = weights["path"] = 0.0
        for k, g in games.items():
            if g["today"] >= 4:
                weights[k] *= 0.3          # it gets bored of the same game
        kind = weighted(m.rng, weights)
        self.cd["game"] = m.rng.uniform(120, 240)
        games[kind]["played"] += 1
        games[kind]["today"] += 1
        if games[kind]["played"] == 1:
            self.remember(f"invented_{kind}", f"{c.name} invented a game of its own: {GAMES[kind]}.")
        getattr(self, "_start_" + kind)()
        return True

    def _length(self, kind, cap=4):
        g = self.b["games"][kind]
        c = self.c
        skill = g["wins"] * 0.35 * self.capacity() + c.personality["curiosity"] * 0.5
        length = 1 + int(skill)
        if self.b["player"]["quick"] > 0.4:
            length -= 1
        cap = max(1, min(cap, 1 + int(self.capacity() * 3)))
        return max(1, min(cap, length))

    def gesture_steps(self, gestures, tag="game"):
        x = self.mind.beh.x
        steps = []
        for g in gestures:
            if g == "left":
                x = max(X_MIN, x - 16)
                steps.append(move(x, speed=1.7, tag=tag))
            elif g == "right":
                x = min(X_MAX, x + 16)
                steps.append(move(x, speed=1.7, tag=tag))
            elif g == "side":
                a, b = max(X_MIN, x - 10), min(X_MAX, x + 10)
                steps += [move(a, speed=2.0, tag=tag), move(b, speed=2.0, tag=tag), move(x, speed=2.0, tag=tag)]
            elif g == "spin":
                steps.append(act("spin", 1.0, tag=tag))
            elif g == "jump":
                steps.append(act("jump", 0.7, tag=tag))
            elif g == "wiggle":
                steps.append(act("bob", 1.0, tag=tag))
            steps.append(act("idle", 0.25, tag=tag))
        return steps

    def _pattern(self, length):
        m, c = self.mind, self.c
        options = ["left", "right", "jump"] if c.stage == "baby" else ["left", "right", "side", "spin", "jump", "wiggle"]
        prefs = self.b["player_gestures"]
        weights = {g: 1.0 + 0.3 * prefs.get(PET_TO_CURSOR[g], 0) for g in options}
        out = []
        x = m.beh.x
        for _ in range(length):
            w = dict(weights)
            if x < X_MIN + 20:
                w["left"] = 0
            if x > X_MAX - 20:
                w["right"] = 0
            g = weighted(m.rng, w)
            x += {"left": -16, "right": 16}.get(g, 0)
            out.append(g)
        return out

    def _start_lead(self, length=None):
        L = length or self._length("lead")
        g = self.game if self.game and self.game["kind"] == "lead" else \
            {"kind": "lead", "round": 0, "fails": 0, "streak": 0}
        g.update({"phase": "show", "t": 0.0, "pattern": self._pattern(L), "inputs": [], "last_input": 0.0})
        g["round"] += 1
        self.game = g
        steps = [act("notice", 0.6, gaze="", tag="game")] + self.gesture_steps(g["pattern"]) + \
                [act("wait", 9.0, gaze="", fx="game_wait", tag="game")]
        self.mind.beh.start_plan(steps)

    def _start_catch(self):
        self.game = {"kind": "catch", "phase": "push", "t": 0.0, "rally": 0, "touched": False}
        self._catch_push()

    def _catch_push(self):
        m = self.mind
        cx = m.cursor[0] if m.cursor else FRONT_X
        side = 1 if m.ball_x > cx else -1
        m.beh.start_plan([move(max(X_MIN, min(X_MAX, m.ball_x + side * 8)), speed=1.6, tag="game"),
                          act("push", 0.4, face=-side, fx="catch_push", tag="game"),
                          act("wait", 8.0, gaze="", tag="game")])
        self.game["phase"] = "push"
        self.game["t"] = 0.0

    def _start_echo(self, beats=None):
        m = self.mind
        n = beats or min(4, 1 + self._length("echo", 3))
        gaps = [m.rng.choice((0.3, 0.3, 0.7)) for _ in range(max(1, n - 1))]
        g = self.game if self.game and self.game["kind"] == "echo" else {"kind": "echo", "round": 0, "fails": 0}
        g.update({"phase": "show", "t": 0.0, "gaps": gaps, "inputs": [], "last_input": 0.0})
        g["round"] += 1
        self.game = g
        m.beh.start_plan([act("notice", 0.5, gaze="", tag="game")] + self.rhythm_steps(gaps, tag="game")
                         + [act("wait", 6.0, gaze="", fx="game_wait", tag="game")])

    def rhythm_steps(self, gaps, tag="game"):
        """One chirp per beat; each beat lasts until the next one."""
        beats = len(gaps) + 1
        return [act("chirp", gaps[i] if i < len(gaps) else 0.4, gaze="", fx="snd:chirp1", tag=tag)
                for i in range(beats)]

    def _start_path(self):
        m = self.mind
        n = 2 + (1 if self.b["games"]["path"]["wins"] >= 2 and self.capacity() > 0.7 else 0)
        seq = []
        options = list(OBJECTS)
        for _ in range(n):
            o = m.rng.choice([x for x in options if not seq or x != seq[-1]])
            seq.append(o)
        self.game = {"kind": "path", "phase": "show", "t": 0.0, "seq": seq, "inputs": []}
        steps = []
        for o in seq:
            x = self.obj_x(o)
            steps += [move(max(X_MIN, min(X_MAX, x + (10 if x < 80 else -10))), speed=1.5, tag="game"),
                      act("look", 0.7, face=_sgn(x - m.beh.x), gaze="u" if o in ("window", "plant") else "d",
                          tag="game")]
        steps += [move(FRONT_X, z=0.8, speed=1.4, tag="game"),
                  act("wait", 10.0, gaze="", fx="game_wait", tag="game")]
        m.beh.start_plan(steps)

    def _game_tick(self, dt, cursor):
        g = self.game
        if not g:
            return
        m = self.mind
        g["t"] += dt
        if m.beh.tag not in ("game", "reaction") and g["phase"] in ("show", "push"):
            self.game = None                 # it got distracted - attention limits
            return
        kind = g["kind"]
        if kind == "lead" and g["phase"] == "wait":
            done = (len(g["inputs"]) >= len(g["pattern"]) or g["t"] > 9.0
                    or (g["inputs"] and m.clock - g["last_input"] > 2.5))
            if done:
                self._lead_eval()
        elif kind == "echo" and g["phase"] == "wait":
            done = (len(g["inputs"]) >= len(g["gaps"]) + 1 and m.clock - g["last_input"] > 0.8) \
                or g["t"] > 6.0 or (g["inputs"] and m.clock - g["last_input"] > 1.6)
            if done:
                self._echo_eval()
        elif kind == "path" and g["phase"] == "wait":
            if len(g["inputs"]) >= len(g["seq"]) or g["t"] > 10.0:
                self._path_eval()
        elif kind == "catch":
            self._catch_tick(cursor)

    def _end_game(self, mood="happy", text=None):
        g = self.game
        if g:
            self.mind.episodes.add("game", f"game:{g['kind']}", GAMES[g["kind"]], 0.6, {"game": g["kind"]})
            self.mind.prituals.credit("play")
        self.game = None
        self.mind.beh.start_plan([act(mood, 1.4, tag="reaction")])
        if text:
            self.mind.log("game", text, "ball")
        self.context = {"name": "play", "t": 0.0}

    def _lead_eval(self):
        g, m = self.game, self.mind
        stats = self.b["games"]["lead"]
        pattern = [PET_TO_CURSOR[x] for x in g["pattern"]]
        inputs = g["inputs"]
        if not inputs and g["round"] == 1:
            self.nudge("imitates", -0.5, 0.1)
            self.nudge("alone", 1.0, 0.05)
            self.game = None
            m.beh.start_plan([act("look", 1.0, tag="activity")])
            return
        sim = sum(similarity(a, inputs[i]) if i < len(inputs) else 0 for i, a in enumerate(pattern)) / len(pattern)
        if sim >= 0.7:
            g["streak"] += 1
            stats["wins"] += 1
            stats["interest"] = round(min(0.95, stats["interest"] + 0.03), 3)
            self.nudge("imitates", 1.0, 0.12)
            self.remember("first_imitation", f"First successful imitation: you copied {self.c.name}'s "
                          f"{' then '.join(PET_WORDS[x] for x in g['pattern'])}.")
            if g["streak"] > stats["best"]:
                stats["best"] = g["streak"]
                if g["streak"] >= 2:
                    self.remember("longest_lead", f"Longest game of Follow My Lead: {g['streak']} rounds in a row.",
                                  update=True)
            if g["round"] >= 5:
                self.mind.award(2, "Follow My Lead")
                self._end_game("dance", f"played Follow My Lead with you - {g['streak']} rounds.")
                return
            extend = m.rng.random() < 0.4 + m.playful() * 0.5
            nxt = len(g["pattern"]) + (1 if extend else 0)
            if m.effects:
                m.effects.notes(m.beh.x, FLOOR_Y - 26, 2)
            m._play("point")
            m.beh.start_plan([act("happy", 1.0, tag="game")])
            self._queue_next(lambda: self._start_lead(min(nxt, max(1, int(1 + self.capacity() * 3)))))
        else:
            g["fails"] += 1
            if g["fails"] >= 2:
                self._end_game("happy" if m.playful() > 0.4 else "sad",
                               f"played Follow My Lead with you - {g['streak']} rounds.")
                return
            m.beh.start_plan([act("tilt", 1.0, tag="game")])
            self._queue_next(lambda: self._start_lead(max(1, len(g["pattern"]) - 1)))

    def _queue_next(self, fn):
        self.game["phase"] = "between"
        self.game["next"] = fn
        self.game["t"] = 0.0
        self.mind.beh.plan.append(act("idle", 0.3, fx="game_next", tag="game"))

    def _echo_eval(self):
        g, m = self.game, self.mind
        stats = self.b["games"]["echo"]
        clicks = g["inputs"]
        if not clicks:
            if g["round"] == 1:
                self.nudge("sound", -0.5, 0.05)
            self._end_game("look")
            return
        gaps = [b - a for a, b in zip(clicks, clicks[1:])]
        want = ["s" if x < 0.45 else "l" for x in g["gaps"]]
        got = ["s" if x < 0.45 else "l" for x in gaps]
        if len(clicks) == len(g["gaps"]) + 1 and want == got:
            stats["wins"] += 1
            self.nudge("sound", 1.0, 0.12)
            self.remember("first_echo", f"You echoed {self.c.name}'s chirps back to it.")
            m._play("point")
            m.beh.start_plan([act("happy", 1.0, tag="game")])
            if g["round"] >= 3:
                self.mind.award(1, "Echo")
                self._end_game("dance", "played Echo with you.")
                return
            n = len(g["gaps"]) + 2 if m.rng.random() < 0.5 else len(g["gaps"]) + 1
            self._queue_next(lambda: self._start_echo(min(5, n)))
        else:
            g["fails"] += 1
            # it imitates *your* rhythm back, then tries again
            m.beh.start_plan([act("tilt", 0.6, tag="game")] + self.rhythm_steps(gaps or [0.4], tag="game"))
            if g["fails"] >= 2:
                self._end_game("happy", "played Echo with you.")
                return
            self._queue_next(lambda: self._start_echo(len(g["gaps"]) + 1))

    def _path_eval(self):
        g, m = self.game, self.mind
        stats = self.b["games"]["path"]
        if g["inputs"][:len(g["seq"])] == g["seq"]:
            stats["wins"] += 1
            self.remember("first_path", f"You followed the path {self.c.name} showed you: "
                          f"{' > '.join(g['seq'])}.")
            self.mind.award(1, "Follow the Path")
            self._end_game("dance", "showed you a path around the room - and you followed it.")
            if m.effects:
                m.effects.hearts(m.beh.x, FLOOR_Y - 30, 2)
        else:
            self._end_game("look" if g["inputs"] else "idle")

    def _catch_tick(self, cursor):
        g, m = self.game, self.mind
        if m.world.ball_in_bowl or m.ball_x > 146:
            self._end_catch()
            return
        if g["phase"] == "wait_touch":
            if cursor and abs(cursor[0] - m.ball_x) < 7 and FLOOR_Y - 14 < cursor[1] < FLOOR_Y + 4:
                self.ball_touched()
            elif g["t"] > 7.0:
                self._end_catch()
        elif g["phase"] == "returning" and abs(m.ball_vx) < 6:
            self._catch_push()

    def ball_touched(self):
        """You sent the ball back."""
        g, m = self.game, self.mind
        if not g or g["kind"] != "catch" or g["phase"] != "wait_touch":
            return False
        m.kick_ball_to(m.beh.x)
        g["rally"] += 1
        g["phase"] = "returning"
        g["t"] = 0.0
        m._play("point")
        self.nudge("ball", 1.0, 0.1)
        m.beh.start_plan([act("excited", 0.8, tag="game"), act("wait", 6.0, gaze="", tag="game")])
        fatigue = 6 + int(m.playful() * 6)
        if g["rally"] == 3:
            self.remember("catch", f"You and {self.c.name} invented a game of catch.")
        if g["rally"] >= fatigue:
            self._end_catch()
        return True

    def _end_catch(self):
        g = self.game
        stats = self.b["games"]["catch"]
        if g["rally"] > stats["best"]:
            stats["best"] = g["rally"]
            if g["rally"] >= 3:
                self.remember("longest_catch", f"Longest game of catch: {g['rally']} passes.", update=True)
        if g["rally"] >= 3:
            self.mind.award(1 + g["rally"] // 4, "catch")
        if g["rally"] >= 2:
            stats["wins"] += 1
            self._end_game("happy", f"played catch with you - {g['rally']} passes.")
        else:
            if g["rally"] == 0:
                self.nudge("ball", -0.4, 0.05)
            self._end_game("look")

    # ---- step side effects -------------------------------------------------------------------
    FX = ("game_wait", "catch_push", "collab_reply", "wall_dot", "bowl_push", "game_next")

    def step_fx(self, fx, step, beh):
        m = self.mind
        g = self.game
        if fx == "game_wait" and g:
            g["phase"] = "wait"
            g["t"] = 0.0
            g["inputs"] = []
        elif fx == "game_next" and g and g.get("next"):
            fn = g.pop("next")
            fn()
        elif fx == "catch_push" and g:
            cx = m.cursor[0] if m.cursor else FRONT_X
            target = cx + m.cursor_dx * 0.4                 # leads a moving cursor a little
            m.kick_ball_to(max(14, min(140, target)))
            g["phase"] = "wait_touch"
            g["t"] = 0.0
        elif fx == "bowl_push":
            m.bowl_wobble = 0.6
            m._play("tap")
        elif fx == "wall_dot":
            mx, my, mw, mh = MURAL_RECT
            x = int(max(mx + 1, min(mx + mw - 2, beh.x + m.rng.uniform(-3, 3))))
            y = int(m.rng.uniform(my + 4, my + mh - 3))
            col = hsv(self.c.genome.get("hue", 0), 0.6, 0.6)
            m.world.add_mural([(x, y, col), (x + 1, y, col)], self.c.generation, self.c.name)
        elif fx == "collab_reply":
            self._collab_reply(beh)

    # ---- creative collaboration -----------------------------------------------------------------
    def on_wall_stroke(self, points):
        """You drew on the wall (points already added to the mural)."""
        m, c = self.mind, self.c
        if not points or c is None:
            return
        self.last_player_stroke = points
        m.note_action("draw")
        if self.last_pet_style and m.clock - self.last_pet_style[1] < 25:
            st = self.last_pet_style[0]
            self.b["styles"][st] = round(self.b["styles"].get(st, 0) + 1, 2)
        if c.stage == "egg" or c.asleep or self.busy() or self.cd["collab"] > 0:
            return
        if m.rng.random() > self.attentive() + 0.1:
            return
        self.cd["collab"] = 6.0
        cx = sum(p[0] for p in points) / len(points)
        tx = max(X_MIN, min(X_MAX, cx + m.rng.choice((-10, 10))))
        m.beh.interject([move(tx, z=0.0, speed=1.4, tag="create"),
                         act("ponder", 1.4, gaze="u", tag="create"),
                         act("draw", 2.0, gaze="u", fx="collab_reply", tag="create"),
                         act("notice", 1.0, gaze="", tag="create")], resume=False)

    def _collab_reply(self, beh):
        m, c = self.mind, self.c
        w = m.world
        col = hsv(c.genome.get("hue", 0), 0.65, 0.55)
        pts = self.last_player_stroke
        self.b["collab"] += 1
        mx, my, mw, mh = MURAL_RECT
        if pts and m.rng.random() < 0.5 + m.playful() * 0.3:
            # imitate your mark - imperfectly
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            x0, y0 = min(xs), min(ys)
            shape = [(x - x0, y - y0) for x, y in zip(xs, ys)]
            span = max(1, max(max(xs) - x0, max(ys) - y0))
            k = min(1.0, 8.0 / span)
            mirror = m.rng.random() < 0.25
            ox = int(max(mx + 2, min(mx + mw - 10, beh.x + m.rng.uniform(-4, 4))))
            oy = int(m.rng.uniform(my + 2, my + mh - 8))
            out = []
            for dx, dy in shape:
                if m.rng.random() < 0.12:
                    continue
                px = int((-dx if mirror else dx) * k) + ox + (8 if mirror else 0)
                py = int(dy * k) + oy + (1 if m.rng.random() < 0.15 else 0)
                out.append((px, py, col))
            w.add_mural(out, c.generation, c.name)
            self.last_pet_style = ("copy", m.clock)
            text = "copied your mark on the wall - not quite exactly."
        else:
            count = 1 + min(3, self.b["collab"] // 3)
            for _ in range(count):
                w.add_mural(m._motif(beh.x + m.rng.uniform(-10, 10)), c.generation, c.name)
            text = "answered your drawing with a mark of its own."
        if self.remember("shared_drawing", f"{c.name} answered your first mark on the wall with one of its own."):
            pass
        m.log("draw", text, "drawing")

    def style_weights(self):
        prefs = self.b["styles"]
        return {s: 1.0 + 0.6 * prefs.get(s, 0) for s in STYLES}

    def note_pet_style(self, style):
        self.last_pet_style = (style, self.mind.clock)

    def copy_old_fragment(self):
        """A new generation imitates part of an older drawing (including yours)."""
        m, c = self.mind, self.c
        old = [p for p in m.world.mural if p[3] != c.generation]
        if not old:
            return False
        seed = m.rng.choice(old)
        cluster = [p for p in old if abs(p[0] - seed[0]) <= 4 and abs(p[1] - seed[1]) <= 4][:14]
        dx = m.rng.choice((-12, 12))
        col = hsv(c.genome.get("hue", 0), 0.6, 0.6)
        m.world.add_mural([(p[0] + dx, p[1], col) for p in cluster], c.generation, c.name)
        return True

    # ---- life stages -----------------------------------------------------------------------
    def on_evolve(self):
        """Changing preferences: a game it loved as a baby may matter less now."""
        for g in self.b["games"].values():
            g["interest"] = round(_clamp(g["interest"] + self.mind.rng.uniform(-0.2, 0.2), 0.1, 0.95), 3)

    # ---- observation lab ----------------------------------------------------------------------
    def lab(self):
        b = self.b
        lang = b["lang"]
        cap = self.capacity()
        lvl = language.level(lang, cap)
        secs = []
        rows = [f"Level {lvl} - {LEVEL_NAMES[lvl]}", f"Leans toward {lang['style']} signals",
                f"Learning capacity right now: {int(cap * 100)}%"]
        for intent, sig in lang["conventions"].items():
            rows.append(f"Convention for {language.INTENTS[intent]['name']}: {language.describe(sig, intent)}")
        secs.append(("Language", rows))
        for intent in language.INTENTS:
            table = lang["stats"].get(intent, {})
            ranked = sorted(table.items(), key=lambda kv: -language.estimate(kv[1]))[:3]
            rows = []
            for sig, st in ranked:
                mark = " *" if lang["conventions"].get(intent) == sig else ""
                rows.append(f"{language.describe(sig, intent)}: {int(language.estimate(st) * 100)}% "
                            f"({st['n']:.0f} tries, {st['m']} misread){mark}")
            label = {"food": "food", "play": "play", "attention": "attention", "draw": "drawing together"}[intent]
            secs.append((f"Signals for {label}", rows or ["(not tried yet)"]))
        p = b["player"]
        secs.append(("How it sees you", [f"{PLAYER_WORDS[k]}: {self._bar(p[k])}" for k in PLAYER_TRAITS]))
        rit = []
        for ctx, r in b["rituals"].items():
            if r["gesture"]:
                rit.append(f"{CONTEXTS[ctx]}: {CURSOR_WORDS[r['gesture']]} (strength {r['strength']:.2f})")
            elif r["counts"]:
                top = max(r["counts"], key=r["counts"].get)
                rit.append(f"{CONTEXTS[ctx]}: forming? {CURSOR_WORDS[top]} x{r['counts'][top]:.0f}")
        secs.append(("Rituals", rit or ["none yet"]))
        secs.append(("Games it plays", [f"{GAMES[k]}: played {g['played']}, won {g['wins']}, best {g['best']}, "
                                        f"interest {g['interest']:.2f}" for k, g in b["games"].items()]))
        gest = [f"{CURSOR_WORDS[g]}: seen {st['seen']}, confirmed {st['ok']}" for g, st in b["gest"].items()
                if st["seen"]]
        secs.append(("Reading your gestures", gest or ["no gestures yet"]))
        daily = [d for d in b["daily"] if d[1]][-5:]
        today = b["today"]
        rows = [f"day {i + 1}: {s:.1f} of {a} signals understood" for i, (_, a, s) in enumerate(daily)]
        if today["attempts"]:
            rows.append(f"today: {today['successes']:.1f} of {today['attempts']} signals understood")
        if rows:
            secs.append(("Understanding over time", rows))
        secs.append(("Last decision", [b["last_decision"] or "-"]))
        return secs

    @staticmethod
    def _bar(v):
        n = int(round((v + 1) * 4))
        return "#" * n + "." * (8 - n) + f" {v:+.2f}"

    def report(self, folder):
        """Export the relationship for comparison experiments (e.g. after swapping saves)."""
        c = self.c
        stamp = time.strftime("%Y%m%d-%H%M")
        path = os.path.join(folder, f"relationship_{c.name}_gen{c.generation}_{stamp}.md")
        lines = [f"# Relationship report: {c.name} (generation {c.generation})", "",
                 f"Exported {time.strftime('%Y-%m-%d %H:%M')}. Species: {c.species}.", ""]
        lines += ["## Shared memories", ""] + [f"- {m['text']}" for m in self.b["memories"]] + [""]
        for title, rows in self.lab():
            lines += [f"## {title}", ""] + [f"- {r}" for r in rows] + [""]
        os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path
