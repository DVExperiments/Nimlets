"""Learning: beliefs about the world and an emergent shared language.

Beliefs
    A handful of learned associations, each a value in -1..1 with a count of
    experiences. They are updated by things that happen (being petted, the
    bed restoring energy, the bowl filling after it taps it...) and they bend
    behaviour: a pet that believes the cursor is overwhelming avoids it; one
    that is unsure whether tapping the bowl works will *test* it.

Signals now live in language.py (each pet's private, evolving language) and
reciprocity.py (how it uses them with you).

Nothing here is a language model - just small numbers and counters.
"""

BELIEFS = {
    # name: (positive realisation, negative realisation)
    "cursor_food": ("seems to expect food when your cursor goes near the Feed button", None),
    "touch": ("seems to have decided that being touched is nice",
              "seems to find being clicked overwhelming"),
    "bed_safe": ("seems to have learned that its bed is a safe place to rest", None),
    "toy_fun": ("seems convinced the ball is the best thing in the room",
                "seems to have lost interest in the ball"),
    "objects_respond": ("seems to understand that things move when you click them", None),
    "room_edge": ("seems to have realised its room has edges", None),
    "edge_passable": ("seems to believe the edge of its world isn't always solid", None),
    "bowl_summons": ("seems to think tapping the bowl makes food appear",
                     "seems to have worked out that tapping the bowl does nothing"),
    "time_control": ("seems to connect the speed control with its world suddenly rushing by", None),
    "pause_button": ("seems to have noticed that its world stops around the pause button", None),
}

# ---------------------------------------------------------------- beliefs
def new_beliefs():
    return {k: {"v": 0.0, "n": 0, "a": None} for k in BELIEFS}


def belief(c, name):
    return c.beliefs.get(name, {}).get("v", 0.0)


def update_belief(c, name, outcome, rate=0.15):
    """outcome in -1..1. Returns a realisation sentence the first time a
    belief becomes firm (for the diary), else None."""
    b = c.beliefs.setdefault(name, {"v": 0.0, "n": 0, "a": None})
    b["v"] = max(-1.0, min(1.0, b["v"] + rate * (outcome - b["v"])))
    b["n"] += 1
    pos, neg = BELIEFS[name]
    if b["n"] >= 3 and b["v"] > 0.45 and b["a"] != "pos":
        b["a"] = "pos"
        return pos
    if neg and b["n"] >= 3 and b["v"] < -0.35 and b["a"] != "neg":
        b["a"] = "neg"
        return neg
    return None


def phrasebook(c):
    """Signals you share with this pet (from its private language)."""
    from . import language
    bond = getattr(c, "bond", None) or {}
    return language.phrasebook(bond.get("lang", {})) if bond else []
