"""The Escape Experiment: the pet climbs out of its room.

A Trip is a short choreography in *window* coordinates: the pet climbs over
the top of the screen bezel, walks along it, pokes the hunger hearts, stares
at the clock, sits on the Settings button and finally dives back home.
Anchors are recomputed from the current layout every frame, so resizing the
window mid-trip still works.

A wander (v2.0, replacing the old desktop companion) is the longest trip: once
a pet is used to going outside, it may take a long walk around the whole
device - along the hearts, past the clock, down the tabs, across the message
screen, over the A/B/C buttons - and come back with a little souvenir. It
never leaves the game window.
"""
import math

SOUVENIRS = ("a stray pixel", "a crumb from the message screen", "a heart that fell off the hearts strip",
             "a speck of shell paint", "a tiny star from the shell", "a loose bit of tab", "a button shine",
             "the tick of the clock")


class Trip:
    def __init__(self, rng, roam=False, contact=False, variant="ui"):
        self.rng = rng
        self.roam = roam
        self.variant = variant          # "ui", "controls" (speed/pause) or "edge" (window boundary)
        self.events = []                # things the app should react to (pokes, edge reached)
        self.poke_toggle = None
        self.contact = contact          # "first contact": watches and reacts to the cursor
        self.steps = self._build()
        self.i = 0
        self.t = 0.0
        self.done = False
        self.facing = 1
        self.pos = None
        self.poke = 0.0                 # makes the hearts wobble when poked
        self.startled = False

    def _build(self):
        if self.variant == "controls":
            return [
                {"mode": "appear", "at": ("bezel", 0.05), "state": "climb", "dur": 0.9},
                {"mode": "walk", "at": ("bezel", 0.4), "state": "walk"},
                {"mode": "hop", "at": ("toggle", "speed"), "state": "jump"},
                {"mode": "stay", "at": ("toggle", "speed"), "state": "tap", "dur": 2.0, "toggle": "speed"},
                {"mode": "stay", "at": ("toggle", "speed"), "state": "tilt", "dur": 1.0},
                {"mode": "hop", "at": ("toggle", "pause"), "state": "jump"},
                {"mode": "stay", "at": ("toggle", "pause"), "state": "tap", "dur": 2.0, "toggle": "pause"},
                {"mode": "stay", "at": ("toggle", "pause"), "state": "watch", "dur": 1.2},
                {"mode": "hop", "at": ("bezel", 0.5), "state": "jump"},
                {"mode": "dive", "at": ("inside", 0), "state": "jump", "dur": 0.6},
            ]
        if self.variant == "edge":
            return [
                {"mode": "appear", "at": ("bezel", 0.05), "state": "climb", "dur": 0.9},
                {"mode": "walk", "at": ("bezel", 0.6), "state": "walk"},
                {"mode": "hop", "at": ("top_right", 0), "state": "jump"},
                {"mode": "walk", "at": ("edge", 0), "state": "walk"},
                {"mode": "stay", "at": ("edge", 0), "state": "push_wall", "dur": 2.6, "face": 1, "event": "edge"},
                {"mode": "stay", "at": ("edge", 0), "state": "watch", "dur": 1.4, "face": -1},
                {"mode": "walk", "at": ("top_right", 0), "state": "walk"},
                {"mode": "hop", "at": ("bezel", 0.5), "state": "jump"},
                {"mode": "dive", "at": ("inside", 0), "state": "jump", "dur": 0.6},
            ]
        steps = [
            {"mode": "appear", "at": ("bezel", 0.05), "state": "climb", "dur": 0.9},
            {"mode": "walk", "at": ("bezel", 0.32), "state": "walk"},
            {"mode": "hop", "at": ("hearts", 0), "state": "jump"},
            {"mode": "stay", "at": ("hearts", 0), "state": "tap", "dur": 2.4, "face": -1, "poke": True},
            {"mode": "walk", "at": ("clock", 0), "state": "walk"},
            {"mode": "stay", "at": ("clock", 0), "state": "look_clock", "dur": 2.2, "face": 1},
            {"mode": "hop", "at": ("settings", 0), "state": "jump"},
            {"mode": "stay", "at": ("settings", 0), "state": "sit", "dur": 3.5 if self.contact else 2.5},
        ]
        if self.roam:                       # a wander around the whole device
            steps += [{"mode": "hop", "at": ("abc", "a"), "state": "jump"},
                      {"mode": "hop", "at": ("abc", "b"), "state": "jump"},
                      {"mode": "stay", "at": ("abc", "b"), "state": "tap", "dur": 1.2},
                      {"mode": "hop", "at": ("abc", "c"), "state": "jump"},
                      {"mode": "hop", "at": ("msg", 0.85), "state": "jump"},
                      {"mode": "walk", "at": ("msg", 0.15), "state": "walk"},
                      {"mode": "stay", "at": ("msg", 0.15), "state": "watch", "dur": 1.4, "face": -1},
                      {"mode": "hop", "at": ("tabside", 3), "state": "jump"},
                      {"mode": "walk", "at": ("tabside", 1), "state": "walk"},
                      {"mode": "stay", "at": ("tabside", 1), "state": "watch", "dur": 1.6, "face": -1},
                      {"mode": "hop", "at": ("tabtop", 0), "state": "jump"},
                      {"mode": "stay", "at": ("tabtop", 0), "state": "sit", "dur": 2.0, "event": "souvenir"},
                      {"mode": "hop", "at": ("tabtop", 4), "state": "jump"},
                      {"mode": "walk", "at": ("tabside", 5), "state": "walk"},
                      {"mode": "stay", "at": ("tabside", 5), "state": "wave", "dur": 1.0, "face": -1}]
        steps += [
            {"mode": "hop", "at": ("bezel", 0.5), "state": "jump"},
            {"mode": "stay", "at": ("bezel", 0.5), "state": "wave", "dur": 1.0},
            {"mode": "dive", "at": ("inside", 0), "state": "jump", "dur": 0.6},
        ]
        return steps

    # ---- geometry -------------------------------------------------------------------
    @staticmethod
    def anchor(L, name, frac=0.0):
        if name == "bezel":
            return (L.bezel.left + 30 + (L.bezel.w - 60) * frac, L.bezel.top + 2)
        if name == "hearts":                       # standing on top of the hearts strip
            r = getattr(L, "hearts_rect", None) or L.top
            return (r.right - 40, r.top + 2)
        if name == "clock":                        # just beside the clock, on the name row
            r = getattr(L, "clock_rect", None) or L.top
            return (r.left - 22, r.bottom)
        if name == "settings":
            r = L.toggles["settings"]
            return (r.centerx, r.top + 4)
        if name == "toggle":
            r = L.toggles.get(frac) or L.toggles["settings"]
            return (r.centerx, r.top + 4)
        if name == "edge":
            return (L.shell.right - 6, L.top.bottom + 4)
        if name == "top_right":
            return (L.shell.right - 30, L.top.bottom + 4)
        if name == "abc":                          # standing on top of an A/B/C button
            r = L.abc[frac]
            return (r.centerx, r.top + 4)
        if name == "msg":                          # walking along the top of the message screen
            return (L.msg.left + 20 + (L.msg.w - 40) * frac, L.msg.top + 3)
        if name == "tabtop":                       # on top of the first tab of a column
            r = L.buttons[frac]
            return (r.centerx, r.top + 3)
        if name == "tabside":                      # on the shell, just outside a column of tabs
            r = L.buttons[frac]
            if getattr(L, "tab_style", "side") == "grid":   # phone layouts: no outside edge, so on top
                return (r.centerx, r.top + 3)
            side = -1 if frac < 4 else 1
            return ((r.left if side < 0 else r.right) + side * 16, r.bottom - 2)
        if name == "inside":
            return (L.lcd.centerx, L.lcd.top + 40)
        return (L.W / 2, L.H / 2)

    def recall(self):
        """Hurry home (the player pressed a button or clicked the pet)."""
        if self.done:
            return
        tail = [s for s in self.steps if s["at"][0] in ("bezel", "inside")][-3:]
        self.steps = self.steps[: self.i] + tail
        self.t = 0.0

    # ---- update -------------------------------------------------------------------------
    def update(self, dt, L, cursor=None):
        """Returns the current visual state name."""
        if self.done:
            return "jump"
        self.poke = max(0.0, self.poke - dt)
        step = self.steps[self.i]
        target = self.anchor(L, *step["at"])
        prev = self.pos or target
        mode = step["mode"]
        speed = 70.0 * max(1, L.scale) / 4.0 * (2.0 if self.startled else 1.0)
        self.t += dt
        state = step["state"]
        if mode == "appear":
            ph = min(1.0, self.t / step["dur"])
            self.pos = (target[0], target[1] + (1 - ph) * 40)
            finished = ph >= 1
        elif mode == "walk":
            dx, dy = target[0] - prev[0], target[1] - prev[1]
            dist = math.hypot(dx, dy)
            stepd = speed * dt
            if dist <= stepd:
                self.pos = target
                finished = True
            else:
                self.pos = (prev[0] + dx / dist * stepd, prev[1] + dy / dist * stepd)
                finished = False
            if abs(dx) > 1:
                self.facing = 1 if dx > 0 else -1
        elif mode in ("hop", "dive"):
            if not hasattr(self, "_hop_from") or self._hop_step != self.i:
                self._hop_from, self._hop_step = prev, self.i
            dur = step.get("dur", 0.6)
            ph = min(1.0, self.t / dur)
            sx, sy = self._hop_from
            arc = -math.sin(math.pi * ph) * (40 if mode == "hop" else 20)
            self.pos = (sx + (target[0] - sx) * ph, sy + (target[1] - sy) * ph + arc)
            if abs(target[0] - sx) > 1:
                self.facing = 1 if target[0] > sx else -1
            finished = ph >= 1
        else:  # stay
            self.pos = target
            if step.get("face"):
                self.facing = step["face"]
            if step.get("poke") and int(self.t * 5) % 2 == 0:
                self.poke = 0.3
            self.poke_toggle = step.get("toggle")
            if self.contact and cursor is not None:
                self.facing = 1 if cursor[0] > self.pos[0] else -1
            finished = self.t >= step.get("dur", 1.0)
        if finished:
            if step.get("toggle"):
                self.events.append(("poked", step["toggle"]))
                self.poke_toggle = None
            if step.get("event"):
                self.events.append((step["event"], None))
            self.i += 1
            self.t = 0.0
            if self.i >= len(self.steps):
                self.done = True
        return state

    def hit(self, pos, size):
        if not self.pos:
            return False
        x, y = self.pos
        return abs(pos[0] - x) < size * 0.4 and y - size * 0.8 < pos[1] < y + 4
