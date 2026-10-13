"""A private, evolving language - one per creature.

Each creature is born with a small *repertoire* of candidate signals for
each thing it can want (food, play, attention, drawing together). A signal
is one or two primitives - a sound and/or a gesture - such as
"two chirps + tapping the bowl" or "a spin + pushing the ball".

The creature keeps a tiny model of how *you* respond to each signal:
attempts, a success score and how often it was misunderstood. When it wants
something it compares its options (estimated success, ambiguity, what kind
of signals you tend to answer), sometimes explores, and updates its
expectations from what you do. Signals that work become conventions; ones
that keep causing confusion are dropped.

Language levels (developmental, driven by experience - not unlocked by age):
  1 Instinctive    looks at what it wants, makes basic sounds
  2 Associative    has noticed that some signals work better than others
  3 Conventional   has at least one reliable signal of its own
  4 Combinatorial  combines its attention call with a gesture that names
                   the thing it wants - a tiny compositional language
"""

SOUNDS = ("chirp1", "chirp2", "trill", "coo")
GENERIC = ("spin", "hop", "pause", "wiggle", "front")
INTENTS = {
    "food": {"obj": "bowl", "name": "food"},
    "play": {"obj": "ball", "name": "to play"},
    "attention": {"obj": "you", "name": "attention"},
    "draw": {"obj": "wall", "name": "to draw with you"},
}
OBJ_GESTURES = {"bowl": ("look", "push", "tap", "point"), "ball": ("look", "push", "tap", "point"),
                "you": ("approach", "hop", "look"), "wall": ("look", "tap", "point")}
OBJ_NAMES = {"bowl": "the bowl", "ball": "the ball", "you": "you", "wall": "the wall"}
NAMES = {
    "chirp1": "one chirp", "chirp2": "two chirps", "trill": "a trill", "coo": "a soft coo",
    "look": "a look at {o}", "spin": "a spin", "push": "pushing {o}", "tap": "tapping {o}",
    "hop": "a hop", "approach": "coming toward you", "pause": "a long pause", "wiggle": "a wiggle",
    "front": "coming right up to the screen", "point": "pointing at {o}",
}
CONVENTION_EST = 0.64
CONVENTION_N = 4


def describe(sig, intent):
    obj = INTENTS[intent]["obj"]
    return " + ".join(NAMES[p].format(o=OBJ_NAMES[obj]) for p in sig.split("+"))


def is_vocal(sig):
    return any(p in SOUNDS for p in sig.split("+"))


def make_repertoire(rng, style):
    rep = {}
    for intent, info in INTENTS.items():
        og = OBJ_GESTURES[info["obj"]]
        options = set()
        tries = 0
        while len(options) < 5 and tries < 60:
            tries += 1
            kind = rng.random()
            if kind < 0.25:
                sig = rng.choice(SOUNDS)
            elif kind < 0.45:
                sig = rng.choice(og)
            elif kind < 0.75:
                sig = f"{rng.choice(SOUNDS)}+{rng.choice(og)}"
            else:
                sig = f"{rng.choice(GENERIC)}+{rng.choice(og)}"
            if style == "vocal" and not is_vocal(sig) and rng.random() < 0.4:
                continue
            if style == "gesture" and is_vocal(sig) and "+" not in sig and rng.random() < 0.5:
                continue
            options.add(sig)
        rep[intent] = sorted(options)
    return rep


def new_language(rng, personality):
    style = "vocal" if rng.random() < 0.3 + personality["sociability"] * 0.4 else "gesture"
    rep = make_repertoire(rng, style)
    stats = {i: {s: {"n": 0, "s": 0.0, "m": 0} for s in sigs} for i, sigs in rep.items()}
    return {"style": style, "repertoire": rep, "stats": stats, "conventions": {}, "history": {},
            "last": None}


def _stat(lang, intent, sig):
    return lang["stats"].setdefault(intent, {}).setdefault(sig, {"n": 0, "s": 0.0, "m": 0})


def estimate(stat):
    return (stat["s"] + 1.0) / (stat["n"] + 2.0)


def ambiguity(stat):
    return stat["m"] / (stat["n"] + 1.0)


def level(lang, capacity=1.0):
    conv = len(lang["conventions"])
    total = sum(st["n"] for t in lang["stats"].values() for st in t.values())
    if conv >= 2 and capacity >= 0.9:
        return 4
    if conv >= 1:
        return 3
    if total >= 4:
        return 2
    return 1


def combo_for(lang, intent):
    """Level 4: its attention call + a gesture naming the thing it wants."""
    att = lang["conventions"].get("attention")
    if not att or intent == "attention":
        return None
    sound = next((p for p in att.split("+") if p in SOUNDS), att.split("+")[0])
    gesture = {"bowl": "tap", "ball": "push", "wall": "tap"}.get(INTENTS[intent]["obj"], "look")
    return f"{sound}+{gesture}"


def choose(lang, intent, rng, explore, player, capacity):
    """Pick a signal. Returns (signal, reason) - the reason is shown in the Observation Lab."""
    candidates = list(lang["repertoire"].get(intent, []))
    combo = combo_for(lang, intent) if level(lang, capacity) >= 4 else None
    if combo and combo not in candidates:
        candidates.append(combo)
        lang["repertoire"][intent].append(combo)
        _stat(lang, intent, combo)
    conv = lang["conventions"].get(intent)
    if conv and rng.random() > explore:
        return conv, f"used its convention for {intent} ({int(estimate(_stat(lang, intent, conv)) * 100)}% expected)"
    if rng.random() < explore:
        sig = rng.choice(candidates)
        return sig, f"explored: tried {describe(sig, intent)} to see what happens"
    bias = (player.get("sound", 0.0) - player.get("gesture", 0.0)) * 0.15
    best, best_score = None, -9.0
    for sig in candidates:
        st = _stat(lang, intent, sig)
        score = estimate(st) - 0.3 * ambiguity(st) + (bias if is_vocal(sig) else -bias)
        score += rng.uniform(0, 0.08)              # a little noise: it isn't a perfect optimiser
        if score > best_score:
            best, best_score = sig, score
    return best, f"chose its best guess ({int(estimate(_stat(lang, intent, best)) * 100)}% expected)"


def record(lang, intent, sig, outcome, misunderstood=False, capacity=1.0):
    """Update the creature's model of you. outcome 0..1. Returns event tuples."""
    events = []
    st = _stat(lang, intent, sig)
    rate = 0.6 + 0.4 * capacity
    st["n"] += 1
    st["s"] += outcome * rate
    if misunderstood:
        st["m"] += 1
    conv = lang["conventions"]
    est = estimate(st)
    if conv.get(intent) == sig and (est < 0.42 or ambiguity(st) > 0.45):
        conv.pop(intent)
        events.append(("convention_lost", intent, sig))
    elif conv.get(intent) != sig and est >= CONVENTION_EST and st["n"] >= CONVENTION_N and ambiguity(st) < 0.35:
        for other_intent, other_sig in list(conv.items()):
            if other_sig == sig and other_intent != intent:
                conv.pop(other_intent)
                events.append(("meaning_changed", other_intent, intent, sig))
        conv[intent] = sig
        events.append(("convention", intent, sig))
    return events


def decay(lang, factor=0.97):
    """Imperfect memory: unreinforced signals slowly lose reliability."""
    for table in lang["stats"].values():
        for st in table.values():
            st["n"] *= factor
            st["s"] *= factor * 0.99


def phrasebook(lang):
    return [(describe(sig, intent), INTENTS[intent]["name"]) for intent, sig in lang.get("conventions", {}).items()]
