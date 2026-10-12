"""Personal rituals the creature invents for itself.

The creature keeps a short log of its own recent actions. Whenever something
good happens - eating, going to sleep, starting to play, you coming back,
being understood - the actions it performed just before get a little credit.
If the same small sequence keeps preceding the same outcome, it starts doing
that sequence on purpose beforehand: circling its bed before sleeping,
tapping its bowl before eating, visiting the window before play.

Like a superstition, it is learned from coincidence and reinforcement, so
every creature ends up with different rituals - or none at all. Rituals
that stop being performed fade.
"""
import time
from collections import deque

CONTEXTS = {"eat": "eating", "sleep": "sleeping", "play": "playing", "return": "greeting you",
            "signal": "asking you for something"}
WORDS = {"spin": "spins", "jump": "hops", "look": "looks around", "tap": "taps", "inspect": "sniffs the floor",
         "dance": "does a little dance", "sit": "sits for a moment", "bob": "wiggles", "ponder": "pauses to think",
         "wave": "waves", "window": "looks out of the window", "hum": "hums",
         "excited": "gets excited", "watch": "watches you", "chirp": "chirps", "notice": "looks at you"}
TRACKED = set(WORDS)
PLACES = {"bed", "bowl", "window", "plant", "front"}


def ensure(c):
    if not isinstance(getattr(c, "prituals", None), dict) or "counts" not in c.prituals:
        c.prituals = {"counts": {k: {} for k in CONTEXTS}, "known": {}, "occ": {k: 0 for k in CONTEXTS},
                      "day": 0}
    for k in CONTEXTS:
        c.prituals["counts"].setdefault(k, {})
        c.prituals["occ"].setdefault(k, 0)
    return c.prituals


def describe(seq):
    parts = []
    for item in seq.split(">"):
        if item.startswith("at:"):
            parts.append(f"visits the {item[3:]}" if item[3:] != "front" else "comes to the front")
        else:
            parts.append(WORDS.get(item, item))
    return ", then ".join(parts)


class Rituals:
    def __init__(self, mind):
        self.mind = mind
        self.log = deque(maxlen=8)        # (clock, action)
        self.last_place = None

    @property
    def data(self):
        return ensure(self.mind.c)

    def note_action(self, state, x):
        """Called when the creature begins an action step."""
        if state not in TRACKED:
            return
        place = self.place_of(x)
        if place and place != self.last_place:
            self.log.append((self.mind.clock, "at:" + place))
        self.last_place = place
        if not self.log or self.log[-1][1] != state:
            self.log.append((self.mind.clock, state))

    def place_of(self, x):
        w = self.mind.world
        if abs(x - w.bed_x) < 12:
            return "bed"
        if abs(x - 64) < 12:
            return "bowl"
        if abs(x - 124) < 10:
            return "window"
        if x > 138:
            return "plant"
        if self.mind.beh.z > 0.7:
            return "front"
        return None

    def credit(self, context):
        """Something good happened in `context`: credit what it did just before."""
        m = self.mind
        if m.c is None or m.c.stage in ("egg",):
            return None
        d = self.data
        d["occ"][context] += 1
        recent = [a for t, a in self.log if m.clock - t < 25]
        if len(recent) < 2:
            return None
        seq = ">".join(recent[-2:])
        table = d["counts"][context]
        for k in list(table):
            table[k] = round(table[k] * 0.97, 3)
        table[seq] = round(table.get(seq, 0) + 1, 3)
        total = sum(table.values())
        if (context not in d["known"] and table[seq] >= 3 and table[seq] >= 0.5 * total
                and d["occ"][context] >= 4):
            d["known"][context] = {"seq": seq, "strength": 0.6, "since": m.world_time, "done": 0}
            m.log("ritual", f"has developed a ritual of its own: before {CONTEXTS[context]} it "
                  f"{describe(seq)}.", "moon", important=True)
            m.episodes.add("ritual", f"ritual:{context}", f"its {CONTEXTS[context]} ritual", 0.8)
            m.trace([f"Before {CONTEXTS[context]}, it happened to {describe(seq)}",
                     f"Same sequence {table[seq]:.0f} times", "Now does it on purpose"], "ritual")
            m.uncanny.record("strange_ritual", f"{CONTEXTS[context]} ritual formed")
            return seq
        known = d["known"].get(context)
        if known and known["seq"] == seq:
            known["strength"] = round(min(1.0, known["strength"] + 0.05), 3)
        return None

    def steps_for(self, context):
        """Action steps for a known ritual (or [])."""
        from .behaviour import act, move
        known = self.data["known"].get(context)
        if not known or self.mind.rng.random() > 0.4 + known["strength"] * 0.6:
            return []
        known["done"] += 1
        steps = []
        for item in known["seq"].split(">"):
            if item.startswith("at:"):
                x = {"bed": self.mind.world.bed_x, "bowl": 52, "window": 124, "plant": 140,
                     "front": 80}[item[3:]]
                steps.append(move(x, z=1.0 if item == "at:front" else None, speed=1.3, tag="ritual"))
            else:
                state = "window" if item == "window" else item
                steps.append(act(state, 0.9 if item != "sit" else 1.2, tag="ritual"))
        return steps

    def day_tick(self):
        d = self.data
        lt = time.localtime(self.mind.world_time)
        day = lt.tm_year * 400 + lt.tm_yday
        if d["day"] == day:
            return
        if d["day"]:
            for ctx in list(d["known"]):
                k = d["known"][ctx]
                k["strength"] = round(k["strength"] - 0.06, 3)
                if k["strength"] <= 0.1:
                    d["known"].pop(ctx)
                    self.mind.log("ritual", f"seems to have dropped its {CONTEXTS[ctx]} ritual.", "moon")
        d["day"] = day
