"""Hidden personality traits (0..1) that drift slowly with experience.

The player never sees the numbers. Traits only show through behaviour,
plus one vague "seems ..." hint on the status screen.
"""

TRAITS = ("playfulness", "sociability", "curiosity", "independence", "stubbornness")

HINTS = {
    "playfulness": "bouncy",
    "sociability": "cuddly",
    "curiosity": "curious",
    "independence": "free-spirited",
    "stubbornness": "headstrong",
}


def _clamp(v, lo=0.02, hi=0.98):
    return max(lo, min(hi, v))


class Personality:
    def __init__(self, traits=None):
        self.traits = {t: 0.5 for t in TRAITS}
        if traits:
            for key, value in traits.items():
                if key in self.traits:
                    self.traits[key] = _clamp(float(value))

    @classmethod
    def from_tendencies(cls, tendencies, rng):
        """Inherited tendencies plus a little individual randomness."""
        return cls({t: tendencies.get(t, 0.5) + rng.uniform(-0.12, 0.12) for t in TRAITS})

    def __getitem__(self, key):
        return self.traits[key]

    def nudge(self, trait, amount):
        if trait in self.traits:
            self.traits[trait] = _clamp(self.traits[trait] + amount)

    def hint(self):
        ranked = sorted(self.traits.items(), key=lambda kv: kv[1], reverse=True)
        words = [HINTS[k] for k, v in ranked[:2] if v >= 0.58]
        return " & ".join(words) if words else "easygoing"

    def to_dict(self):
        return dict(self.traits)

    @classmethod
    def from_dict(cls, data):
        return cls(data)


# ---------------------------------------------------------------- quirks
# Each pet gets three hidden quirks: one from birth, one that shows up as a
# child and one as a teen. They are never displayed - only behaviour shows them.
QUIRKS = ("observer", "troublemaker", "clingy", "independent",
          "sleepyhead", "showoff", "shy", "explorer")
EXCLUSIVE = (("clingy", "independent"), ("shy", "showoff"))
UNLOCK = ("baby", "child", "teen")
STAGE_ORDER = ("egg", "baby", "child", "teen", "adult", "elder")


def quirk_weights(p):
    return {
        "observer": p["curiosity"] * 0.6 + (1 - p["playfulness"]) * 0.4,
        "troublemaker": p["stubbornness"] * 0.6 + p["playfulness"] * 0.4,
        "clingy": p["sociability"],
        "independent": p["independence"],
        "sleepyhead": 0.3 + (1 - p["playfulness"]) * 0.3,
        "showoff": p["playfulness"] * 0.6 + p["sociability"] * 0.4,
        "shy": (1 - p["sociability"]) * 0.8,
        "explorer": p["curiosity"],
    }


def assign_quirks(personality, rng, count=3):
    pool = {q: max(0.05, w) for q, w in quirk_weights(personality).items()}
    chosen = []
    while len(chosen) < count and pool:
        total = sum(v * v for v in pool.values())
        r = rng.uniform(0, total)
        pick = next(iter(pool))
        for q, v in pool.items():
            r -= v * v
            if r <= 0:
                pick = q
                break
        chosen.append(pick)
        pool.pop(pick)
        for a, b in EXCLUSIVE:
            if pick == a:
                pool.pop(b, None)
            elif pick == b:
                pool.pop(a, None)
    return [{"id": q, "from": UNLOCK[i]} for i, q in enumerate(chosen)]


def has_quirk(c, quirk):
    stage = STAGE_ORDER.index(c.stage) if c.stage in STAGE_ORDER else 0
    for item in getattr(c, "quirks", []) or []:
        if item.get("id") == quirk and stage >= STAGE_ORDER.index(item.get("from", "baby")):
            return True
    return False
