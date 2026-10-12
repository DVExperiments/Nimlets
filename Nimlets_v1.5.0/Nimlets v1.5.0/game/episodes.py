"""Episodic memory: a small, bounded store of meaningful experiences.

Each episode has a strength. Important or repeated experiences grow
stronger and fade slowly; trivial ones fade away. Occasionally the creature
*recalls* an episode that hasn't been repeated for a while and acts it out -
greeting you with a gesture you stopped using days ago, inviting you to an
old game, returning to a place where something happened.
"""
import time

MAX_EPISODES = 60
IMPORTANCE = {"communication": 0.9, "gesture": 0.6, "game": 0.6, "object": 0.5, "change": 0.5,
              "discovery": 0.7, "experiment": 0.6, "collaboration": 0.7, "ritual": 0.8, "skill": 0.7}


def ensure_episodes(c):
    if not isinstance(getattr(c, "episodes", None), list):
        c.episodes = []
    return c.episodes


class Episodes:
    def __init__(self, mind):
        self.mind = mind
        self.day = 0

    @property
    def items(self):
        return ensure_episodes(self.mind.c)

    def add(self, kind, key, text, importance=None, data=None):
        m = self.mind
        if m.c is None:
            return None
        imp = importance if importance is not None else IMPORTANCE.get(kind, 0.5)
        wt = m.offline_wt or m.world_time
        for ep in self.items:
            if ep["key"] == key:
                ep["n"] += 1
                ep["strength"] = round(min(1.0, ep["strength"] + 0.2 * imp), 3)
                ep["last"] = wt
                if data:
                    ep["data"].update(data)
                return ep
        ep = {"key": key, "kind": kind, "text": text, "imp": imp, "strength": round(0.4 + 0.5 * imp, 3),
              "n": 1, "first": wt, "last": wt, "recalled": 0, "data": dict(data or {})}
        self.items.append(ep)
        if len(self.items) > MAX_EPISODES:
            self.items.sort(key=lambda e: e["strength"])
            del self.items[0]
        return ep

    def get(self, key):
        return next((e for e in self.items if e["key"] == key), None)

    def day_tick(self):
        lt = time.localtime(self.mind.world_time)
        day = lt.tm_year * 400 + lt.tm_yday
        if self.day == day:
            return
        if self.day:
            keep = []
            for ep in self.items:
                ep["strength"] = round(ep["strength"] - 0.05 * (1 - ep["imp"]) / (1 + 0.3 * ep["n"]), 3)
                if ep["strength"] > 0.05:
                    keep.append(ep)
            self.items[:] = keep
        self.day = day

    def forgotten(self, min_days=2.0):
        """Strong episodes that haven't been repeated for a while."""
        now = self.mind.world_time
        return [e for e in self.items if e["strength"] > 0.3 and now - e["last"] > min_days * 86400]

    def recall(self):
        """Pick a forgotten episode to act out (weighted by strength). Returns it or None."""
        options = self.forgotten()
        if not options:
            return None
        weights = {i: e["strength"] for i, e in enumerate(options)}
        total = sum(weights.values())
        r = self.mind.rng.uniform(0, total)
        for i, w in weights.items():
            r -= w
            if r <= 0:
                ep = options[i]
                ep["recalled"] += 1
                ep["last"] = self.mind.world_time
                return ep
        return options[-1]
