"""Decorated shells for the handheld device (v1.7).

Shells are unlocked by your family's history, which the records already
keep: hatching a line's first egg unlocks that line's shell, and raising a
secret form unlocks its shell. Because unlocks are derived from
`records.discovered`, older saves get the shells they have earned
automatically, and "Erase everything" re-locks them.

The player's choice lives in preferences ("shell": "match" or a shell id).
"match" follows the pet: its secret form if it is one, otherwise its family
line. Eggs wear the Classic shell so the line stays a surprise.

Decorations are drawn in code, in a 940 x 760 design space that is scaled to
the shell's size, then clipped to the shell's rounded shape.
"""
import math
import random

import pygame

from .sprites import hsv

DESIGN_W, DESIGN_H = 940, 760

# id: name, how it's unlocked (shown on locked shells), species that unlock it
SHELLS = {
    "classic": {"name": "Classic", "hint": "Where every family starts", "unlock": ()},
    "tide": {"name": "Tide", "hint": "Hatch a Dewdrop egg", "unlock": ("dewdrop",)},
    "meadow": {"name": "Meadow", "hint": "Hatch a Pipling egg", "unlock": ("pipling",)},
    "starlight": {"name": "Starlight", "hint": "Raise a Celestine or Aurora", "unlock": ("celestine", "aurora")},
    "glitch": {"name": "Glitch", "hint": "Raise a Glitchling", "unlock": ("glitchling",)},
    "spore": {"name": "Spore", "hint": "Raise a Mycelia", "unlock": ("mycelia",)},
    # family milestones (v1.9)
    "patchwork": {"name": "Patchwork", "hint": "Reach generation 3", "unlock": (), "gen": 3},
    "heirloom": {"name": "Heirloom", "hint": "Reach generation 5", "unlock": (), "gen": 5},
    "familytree": {"name": "Family Tree", "hint": "Reach generation 10", "unlock": (), "gen": 10},
    # rare eggs (v1.9): the colour mutation a pet hatched with
    "golden": {"name": "Golden", "hint": "Hatch a Golden egg", "unlock": (), "egg": "shiny"},
    "void": {"name": "Void", "hint": "Hatch a Void egg", "unlock": (), "egg": "midnight"},
    "chimera": {"name": "Chimera", "hint": "Hatch a Chimera egg", "unlock": (), "egg": "chimera"},
    "pastel": {"name": "Pastel", "hint": "Hatch a Pastel egg", "unlock": (), "egg": "pastel"},
    "static": {"name": "Static", "hint": "Hatch a Glitch egg", "unlock": (), "egg": "glitch"},
}
EGG_SHELL = {v["egg"]: k for k, v in SHELLS.items() if v.get("egg")}
ORDER = list(SHELLS)
SECRET_SHELL = {"celestine": "starlight", "aurora": "starlight", "glitchling": "glitch", "mycelia": "spore"}

# base, lip shadow, name plate, utility button, utility shadow, page background
PALETTES = {
    "tide": ((143, 123, 196), (111, 90, 168), (111, 90, 168), (169, 150, 216), (125, 105, 182), (233, 228, 240)),
    "meadow": ((140, 198, 138), (106, 168, 104), (79, 138, 76), (180, 224, 176), (134, 191, 132), (230, 239, 224)),
    "starlight": ((59, 63, 143), (42, 45, 108), (38, 41, 97), (96, 102, 189), (62, 67, 148), (223, 225, 242)),
    "glitch": ((63, 181, 168), (44, 140, 130), (31, 111, 104), (127, 218, 207), (58, 157, 146), (222, 242, 239)),
    "spore": ((233, 217, 189), (205, 185, 148), (138, 90, 60), (246, 236, 217), (214, 194, 158), (239, 232, 220)),
    "patchwork": ((228, 178, 146), (196, 140, 110), (140, 82, 64), (246, 222, 202), (212, 176, 148), (245, 236, 228)),
    "heirloom": ((240, 228, 204), (212, 192, 152), (150, 112, 52), (250, 242, 224), (222, 202, 162), (246, 241, 231)),
    "familytree": ((176, 128, 88), (138, 96, 62), (92, 62, 38), (216, 178, 136), (170, 130, 90), (236, 228, 214)),
    "golden": ((232, 190, 82), (196, 150, 50), (146, 100, 18), (250, 224, 144), (212, 172, 72), (250, 244, 222)),
    "void": ((36, 28, 56), (20, 14, 34), (78, 58, 122), (138, 122, 186), (92, 80, 136), (222, 218, 232)),
    "chimera": ((122, 176, 168), (92, 138, 132), (66, 86, 98), (192, 222, 216), (130, 170, 164), (236, 236, 232)),
    "pastel": ((246, 204, 224), (226, 176, 200), (190, 116, 156), (252, 230, 240), (230, 192, 212), (250, 242, 246)),
    "static": ((98, 104, 118), (72, 76, 88), (46, 50, 60), (152, 158, 172), (112, 118, 130), (230, 232, 236)),
}


def unlocked(records):
    """Shell ids this player has unlocked, in display order. Everything comes from the records:
    species discovered, generations raised, and rare colourings found."""
    from .genetics import MUTATION_NAMES
    seen = set(getattr(records, "discovered", []) or [])
    gens = len(getattr(records, "lineage", []) or []) + 1
    rare = set(getattr(records, "rare", []) or [])
    out = []
    for sid in ORDER:
        sh = SHELLS[sid]
        if sh.get("gen"):
            ok = gens >= sh["gen"]
        elif sh.get("egg"):
            ok = f"{MUTATION_NAMES.get(sh['egg'], sh['egg'])} colouring" in rare
        else:
            ok = not sh["unlock"] or bool(seen & set(sh["unlock"]))
        if ok:
            out.append(sid)
    return out


def unlocked_by(species_id):
    """The shell (if any) that discovering this species unlocks."""
    for sid in ORDER:
        if species_id in SHELLS[sid]["unlock"]:
            return sid
    return None


def match_candidates(c):
    """What "Match my pet" would like, best first: its secret form, then a rare egg, then its line."""
    if c is None or c.stage == "egg":
        return ["classic"]
    out = []
    if c.species in SECRET_SHELL:
        out.append(SECRET_SHELL[c.species])
    if c.genome.get("mutation") in EGG_SHELL:          # a rare-egg pet wears its egg's shell
        out.append(EGG_SHELL[c.genome["mutation"]])
    out.append("tide" if c.genome.get("line") == "water" else "meadow")
    return out + ["classic"]


def match_for(c):
    """The shell that "Match my pet" picks for this creature (ignoring what's unlocked)."""
    return match_candidates(c)[0]


def current(prefs, records, c):
    """The shell to draw right now: the first one the player has actually unlocked."""
    have = unlocked(records)
    choice = prefs.get("shell", "match")
    wanted = match_candidates(c) if choice == "match" else [choice, "classic"]
    return next((sid for sid in wanted if sid in have), "classic")


def options(records):
    """What the Settings shell picker cycles through."""
    return ["match"] + unlocked(records)


def label(choice):
    return "Match my pet" if choice == "match" else SHELLS.get(choice, SHELLS["classic"])["name"]


def palette(sid, hue, dark=False):
    """base, lip, plate, util, util_lip, page. Classic follows the theme colour."""
    if sid in PALETTES:
        base, lip, plate, util, util_lip, page = PALETTES[sid]
    else:
        base, lip, plate = hsv(hue, 0.36, 0.78), hsv(hue, 0.45, 0.62), hsv(hue, 0.50, 0.52)
        util, util_lip, page = hsv(hue, 0.25, 0.88), hsv(hue, 0.36, 0.72), hsv(hue, 0.06, 0.94)
    if dark:
        dim = lambda col, k: tuple(int(v * k) for v in col)
        base, lip, plate, util, util_lip = (dim(base, 0.62), dim(lip, 0.55), dim(plate, 0.6),
                                            dim(util, 0.6), dim(util_lip, 0.5))
        page = (18, 16, 26)
    return {"base": base, "lip": lip, "plate": plate, "util": util, "util_lip": util_lip, "page": page}


# ---------------------------------------------------------------- decorations
TOP = [((40, 300), (18, 112)), ((640, 900), (18, 112))]
SIDE = [((8, 48), (140, 590)), ((892, 932), (140, 590))]
CORNER = [((14, 170), (600, 748)), ((770, 926), (600, 748))]
BOTTOM = [((180, 760), (728, 752))]


def _scatter(rng, n, regions):
    out = []
    for i in range(n):
        (x0, x1), (y0, y1) = regions[i % len(regions)]
        out.append((rng.randint(x0, x1), rng.randint(y0, y1)))
    return out


class _Pen:
    """Draws in design coordinates onto a surface of any size."""

    def __init__(self, surf):
        self.s = surf
        self.kx = surf.get_width() / DESIGN_W
        self.ky = surf.get_height() / DESIGN_H
        self.k = min(self.kx, self.ky)

    def p(self, x, y):
        return (int(x * self.kx), int(y * self.ky))

    def r(self, v):
        return max(1, int(round(v * self.k)))

    def circle(self, col, x, y, rad, width=0):
        pygame.draw.circle(self.s, col, self.p(x, y), self.r(rad), self.r(width) if width else 0)

    def ellipse(self, col, x, y, rx, ry, rot=0):
        if not rot:
            cx, cy = self.p(x, y)
            w, h = self.r(rx * 2), self.r(ry * 2)
            pygame.draw.ellipse(self.s, col, (cx - w // 2, cy - h // 2, w, h))
            return
        a = math.radians(rot)
        pts = [(x + rx * math.cos(t) * math.cos(a) - ry * math.sin(t) * math.sin(a),
                y + rx * math.cos(t) * math.sin(a) + ry * math.sin(t) * math.cos(a))
               for t in (i * math.pi / 10 for i in range(20))]
        self.poly(col, pts)

    def poly(self, col, pts):
        pygame.draw.polygon(self.s, col, [self.p(*q) for q in pts])

    def line(self, col, pts, width):
        pygame.draw.lines(self.s, col, False, [self.p(*q) for q in pts], self.r(width))

    def rect(self, col, x, y, w, h):
        x0, y0 = self.p(x, y)
        x1, y1 = self.p(x + w, y + h)
        pygame.draw.rect(self.s, col, (x0, y0, max(1, x1 - x0), max(1, y1 - y0)))

    def band(self, col, y, amp, step=47):
        pts = [(x, y - amp * math.sin(x / step * math.pi)) for x in range(0, DESIGN_W + 10, 10)]
        self.poly(col, pts + [(DESIGN_W, DESIGN_H), (0, DESIGN_H)])

    def crest(self, col, y, amp, width, step=47):
        self.line(col, [(x, y - amp * math.sin(x / step * math.pi)) for x in range(0, DESIGN_W + 10, 10)], width)

    def star(self, col, x, y, s):
        self.poly(col, [(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3),
                        (x, y + s), (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)])


def _tide(pen):
    pen.band((131, 112, 189), 610, 12, 60)
    pen.band((117, 97, 178), 668, 12, 60)
    pen.crest((179, 163, 226), 70, 8, 5)
    pen.crest((164, 147, 214), 104, 8, 4)
    for x0, h, flip in ((70, 170, 1), (108, 120, -1), (870, 160, -1), (832, 110, 1)):
        pts = [(x0 + flip * 12 * math.sin(i / 2.0), DESIGN_H - h * i / 12.0) for i in range(13)]
        pen.line((95, 133, 128), pts, 9)
    for x, y, s, col, flip in ((200, 712, 15, (242, 167, 181), 1), (745, 700, 13, (244, 213, 141), -1),
                               (160, 140, 10, (169, 212, 232), 1)):
        pen.ellipse(col, x, y, s, s * 0.6)
        tx = x - flip * s * 1.1
        pen.poly(col, [(tx, y), (tx - flip * s * 0.7, y - s * 0.55), (tx - flip * s * 0.7, y + s * 0.55)])
        pen.circle((43, 34, 64), x + flip * s * 0.45, y - s * 0.1, s * 0.14)
    for x, y, r in ((28, 520, 9), (40, 470, 6), (22, 420, 11), (36, 360, 5), (26, 300, 8), (42, 250, 5),
                    (912, 520, 8), (900, 455, 11), (918, 390, 6), (904, 330, 9), (916, 270, 5), (230, 40, 10),
                    (262, 22, 6), (700, 36, 9), (726, 18, 5), (150, 60, 7), (790, 62, 7), (320, 690, 7),
                    (620, 700, 8), (640, 672, 5)):
        pen.circle((164, 147, 217), x, y, r)
        pen.circle((217, 207, 245), x, y, r, max(2, r // 4))
        pen.circle((243, 238, 255), x - r * 0.35, y - r * 0.35, max(1.5, r * 0.25))
    for x, y, s in ((110, 32, 9), (830, 30, 10), (470, 744, 8), (30, 600, 7), (910, 600, 8), (560, 18, 6), (380, 20, 6)):
        pen.star((246, 231, 168), x, y, s)


def _meadow(pen):
    rng = random.Random(11)
    pen.band((124, 185, 122), 620, 12)
    pen.band((106, 168, 104), 676, 10)
    for x, y in _scatter(rng, 14, TOP + SIDE):
        s, rot = rng.randint(9, 15), rng.randint(-60, 60)
        pen.ellipse(rng.choice([(95, 154, 92), (111, 174, 106), (156, 207, 143)]), x, y, s, s * 0.45, rot)
    for x, y in _scatter(rng, 9, TOP + SIDE + CORNER):
        col, r = rng.choice([(242, 167, 181), (244, 213, 141), (255, 255, 255)]), rng.choice([5, 6, 7])
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            pen.circle(col, x + dx * r * 0.9, y + dy * r * 0.9, r)
        pen.circle((246, 231, 168), x, y, r * 0.7)
    for x, y in ((70, 744), (120, 730), (860, 742), (820, 732)):
        pen.line((79, 138, 76), [(x, y), (x, y - 34)], 5)
        pen.ellipse((95, 154, 92), x - 12, y - 36, 14, 6.3, -30)
        pen.ellipse((95, 154, 92), x + 12, y - 40, 14, 6.3, 30)
    for x in (190, 260, 640, 700):
        pen.poly((95, 154, 92), [(x, 760), (x + 6, 734), (x + 12, 760), (x + 18, 742), (x + 24, 760)])
    pen.ellipse((214, 54, 60), 150, 56, 9, 7)
    pen.circle((43, 34, 64), 146, 54, 2)
    pen.circle((43, 34, 64), 153, 58, 2)


def _starlight(pen):
    rng = random.Random(5)
    for x, y in _scatter(rng, 34, TOP + SIDE + CORNER + BOTTOM):
        pen.star(rng.choice([(246, 231, 168), (255, 255, 255), (201, 205, 247)]), x, y, rng.choice([4, 5, 7, 9]))
    for x, y in _scatter(rng, 60, TOP + SIDE + CORNER + BOTTOM):
        pen.circle((223, 227, 255), x, y, 1.6)
    pen.circle((246, 231, 168), 130, 80, 32)                 # crescent moon
    pen.circle(PALETTES["starlight"][0], 146, 70, 28)
    pen.line((154, 163, 232), [(760, 40), (800, 70), (830, 58), (870, 96)], 2)
    for x, y in ((760, 40), (800, 70), (830, 58), (870, 96)):
        pen.circle((255, 255, 255), x, y, 4)
    pen.line((154, 163, 232), [(40, 640), (90, 660), (70, 700), (120, 720)], 2)
    for x, y in ((40, 640), (90, 660), (70, 700), (120, 720)):
        pen.circle((255, 255, 255), x, y, 3.5)
    pen.circle((185, 138, 217), 860, 680, 22)
    pen.line((242, 167, 181), [(822 + i * 3.8, 680 + 9 * math.sin(i / 20 * math.pi)) for i in range(21)], 4)
    pen.line((246, 231, 168), [(560, 30), (640, 70)], 3)
    pen.star((255, 255, 255), 640, 70, 8)


def _glitch(pen):
    rng = random.Random(9)
    for y in range(6, DESIGN_H, 12):
        pen.rect((52, 160, 148), 0, y, DESIGN_W, 3)
    for x, y in _scatter(rng, 70, TOP + SIDE + CORNER + BOTTOM):
        pen.rect(rng.choice([(255, 111, 216), (127, 240, 255), (31, 111, 104), (246, 231, 168), (255, 255, 255)]),
                 x, y, rng.choice([8, 12, 16, 24, 32]), rng.choice([4, 6, 8, 12]))
    pen.rect((176, 136, 196), 0, 22, DESIGN_W, 10)       # glitch bands, kept clear of the name row
    pen.rect((126, 214, 214), 6, 30, DESIGN_W, 5)        # and the buttons
    pen.rect((110, 205, 210), 0, 742, DESIGN_W, 8)
    pen.rect((176, 136, 196), 0, 748, DESIGN_W, 5)


def _spore(pen):
    rng = random.Random(4)
    pen.band((220, 200, 166), 640, 10)
    pen.band((205, 182, 143), 700, 8)
    for x, y, s in ((80, 60, 22), (170, 90, 14), (780, 70, 20), (870, 46, 13), (30, 300, 12), (912, 360, 14),
                    (28, 470, 10), (910, 520, 11), (70, 700, 26), (130, 722, 15), (860, 700, 24), (800, 728, 14)):
        cap = rng.choice([(200, 100, 78), (184, 120, 74), (213, 138, 92)])
        pen.rect((251, 244, 230), x - s * 0.32, y, s * 0.64, s * 0.95)
        pen.poly(cap, [(x + s * math.cos(t), y + 3 - s * 0.8 * math.sin(t))
                       for t in (i * math.pi / 12 for i in range(13))])
        for dx, dy, r in ((-0.42, -0.3, 0.16), (0.3, -0.5, 0.13), (0.55, -0.1, 0.1)):
            pen.circle((251, 244, 230), x + s * dx, y + s * dy, s * r)
    for x, y in _scatter(rng, 40, TOP + SIDE + CORNER + BOTTOM):
        pen.circle((191, 164, 124), x, y, rng.choice([2, 2.5, 3]))


def _patchwork(pen):
    rng = random.Random(21)
    # deeper than the tabs' pastels, so the tabs still stand out against the quilt
    fabrics = [(206, 128, 102), (210, 166, 74), (104, 152, 190), (132, 172, 104), (180, 120, 168), (196, 146, 108)]
    size = 76
    for gy in range(0, DESIGN_H, size):
        for gx in range(0, DESIGN_W, size):
            pen.rect(rng.choice(fabrics), gx, gy, size, size)
            if rng.random() < 0.35:                         # a few patches have little prints
                for _ in range(3):
                    pen.circle((255, 255, 255), gx + rng.randint(12, size - 12), gy + rng.randint(12, size - 12), 3)
    stitch = (255, 246, 232)
    for gx in range(0, DESIGN_W + 1, size):                # running stitches along every seam
        for y in range(4, DESIGN_H, 14):
            pen.rect(stitch, gx - 1.5, y, 3, 7)
    for gy in range(0, DESIGN_H + 1, size):
        for x in range(4, DESIGN_W, 14):
            pen.rect(stitch, x, gy - 1.5, 7, 3)
    for x, y in ((110, 46), (836, 52), (44, 640), (896, 660)):   # sewn-on buttons
        pen.circle((140, 82, 64), x, y, 11)
        for dx, dy in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
            pen.circle((246, 222, 202), x + dx, y + dy, 1.6)


def _heirloom(pen):
    gold, deep = (204, 164, 82), (168, 126, 48)
    pen.line(gold, [(40, 30), (900, 30)], 3)
    pen.line(gold, [(40, 734), (900, 734)], 3)
    for x in range(60, 900, 34):                          # a string of pearls along the top
        pen.circle((252, 248, 240), x, 46, 6)
        pen.circle((226, 214, 196), x + 1.5, 47.5, 6, 1.5)
    for cx, cy, fx, fy in ((70, 110, 1, 1), (870, 110, -1, 1), (70, 650, 1, -1), (870, 650, -1, -1)):
        for r, w in ((40, 5), (26, 4), (14, 3)):          # corner flourishes: nested curls
            pts = [(cx + fx * r * math.cos(t), cy + fy * r * math.sin(t))
                   for t in (i * math.pi / 16 for i in range(0, 25))]
            pen.line(gold if r != 26 else deep, pts, w)
        pen.circle(gold, cx, cy, 5)
    for x, y in ((470, 14), (24, 380), (916, 380), (470, 748)):   # little diamonds
        pen.poly(deep, [(x, y - 9), (x + 7, y), (x, y + 9), (x - 7, y)])
    for x in range(200, 760, 40):
        pen.circle(gold, x, 718, 3)


def _familytree(pen):
    rng = random.Random(8)
    for y in range(20, DESIGN_H, 38):                    # wood grain
        pts = [(x, y + 6 * math.sin(x / 70.0 + y)) for x in range(0, DESIGN_W + 20, 20)]
        pen.line((162, 116, 78), pts, 3)
    bark = (110, 74, 46)
    for side in (1, -1):                                 # two trees climbing the sides
        x0 = 40 if side == 1 else 900
        trunk = [(x0 + side * 10 * math.sin(i / 3.0), 760 - i * 46) for i in range(15)]
        pen.line(bark, trunk, 14)
        for i in range(2, 14, 2):
            bx, by = trunk[i]
            tip = (bx + side * rng.randint(40, 70), by - rng.randint(20, 40))
            pen.line(bark, [(bx, by), tip], 6)
            for k in range(3):
                lx, ly = tip[0] + rng.randint(-14, 14), tip[1] + rng.randint(-12, 12)
                pen.ellipse(rng.choice([(96, 158, 84), (122, 180, 98), (150, 198, 112)]), lx, ly, 10, 6,
                            rng.randint(-50, 50))
            if rng.random() < 0.5:                       # little heart-shaped fruit
                hx, hy = tip[0] + side * 8, tip[1] + 14
                pen.circle((214, 84, 96), hx - 3, hy, 4.5)
                pen.circle((214, 84, 96), hx + 3, hy, 4.5)
                pen.poly((214, 84, 96), [(hx - 7.5, hy + 1), (hx + 7.5, hy + 1), (hx, hy + 9)])
    pen.band((150, 104, 66), 712, 6)


def _golden(pen):
    rng = random.Random(13)
    for x0 in (-200, 60, 420, 700):                       # diagonal shine
        pen.poly((244, 210, 116), [(x0, 0), (x0 + 70, 0), (x0 + 70 + 380, DESIGN_H), (x0 + 380, DESIGN_H)])
    for x, y in _scatter(rng, 26, TOP + SIDE + CORNER + BOTTOM):
        pen.star(rng.choice([(255, 255, 255), (255, 244, 196)]), x, y, rng.choice([5, 7, 10, 13]))
    for x, y, col in ((130, 70, (226, 90, 110)), (810, 74, (90, 170, 220)), (60, 690, (120, 200, 140)),
                      (880, 700, (180, 120, 220))):     # set gems
        pen.circle((176, 132, 40), x, y, 13)
        pen.circle(col, x, y, 9)
        pen.circle((255, 255, 255), x - 3, y - 3, 2.5)


def _void(pen):
    rng = random.Random(31)
    base = PALETTES["void"][0]
    for x, y, r, col in ((120, 90, 120, (70, 46, 112)), (840, 640, 140, (44, 64, 116)), (880, 80, 80, (86, 46, 106)),
                         (60, 620, 90, (58, 40, 98))):
        for k in range(6):                                # soft nebula clouds: layered, fading outward
            f = (k + 1) / 6.0
            mix = tuple(int(b + (c - b) * f) for b, c in zip(base, col))
            pen.circle(mix, x, y, r * (1.0 - k * 0.14))
    for arm in range(3):                                  # a slow spiral of stars
        for i in range(60):
            t = i / 6.0 + arm * 2.1
            r = 20 + i * 7
            x, y = 470 + r * math.cos(t), 380 + r * 0.8 * math.sin(t)
            pen.circle(rng.choice([(186, 160, 255), (120, 220, 230), (255, 255, 255)]), x, y,
                       rng.choice([1.4, 2, 2.6]))
    for x, y in _scatter(rng, 30, TOP + SIDE + CORNER + BOTTOM):
        pen.star((230, 224, 255), x, y, rng.choice([3, 4, 6]))
    pen.circle((14, 8, 24), 840, 92, 26)                  # a little black hole
    pen.circle((186, 160, 255), 840, 92, 30, 3)


def _chimera(pen):
    other = (232, 168, 128)
    pen.rect(other, DESIGN_W / 2, 0, DESIGN_W / 2, DESIGN_H)
    for y in range(-40, DESIGN_H, 44):                    # stripes on one half...
        pen.poly((98, 150, 142), [(0, y), (DESIGN_W / 2, y + 150), (DESIGN_W / 2, y + 168), (0, y + 18)])
    rng = random.Random(17)
    for _ in range(46):                                   # ...spots on the other
        x, y = rng.randint(486, 930), rng.randint(10, 750)
        pen.circle((204, 128, 92), x, y, rng.choice([6, 9, 12]))
    for y in range(0, DESIGN_H, 24):                      # stitched together down the middle
        pen.line((250, 240, 226), [(DESIGN_W / 2 - 8, y), (DESIGN_W / 2 + 8, y + 12)], 4)
        pen.line((250, 240, 226), [(DESIGN_W / 2 + 8, y + 12), (DESIGN_W / 2 - 8, y + 24)], 4)


def _pastel(pen):
    rng = random.Random(5)
    cols = [(196, 232, 214), (250, 236, 170), (190, 220, 246), (220, 204, 246), (255, 255, 255)]
    for gy in range(18, DESIGN_H, 54):                    # polka dots
        for gx in range(18 + (27 if (gy // 54) % 2 else 0), DESIGN_W, 54):
            pen.circle(rng.choice(cols), gx, gy, rng.choice([8, 10, 12]))
    for x, y in ((140, 60), (800, 70), (60, 660), (880, 650), (470, 740)):     # little hearts
        pen.circle((232, 128, 168), x - 6, y, 8)
        pen.circle((232, 128, 168), x + 6, y, 8)
        pen.poly((232, 128, 168), [(x - 13.5, y + 2), (x + 13.5, y + 2), (x, y + 17)])


def _static(pen):
    rng = random.Random(3)
    for _ in range(900):                                  # snow
        x, y = rng.randint(0, DESIGN_W), rng.randint(0, DESIGN_H)
        g = rng.randint(70, 220)
        pen.rect((g, g, g + 8), x, y, rng.choice([3, 4, 6]), 3)
    for y in range(4, DESIGN_H, 9):
        pen.rect((80, 86, 98), 0, y, DESIGN_W, 2)
    for y, col, dx in ((26, (220, 80, 90), 0), (30, (90, 210, 120), 6), (34, (90, 130, 230), 12),
                       (726, (220, 80, 90), 12), (730, (90, 210, 120), 6), (734, (90, 130, 230), 0)):
        pen.rect(col, dx, y, DESIGN_W, 3)                 # RGB fringes, top and bottom


DECOR = {"tide": _tide, "meadow": _meadow, "starlight": _starlight, "glitch": _glitch, "spore": _spore,
         "patchwork": _patchwork, "heirloom": _heirloom, "familytree": _familytree, "golden": _golden,
         "void": _void, "chimera": _chimera, "pastel": _pastel, "static": _static}


def shell_surface(sid, size, radii, hue, dark=False):
    """The whole shell (body, lip and decoration) as one surface, clipped to its shape."""
    w, h = size
    top, bottom = radii
    pal = palette(sid, hue, dark)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    shape = dict(border_top_left_radius=top, border_top_right_radius=top,
                 border_bottom_left_radius=bottom, border_bottom_right_radius=bottom)
    lip = max(6, h // 54)
    pygame.draw.rect(surf, pal["lip"], (0, 0, w, h), **shape)
    pygame.draw.rect(surf, pal["base"], (0, 0, w, h - lip), **shape)
    if sid in DECOR:
        deco = pygame.Surface((w, h), pygame.SRCALPHA)
        DECOR[sid](_Pen(deco))
        if dark:
            deco.fill((150, 150, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h - lip), **shape)
        deco.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(deco, (0, 0))
    return surf
