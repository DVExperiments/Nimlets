"""Rare, unusual behaviour: eligibility, selection and cooldowns.

Events are grouped in three levels. Each has prerequisites drawn from the
creature's real history (stage of its model of you, memories, skills,
experiments, mutations...). Many events are *produced* by other systems
(rituals, world model, skills, mirror) and only recorded here; a few
"spontaneous" ones are scheduled here when their prerequisites are met.

Rules: level and per-event cooldowns, strict prerequisites, never while the
pet needs care or is busy, and nothing frightening - just behaviour.
Everything can be switched off in Settings ("Experimental behaviours").
"""
from .behaviour import act, move
from .config import X_MAX, X_MIN

LEVEL_COOLDOWN = {1: 90.0, 2: 600.0, 3: 2400.0}
EVENT_COOLDOWN = {1: 300.0, 2: 1800.0, 3: 7200.0}
LEVEL_NAMES = {1: "subtle", 2: "uncanny", 3: "existential"}

EVENTS = {
    # id: (level, spontaneous, description)
    "eye_contact": (1, True, "Extended eye contact"),
    "unexpected_look": (1, True, "Looked toward the cursor unexpectedly"),
    "forgotten_gesture": (1, True, "Repeated a gesture you stopped using"),
    "strange_ritual": (1, False, "Developed a personal ritual"),
    "env_investigate": (1, False, "Investigated a change in the room"),
    "draw_cursor": (2, True, "Drew a picture of the cursor"),
    "test_signal": (2, False, "Deliberately tested a signal"),
    "ui_experiment": (2, True, "Experimented with the speed/pause controls"),
    "hide_object": (2, True, "Hid an object from view"),
    "novel_sequence": (2, False, "Learned a new multi-step interaction"),
    "restore_arrangement": (2, False, "Restored a previous room arrangement"),
    "repeat_old_experience": (2, True, "Repeated an old shared experience"),
    "app_boundary": (3, True, "Went looking for the edge of the application"),
    "multi_step_skill": (3, False, "Used one object to move another"),
    "teach_entity": (3, False, "Taught another entity a behaviour"),
    "mirror_mastery": (3, False, "Examined itself in the mirror"),
    "ancestral_creation": (3, True, "Built on an artifact from a past generation"),
    "build_figure": (3, True, "Built a little figure"),
}


def ensure(c):
    if not isinstance(getattr(c, "uncanny", None), dict) or "done" not in c.uncanny:
        c.uncanny = {"done": {}, "last": {}, "level_last": {}, "history": []}
    return c.uncanny


class Uncanny:
    def __init__(self, mind):
        self.mind = mind
        self.tick_t = 0.0
        self.clock = 0.0           # pace-scaled clock for cooldowns

    @property
    def u(self):
        return ensure(self.mind.c)

    # ---- prerequisites ------------------------------------------------------------------
    def prereq(self, eid):
        m = self.mind
        c = m.c
        if c is None or c.stage in ("egg",):
            return False
        stage = m.observer.stage()
        fr = c.frontier
        grown = c.stage in ("teen", "adult", "elder")
        if eid == "eye_contact":
            return stage >= 2 and c.memory.attachment >= 40 and m.cursor is not None
        if eid == "unexpected_look":
            return m.cursor is not None
        if eid == "forgotten_gesture":
            return any(e["kind"] == "gesture" for e in m.episodes.forgotten())
        if eid == "draw_cursor":
            return stage >= 4 and c.stage != "baby" and m.recip.capacity() >= 0.7
        if eid == "ui_experiment":
            o = m.observer.o
            return fr["escapes"] >= 1 and (o["speed_seen"] >= 2 or o["pause_seen"] >= 2)
        if eid == "hide_object":
            p = c.personality
            return bool(m.world.pile["items"]) and grown and (
                p["independence"] > 0.55 or m.shyness() > 0.45 or m.mut("trickster") or m.mut("collector"))
        if eid == "repeat_old_experience":
            return any(e["kind"] in ("game", "collaboration") for e in m.episodes.forgotten(1.5))
        if eid == "app_boundary":
            return fr["escapes"] >= 2 and grown
        if eid == "ancestral_creation":
            return grown and any(g < c.generation for g in m.world.mural_generations()) \
                and "studied_mural" in c.firsts
        if eid == "build_figure":
            return m.existential.can_build()
        return True

    def allow(self, eid):
        m = self.mind
        if not m.experimental() or eid not in EVENTS:
            return False
        level = EVENTS[eid][0]
        u = self.u
        if self.clock - u["level_last"].get(str(level), -1e9) < LEVEL_COOLDOWN[level]:
            return False
        if self.clock - u["last"].get(eid, -1e9) < EVENT_COOLDOWN[level]:
            return False
        return self.prereq(eid)

    def record(self, eid, why=""):
        if eid not in EVENTS or self.mind.c is None:
            return
        level = EVENTS[eid][0]
        u = self.u
        u["done"][eid] = u["done"].get(eid, 0) + 1
        u["last"][eid] = self.clock
        u["level_last"][str(level)] = self.clock
        u["history"].append([round(self.mind.world_time), eid, level, why])
        del u["history"][:-60]
        self.mind.trace([f"Rare event, level {level} ({LEVEL_NAMES[level]}): {EVENTS[eid][2]}"]
                        + ([why] if why else []), "uncanny")

    # ---- spontaneous events --------------------------------------------------------------
    def tick(self, dt):
        m = self.mind
        self.clock += dt * m.pace
        self.tick_t += dt
        if self.tick_t < 2.0:
            return
        self.tick_t = 0.0
        c = m.c
        if (c is None or c.stage == "egg" or c.asleep or c.sick or c.hunger < 30 or c.attention
                or m.recip.busy() or not m.experimental() or m.beh.tag not in (None, "activity", "watch")):
            return
        if m.rng.random() > 0.08:
            return
        p = c.personality
        weights = {}
        for eid, (level, spont, _) in EVENTS.items():
            if not spont or not self.allow(eid):
                continue
            w = {1: 1.0, 2: 0.35, 3: 0.12}[level]
            if eid in ("draw_cursor", "ui_experiment", "app_boundary"):
                w *= 0.6 + p["curiosity"] + (0.8 if m.mut("wanderer") else 0)
            if eid == "eye_contact" and m.q("observer"):
                w *= 2
            weights[eid] = w
        if not weights:
            return
        total = sum(weights.values())
        r = m.rng.uniform(0, total)
        for eid, w in weights.items():
            r -= w
            if r <= 0:
                self.run(eid)
                return

    def run(self, eid):
        m = self.mind
        beh = m.beh
        if eid == "eye_contact":
            beh.interject([move(max(X_MIN, min(X_MAX, m.cursor[0])), z=1.0, speed=1.0, tag="watch"),
                           act("watch", 4.0, gaze="", tag="watch")])
            m.log("observe", "held your gaze for a long, still moment.", "ghost")
        elif eid == "unexpected_look":
            beh.interject([act("watch", 1.5, tag="watch")])
        elif eid == "forgotten_gesture":
            ep = next(e for e in m.episodes.forgotten() if e["kind"] == "gesture")
            g = ep["data"].get("gesture")
            if not g:
                return
            days = (m.world_time - ep["last"]) / 86400
            m.recip.anticipating = {"ctx": "return", "expect": g, "t": 0.0}
            from .reciprocity import CURSOR_TO_PET, CURSOR_WORDS
            beh.interject([act("notice", 0.6, gaze="", tag="game")]
                          + m.recip.gesture_steps([CURSOR_TO_PET[g]], tag="game")
                          + [act("wait", 4.0, gaze="", tag="game")])
            ep["last"] = m.world_time
            m.log("memory", f"made the movement that answers {CURSOR_WORDS[g]} - something you haven't "
                  f"done for {max(1, int(days))} days.", "ghost", important=True)
        elif eid == "draw_cursor":
            beh.interject(m.drawing_plan("cursor"))
        elif eid == "ui_experiment":
            m.escape_request = {"roam": False, "variant": "controls"}
        elif eid == "hide_object":
            plan = m.skills.stash_plan()
            if not plan:
                return
            beh.interject(plan)
        elif eid == "repeat_old_experience":
            ep = next(e for e in m.episodes.forgotten(1.5) if e["kind"] in ("game", "collaboration"))
            if ep["kind"] == "game" and ep["data"].get("game") in ("lead", "catch", "echo", "path"):
                m.recip.game = None
                getattr(m.recip, "_start_" + ep["data"]["game"])()
            else:
                beh.interject(m.drawing_plan("collab"))
            ep["last"] = m.world_time
            m.log("memory", f"started something you used to do together: {ep['text']}.", "heart", important=True)
        elif eid == "app_boundary":
            m.escape_request = {"roam": False, "variant": "edge"}
        elif eid == "ancestral_creation":
            beh.interject(m.drawing_plan("ancestral"))
        elif eid == "build_figure":
            beh.interject(m.existential.build_plan())
        self.record(eid, "prerequisites met: " + self.explain(eid))

    def explain(self, eid):
        m = self.mind
        c = m.c
        return (f"stage {m.observer.stage()}, curiosity {c.personality['curiosity']:.2f}, "
                f"attachment {c.memory.attachment:.0f}, escapes {c.frontier['escapes']}")

    def summary(self):
        u = self.u
        rows = [f"{EVENTS[e][2]} (L{EVENTS[e][0]}): x{n}" for e, n in u["done"].items() if e in EVENTS]
        eligible = [EVENTS[e][2] for e in EVENTS if EVENTS[e][1] and self.prereq(e)]
        return rows or ["none yet"], eligible or ["none"]
