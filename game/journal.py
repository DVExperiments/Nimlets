"""The behaviour diary: a log of interesting things the pet did.

Entries that happen while you are watching are marked as seen straight
away; the rest show up in the "While you were away" summary.
"""
import time

MAX_ENTRIES = 300
# repeated entries of these kinds within the merge window become "(x3)"
MERGEABLE = {"ball", "window", "doze", "silly", "dream", "collect", "draw", "signal", "sleep_spot",
             "care", "edge", "experiment", "wait", "avoid"}


class Journal:
    def __init__(self):
        self.entries = []
        self.next_id = 1
        self.seen_id = 1

    def add(self, kind, text, world_time, icon=None, merge_window=1800.0, important=False):
        if self.entries:
            last = self.entries[-1]
            if (last["kind"] == kind and kind in MERGEABLE and last["text"] == text
                    and world_time - last["wt"] < merge_window):
                last["n"] += 1
                last["wt"] = world_time
                if last["id"] < self.seen_id:          # happened again while away
                    last["id"] = self.next_id
                    self.next_id += 1
                return last
        entry = {"id": self.next_id, "kind": kind, "text": text, "wt": world_time,
                 "icon": icon or kind, "n": 1, "important": important}
        self.next_id += 1
        self.entries.append(entry)
        if len(self.entries) > MAX_ENTRIES:
            self.entries = self.entries[-MAX_ENTRIES:]
        return entry

    def unseen(self):
        return [e for e in self.entries if e["id"] >= self.seen_id]

    def mark_seen(self):
        self.seen_id = self.next_id

    def recent(self, n=50):
        return list(reversed(self.entries[-n:]))

    @staticmethod
    def label(entry):
        text = entry["text"]
        return f"{text} (x{entry['n']})" if entry["n"] > 1 else text

    @staticmethod
    def stamp(entry):
        return time.strftime("%a %H:%M", time.localtime(entry["wt"]))

    def to_dict(self):
        return {"entries": self.entries, "next_id": self.next_id, "seen_id": self.seen_id}

    @classmethod
    def from_dict(cls, data):
        j = cls()
        data = data or {}
        j.entries = list(data.get("entries", []))[-MAX_ENTRIES:]
        j.next_id = int(data.get("next_id", len(j.entries) + 1))
        j.seen_id = int(data.get("seen_id", j.next_id))
        return j
