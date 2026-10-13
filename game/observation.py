"""Observation Mode support: a bounded reasoning trace and exportable logs.

Every significant decision appends a short causal chain, e.g.
  "Wanted food because it was getting hungry -> tapping the bowl
   -> expected 67% (4/6 before) -> chose its best guess"
so you can tell system-driven behaviour apart from random animation.
"""
import json
import os
import time
from collections import deque


class Trace:
    def __init__(self, size=300):
        self.items = deque(maxlen=size)

    def add(self, world_time, chain, kind):
        self.items.append({"wt": round(world_time), "kind": kind, "chain": [str(x) for x in chain]})

    def recent(self, n=40, kind=None):
        out = [e for e in self.items if kind is None or e["kind"] == kind]
        return list(reversed(out[-n:]))

    @staticmethod
    def line(e):
        return time.strftime("%H:%M", time.localtime(e["wt"])) + "  " + " -> ".join(e["chain"])


def export_log(mind, folder):
    """Write an observation log (JSON + Markdown) for comparing creatures and generations."""
    c = mind.c
    stamp = time.strftime("%Y%m%d-%H%M")
    base = os.path.join(folder, f"observation_{c.name}_gen{c.generation}_{stamp}")
    snap = mind.observation_snapshot()
    data = {"creature": {"name": c.name, "species": c.species, "generation": c.generation,
                         "age_days": round(c.age_days, 2), "personality": c.personality.traits},
            "snapshot": snap, "trace": list(mind.trace_log.items)}
    os.makedirs(folder, exist_ok=True)
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    lines = [f"# Observation log: {c.name} (generation {c.generation})", "",
             f"Exported {time.strftime('%Y-%m-%d %H:%M')}. Species {c.species}, age {c.age_days:.1f} days.", ""]
    for title, rows in snap:
        lines += [f"## {title}", ""] + [f"- {r}" for r in rows] + [""]
    lines += ["## Reasoning trace (newest first)", ""] + [f"- {Trace.line(e)}" for e in mind.trace_log.recent(300)]
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return base + ".md"
