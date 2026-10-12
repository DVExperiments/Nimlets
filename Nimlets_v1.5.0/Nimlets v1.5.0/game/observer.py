"""The Observer: a creature that studies the player.

The creature builds a small statistical model of the cursor - the one thing
in its world that is not like the other objects.

What it learns (all from this game window only):
  * which interface areas the cursor visits ("zones": buttons, toggles, and
    places in the room such as the bowl or the wall),
  * the order the cursor moves between zones (transition counts),
  * which of your actions tend to follow a zone, a pair of zones, or the
    cursor *heading toward* a button (association tables).

From that it predicts your next action. Confident predictions make it act
early - trotting to the bowl as your cursor heads for Feed. Predictions are
scored; misses lower its confidence and it adapts as your habits change
(tables decay daily).

It also chooses to *watch* the cursor deliberately, notices the speed and
pause controls, and moves through seven developmental stages in how it
models you (encounter -> association -> prediction -> experimentation ->
representation -> communication -> collaboration). Stages are milestones
reached through experience; some creatures never reach them all.
"""
import math
import time
from collections import deque

from .behaviour import act, move
from .config import X_MAX, X_MIN

CLOCK_X = 72
STAGE_NAMES = {1: "Encounter", 2: "Association", 3: "Prediction", 4: "Experimentation",
               5: "Representation", 6: "Communication", 7: "Collaboration"}
ACTIONS = ("feed", "play", "clean", "medicine", "discipline", "lights", "status", "records",
           "ball", "pet", "draw", "speed", "pause", "settings")
PRED_WINDOW = 4.0


def new_observer():
    return {"zones": {}, "trans": {}, "assoc": {}, "conf": {}, "hits": 0, "misses": 0,
            "acc": 0.5, "log": [], "stage": 1, "ms": {}, "speed_seen": 0, "pause_seen": 0,
            "rapid": 0.0, "symbols": 0, "studied": 0, "day": 0}


def ensure_observer(c):
    if not getattr(c, "observer", None):
        c.observer = new_observer()
    for k, v in new_observer().items():
        c.observer.setdefault(k, v)
    return c.observer


class Observer:
    def __init__(self, mind):
        self.mind = mind
        self.reset()

    def reset(self):
        self.zone = None
        self.prev_zone = None
        self.heading = None
        self.heading_t = 0.0
        self.context_t = 0.0
        self.prediction = None
        self.acted_on = None
        self.tick_t = 0.0
        self.cd = {"anticipate": 0.0, "watch": 15.0, "time": 0.0, "study": 0.0, "curious": 0.0}
        self.recent_dirs = deque()
        self.still_room = 0.0

    @property
    def o(self):
        return ensure_observer(self.mind.c)

    # ---- learning from what the cursor does ------------------------------------------------
    def _contexts(self):
        keys = []
        if self.zone:
            keys.append(f"z:{self.zone}")
            if self.prev_zone:
                keys.append(f"zz:{self.prev_zone}>{self.zone}")
        if self.heading and self.mind.clock - self.heading_t < 2.5:
            keys.append(f"to:{self.heading}")
        return keys

    def observe(self, dt, zone, heading):
        """Called every frame with the cursor's zone and the button it is heading toward."""
        m = self.mind
        c = m.c
        if c is None or c.stage == "egg":
            return
        o = self.o
        for k in self.cd:
            self.cd[k] = max(0.0, self.cd[k] - dt)
        if zone is not None:
            o["ms"].setdefault("encounter", m.world_time)
        changed = False
        if zone != self.zone and zone is not None:
            o["zones"][zone] = o["zones"].get(zone, 0) + 1
            if self.zone:
                row = o["trans"].setdefault(self.zone, {})
                row[zone] = row.get(zone, 0) + 1
            self.prev_zone, self.zone = self.zone, zone
            changed = True
        if heading and heading != self.heading:
            self.heading, self.heading_t = heading, m.clock
            changed = True
        if changed:
            self._predict()
        if self.prediction and m.clock - self.prediction["t"] > PRED_WINDOW:
            self._resolve(None)
        self.tick_t += dt
        if self.tick_t >= 0.5:                 # the cheap behavioural checks run twice a second
            self.tick_t = 0.0
            self._watch_tick()

    def _predict(self):
        m = self.mind
        o = self.o
        best = None
        for key in self._contexts():
            table = o["assoc"].get(key)
            if not table:
                continue
            total = sum(table.values())
            if total < 3:
                continue
            action = max(table, key=table.get)
            p = (table[action] + 0.2) / (total + 0.2 * len(ACTIONS))
            if best is None or p > best[1]:
                best = (action, p, key, total)
        if best and best[1] >= 0.45:
            action, p, key, n = best
            if self.prediction and self.prediction["action"] == action:
                return
            self.prediction = {"action": action, "p": round(p, 2), "key": key, "n": int(n), "t": m.clock}
            self._maybe_anticipate()

    def on_action(self, action):
        """A player action happened: learn which contexts preceded it, and score predictions."""
        m = self.mind
        if m.c is None or m.c.stage == "egg":
            return
        o = self.o
        for key in self._contexts():
            table = o["assoc"].setdefault(key, {})
            table[action] = table.get(action, 0) + 1
        if len(o["assoc"]) > 160:              # bounded memory: forget the rarest contexts
            weakest = sorted(o["assoc"], key=lambda k: sum(o["assoc"][k].values()))[:20]
            for k in weakest:
                o["assoc"].pop(k, None)
        self._resolve(action)
        self.heading = None

    def _resolve(self, action):
        pred, self.prediction = self.prediction, None
        if not pred:
            return
        o = self.o
        hit = action == pred["action"]
        conf = o["conf"].get(pred["action"], 0.5)
        o["conf"][pred["action"]] = round(conf + 0.15 * ((1.0 if hit else 0.0) - conf), 3)
        o["acc"] = round(o["acc"] + 0.1 * ((1.0 if hit else 0.0) - o["acc"]), 3)
        if hit:
            o["hits"] += 1
        else:
            o["misses"] += 1
        o["log"].append([round(self.mind.world_time), pred["action"], pred["p"], int(hit)])
        del o["log"][:-40]
        acted = self.acted_on and self.acted_on == pred["action"]
        self.acted_on = None
        m = self.mind
        if hit and acted:
            m.trace(["Cursor moved: " + pred["key"].split(":", 1)[1],
                     f"Predicted {pred['action']} ({int(pred['p'] * 100)}%, {pred['n']} past cases)",
                     "Acted early", "You did it - prediction confirmed"], "prediction")
            if m.first("first_prediction"):
                m.log("predict", "seemed to know what you were about to do before you did it.", "star",
                      important=True)
                m.episodes.add("discovery", "first_prediction", "anticipated one of your actions", 0.7)
        elif acted and not hit:
            m.trace([f"Predicted {pred['action']} ({int(pred['p'] * 100)}%)", "Acted early",
                     "You did something else", "Confidence lowered"], "prediction")
            if not m.beh.reaction and m.rng.random() < 0.5:
                m.beh.interject([act("tilt", 1.0, tag="reaction")])

    def _maybe_anticipate(self):
        m = self.mind
        pred = self.prediction
        if not pred or self.cd["anticipate"] > 0 or m.recip.busy() or not m.experimental():
            return
        # trivial "predictions" (the cursor is already on the thing) aren't worth acting on
        if pred["key"].startswith("z:room:") and pred["key"].split(":")[-1] in ("pet", "ball", "wall") and \
                pred["action"] in ("pet", "ball", "draw"):
            return
        if self.stage() < 3 and self.o["hits"] < 3:
            return
        conf = self.o["conf"].get(pred["action"], 0.5)
        if pred["p"] * (0.5 + conf) < 0.42:
            return
        beh = m.beh
        a = pred["action"]
        steps = None
        if a == "feed":
            side = -1 if beh.x < 64 else 1
            steps = [move(64 + side * 11, speed=1.8, tag="anticipate"),
                     act("excited", 1.6, face=-side, tag="anticipate")]
        elif a in ("play", "ball"):
            side = -1 if beh.x < m.ball_x else 1
            steps = [move(max(X_MIN, min(X_MAX, m.ball_x + side * 10)), speed=1.6, tag="anticipate"),
                     act("excited", 1.2, face=-side, tag="anticipate")]
        elif a == "medicine":
            steps = [move(max(X_MIN, min(X_MAX, beh.x + (10 if beh.x < 100 else -10))), speed=1.8,
                          tag="anticipate"), act("nervous", 1.4, tag="anticipate")]
        elif a == "lights" and m.sleepy() > 0.3:
            steps = [move(m.world.bed_x, speed=1.0, tag="anticipate"), act("sit", 2.0, tag="anticipate")]
        elif a == "pet":
            steps = [act("love", 1.4, gaze="", tag="anticipate")]
        elif a == "discipline":
            steps = [act("sit", 1.6, gaze="", tag="anticipate")]
        elif a in ("speed", "pause"):
            steps = [act("watch", 1.8, face=1, gaze="ur", tag="anticipate")]
        elif a == "draw":
            steps = [act("look", 1.2, gaze="u", tag="anticipate")]
        if steps:
            self.cd["anticipate"] = 15.0
            self.acted_on = a
            beh.interject(steps)
            m.trace([f"Cursor context {pred['key']}", f"Past cases: {pred['n']}",
                     f"Expected you to {a} ({int(pred['p'] * 100)}%)", "Moved early"], "anticipate")

    # ---- deliberate observation ----------------------------------------------------------
    def _watch_tick(self):
        m = self.mind
        c, beh = m.c, m.beh
        if c.asleep or m.recip.busy() or beh.tag in ("watch", "anticipate", "create", "private") \
                or not m.watched or m.cursor is None:
            self.still_room = 0.0
            return
        p = c.personality
        cx, cy = m.cursor
        self.still_room = self.still_room + 0.5 if m.cursor_speed < 4 else 0.0
        # curious when the cursor stops moving
        if self.still_room > 2.5 and self.cd["curious"] == 0 and m.rng.random() < 0.25 + p["curiosity"] * 0.3:
            self.cd["curious"] = 25.0
            tx = max(X_MIN, min(X_MAX, cx + (14 if cx < beh.x else -14)))
            beh.interject([move(tx, z=0.6, speed=0.9, tag="watch"), act("tilt", 1.4, tag="watch"),
                           act("watch", 2.0, tag="watch")])
            m.trace(["Cursor stopped moving", f"Curiosity {p['curiosity']:.2f}", "Went to look"], "observe")
            return
        # studying repetitive movement
        if len(m.dir_changes) >= 3 and self.cd["study"] == 0 and m.rng.random() < 0.3 + p["curiosity"] * 0.3:
            self.cd["study"] = 40.0
            self.o["studied"] += 1
            beh.interject([act("watch", 3.5, tag="watch")])
            if m.first("studied_movement"):
                m.log("observe", "stopped everything to study the way your cursor kept repeating a movement.",
                      "ghost")
            m.trace(["Cursor repeated a movement", "Stopped to study it"], "observe")
            return
        if self.cd["watch"] > 0:
            return
        trust = m.trust()
        chance = (0.03 + 0.07 * p["curiosity"] + 0.04 * max(0.0, trust)
                  + 0.03 * c.memory.attachment / 100 + (0.05 if m.q("observer") else 0.0))
        if m.rng.random() > chance:
            return
        self.cd["watch"] = m.rng.uniform(20, 45)
        if m.fearful() or (m.shyness() > 0.55 and trust < 0.4):
            beh.interject([move(141, speed=1.6, tag="watch"), act("peek", 3.0, tag="watch")])
            m.trace(["Cursor active", f"Shy/fearful (trust {trust:+.2f})", "Watched from behind the plant"],
                    "observe")
        elif m.rng.random() < 0.3 and c.memory.attachment > 50:
            beh.interject([move(max(X_MIN, min(X_MAX, cx)), z=1.0, speed=1.0, tag="watch"),
                           act("watch", 3.0, gaze="", tag="watch")])
            m.trace(["Cursor active", "Comfortable with you", "Came to the front to watch"], "observe")
        else:
            beh.interject([act("watch", m.rng.uniform(2.0, 4.0), tag="watch")])
            m.trace(["Cursor active", f"Curiosity {p['curiosity']:.2f}", "Stopped to watch"], "observe")

    # ---- time and pause --------------------------------------------------------------------
    def on_speed(self, new, old):
        m = self.mind
        c = m.c
        if c is None or c.stage == "egg" or c.asleep or not m.watched:
            return
        o = self.o
        o["speed_seen"] += 1
        if not m.experimental() or m.recip.busy() or self.cd["time"] > 0:
            return
        self.cd["time"] = 20.0
        if new > old:
            steps = [move(CLOCK_X, z=0.0, speed=1.3, tag="watch"), act("ponder", 1.6, gaze="u", tag="watch"),
                     act("tilt", 1.0, tag="watch")]
            if o["speed_seen"] >= 3:
                steps += [act("watch", 1.8, face=1, gaze="ur", tag="watch")]
                m.learn("time_control", 1.0, 0.25)
            m.beh.interject(steps)
            m.trace(["Simulation sped up", f"Seen {o['speed_seen']} speed changes",
                     "Looked at the clock" + (" then at the speed control" if o["speed_seen"] >= 3 else "")],
                    "time")
            if o["speed_seen"] == 3:
                m.log("time", "looked at the clock as the world sped up, then straight at the speed control.",
                      "ghost", important=True)

    def on_rapid(self, dt, speed):
        if speed >= 60 and self.mind.watched and self.mind.c and not self.mind.c.asleep:
            self.o["rapid"] += dt

    def on_unpause(self):
        m = self.mind
        c = m.c
        if c is None or c.stage == "egg" or c.asleep:
            return
        o = self.o
        o["pause_seen"] += 1
        if o["pause_seen"] >= 3 and m.experimental() and not m.recip.busy() and m.rng.random() < 0.6:
            m.learn("pause_button", 1.0, 0.25)
            m.beh.interject([act("watch", 1.6, face=1, gaze="ur", tag="watch")])
            m.trace([f"Unpaused ({o['pause_seen']} times so far)", "Looked toward the pause control"], "time")
            if o["pause_seen"] == 3:
                m.log("time", "glanced toward the pause button as the world started moving again.", "ghost")

    def on_slowdown(self):
        """Back to normal speed after a long fast spell: it looks around, puzzled."""
        m = self.mind
        if self.o["rapid"] > 30 and not m.recip.busy() and m.experimental():
            self.o["rapid"] = 0.0
            m.beh.interject([act("look", 1.4, tag="watch"), act("tilt", 1.0, tag="watch")])
            m.trace(["Long stretch at high speed", "Speed returned to normal", "Looked around, puzzled"], "time")

    # ---- the model of you, as stages ---------------------------------------------------------
    def stage(self):
        """Developmental stage of its model of you (milestones, in order)."""
        m = self.mind
        o = self.o
        r = m.recip.b
        lang = r["lang"]
        tries = sum(st["n"] for t in lang["stats"].values() for st in t.values())
        checks = [
            "encounter" in o["ms"],
            any(sum(t.values()) >= 4 and max(t.values()) / sum(t.values()) >= 0.5 for t in o["assoc"].values()),
            o["hits"] >= 3,
            tries >= 5,
            o["symbols"] >= 1,
            bool(lang["conventions"]),
            any(g["wins"] >= 1 for g in r["games"].values()) or r["collab"] >= 1,
        ]
        stage = 0
        for ok in checks:
            if not ok:
                break
            stage += 1
        stage = max(1, stage)
        if stage > o["stage"]:
            o["stage"] = stage
            o["ms"][STAGE_NAMES[stage].lower()] = m.world_time
            m.trace([f"Model of you reached stage {stage}: {STAGE_NAMES[stage]}"], "stage")
        return o["stage"]

    def day_tick(self):
        """Habits change: old associations fade."""
        o = self.o
        lt = time.localtime(self.mind.world_time)
        day = lt.tm_year * 400 + lt.tm_yday
        if o["day"] == day:
            return
        if o["day"]:
            for key in list(o["assoc"]):
                table = {a: round(n * 0.85, 2) for a, n in o["assoc"][key].items() if n * 0.85 >= 0.3}
                if table:
                    o["assoc"][key] = table
                else:
                    o["assoc"].pop(key)
        o["day"] = day

    def summary(self):
        o = self.o
        top_zones = sorted(o["zones"].items(), key=lambda kv: -kv[1])[:6]
        rows = []
        for key, table in sorted(o["assoc"].items(), key=lambda kv: -sum(kv[1].values()))[:8]:
            total = sum(table.values())
            a = max(table, key=table.get)
            rows.append(f"{key} -> {a} ({int(table[a] / total * 100)}% of {total:.0f})")
        return {
            "stage": f"{self.stage()} - {STAGE_NAMES[self.stage()]}",
            "zones": [f"{z}: {n}" for z, n in top_zones],
            "assoc": rows,
            "accuracy": f"{o['hits']} right, {o['misses']} wrong (recent accuracy {o['acc']:.0%})",
            "conf": [f"{a}: {v:.2f}" for a, v in sorted(o["conf"].items(), key=lambda kv: -kv[1])[:6]],
            "prediction": (f"{self.prediction['action']} ({int(self.prediction['p'] * 100)}%) from {self.prediction['key']}"
                           if self.prediction else "-"),
            "time": f"speed changes seen {o['speed_seen']}, unpauses seen {o['pause_seen']}",
        }


def heading_target(pos, vel, rects, max_dist=420):
    """Which button rect is the cursor moving toward? Returns its name or None."""
    vx, vy = vel
    speed = math.hypot(vx, vy)
    if speed < 120:
        return None
    best, best_d = None, max_dist
    for name, r in rects.items():
        cx, cy = r.centerx, r.centery
        dx, dy = cx - pos[0], cy - pos[1]
        d = math.hypot(dx, dy)
        if d < 1 or d > max_dist:
            continue
        cos = (dx * vx + dy * vy) / (d * speed)
        if cos > 0.94 and d < best_d:
            best, best_d = name, d
    return best


