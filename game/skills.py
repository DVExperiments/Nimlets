"""Simple tool use, discovered by experiment.

The creature has a few primitive ways of acting on its ball (kick it at a
wall, toward the bowl, toward a trinket, behind the plant, then wait or
chase). It tries short sequences, watches what the ball does, and keeps
counts of action -> outcome. Sequences that reliably produce an interesting
outcome become *skills* it uses on purpose:

  rebound   the ball comes back after hitting the wall
  in_bowl   the ball drops into the bowl
  hit_item  the ball knocks a trinket it can't reach out from under the plant
  hidden    the ball disappears behind the plant

The most elaborate behaviour - using the ball to free a trinket it cannot
reach, then picking it up - is never scripted as a single scene: it emerges
when a creature that has discovered `hit_item` wants an unreachable item.

Also here: private stashes behind the plant, the pet's own arrangement of
its collection, and pausing private activities when the cursor comes close.
"""
from .behaviour import act, chase, move
from .config import FLOOR_Y, X_MAX, X_MIN

PRIMS = {"wall": "kicking the ball at the wall", "bowl": "nudging the ball toward the bowl",
         "item": "knocking the ball into a trinket", "plant": "pushing the ball behind the plant",
         "wait": "waiting to see what happens", "chase": "chasing after it"}
OUTCOMES = {"rebound": "the ball bounces back to it", "in_bowl": "the ball lands in the bowl",
            "hit_item": "the ball can knock a trinket out from under the plant",
            "hidden": "the ball disappears behind the plant"}
CULTURE = {"wall_bounce": "rebound", "ball_bowl": "in_bowl", "tool_item": "hit_item", "hide_ball": "hidden"}
REACH = 147.0          # it can't reach trinkets further right than this (under the plant)
ARRANGEMENTS = ("line", "stack", "circle", "sorted")


def ensure(c):
    if not isinstance(getattr(c, "skills", None), dict) or "tries" not in c.skills:
        c.skills = {"tries": {}, "known": {}, "accidents": {}}
    c.skills.setdefault("accidents", {})
    return c.skills


class Skills:
    def __init__(self, mind):
        self.mind = mind
        self.trial = None             # {"seq", "t", "start_x"}
        self.last_trial = None        # (seq, clock) - late outcomes are credited back to it
        self.wall_t = None
        self.private_hold = 0.0

    @property
    def s(self):
        return ensure(self.mind.c)

    # ---- choosing what to try ------------------------------------------------------------
    def explore_plan(self):
        """Try a sequence: mostly known skills, sometimes something new."""
        m = self.mind
        s = self.s
        loose_far = [it for it in m.world.loose if it["x"] > REACH]
        if loose_far and "hit_item" in s["known"]:
            return self.plan_for(s["known"]["hit_item"]["seq"], purpose="tool")
        if loose_far and m.rng.random() < 0.6:
            # goal-directed: it wants that trinket, so it experiments with the ball near it
            m.trace(["A trinket is out of reach under the plant", "Trying the ball on it"], "skill")
            return self.plan_for("item>" + m.rng.choice(["wait", "chase"]), purpose="tool")
        explore = 0.55 if not s["known"] else 0.25
        if m.mut("inventor"):
            explore += 0.2
        if s["known"] and m.rng.random() > explore:
            # vary its play between the things it knows how to make happen
            options = sorted(s["known"])
            weights = [1.0 / (1 + s["known"][o]["uses"] * 0.15) for o in options]
            r = m.rng.uniform(0, sum(weights))
            outcome = options[-1]
            for o, wgt in zip(options, weights):
                r -= wgt
                if r <= 0:
                    outcome = o
                    break
            return self.plan_for(s["known"][outcome]["seq"], purpose="skill")
        firsts = ["wall", "bowl", "plant"] + (["item"] if m.world.loose else [])
        hinted = [p for inv, o in CULTURE.items() if m.world.knows(inv)
                  for p, oo in (("wall", "rebound"), ("bowl", "in_bowl"), ("item", "hit_item"), ("plant", "hidden"))
                  if oo == o and p in firsts]
        if s["accidents"].get("hit_item") and "item" in firsts:
            hinted.append("item")
        first = m.rng.choice(hinted) if hinted and m.rng.random() < 0.6 else m.rng.choice(firsts)
        seq = first + ">" + m.rng.choice(["wait", "chase", "wait"])
        return self.plan_for(seq, purpose="explore")

    def plan_for(self, seq, purpose="explore"):
        m = self.mind
        bx = m.ball_x
        first, second = (seq.split(">") + ["wait"])[:2]
        steps = []
        if first == "wall":
            left = bx < 80
            stand = bx + (8 if left else -8)
            steps += [move(max(X_MIN, min(X_MAX, stand)), speed=1.4, tag="tool"),
                      act("push", 0.4, face=-1 if left else 1, fx="tool:wall", tag="tool")]
        elif first == "bowl":
            side = 1 if bx > 64 else -1
            steps += [move(max(X_MIN, min(X_MAX, bx + side * 8)), speed=1.4, tag="tool"),
                      act("push", 0.4, face=-side, fx="tool:bowl", tag="tool")]
        elif first == "plant":
            steps += [move(max(X_MIN, bx - 8), speed=1.4, tag="tool"),
                      act("push", 0.4, face=1, fx="tool:plant", tag="tool")]
        elif first == "item":
            target = self._target_item()
            tx = target["x"] if target else 150
            side = -1 if bx < tx else 1
            steps += [move(max(X_MIN, min(X_MAX, bx + side * 8)), speed=1.4, tag="tool"),
                      act("push", 0.4, face=-side, fx="tool:item", tag="tool")]
        if second == "wait":
            steps.append(act("watch", 2.2, tag="tool"))
        else:
            steps.append(chase(kicks=1, tag="tool"))
        steps.append(act("idle", 0.6, fx="tool:end", tag="tool"))
        if purpose == "tool":
            steps += [act("look", 0.6, tag="tool"), act("idle", 0.2, fx="tool:fetch", tag="tool")]
        m.trace([f"Wanted to {'free a trinket' if purpose == 'tool' else 'play'}",
                 f"{'Used known skill' if purpose != 'explore' else 'Explored'}: "
                 f"{PRIMS[first]}, then {PRIMS[second]}"], "skill")
        self.pending_seq = seq
        return steps

    def _target_item(self):
        far = [it for it in self.mind.world.loose if it["x"] > REACH]
        return far[0] if far else (self.mind.world.loose[0] if self.mind.world.loose else None)

    # ---- step effects ---------------------------------------------------------------------
    def step_fx(self, fx):
        m = self.mind
        kind = fx.split(":", 1)[1]
        if kind in ("wall", "bowl", "plant", "item"):
            self.trial = {"seq": getattr(self, "pending_seq", kind + ">wait"), "t": m.clock,
                          "x": m.beh.x, "outcomes": set()}
            if kind == "wall":
                m.kick_ball(-1 if m.ball_x < 80 else 1, 2.6)
            elif kind == "bowl":
                m.kick_ball_to(64)
            elif kind == "plant":
                m.kick_ball(1, 2.8)
            elif kind == "item":
                target = self._target_item()
                m.kick_ball(1 if (target and target["x"] > m.ball_x) else -1, 2.6)
        elif kind == "end":
            self._score()
        elif kind == "fetch":
            reachable = [it for it in m.world.loose if it["x"] <= REACH]
            if reachable:
                it = reachable[0]
                m.beh.plan[0:0] = [move(max(X_MIN, min(X_MAX, it["x"])), speed=1.3, tag="tool"),
                                   act("inspect", 1.0, fx="tool:pick", tag="tool"),
                                   move(m.world.pile["x"], speed=1.1, tag="tool"),
                                   act("drop", 0.6, fx="drop_item", tag="tool")]
        elif kind == "pick":
            for it in list(m.world.loose):
                if abs(it["x"] - m.beh.x) < 10:
                    m.world.loose.remove(it)
                    m.carrying = it["kind"]
                    if m.first("tool_use") and m.uncanny.allow("multi_step_skill"):
                        m.uncanny.record("multi_step_skill", "used the ball to free a trinket")
                        m.log("skill", "used its ball to knock a trinket out from under the plant, then "
                              "picked it up. Nobody taught it that.", "ball", important=True)
                        m.episodes.add("skill", "tool_use", "freed a trinket with the ball", 0.9)
                    break

    def on_ball_event(self, event):
        """Physics events from the ball: 'wall', 'bowl', 'plant', 'item'."""
        m = self.mind
        if event == "wall":
            self.wall_t = m.clock
        tr = self.trial
        outcome = {"bowl": "in_bowl", "plant": "hidden", "item": "hit_item"}.get(event)
        if event == "item_freed":
            outcome = "hit_item"
        if tr and m.clock - tr["t"] < 5:
            if outcome and outcome != "hit_item":
                tr["outcomes"].add(outcome)
            elif outcome == "hit_item" and event == "item_freed":
                tr["outcomes"].add(outcome)
        elif event == "item_freed" and self.last_trial and m.clock - self.last_trial[1] < 10:
            seq = self.last_trial[0]                 # it slid out after the experiment "ended"
            rec = self.s["tries"].setdefault(seq, {"n": 1, "out": {}})
            rec["out"]["hit_item"] = rec["out"].get("hit_item", 0) + 1
            self._learn(seq, rec, "hit_item")
        elif outcome == "hit_item":
            acc = self.s["accidents"]
            acc["hit_item"] = acc.get("hit_item", 0) + 1
            if acc["hit_item"] == 1 and not m.recip.busy():
                m.beh.interject([act("inspect", 1.2, tag="reaction")])
                m.trace(["Ball hit a trinket by accident", "Stopped to inspect what happened"], "skill")

    def tick(self):
        """Detect a rebound: ball hit a wall and came back near the pet."""
        m = self.mind
        tr = self.trial
        if tr and self.wall_t and self.wall_t > tr["t"] and abs(m.ball_x - m.beh.x) < 24 \
                and m.clock - self.wall_t < 3.5:
            tr["outcomes"].add("rebound")

    def _score(self):
        m = self.mind
        tr, self.trial = self.trial, None
        if not tr:
            return
        s = self.s
        rec = s["tries"].setdefault(tr["seq"], {"n": 0, "out": {}})
        rec["n"] += 1
        self.last_trial = (tr["seq"], m.clock)
        for o in tr["outcomes"]:
            rec["out"][o] = rec["out"].get(o, 0) + 1
        for o in tr["outcomes"]:
            self._learn(tr["seq"], rec, o)
        for o, k in s["known"].items():
            if k["seq"] == tr["seq"]:
                k["uses"] += 1
        if len(s["tries"]) > 40:
            weakest = sorted(s["tries"], key=lambda q: s["tries"][q]["n"])[:5]
            for q in weakest:
                s["tries"].pop(q, None)

    def _learn(self, seq, rec, o):
        m = self.mind
        s = self.s
        known = s["known"].get(o)
        if known:
            if known["seq"] == seq:
                known["ok"] += 1
            return
        if rec["out"][o] >= 2 and rec["out"][o] / max(1, rec["n"]) >= 0.3:
            if True:
                s["known"][o] = {"seq": seq, "uses": 0, "ok": rec["out"][o]}
                first, second = seq.split(">")
                m.log("skill", f"discovered that {PRIMS[first]} and then {PRIMS[second]} means "
                      f"{OUTCOMES[o]}. It does it on purpose now.", "ball", important=True)
                m.episodes.add("discovery", f"skill:{o}", f"discovered: {OUTCOMES[o]}", 0.8)
                inv = {v: k for k, v in CULTURE.items()}[o]
                if not m.world.knows(inv):
                    m.world.inventions.append({"id": inv, "by": m.c.name, "gen": m.c.generation})
                m.uncanny.record("novel_sequence", f"learned {seq} -> {o}")
                m.trace([f"Tried {PRIMS[first]} then {PRIMS[second]}",
                         f"Outcome '{o}' {rec['out'][o]} of {rec['n']} times", "Learned it as a skill"], "skill")

    # ---- trinkets on the floor ---------------------------------------------------------
    def drop_loose(self, kind, under_plant=False):
        m = self.mind
        x = m.rng.uniform(149, 153) if under_plant else m.rng.uniform(X_MIN, X_MAX)
        m.world.loose.append({"kind": kind, "x": x, "vx": 0.0})
        del m.world.loose[:-4]

    def physics(self, dt, ball_old, ball_new, ball_vx):
        """Loose trinkets slide when the ball hits them; returns new ball velocity."""
        for it in self.mind.world.loose:
            if min(ball_old, ball_new) - 2 <= it["x"] <= max(ball_old, ball_new) + 2 and abs(ball_vx) > 15:
                it["vx"] = ball_vx * 0.8
                ball_vx *= 0.4
                self.on_ball_event("item")
            if abs(it["vx"]) > 0.5:
                it["x"] += it["vx"] * dt
                it["vx"] *= 0.975 ** (dt * 30)
                if it["x"] > 157:
                    it["x"], it["vx"] = 157, -abs(it["vx"]) * 0.85
                if it["x"] < 6:
                    it["x"], it["vx"] = 6, abs(it["vx"]) * 0.6
            else:
                it["vx"] = 0.0
            if it["x"] > REACH:
                it["far"] = True
            elif it.get("far") and it["vx"] == 0.0:
                it["far"] = False
                self.on_ball_event("item_freed")           # it slid out to where the pet can reach it
        return ball_vx

    def reach_attempt_plan(self):
        """It wants an item under the plant but can't reach it (yet)."""
        return [move(REACH - 1, speed=1.3, tag="tool"), act("push_wall", 1.6, face=1, tag="tool"),
                act("tilt", 1.0, fx="tool:cantreach", tag="tool")]

    # ---- private collections -------------------------------------------------------------
    def stash_plan(self):
        m = self.mind
        w = m.world
        if not w.pile["items"]:
            return None
        return [move(w.pile["x"], speed=1.1, tag="private"), act("inspect", 1.0, fx="stash:take", tag="private"),
                move(REACH - 2, speed=0.9, walk="sneak", tag="private"),
                act("hide", 1.2, fx="stash:put", tag="private"), act("peek", 1.0, gaze="", tag="private")]

    def stash_fx(self, kind):
        m = self.mind
        w = m.world
        if kind == "take" and w.pile["items"]:
            m.carrying = w.pile["items"].pop()
        elif kind == "put" and m.carrying:
            w.stash["items"].append(m.carrying)
            del w.stash["items"][:-10]
            m.carrying = None
            if m.first("stash"):
                m.log("private", "has started hiding some of its treasures behind the plant.", "pebble",
                      important=True)
            m.uncanny.record("hide_object", "hid a trinket behind the plant")
            m.trace(["Prefers less exposed places", "Moved a trinket behind the plant"], "private")

    def private_guard(self, dt):
        """Pause a private activity while the cursor is close; resume when it leaves."""
        m = self.mind
        beh = m.beh
        near = m.cursor is not None and abs(m.cursor[0] - beh.x) < 30 and m.cursor[1] > FLOOR_Y - 60
        if beh.tag == "private" and near and not beh.reaction:
            beh.interject([act("idle", 30.0, gaze="", tag="hush")])
            self.private_hold = 0.0
            m.trace(["Doing something private", "Cursor came close", "Stopped and acted innocent"], "private")
        elif beh.tag == "hush":
            self.private_hold = self.private_hold + dt if not near else 0.0
            if self.private_hold > 1.5:
                beh.step = None
                beh._advance()          # carries on with what it was doing

    def arrange(self):
        """Its personal way of arranging its collection."""
        m = self.mind
        p = m.c.personality
        style = ("sorted" if p["stubbornness"] > 0.6 else "circle" if p["sociability"] > 0.6
                 else "stack" if p["independence"] > 0.6 else "line")
        m.world.pile["style"] = style
        if style == "sorted":
            m.world.pile["items"].sort()
        return style

    def summary(self):
        s = self.s
        rows = [f"{OUTCOMES[o]}: {k['seq'].replace('>', ' then ')} (used {k['uses']}x)" for o, k in s["known"].items()]
        tries = sorted(s["tries"].items(), key=lambda kv: -kv[1]["n"])[:6]
        rows += [f"tried {q.replace('>', ' then ')} x{r['n']}: " +
                 (", ".join(f"{o} {n}" for o, n in r["out"].items()) or "nothing happened") for q, r in tries]
        return rows or ["no experiments with objects yet"]
