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
}
ORDER = list(SHELLS)
SECRET_SHELL = {"celestine": "starlight", "aurora": "starlight", "glitchling": "glitch", "mycelia": "spore"}

# base, lip shadow, name plate, utility button, utility shadow, page background
PALETTES = {
    "tide": ((143, 123, 196), (111, 90, 168), (111, 90, 168), (169, 150, 216), (125, 105, 182), (233, 228, 240)),
    "meadow": ((140, 198, 138), (106, 168, 104), (79, 138, 76), (180, 224, 176), (134, 191, 132), (230, 239, 224)),
    "starlight": ((59, 63, 143), (42, 45, 108), (38, 41, 97), (96, 102, 189), (62, 67, 148), (223, 225, 242)),
    "glitch": ((63, 181, 168), (44, 140, 130), (31, 111, 104), (127, 218, 207), (58, 157, 146), (222, 242, 239)),
    "spore": ((233, 217, 189), (205, 185, 148), (138, 90, 60), (246, 236, 217), (214, 194, 158), (239, 232, 220)),
}


def unlocked(records):
    """Shell ids this player has unlocked, in display order."""
    seen = set(getattr(records, "discovered", []) or [])
    return [sid for sid in ORDER if not SHELLS[sid]["unlock"] or seen & set(SHELLS[sid]["unlock"])]


def unlocked_by(species_id):
    """The shell (if any) that discovering this species unlocks."""
    for sid in ORDER:
        if species_id in SHELLS[sid]["unlock"]:
            return sid
    return None


def match_for(c):
    """The shell that "Match my pet" picks for this creature."""
    if c is None or c.stage == "egg":
        return "classic"
    if c.species in SECRET_SHELL:
        return SECRET_SHELL[c.species]
    return "tide" if c.genome.get("line") == "water" else "meadow"


def current(prefs, records, c):
    """The shell to draw right now."""
    have = unlocked(records)
    choice = prefs.get("shell", "match")
    sid = match_for(c) if choice == "match" else choice
    return sid if sid in have else "classic"


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


DECOR = {"tide": _tide, "meadow": _meadow, "starlight": _starlight, "glitch": _glitch, "spore": _spore}


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
