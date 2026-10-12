"""Autonomous behaviour: an interruptible plan of small steps.

Everything the pet does is a *step*: walk somewhere ("move"), chase the
ball ("chase") or perform an animation for a while ("act"). Steps are queued
into a plan. The Living mind (living.py) chooses plans; when it has nothing
special in mind, a utility-weighted idle choice is used.

`interject()` inserts new steps *in front of* the current activity and puts
the unfinished activity back in the queue - so the pet can stop, look at
you, and then carry on with what it was doing instead of resetting.

Animation runs in real time (the pet never looks frantic at test speeds).
"""
import math

from .config import X_MIN, X_MAX
from .personality import has_quirk

DURATIONS = {
    "idle": (2.0, 4.0), "sit": (4.0, 8.0), "jump": (0.7, 0.7), "spin": (1.2, 1.2),
    "dance": (2.4, 2.4), "look": (2.0, 3.2), "sulk": (3.0, 5.0), "sick": (3.0, 5.0),
    "sad": (3.0, 5.0),
}
REACTION_TIME = {
    "eat": 2.4, "love": 2.0, "happy": 1.6, "sad": 2.0, "sulk": 2.6, "refuse": 1.4,
    "confused": 1.6, "proud": 2.0, "medicine": 1.5, "recover": 2.0, "dance": 2.4,
    "poop": 1.2, "idle": 1.2, "sick": 1.6, "call": 1.6,
}
IDLE_ACTIONS = ("idle", "sit", "jump", "spin", "dance", "look")
WALK_STATES = ("walk", "zoom", "sneak")
X_LIMIT = (10, 154)


def move(x, z=None, speed=1.0, walk="walk", tag=None, fx=None):
    return {"kind": "move", "x": float(x), "z": z, "speed": speed, "walk": walk, "tag": tag, "fx": fx}


def act(state, dur, face=None, gaze=None, tag=None, fx=None):
    return {"kind": "act", "state": state, "dur": float(dur), "face": face, "gaze": gaze,
            "tag": tag, "fx": fx}


def chase(kicks=2, power=1.0, tag=None, fx=None):
    return {"kind": "chase", "kicks": kicks, "power": power, "tag": tag, "fx": fx}


class Behaviour:
    def __init__(self, rng):
        self.rng = rng
        self.mind = None
        self.reset()
        self.anim_t = 0.0

    def reset(self):
        self.x = 80.0
        self.z = 0.0          # 0 = back of the rug, 1 = front of the screen
        self.facing = -1
        self.state = "idle"
        self.t = 0.0
        self.dur = 2.0
        self.target = None
        self.tz = None
        self.plan = []
        self.step = None
        self.last_idle = None
        self.call_timer = 0.0
        self.walk_check_t = 0.0
        self.sleep_spot = None
        self.sleepwalk_to = None
        self.ritual_q = []
        self._c = self._sp = None

    # ---- compatibility helpers ------------------------------------------------
    @property
    def reaction(self):
        return bool(self.step and self.step.get("tag") == "reaction")

    @property
    def tag(self):
        return self.step.get("tag") if self.step else None

    def set(self, state, dur=None):
        if dur is None:
            lo, hi = DURATIONS.get(state, (2.0, 3.0))
            dur = self.rng.uniform(lo, hi)
        self.plan = []
        self._begin(act(state, dur))

    def react(self, name, then=None):
        steps = [act(name, REACTION_TIME.get(name, 1.6), tag="reaction")]
        if then:
            steps.append(act(then, REACTION_TIME.get(then, 1.6), tag="reaction"))
        self.interject(steps)

    # ---- plans ----------------------------------------------------------------
    def _current_as_step(self):
        st = self.step
        if st is None or self.state in ("sleep", "wake", "egg"):
            return None
        if st.get("tag") == "reaction":
            return None
        if st["kind"] == "act":
            remaining = st["dur"] - self.t
            if remaining < 0.3:
                return None
            resumed = dict(st)
            resumed["dur"] = remaining
            resumed["fx"] = None
            return resumed
        resumed = dict(st)
        resumed["fx"] = None
        return resumed

    def interject(self, steps, resume=True):
        """Do `steps` now, then (optionally) carry on with the current activity."""
        cur = self._current_as_step() if resume else None
        rest = self.plan if resume else []
        self.plan = list(steps) + ([cur] if cur else []) + rest
        self.step = None
        self._advance()

    def start_plan(self, steps):
        self.plan = list(steps)
        self.step = None
        self._advance()

    def _advance(self, depth=0):
        if not self.plan:
            if self._c is None:
                self._begin(act("idle", 1.0))
                return
            plan = self.mind.pick(self._c, self._sp, self) if self.mind else None
            self.plan = list(plan) if plan else self.basic_choice(self._c, self._sp)
        self._begin(self.plan.pop(0), depth)

    def _begin(self, step, depth=0):
        self.step = step
        self.t = 0.0
        if step.get("fx") and self.mind:
            self.mind.step_fx(step, self)
        kind = step["kind"]
        if kind == "act" and self.mind is not None:
            self.mind.prituals.note_action(step["state"], self.x)
        if kind == "act":
            self.state = step["state"]
            self.dur = step["dur"]
            if step.get("face"):
                self.facing = step["face"]
            if self.state in IDLE_ACTIONS:
                self.last_idle = self.state
        elif kind == "move":
            self.target = max(X_LIMIT[0], min(X_LIMIT[1], step["x"]))
            self.tz = step.get("z")
            self.state = step.get("walk", "walk")
            self.dur = 1e9
            close = abs(self.target - self.x) < 1 and (self.tz is None or abs(self.tz - self.z) < 0.05)
            if close and depth < 6:
                self._advance(depth + 1)
        elif kind == "chase":
            self.state = "walk"
            self.dur = 1e9

    def basic_choice(self, c, sp):
        p, m = c.personality, c.memory
        if c.sick:
            weights = {"sick": 5.0, "idle": 2.0, "walk": 1.0, "sit": 2.0}
        else:
            happy, energy = c.happiness / 100.0, c.energy / 100.0
            weights = {
                "idle": 2.0 + p["independence"] * 2,
                "walk": 2.5 + p["curiosity"] * 3,
                "sit": 1.0 + (1 - energy) * 3 + p["independence"],
                "jump": p["playfulness"] * 3 * happy,
                "spin": p["playfulness"] * 1.5 * happy,
                "dance": p["playfulness"] * 2 if happy > 0.6 else 0.0,
                "look": p["curiosity"] * 2.5,
                "sulk": (2.5 if happy < 0.3 else 0.0)
                        + (p["stubbornness"] * 0.6 if c.discipline < 30 and c.stage != "baby" else 0.0),
                "sad": 3.0 if happy < 0.2 else 0.0,
            }
            if c.stage == "baby":
                weights["dance"] = 0.0
                weights["spin"] *= 0.3
                weights["jump"] += 1.0
            if c.elder:
                for k in ("jump", "dance", "spin"):
                    weights[k] *= 0.3
                weights["sit"] += 2.0
            for k, v in sp.get("tendencies", {}).items():
                if k in weights:
                    weights[k] += v * (0.4 if k == "sulk" and happy > 0.6 else 1.0)
            for k, v in m.habits.items():
                if k in weights:
                    weights[k] += v
        choice = weighted(self.rng, weights)
        if choice == "walk":
            fav = m.favourite_spot()
            if fav is not None and self.rng.random() < 0.35:
                target = fav + self.rng.uniform(-6, 6)
            else:
                target = self.rng.uniform(X_MIN, X_MAX)
                if abs(target - self.x) < 12:
                    target = X_MIN + X_MAX - target
            z = self.rng.choice([None, None, 0.0, 0.4])
            return [move(max(X_MIN, min(X_MAX, target)), z=z)]
        lo, hi = DURATIONS.get(choice, (2.0, 3.0))
        if choice in IDLE_ACTIONS:
            m.record_spot(self.x)
        return [act(choice, self.rng.uniform(lo, hi))]

    # ---- per-frame --------------------------------------------------------------
    def update(self, dt, c, sp):
        self._c, self._sp = c, sp
        self.anim_t += dt
        self.t += dt
        if c.stage == "egg":
            self.state, self.x, self.z, self.plan, self.step = "egg", 80.0, 0.0, [], None
            return
        if c.asleep:
            self._sleep_update(dt, c)
            return
        if self.state in ("sleep", "drowsy", "sleepwalk", "ritual"):
            self.sleep_spot = None
            self.sleepwalk_to = None
            self.ritual_q = []
            wake = 3.0 if has_quirk(c, "sleepyhead") else 1.6
            self.start_plan([act("wake", wake, tag="reaction")])
            if self.mind:
                self.mind.on_wake()
            return
        if self.step is None:
            self._advance()
            return
        if c.attention and c.attention != "dark" and not self.reaction and self.tag not in ("game", "signal"):
            self.call_timer += dt
            if self.call_timer > 7.0 and self.state in ("idle", "sit", "walk", "look", "wait", "ponder"):
                self.call_timer = 0.0
                self.interject([act("call", 1.6, tag="reaction")])
                return
        kind = self.step["kind"]
        if kind in ("move", "chase"):
            self._move_update(dt, c, sp)
        elif self.t >= self.dur:
            self._advance()

    def _speed(self, c, sp, mult=1.0):
        speed = 14.0 * sp.get("speed", 1.0) * mult
        if c.sick:
            speed *= 0.5
        if c.elder:
            speed *= 0.6
        if c.energy < 25:
            speed *= 0.7
        return speed

    def _move_update(self, dt, c, sp):
        step = self.step
        if step["kind"] == "chase":
            bx = self.mind.ball_x if self.mind else self.x
            side = 1 if bx >= self.x else -1
            self.target = max(X_LIMIT[0], min(X_LIMIT[1], bx - side * 7))
            if self.t > 9.0:          # give up if the ball keeps escaping
                self._advance()
                return
        speed = self._speed(c, sp, step.get("speed", 1.0))
        delta = self.target - self.x
        stepx = speed * dt
        if self.tz is not None:
            dz = self.tz - self.z
            self.z += max(-dt * 0.9, min(dt * 0.9, dz))
        self.walk_check_t += dt
        if self.walk_check_t > 0.6 and step["kind"] == "move" and self.mind:
            self.walk_check_t = 0.0
            if self.mind.walk_check(c, self):
                return
        if abs(delta) <= stepx:
            self.x = self.target
            z_done = self.tz is None or abs(self.tz - self.z) < 0.05
            if not z_done:
                return
            if step["kind"] == "chase":
                bx = self.mind.ball_x if self.mind else self.x
                direction = 1 if bx >= self.x else -1
                self.facing = direction
                if self.mind:
                    self.mind.kick_ball(direction, step.get("power", 1.0))
                left = step["kicks"] - 1
                nxt = [act("push", 0.35, face=direction, tag=step.get("tag"))]
                if left > 0:
                    again = dict(step)
                    again["kicks"] = left
                    nxt.append(again)
                self.plan = nxt + self.plan
            self._advance()
        else:
            self.x += stepx if delta > 0 else -stepx
            self.facing = 1 if delta > 0 else -1

    def _sleep_update(self, dt, c):
        if self.state == "sleep":
            if self.sleepwalk_to is not None:
                self.state = "sleepwalk"
            return
        if self.state == "sleepwalk":
            delta = self.sleepwalk_to - self.x
            if abs(delta) > 1.0:
                self.x += math.copysign(min(abs(delta), 5.0 * dt), delta)
                self.facing = 1 if delta > 0 else -1
            else:
                self.sleepwalk_to = None
                self.state = "sleep"
            return
        if self.sleep_spot is None and self.state not in ("drowsy", "ritual"):
            self.plan, self.step = [], None
            self.ritual_q = [(m, 1.0) for m in (self.mind.bedtime_ritual(c) if self.mind else [])]
            self.sleep_spot = self.mind.sleep_spot(c, self) if self.mind else self.x
            self.t = 0.0
        if self.ritual_q:
            move_name, dur = self.ritual_q[0]
            if self.state != "ritual":
                self.state, self.t = "ritual", 0.0
            self.ritual_state = move_name
            if self.t >= dur:
                self.ritual_q.pop(0)
                self.t = 0.0
            return
        self.plan, self.step = [], None
        delta = self.sleep_spot - self.x
        self.z += max(-dt * 0.5, min(dt * 0.5, -self.z))
        if abs(delta) > 1.0:
            self.state = "drowsy"
            self.x += math.copysign(min(abs(delta), 9.0 * dt), delta)
            self.facing = 1 if delta > 0 else -1
        else:
            moved = self.mind.on_sleep_arrive(self.x) if self.mind else None
            if moved is not None:                # its bed wasn't where it remembered
                self.sleep_spot = moved
                return
            self.state = "sleep"
            self.t = 0.0


def weighted(rng, weights):
    total = sum(max(0.0, w) for w in weights.values())
    if total <= 0:
        return next(iter(weights))
    r = rng.uniform(0, total)
    for k, w in weights.items():
        r -= max(0.0, w)
        if r <= 0:
            return k
    return next(iter(weights))


def pose_for(state, st, at, c, sp, facing):
    """Map a behaviour state to a sprite pose.

    st = time in state, at = global animation time.
    Returns (pose dict, y offset in LCD pixels, horizontal flip).
    """
    feats = sp.get("features", {})
    if c.sick:
        eyes, mouth = "sick", "frown"
    elif c.happiness < 25:
        eyes, mouth = "sad", "frown"
    elif c.happiness >= 60:
        eyes, mouth = "open", "smile"
    else:
        eyes, mouth = "open", "flat"
    pose = {"eyes": eyes, "mouth": mouth, "squash": 0, "feet": "both", "arms": "down"}
    y = 0.0
    flip = facing > 0
    breathe = 1 if math.sin(at * 2.4) > 0.75 else 0
    tick = int(at * 6) % 2
    cheerful = not c.sick
    sleepy = c.energy < 25 and not c.sick

    if state in ("idle", "egg"):
        pose["squash"] = breathe
        if sleepy:
            pose["eyes"] = "half"
    elif state in ("walk", "sneak"):
        pose["feet"] = "left" if tick else "right"
        y = -1 if tick else 0
        if sleepy:
            pose["eyes"] = "half"
    elif state == "zoom":
        fast = int(at * 12) % 2
        pose.update(feet="left" if fast else "right", eyes="happy" if cheerful else eyes,
                    mouth="big" if cheerful else mouth, arms="up")
        y = -2 if fast else 0
    elif state == "drowsy":
        pose.update(eyes="half", mouth="flat", feet="left" if int(at * 3) % 2 else "right")
    elif state == "sit":
        pose["squash"] = 1
        pose["feet"] = "tuck"
        if (st % 6) > 4.4 and eyes == "open":
            pose["eyes"] = "closed"
    elif state == "jump":
        ph = min(1.0, (st % 0.7) / 0.7)
        y = -math.sin(math.pi * ph) * 10
        pose["squash"] = -1 if 0.1 < ph < 0.9 else 1
        if cheerful:
            pose.update(eyes="happy", mouth="big", arms="up")
    elif state == "spin":
        flip = int(st * 7) % 2 == 0
        if cheerful:
            pose.update(eyes="happy", mouth="big", arms="up")
    elif state == "dance":
        flip = int(st * 2.5) % 2 == 0
        pose.update(feet="left" if tick else "right", arms="wave" if tick else "up")
        y = -abs(math.sin(st * 5)) * 3
        if cheerful:
            pose.update(eyes="happy", mouth="big")
    elif state == "look":
        flip = int(st / 0.8) % 2 == 0
        if eyes == "open":
            pose["mouth"] = "o" if (st % 1.6) > 1.0 else mouth
    elif state == "sleep":
        pose.update(eyes="closed", mouth="flat", feet="tuck")
        pose["squash"] = 1 if math.sin(at * 1.2) > 0 else 0
    elif state == "wake":
        pose.update(eyes="closed" if st < 0.8 else "half", mouth="o", arms="up")
    elif state == "eat":
        pose.update(eyes="happy", mouth="open" if int(st * 5) % 2 else "flat")
        pose["squash"] = int(st * 5) % 2
    elif state in ("happy", "pet"):
        pose.update(eyes="happy", mouth="big", arms="up")
        y = -abs(math.sin(st * 7)) * 3
    elif state == "love":
        pose.update(eyes="love", mouth="smile", blush=True)
        y = -abs(math.sin(st * 5)) * 2
    elif state == "proud":
        pose.update(eyes="happy", mouth="smile", arms="up", squash=-1)
    elif state == "sad":
        pose.update(eyes="sad", mouth="frown", squash=1)
    elif state == "sulk":
        pose.update(eyes="angry", mouth="frown", squash=1)
        flip = not flip
    elif state == "refuse":
        pose.update(eyes="angry", mouth="flat")
        flip = int(st * 6) % 2 == 0
    elif state == "confused":
        pose.update(eyes="wide", mouth="o")
    elif state == "call":
        pose.update(eyes="wide", mouth="open", arms="up")
        y = -abs(math.sin(st * 9)) * 3
    elif state == "medicine":
        pose.update(eyes="closed", mouth="frown", squash=1)
    elif state == "recover":
        pose.update(eyes="happy", mouth="smile", arms="up")
        y = -abs(math.sin(st * 6)) * 2
    elif state == "sick":
        pose.update(eyes="sick", mouth="frown", squash=breathe)
    elif state == "poop":
        pose.update(eyes="closed", mouth="flat", squash=1)
    elif state == "depart":
        pose.update(eyes="happy", mouth="smile", arms="up")
    elif state == "evolve":
        pose.update(eyes="closed", mouth="o")
    # ---- living-pet states ------------------------------------------------------
    elif state == "notice":
        pose.update(eyes="wide" if st < 0.5 else "open",
                    mouth="o" if st < 0.35 else ("smile" if c.happiness >= 40 else "flat"))
    elif state == "caught":
        pose.update(eyes="wide", mouth="o", blush=True, squash=-1 if st < 0.2 else 0)
    elif state == "wave":
        pose.update(eyes="happy" if cheerful else eyes, mouth="smile",
                    arms="wave" if int(at * 5) % 2 else "up")
    elif state == "inspect":
        pose.update(squash=1 if (st % 0.8) < 0.4 else 0, gaze="d",
                    mouth="o" if (st % 1.2) > 0.9 else mouth)
    elif state == "push":
        pose.update(feet="left", arms="up", eyes="happy" if cheerful else eyes, mouth="big")
    elif state == "yawn":
        pose.update(eyes="closed", mouth="o", arms="up", squash=-1 if st < 0.9 else 1)
    elif state == "doze":
        pose.update(eyes="closed", mouth="flat", feet="tuck", squash=breathe)
    elif state == "fakesleep":
        peeking = (st % 1.8) > 1.35
        pose.update(eyes="wink" if peeking else "closed", mouth="smile" if peeking else "flat",
                    feet="tuck", squash=1)
    elif state == "hum":
        pose.update(eyes="closed", mouth="smile" if int(st * 1.5) % 2 else "o", feet="tuck",
                    squash=breathe)
    elif state == "peek":
        pose.update(eyes="wide", mouth="flat")
    elif state == "hide":
        pose.update(mouth="flat", squash=1)
    elif state == "ponder":
        pose.update(eyes="half" if (st % 4) > 2.5 else eyes, mouth="flat", squash=1, feet="tuck",
                    gaze="u")
    elif state == "tilt":
        pose.update(eyes="wide", mouth="o", tilt=-1 if facing > 0 else 1)
    elif state == "silly":
        pose.update(eyes="wink", mouth="tongue", arms="wave" if int(at * 4) % 2 else "up")
        flip = int(st * 2) % 2 == 0
    elif state == "balance":
        pose.update(eyes="wide", mouth="wobbly", arms="up")
        flip = int(st * 3) % 2 == 0
        y = -5 + math.sin(st * 9) * 0.8
    elif state == "fall":
        pose.update(eyes="sick", mouth="o", squash=1)
    elif state == "present":
        pose.update(eyes="happy", mouth="smile", arms="up", squash=-1)
    elif state == "window":
        pose.update(feet="tuck", squash=1, mouth="o" if (st % 5) > 4 else "flat")
    elif state == "wait":
        pose.update(feet="tuck", squash=1, mouth="flat", gaze="")
    elif state == "nervous":
        pose.update(eyes="wide", mouth="wobbly", squash=1)
        y = -1 if int(at * 14) % 2 else 0
    elif state == "excited":
        pose.update(eyes="happy", mouth="big", arms="up")
        y = -abs(math.sin(st * 10)) * 2
    # ---- artificial-life states ----------------------------------------------------
    elif state == "chirp":
        pose.update(eyes="open", mouth="open" if int(st * 6) % 2 else "o")
        y = -abs(math.sin(st * 12)) * 1.5
    elif state == "bob":
        pose.update(eyes="happy", mouth="smile", squash=1 if int(st * 5) % 2 else -1)
    elif state == "tap":
        pose.update(arms="up" if int(st * 5) % 2 else "down", gaze="d", squash=int(st * 5) % 2)
    elif state in ("draw", "draw_floor"):
        pose.update(arms="wave" if int(st * 4) % 2 else "up", mouth="o" if (st % 1.5) > 1.1 else "smile",
                    gaze="u" if state == "draw" else "d")
        flip = int(st * 1.5) % 2 == 0
    elif state == "drop":
        pose.update(squash=1, eyes="happy", mouth="smile")
    elif state == "press":
        pose.update(eyes="wide", mouth="o", squash=-1, gaze="")
    elif state == "knock":
        pose.update(eyes="open", mouth="flat", arms="up" if int(st * 6) % 2 else "down", gaze="")
    elif state == "push_wall":
        pose.update(arms="up", eyes="angry" if (st % 1.0) < 0.5 else "open", mouth="flat",
                    feet="left" if int(st * 4) % 2 else "right")
    elif state == "climb":
        ph = min(1.0, st / 2.2)
        y = -ph * 34
        pose.update(arms="up" if int(st * 5) % 2 else "wave", feet="tuck", eyes="open", mouth="flat",
                    gaze="u")
    elif state == "drag":
        pose.update(arms="up", feet="left" if tick else "right", eyes="angry", mouth="flat")
        y = -1 if tick else 0
    elif state == "dropin":
        ph = min(1.0, st / 0.6)
        y = -70 * (1 - ph) ** 2
        pose.update(eyes="wide" if ph < 1 else "happy", mouth="o", squash=1 if ph >= 1 else -1)
    elif state == "sleepwalk":
        pose.update(eyes="closed", mouth="flat", arms="up", feet="left" if int(at * 2) % 2 else "right")
    elif state == "watch":
        pose.update(squash=0, mouth="flat" if eyes == "open" else mouth)
    elif state == "point":
        pose.update(arms="wave", mouth="o")
    elif state == "ritual":
        pose.update(eyes="happy", mouth="smile", arms="up")
        flip = int(st * 4) % 2 == 0

    if feats.get("face") == "grumpy" and pose["eyes"] == "open":
        pose["eyes"] = "grumpy"
    if pose["eyes"] in ("open", "grumpy") and (at % 3.4) < 0.14:
        pose["eyes"] = "closed"
    if feats.get("wings"):
        pose["wing"] = int(at * (4 if state in ("happy", "dance", "jump", "call", "zoom", "excited") else 1.5)) % 2
    if feats.get("tail", "none") != "none" and c.happiness >= 50 and not c.asleep:
        pose["wag"] = int(at * (6 if state == "excited" else 3)) % 2
    if feats.get("sparkle") or c.genome.get("mutation") == "shiny":
        pose["twinkle"] = int(at * 3) % 4 + 1
    if feats.get("glitch") or c.genome.get("mutation") == "glitch":
        g = int(at * 12)
        pose["glitch"] = (g % 4) + 1 if (g % 50) < 3 else 0
    return pose, y, flip
