"""Mirrors, identity and personal history - rare, optional experiments.

The mirror (Settings -> Room extras). A standing mirror reflects whatever the
creature is doing, frame by frame. How the creature treats it develops over
sessions, at a pace set by curiosity and capacity:
  0  greets the "other creature" in the glass
  1  tries to communicate with it
  2  tests it - moving and watching, moving and watching
  3  makes unusual movements and faces at it
  4  uses it to look at markings on its own body
None of this is presented as proof of self-awareness; the diary only
describes what it did.

The memory frame. The picture on the wall shows the creature's first form
(from its real evolution history). Now and then it stands under it, looks
up, then looks down at itself.

The caretaker experiment (PROTOTYPE). A rare, curious adult may build a tiny
figure out of its collected trinkets. The figure has its own little learning
table: when the creature demonstrates a movement next to it, the figure may
copy it, a little more reliably each time. If it copies successfully the
creature is delighted. Optional and rare; never a second pet to care for.
"""
from .behaviour import act, move
from .config import X_MAX, X_MIN

MIRROR_STAND = 92
STAGE_TEXT = {
    0: "met a creature in the mirror and tried to say hello to it.",
    1: "chirped and hopped at its reflection, as if trying to talk to it.",
    2: "kept moving, then stopping to watch the reflection - again and again, as if testing it.",
    3: "made strange faces and movements at its reflection.",
    4: "stood at the mirror and examined the markings on its own body.",
}
STAGE_CAP = {"baby": 1, "child": 2, "teen": 3, "adult": 4, "elder": 4}
TEACHABLE = ("spin", "jump", "bob")


def ensure(c):
    if not isinstance(getattr(c, "mirror", None), dict):
        c.mirror = {}
    for k, v in (("sessions", 0), ("stage", 0), ("logged", [])):
        c.mirror.setdefault(k, v)
    return c.mirror


class Existential:
    def __init__(self, mind):
        self.mind = mind

    # ---- mirror ----------------------------------------------------------------------------
    @property
    def mr(self):
        return ensure(self.mind.c)

    def mirror_plan(self):
        m = self.mind
        c = m.c
        mr = self.mr
        stage = mr["stage"]
        has_marks = (c.genome.get("marking", "none") != "none" or c.genome.get("mutation") in
                     ("chimera", "shiny", "glitch") or m.c.species in ("frolicat", "thornback", "grumblin"))
        if stage >= 4 and not has_marks:
            stage = 3
        go = [move(MIRROR_STAND, z=0.0, speed=1.2, tag="mirror"), act("notice", 0.8, face=1, tag="mirror")]
        body = {
            0: [act("wave", 1.4, face=1, tag="mirror"), act("chirp", 0.8, fx="snd:chirp1", tag="mirror"),
                act("confused", 1.0, tag="mirror")],
            1: [act("chirp", 0.8, fx="snd:chirp2", tag="mirror"), act("jump", 0.7, tag="mirror"),
                act("watch", 1.5, face=1, tag="mirror")],
            2: [act("bob", 1.0, tag="mirror"), act("watch", 1.0, face=1, tag="mirror"),
                act("jump", 0.7, tag="mirror"), act("watch", 1.0, face=1, tag="mirror"),
                act("spin", 1.0, tag="mirror"), act("watch", 1.2, face=1, tag="mirror")],
            3: [act("silly", 2.0, tag="mirror"), act("tilt", 1.2, tag="mirror"), act("dance", 1.6, tag="mirror")],
            4: [act("watch", 1.4, face=1, tag="mirror"), act("inspect", 1.6, tag="mirror"),
                act("watch", 1.0, face=1, tag="mirror"), act("proud", 1.0, tag="mirror")],
        }[stage]
        return go + body + [act("idle", 0.3, fx=f"mirror:{stage}", tag="mirror")]

    def mirror_done(self, stage):
        m = self.mind
        c = m.c
        mr = self.mr
        mr["sessions"] += 1
        if stage not in mr["logged"]:
            mr["logged"].append(stage)
            m.log("mirror", STAGE_TEXT[stage], "star", important=stage >= 2)
            m.episodes.add("discovery", f"mirror:{stage}", "the mirror", 0.6 + 0.08 * stage)
        if stage == 4:
            m.uncanny.record("mirror_mastery", "examined its own markings in the mirror")
        per_stage = 2 if c.personality["curiosity"] > 0.6 else 3
        cap = min(STAGE_CAP.get(c.stage, 2), 4)
        new = min(cap, mr["sessions"] // per_stage)
        if new > mr["stage"]:
            mr["stage"] = new
            m.trace([f"{mr['sessions']} mirror sessions", f"Curiosity {c.personality['curiosity']:.2f}",
                     f"Mirror understanding stage {new}"], "mirror")

    # ---- memory frame ----------------------------------------------------------------------
    def reminisce_plan(self):
        m = self.mind
        if len(m.c.forms) < 2:
            return None
        return [move(26, z=0.0, speed=1.0, tag="memory"), act("ponder", 2.2, face=-1, gaze="ul", tag="memory"),
                act("inspect", 1.5, tag="memory"), act("look", 0.8, fx="reminisce", tag="memory")]

    def reminisced(self):
        m = self.mind
        first = m.species_name(m.c.forms[0])
        if m.first("reminisce"):
            m.log("memory", f"stood under the picture of itself as a little {first}, looked up at it for a "
                  "long time, then looked down at itself.", "heart", important=True)
        m.trace(["Picture on the wall shows its first form", "Looked at it, then at itself"], "memory")
        ep = m.episodes.recall()
        if ep and ep["kind"] in ("game", "object", "ritual"):
            m.trace([f"Recalled: {ep['text']}"], "memory")

    # ---- caretaker experiment (prototype) ---------------------------------------------------
    def can_build(self):
        m = self.mind
        c = m.c
        return (m.world.figure is None and c.stage in ("adult", "elder") and len(m.world.pile["items"]) >= 4
                and (c.personality["curiosity"] > 0.6 or m.mut("inventor") or m.mut("collector")
                     or len(m.skills.s["known"]) >= 1))

    def build_plan(self):
        m = self.mind
        return [move(m.world.pile["x"], speed=1.1, tag="caretaker"),
                act("inspect", 2.5, fx="figure:build", tag="caretaker"), act("proud", 1.2, tag="caretaker")]

    def build(self):
        m = self.mind
        w = m.world
        parts = [w.pile["items"].pop() for _ in range(min(3, len(w.pile["items"])))]
        w.figure = {"x": max(X_MIN, min(X_MAX, w.pile["x"] + 14)), "skills": {g: 0.05 for g in TEACHABLE},
                    "built_by": m.c.name, "gen": m.c.generation, "parts": parts, "anim": None, "t": 0.0,
                    "taught": []}
        m.log("caretaker", "built a tiny figure out of its trinkets and sat looking at it.", "star", important=True)
        m.episodes.add("discovery", "figure", "built a little figure", 0.8)
        m.trace(["Curious adult with a collection", "Assembled trinkets into a figure"], "caretaker")

    def teach_plan(self):
        m = self.mind
        f = m.world.figure
        if not f:
            return None
        g = min(TEACHABLE, key=lambda k: f["skills"].get(k, 0)) if m.rng.random() < 0.6 \
            else m.rng.choice(TEACHABLE)
        x = max(X_MIN, min(X_MAX, f["x"] - 12))
        return [move(x, speed=1.1, tag="caretaker"), act("watch", 1.0, face=1, tag="caretaker"),
                act(g, 1.0, tag="caretaker"), act("watch", 1.6, face=1, fx=f"figure:try:{g}", tag="caretaker")]

    def figure_try(self, g):
        m = self.mind
        f = m.world.figure
        if not f:
            return
        p = f["skills"].get(g, 0.05)
        ok = m.rng.random() < p
        f["anim"], f["t"] = (g if ok else "wobble"), 0.0
        if ok:
            f["skills"][g] = round(min(0.95, p + 0.1), 3)
            m.beh.plan[0:0] = [act("happy", 1.2, tag="caretaker")]
            if g not in f["taught"]:
                f["taught"].append(g)
                if m.uncanny.allow("teach_entity") or len(f["taught"]) == 1:
                    m.uncanny.record("teach_entity", f"taught its figure to {g}")
                m.log("caretaker", f"showed its little figure how to {g} - and the figure copied it.", "star",
                      important=True)
                m.episodes.add("skill", f"taught:{g}", f"taught the figure to {g}", 0.8)
        else:
            f["skills"][g] = round(min(0.95, p + 0.15), 3)      # learning by demonstration
            m.beh.plan[0:0] = [act("tilt", 0.8, tag="caretaker"), act(g, 1.0, tag="caretaker")]
        m.trace([f"Demonstrated '{g}' to the figure", f"Figure's chance was {p:.0%}",
                 "Figure copied it" if ok else "Figure didn't copy - tried again"], "caretaker")

    def figure_tick(self, dt):
        f = self.mind.world.figure
        if f and f.get("anim"):
            f["t"] += dt
            if f["t"] > 1.0:
                f["anim"] = None
