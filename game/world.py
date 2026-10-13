"""The room as a persistent place.

Unlike the creature, the World outlives each generation: where the bed has
been dragged, the drawing on the wall, the pile of collected trinkets, the
games pets have invented, scratch marks at the edges of the room and
souvenirs from trips outside. New pets inherit the room - a tiny culture.
"""

PILE_MAX = 12
MURAL_MAX = 700
ITEM_KINDS = ("pebble", "leaf", "button", "feather", "bead", "petal")
BED_RANGE = (22.0, 116.0)
MURAL_RECT = (8, 50, 132, 20)      # x, y, w, h on the lower wall (LCD pixels)


class World:
    def __init__(self):
        self.bed_x = 30.0
        self.ball_x = 100.0
        self.ball_in_bowl = False
        self.pile = {"x": 44.0, "items": []}
        self.mural = []            # [x, y, [r, g, b], generation]
        self.mural_artists = {}    # generation (str) -> name
        self.inventions = []       # {"id", "by", "gen"}
        self.marks = {"left": 0, "right": 0, "glass": 0}
        self.souvenirs = []
        self.nest = False
        self.bowl_food = None      # transient: food sitting in the bowl
        self.stash = {"x": 151.0, "items": []}     # hidden behind the plant
        self.loose = []            # trinkets lying on the floor: {"kind", "x", "vx"}
        self.figure = None         # the caretaker experiment's little figure
        self.mirror_x = 106.0
        self.symbols = {}          # generation (str) -> [x, y] personal symbol on the wall
        self.frame_tilt = 0        # you can knock the picture crooked
        self.active_toy = None     # transient: a shop toy being played with

    # ---- creations -------------------------------------------------------------
    def add_item(self, kind):
        self.pile["items"].append(kind)
        if len(self.pile["items"]) > PILE_MAX:
            self.pile["items"].pop(0)

    def add_mural(self, pixels, gen, artist):
        mx, my, mw, mh = MURAL_RECT
        taken = {(p[0], p[1]) for p in self.mural}
        added = 0
        for x, y, col in pixels:
            if mx <= x < mx + mw and my <= y < my + mh and (x, y) not in taken:
                self.mural.append([int(x), int(y), list(col), gen])
                taken.add((x, y))
                added += 1
        if len(self.mural) > MURAL_MAX:
            self.mural = self.mural[-MURAL_MAX:]
        if added:
            self.mural_artists[str(gen)] = artist
        return added

    def mural_generations(self):
        """Pet generations that drew here (your own marks are generation 0)."""
        return sorted({p[3] for p in self.mural if p[3] >= 1})

    def knows(self, invention):
        return any(i["id"] == invention for i in self.inventions)

    def inventor_of(self, invention):
        for i in self.inventions:
            if i["id"] == invention:
                return i
        return None

    # ---- persistence -----------------------------------------------------------------
    def to_dict(self):
        return {k: v for k, v in vars(self).items() if k not in ("bowl_food", "active_toy")}

    @classmethod
    def from_dict(cls, data):
        w = cls()
        for k, v in (data or {}).items():
            if hasattr(w, k) and k not in ("bowl_food", "active_toy"):
                if isinstance(getattr(w, k), dict) and isinstance(v, dict):
                    getattr(w, k).update(v)
                else:
                    setattr(w, k, v)
        w.bed_x = max(BED_RANGE[0], min(BED_RANGE[1], float(w.bed_x)))
        return w
