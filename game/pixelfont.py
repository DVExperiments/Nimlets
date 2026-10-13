"""An original pixel font, drawn in code like everything else in Nimlets (v1.9).

Glyphs are designed on a small grid: capitals and digits are 7 rows tall,
lower-case letters have a 5-row x-height, and g, j, p, q and y drop two rows
below the baseline. Most letters are 4 pixels wide (M, N, T, V, W, X and Y
are 5) so text doesn't run much wider than the system font it replaces.

PixelFont mimics the parts of pygame.font.Font the game uses (size, render,
get_height, get_linesize), so the UI can swap fonts without other changes.
Text is drawn at a whole-number scale so every pixel stays crisp.
"""
import pygame

ROWS = 9           # 7 above the baseline, 2 below
PAD_TOP = 1        # a pixel row of breathing room above capitals

_G = {
    "A": ".##.|#..#|#..#|####|#..#|#..#|#..#", "B": "###.|#..#|#..#|###.|#..#|#..#|###.",
    "C": ".###|#...|#...|#...|#...|#...|.###", "D": "###.|#..#|#..#|#..#|#..#|#..#|###.",
    "E": "####|#...|#...|###.|#...|#...|####", "F": "####|#...|#...|###.|#...|#...|#...",
    "G": ".###|#...|#...|#.##|#..#|#..#|.###", "H": "#..#|#..#|#..#|####|#..#|#..#|#..#",
    "I": "###|.#.|.#.|.#.|.#.|.#.|###", "J": "..##|...#|...#|...#|...#|#..#|.##.",
    "K": "#..#|#..#|#.#.|##..|#.#.|#..#|#..#", "L": "#...|#...|#...|#...|#...|#...|####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|##..#|#.#.#|#.#.#|#..##|#...#|#...#",
    "O": ".##.|#..#|#..#|#..#|#..#|#..#|.##.", "P": "###.|#..#|#..#|###.|#...|#...|#...",
    "Q": ".##.|#..#|#..#|#..#|#..#|#.#.|.#.#", "R": "###.|#..#|#..#|###.|#.#.|#..#|#..#",
    "S": ".###|#...|#...|.##.|...#|...#|###.", "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#..#|#..#|#..#|#..#|#..#|#..#|.##.", "V": "#...#|#...#|#...#|.#.#.|.#.#.|..#..|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "####|...#|..#.|.#..|#...|#...|####",
    "a": "....|....|.###|...#|.###|#..#|.###", "b": "#...|#...|###.|#..#|#..#|#..#|###.",
    "c": "...|...|.##|#..|#..|#..|.##", "d": "...#|...#|.###|#..#|#..#|#..#|.###",
    "e": "....|....|.##.|#..#|####|#...|.###", "f": "..#|.#.|###|.#.|.#.|.#.|.#.",
    "g": "....|....|.###|#..#|#..#|#..#|.###|...#|.##.", "h": "#...|#...|###.|#..#|#..#|#..#|#..#",
    "i": "#|.|#|#|#|#|#", "j": "..#|...|.##|..#|..#|..#|..#|..#|##.",
    "k": "#...|#...|#..#|#.#.|##..|#.#.|#..#", "l": "#.|#.|#.|#.|#.|#.|.#",
    "m": ".....|.....|##.#.|#.#.#|#.#.#|#.#.#|#.#.#", "n": "....|....|###.|#..#|#..#|#..#|#..#",
    "o": "....|....|.##.|#..#|#..#|#..#|.##.", "p": "....|....|###.|#..#|#..#|#..#|###.|#...|#...",
    "q": "....|....|.###|#..#|#..#|#..#|.###|...#|...#", "r": "...|...|#.#|##.|#..|#..|#..",
    "s": "...|...|.##|#..|.#.|..#|##.", "t": ".#.|.#.|###|.#.|.#.|.#.|..#",
    "u": "....|....|#..#|#..#|#..#|#..#|.###", "v": "...|...|#.#|#.#|#.#|#.#|.#.",
    "w": ".....|.....|#...#|#...#|#.#.#|#.#.#|.#.#.", "x": "...|...|#.#|#.#|.#.|#.#|#.#",
    "y": "....|....|#..#|#..#|#..#|#..#|.###|...#|.##.", "z": "...|...|###|..#|.#.|#..|###",
    "0": ".##.|#..#|#.##|##.#|#..#|#..#|.##.", "1": ".#.|##.|.#.|.#.|.#.|.#.|###",
    "2": ".##.|#..#|...#|..#.|.#..|#...|####", "3": "###.|...#|...#|.##.|...#|...#|###.",
    "4": "..#.|.##.|#.#.|#.#.|####|..#.|..#.", "5": "####|#...|###.|...#|...#|#..#|.##.",
    "6": ".##.|#...|#...|###.|#..#|#..#|.##.", "7": "####|...#|..#.|..#.|.#..|.#..|.#..",
    "8": ".##.|#..#|#..#|.##.|#..#|#..#|.##.", "9": ".##.|#..#|#..#|.###|...#|...#|.##.",
    " ": "..|..|..|..|..|..|..", ".": ".|.|.|.|.|.|#", ",": "..|..|..|..|..|.#|.#|#.",
    "!": "#|#|#|#|#|.|#", "?": ".##.|#..#|...#|..#.|.#..|....|.#..", ":": ".|.|#|.|.|#|.",
    ";": "..|..|.#|..|..|.#|.#|#.", "'": "#|#|.|.|.|.|.", '"': "#.#|#.#|...|...|...|...|...",
    "-": "...|...|...|###|...|...|...", "+": "...|...|.#.|###|.#.|...|...",
    "=": "...|...|###|...|###|...|...", "(": ".#|#.|#.|#.|#.|#.|.#", ")": "#.|.#|.#|.#|.#|.#|#.",
    "[": "##|#.|#.|#.|#.|#.|##", "]": "##|.#|.#|.#|.#|.#|##", "/": "...#|...#|..#.|.#..|.#..|#...|#...",
    "%": "#..#|...#|..#.|.#..|.#..|#...|#..#", "&": ".#..|#.#.|#.#.|.#..|#.##|#..#|.##.",
    "#": ".#.#.|#####|.#.#.|.#.#.|#####|.#.#.|.....", "*": "...|#.#|.#.|#.#|...|...|...",
    "<": "..#|.#.|#..|.#.|..#|...|...", ">": "#..|.#.|..#|.#.|#..|...|...",
    "_": "....|....|....|....|....|....|....|####", "|": "#|#|#|#|#|#|#",
    "~": "....|....|.#.#|#.#.|....|....|....", "^": ".#.|#.#|...|...|...|...|...",
    "@": ".##.|#..#|#.##|#.##|#.#.|#...|.###", "$": ".#.|.##|#..|.#.|..#|##.|.#.",
    "\u00b7": ".|.|.|#|.|.|.", "\u00d7": "...|...|#.#|.#.|#.#|...|...",
    "\u00b0": ".#.|#.#|.#.|...|...|...|...",
}
# characters we can stand in for rather than draw
_SUB = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\u2014": "-", "\u2013": "-",
        "\u2026": "...", "{": "(", "}": ")", "`": "'", "\\": "/", "\u2190": "<", "\u2192": ">"}


def _parse(spec):
    rows = spec.split("|")
    rows += ["." * len(rows[0])] * (ROWS - len(rows))
    return [[ch == "#" for ch in row] for row in rows]


GLYPHS = {ch: _parse(spec) for ch, spec in _G.items()}


def normalise(text):
    out = []
    for ch in text:
        if ch in GLYPHS:
            out.append(ch)
        else:
            sub = _SUB.get(ch)
            if sub is None and ch.isalpha():
                sub = ch.upper() if ch.upper() in GLYPHS else (ch.lower() if ch.lower() in GLYPHS else "?")
            out.append(sub or "?")
    return "".join(out)


def scale_for(size):
    """Whole-number scale for a requested point size (crisp pixels only)."""
    return max(1, int(round(size / 8.0)))


class PixelFont:
    def __init__(self, size, bold=False):
        self.scale = scale_for(size)
        self.bold = bold and self.scale >= 2      # at 1x a bold smear just fills the letters in
        self._cache = {}

    def get_height(self):
        return (ROWS + PAD_TOP) * self.scale

    def get_linesize(self):
        return (ROWS + PAD_TOP + 1) * self.scale

    def _width(self, text):
        s = self.scale
        w = sum((len(GLYPHS[ch][0]) + 1) * s for ch in text)
        return max(0, w - s) + (1 if self.bold and text else 0)

    def size(self, text):
        return (self._width(normalise(text)), self.get_height())

    def render(self, text, antialias=True, color=(0, 0, 0), background=None):
        text = normalise(text)
        key = (text, tuple(color), tuple(background) if background else None)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        s = self.scale
        w, h = max(1, self._width(text)), self.get_height()
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        if background:
            surf.fill(background)
        col = tuple(color)[:3] + ((tuple(color)[3],) if len(tuple(color)) > 3 else (255,))
        x = 0
        top = PAD_TOP * s
        for ch in text:
            g = GLYPHS[ch]
            for ry, row in enumerate(g):
                for rx, on in enumerate(row):
                    if on:
                        surf.fill(col, (x + rx * s, top + ry * s, s + (1 if self.bold else 0), s))
            x += (len(g[0]) + 1) * s
        if len(self._cache) > 400:
            self._cache.clear()
        self._cache[key] = surf
        return surf
