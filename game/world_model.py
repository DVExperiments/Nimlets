"""Spatial memory: where the creature *thinks* things are.

The creature does not magically know the position of every object. It keeps
remembered positions, notices changes only if it sees them happen or comes
across them later, searches the old spot when something has moved, and then
either restores its preferred arrangement (dragging its bed back) or slowly
gets used to the new layout.
"""
from .behaviour import act, move
from .config import X_MAX, X_MIN

TRACKED = ("bed", "pile", "stash", "figure", "mirror")


def ensure(c):
    if not isinstance(getattr(c, "spatial", None), dict) or "expect" not in c.spatial:
        c.spatial = {"expect": {}, "pref": {}, "pref_str": {}, "adapt": {}, "changes": 0}
    for k in ("expect", "pref", "pref_str", "adapt"):
        c.spatial.setdefault(k, {})
    c.spatial.setdefault("changes", 0)
    return c.spatial


class WorldModel:
    def __init__(self, mind):
        self.mind = mind
        self.survey_t = 0.0

    @property
    def s(self):
        return ensure(self.mind.c)

    def actual(self, obj):
        w = self.mind.world
        if obj == "bed":
            return w.bed_x
        if obj == "pile":
            return w.pile["x"] if w.pile["items"] else None
        if obj == "stash":
            return w.stash["x"] if w.stash["items"] else None
        if obj == "figure":
            return w.figure["x"] if w.figure else None
        if obj == "mirror":
            return w.mirror_x if self.mind.mirror_on else None
        return None

    def learn_room(self):
        """A newly hatched creature learns the room as it is."""
        for obj in TRACKED:
            x = self.actual(obj)
            if x is not None:
                self.s["expect"][obj] = x

    def expect(self, obj):
        x = self.s["expect"].get(obj)
        return x if x is not None else self.actual(obj)

    def saw(self, obj):
        x = self.actual(obj)
        if x is not None:
            self.s["expect"][obj] = x

    def chose(self, obj, x):
        """It placed this object itself: a preference."""
        self.s["expect"][obj] = x
        self.s["pref"][obj] = x
        self.s["pref_str"][obj] = 0.6

    def rested(self):
        """Sleeping in its bed reinforces liking where the bed is."""
        bx = self.actual("bed")
        pref = self.s["pref"].get("bed")
        if pref is None or abs(pref - bx) < 8:
            self.s["pref"]["bed"] = bx
            self.s["pref_str"]["bed"] = round(min(1.0, self.s["pref_str"].get("bed", 0.3) + 0.05), 3)

    def mismatched(self):
        out = []
        for obj in TRACKED:
            a, e = self.actual(obj), self.s["expect"].get(obj)
            if a is not None and e is not None and abs(a - e) > 10:
                out.append(obj)
        return out

    # ---- events ------------------------------------------------------------------------
    def player_moved(self, obj, old, new):
        """You dragged something. Did it see?"""
        m = self.mind
        c = m.c
        if c is None or c.stage == "egg":
            return
        self.s["changes"] += 1
        m.episodes.add("change", f"moved:{obj}", f"you moved its {obj}", 0.5, {"from": old, "to": new})
        seen = (not c.asleep and m.watched and m.rng.random() < m.recip.attentive() + 0.1)
        if not seen:
            m.trace([f"You moved the {obj} ({old:.0f} -> {new:.0f})", "It didn't see",
                     "Its memory still says the old place"], "world")
            return
        self.s["expect"][obj] = new
        m.beh.interject([act("notice", 0.8, gaze="", tag="reaction"),
                         move(max(X_MIN, min(X_MAX, new + 12)), speed=1.4, tag="world"),
                         act("inspect", 1.4, face=-1, tag="world")])
        m.trace([f"You moved the {obj}", "It watched you do it", "Went to inspect the new spot"], "world")
        self._react_to_layout(obj, new)

    def on_arrive(self, obj, x):
        """It walked to where it expected `obj`. Returns the real position if it was wrong."""
        a = self.actual(obj)
        e = self.s["expect"].get(obj)
        if a is None or e is None or abs(a - e) <= 10:
            return None
        self.s["expect"][obj] = a
        m = self.mind
        m.log("change", f"went to where its {obj} used to be, looked around, then found it somewhere else.",
              "ghost")
        m.trace([f"Expected the {obj} at {e:.0f}", "Found nothing there", f"Searched and found it at {a:.0f}"],
                "world")
        m.uncanny.record("env_investigate", f"searched for the moved {obj}")
        return a

    def survey(self, dt):
        """Every few seconds, it may notice that something isn't where it remembers."""
        m = self.mind
        self.survey_t += dt
        if self.survey_t < 3.0:
            return
        self.survey_t = 0.0
        if m.c.asleep or m.recip.busy() or m.beh.tag not in (None, "activity", "watch"):
            return
        stale = self.mismatched()
        if not stale or m.rng.random() > 0.12 + 0.2 * m.c.personality["curiosity"]:
            return
        obj = stale[0]
        old, new = self.s["expect"][obj], self.actual(obj)
        steps = [move(max(X_MIN, min(X_MAX, old)), speed=1.2, tag="world"), act("look", 1.4, tag="world"),
                 act("tilt", 1.0, tag="world"), move(max(X_MIN, min(X_MAX, new + 12)), speed=1.2, tag="world"),
                 act("inspect", 1.4, face=-1, fx=f"spatial:{obj}", tag="world")]
        m.beh.interject(steps)
        m.trace([f"Remembered the {obj} at {old:.0f}", "Noticed it isn't there", "Searching the old spot"],
                "world")

    def found(self, obj):
        """fx callback at the end of a search."""
        m = self.mind
        new = self.actual(obj)
        if new is None:
            return
        self.s["expect"][obj] = new
        m.log("change", f"searched for its {obj} where it used to be, then found it in its new place.", "ghost")
        m.uncanny.record("env_investigate", f"found the moved {obj}")
        self._react_to_layout(obj, new)

    def _react_to_layout(self, obj, new):
        """Restore the old arrangement, or start getting used to the new one."""
        m = self.mind
        if obj != "bed":
            return
        pref = self.s["pref"].get("bed")
        strength = self.s["pref_str"].get("bed", 0.0)
        if pref is None or abs(pref - new) < 20:
            return
        stubborn = m.c.personality["stubbornness"]
        if strength * (0.6 + stubborn) > 0.55 and m.uncanny.allow("restore_arrangement"):
            m.beh.plan += m.drag_bed_plan(pref)
            m.uncanny.record("restore_arrangement", "dragged its bed back to where it likes it")
            m.log("change", "dragged its bed back to where it likes it.", "moon", important=True)
            m.trace([f"Bed moved away from its preferred spot ({pref:.0f})",
                     f"Preference strength {strength:.2f}, stubbornness {stubborn:.2f}", "Restored it"], "world")
            return
        self.s["adapt"]["bed"] = self.s["adapt"].get("bed", 0) + 1
        self.s["pref_str"]["bed"] = round(max(0.0, strength - 0.2), 3)
        if self.s["adapt"]["bed"] >= 3:
            self.s["pref"]["bed"] = new
            self.s["adapt"]["bed"] = 0
            m.log("change", "seems to have got used to its bed's new spot.", "moon")
            m.trace(["Bed moved several times", "Accepted the new layout"], "world")

    def summary(self):
        rows = []
        for obj in TRACKED:
            a, e = self.actual(obj), self.s["expect"].get(obj)
            if a is None and e is None:
                continue
            pref = self.s["pref"].get(obj)
            rows.append(f"{obj}: thinks {e:.0f}" if e is not None else f"{obj}: unknown")
            rows[-1] += f", really {a:.0f}" if a is not None else ", gone"
            if pref is not None:
                rows[-1] += f", prefers {pref:.0f} ({self.s['pref_str'].get(obj, 0):.2f})"
        return rows
