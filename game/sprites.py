"""Procedural pixel-art creatures.

Each species is described in config/species.json by a body shape and a
handful of features (ears, feet, arms, tail, wings, markings, eyes). The
builder paints these onto a 32x32 grid of palette keys, adds an automatic
dark outline, and converts the result to a pygame Surface. Poses (eyes,
mouth, squash, feet, arms...) give the frames for animation.
"""
import colorsys

import pygame

GRID = 32


def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, max(0.0, min(1.0, s)),
                                  max(0.0, min(1.0, v)))
    return (int(r * 255), int(g * 255), int(b * 255))


FIXED = {
    "eye": (34, 28, 46), "white": (255, 255, 255), "cheek": (255, 138, 160),
    "mouth": (110, 36, 56), "tongue": (238, 104, 120), "gold": (255, 214, 90),
    "leaf": (112, 186, 92), "leafd": (64, 132, 70), "bone": (246, 236, 212),
    "tear": (120, 186, 255), "heart": (232, 62, 96),
}


def make_palette(sp, genome, elder=False):
    pd = sp.get("palette", {})
    if pd.get("fixed_hue") is not None:
        hue = pd["fixed_hue"]
    else:
        hue = genome.get("hue", 200) + pd.get("hue_shift", 0)
    sat = pd.get("fixed_sat", genome.get("sat", 0.55) * pd.get("sat", 1.0))
    val = pd.get("val", 0.93)
    mut = genome.get("mutation")
    if mut == "pastel":
        sat *= 0.45
        val = min(1.0, val + 0.06)
    elif mut == "midnight":
        val *= 0.55
        sat = min(1.0, sat * 1.1)
    if elder:
        sat *= 0.45
        val *= 0.97
    mh = genome.get("marking_hue", hue + 180)
    if mut == "chimera" and genome.get("chimera"):
        mh = genome["chimera"].get("hue2", mh)
    pal = dict(FIXED)
    pal.update({
        "base": hsv(hue, sat, val),
        "shade": hsv(hue + 8, sat * 1.15 + 0.05, val * 0.74),
        "light": hsv(hue - 6, sat * 0.42, min(1.0, val * 1.1)),
        "belly": hsv(hue, sat * 0.22, min(1.0, val * 1.06)),
        "outline": hsv(hue + 12, min(1.0, sat * 0.8 + 0.25), 0.09 if mut == "midnight" else 0.2),
        "mark": hsv(mh, 0.5, 0.45 if mut == "midnight" else 0.68),
        "accent": hsv(pd.get("accent_hue", hue + 40), 0.6, 0.97),
    })
    if mut == "midnight":
        pal["eye"] = (250, 236, 150)
    if mut == "shiny":
        pal["light"] = (255, 240, 170)
    return pal


class Canvas:
    def __init__(self):
        self.px = [[None] * GRID for _ in range(GRID)]

    def set(self, x, y, key):
        if 0 <= x < GRID and 0 <= y < GRID:
            self.px[y][x] = key

    def set_empty(self, x, y, key):
        if 0 <= x < GRID and 0 <= y < GRID and self.px[y][x] is None:
            self.px[y][x] = key

    def get(self, x, y):
        if 0 <= x < GRID and 0 <= y < GRID:
            return self.px[y][x]
        return None

    def sym(self, x, y, key):
        self.set(x, y, key)
        self.set(GRID - 1 - x, y, key)


def draw_body(cv, cx, cy, rx, ry, p, taper):
    cells = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        ty = (y + 0.5 - cy) / ry
        if abs(ty) > 1:
            continue
        rxy = rx * (1 + taper * ty)
        if rxy <= 0.3:
            continue
        for x in range(int(cx - rxy) - 2, int(cx + rxy) + 3):
            tx = (x + 0.5 - cx) / rxy
            if abs(tx) ** p + abs(ty) ** p <= 1.0:
                if (tx + 0.4) ** 2 + (ty + 0.45) ** 2 < 0.07:
                    key = "light"
                elif tx * 0.6 + ty > 0.78 or ty > 0.8:
                    key = "shade"
                else:
                    key = "base"
                cv.set(x, y, key)
                cells.add((x, y))
    return cells


def _extents(cells):
    top, bottom, left, right = {}, {}, {}, {}
    for x, y in cells:
        top[x] = min(top.get(x, 99), y)
        bottom[x] = max(bottom.get(x, -1), y)
        left[y] = min(left.get(y, 99), x)
        right[y] = max(right.get(y, -1), x)
    return top, bottom, left, right


def _outline(cv):
    filled = [[cv.px[y][x] is not None for x in range(GRID)] for y in range(GRID)]
    for y in range(GRID):
        for x in range(GRID):
            if filled[y][x]:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < GRID and 0 <= ny < GRID and filled[ny][nx]:
                    cv.px[y][x] = "outline"
                    break


MOUTHS = {
    "smile": [(14, 0, "mouth"), (15, 1, "mouth"), (16, 1, "mouth"), (17, 0, "mouth")],
    "flat": [(15, 0, "mouth"), (16, 0, "mouth")],
    "open": [(15, 0, "mouth"), (16, 0, "mouth"), (15, 1, "tongue"), (16, 1, "tongue")],
    "big": [(14, 0, "mouth"), (15, 0, "mouth"), (16, 0, "mouth"), (17, 0, "mouth"),
            (15, 1, "tongue"), (16, 1, "tongue")],
    "frown": [(15, 0, "mouth"), (16, 0, "mouth"), (14, 1, "mouth"), (17, 1, "mouth")],
    "o": [(15, 0, "mouth"), (16, 0, "mouth"), (15, 1, "mouth"), (16, 1, "mouth")],
    "tongue": [(14, 0, "mouth"), (15, 0, "mouth"), (16, 0, "mouth"), (17, 0, "mouth"),
               (16, 1, "tongue"), (16, 2, "tongue"), (17, 1, "tongue")],
    "wobbly": [(13, 1, "mouth"), (14, 0, "mouth"), (15, 1, "mouth"), (16, 0, "mouth"),
               (17, 1, "mouth"), (18, 0, "mouth")],
}

GAZE = {"": (0, 0), "l": (-1, 0), "r": (1, 0), "u": (0, -1), "d": (0, 1),
        "ul": (-1, -1), "ur": (1, -1)}


def _shift_row(row, n):
    if n > 0:
        return [None] * n + row[:-n]
    if n < 0:
        return row[-n:] + [None] * (-n)
    return row


def build_creature(sp, pose, genome_marking="none", overrides=None):
    f = dict(sp.get("features", {}))
    if overrides:
        f.update(overrides)
    b = sp.get("body", {})
    rx, ry = b.get("rx", 8.0), b.get("ry", 8.0)
    sq = pose.get("squash", 0)
    if sq > 0:
        rx, ry = rx + 0.8, ry - 0.8
    elif sq < 0:
        rx, ry = rx - 0.6, ry + 0.8
    cx, cy = 16.0, 29.5 - ry
    cv = Canvas()
    cells = draw_body(cv, cx, cy, rx, ry, b.get("p", 2.0), b.get("taper", 0.0))
    top, bottom, left, right = _extents(cells)
    min_top = min(top.values())

    def top_at(x):
        return top.get(x, min_top)

    def fill_down(x, y):
        """Connect a feature pixel down to the body."""
        for yy in range(y + 1, y + 4):
            if cv.get(x, yy) is not None:
                break
            cv.set(x, yy, "base")

    # ---- belly & markings -------------------------------------------------
    if f.get("belly"):
        bcy = cy + ry * 0.35
        for x, y in cells:
            ex = (x + 0.5 - cx) / (rx * 0.58)
            ey_ = (y + 0.5 - bcy) / (ry * 0.5)
            if ex * ex + ey_ * ey_ <= 1:
                cv.set(x, y, "belly")

    es = f.get("eye_size", 2)
    w = {1: 1, 2: 2, 3: 3}.get(es, 2)
    ey = int(round(cy - ry * 0.12))
    dx = max(2, int(round(rx * 0.42)))
    a = 16 - dx - 1 - (1 if w == 3 else 0)       # left eye first column
    bcol = GRID - a - w                          # right eye first column
    my = ey + 2 + (1 if w >= 2 else 0)           # mouth row

    marking = f.get("marking") or genome_marking or "none"
    body_keys = ("base", "shade", "light")

    def mark(x, y, key="mark"):
        if (x, y) in cells and cv.get(x, y) in body_keys:
            cv.set(x, y, key)

    if marking == "spots":
        for fx, fy in ((-0.55, -0.55), (0.35, -0.75), (0.62, -0.05), (-0.72, 0.2), (0.15, -0.35)):
            x, y = int(cx + fx * rx), int(cy + fy * ry)
            mark(x, y)
            mark(x + 1, y)
    elif marking == "stripes":
        for col, n in ((15, 3), (16, 3), (12, 2), (19, 2)):
            tt = top_at(col)
            for k in range(0, n):
                mark(col, tt + k)
    elif marking == "mask":
        for x, y in cells:
            if ey - 2 <= y <= ey + 1 and abs(x + 0.5 - cx) <= rx * 0.85:
                mark(x, y)

    # ---- ears / head features ---------------------------------------------
    ears = f.get("ears", "none")
    if ears == "cat":
        col = 16 - int(round(rx * 0.5)) - 1
        t = top_at(col)
        for ox, oy in ((-1, 1), (0, 1), (1, 1), (-1, 2), (0, 2), (-1, 3)):
            cv.sym(col + ox, t - oy, "base")
            fill_down(col + ox, t - oy)
            fill_down(GRID - 1 - (col + ox), t - oy)
        cv.sym(col, t - 1, "cheek")
    elif ears == "bunny":
        col = 16 - int(round(rx * 0.35)) - 2
        t = min(top_at(col), top_at(col + 1))
        height = 6
        for k in range(1, height + 1):
            cv.sym(col, t - k, "base")
            cv.sym(col + 1, t - k, "cheek" if 2 <= k <= height - 1 else "base")
        for x in (col, col + 1):
            fill_down(x, t - 1)
            fill_down(GRID - 1 - x, t - 1)
    elif ears == "round":
        col = 16 - int(round(rx * 0.62)) - 1
        t = top_at(col)
        for ox, oy in ((-1, 1), (0, 1), (1, 1), (-1, 2), (0, 2)):
            cv.sym(col + ox, t - oy, "base")
            fill_down(col + ox, t - oy)
            fill_down(GRID - 1 - (col + ox), t - oy)
        cv.sym(col, t - 1, "shade")
    elif ears in ("antenna", "star"):
        t = top_at(15)
        cv.sym(15, t - 1, "shade")
        cv.sym(15, t - 2, "shade")
        if ears == "star":
            for x, y in ((15, t - 7), (14, t - 6), (15, t - 6), (12, t - 5), (13, t - 5),
                         (14, t - 5), (15, t - 5), (14, t - 4), (15, t - 4), (13, t - 3)):
                cv.sym(x, y, "gold")
        else:
            for x, y in ((15, t - 5), (14, t - 4), (15, t - 4), (14, t - 3), (15, t - 3)):
                cv.sym(x, y, "accent")
    elif ears == "horns":
        col = 16 - int(round(rx * 0.45)) - 1
        t = top_at(col)
        for x, y in ((col, t - 1), (col - 1, t - 1), (col - 1, t - 2), (col - 2, t - 3)):
            cv.sym(x, y, "bone")
        fill_down(col - 1, t - 1)
        fill_down(GRID - 1 - (col - 1), t - 1)
    elif ears == "owl":
        col = 16 - int(round(rx * 0.6)) - 1
        t = top_at(col)
        for x, y in ((col, t - 1), (col - 1, t - 1), (col - 1, t - 2), (col - 2, t - 3), (col + 1, t - 1)):
            cv.sym(x, y, "shade")
        fill_down(col - 1, t - 1)
        fill_down(GRID - 1 - (col - 1), t - 1)
    elif ears == "crest":
        for d, hgt in ((0, 3), (3, 2), (6, 2)):
            col = 15 - d
            if col not in top:
                continue
            t = top_at(col)
            for k in range(1, hgt + 1):
                cv.sym(col, t - k, "accent")
    elif ears == "sprout":
        t = top_at(16)
        for x, y in ((16, t - 1), (16, t - 2)):
            cv.set(x, y, "leafd")
        for x, y in ((14, t - 3), (15, t - 3), (15, t - 2), (17, t - 4), (18, t - 4),
                     (17, t - 3), (19, t - 5), (13, t - 4)):
            cv.set(x, y, "leaf")
    elif ears == "fin":                       # a dorsal fin
        t = top_at(16)
        for x, y in ((15, t - 1), (16, t - 1), (17, t - 1), (14, t - 1), (15, t - 2), (16, t - 2),
                     (17, t - 2), (16, t - 3), (17, t - 3), (17, t - 4)):
            cv.set(x, y, "accent")
    elif ears == "antlers":
        col = 16 - int(round(rx * 0.4)) - 1
        t = top_at(col)
        for x, y in ((col, t - 1), (col, t - 2), (col, t - 3), (col - 1, t - 3), (col - 2, t - 4),
                     (col + 1, t - 4), (col, t - 4), (col - 2, t - 5), (col + 1, t - 5)):
            cv.sym(x, y, "bone")
    elif ears == "lop":                       # long droopy ears
        col = 16 - int(round(rx * 0.45)) - 1
        t = top_at(col)
        for x, y in ((col, t - 1), (col - 1, t - 1), (col - 2, t), (col - 3, t + 1)):
            cv.sym(x, y, "base")
        lx = left.get(t + 2, 8)
        for k in range(0, 7):
            cv.sym(min(lx, col - 3) - 1, t + 1 + k, "shade")
            if 1 <= k <= 5:
                cv.sym(min(lx, col - 3) - 2, t + 1 + k, "cheek" if 2 <= k <= 4 else "shade")
    elif ears == "horn1":                     # a single spiral horn
        t = top_at(16)
        for x, y in ((15, t - 1), (16, t - 1), (16, t - 2), (15, t - 2), (15, t - 3), (16, t - 4),
                     (16, t - 5), (16, t - 6)):
            cv.set(x, y, "gold")
    elif ears == "flower":
        t = top_at(19)
        cv.set(19, t - 1, "leafd")
        cv.set(20, t - 2, "leaf")
        cv.set(19, t - 2, "leafd")
        for x, y in ((19, t - 4), (18, t - 4), (20, t - 4), (19, t - 3), (19, t - 5)):
            cv.set(x, y, "cheek")
        cv.set(19, t - 4, "gold")
    elif ears == "tuft":
        t = top_at(16)
        for x, y in ((16, t - 1), (17, t - 2), (16, t - 3), (15, t - 1)):
            cv.set(x, y, "shade")

    # ---- mushroom cap (drawn over the top of the head) ---------------------
    if f.get("cap"):
        cyc = min_top + 1.5
        for y in range(min_top - 4, min_top + 5):
            for x in range(GRID):
                ex = (x + 0.5 - cx) / (rx * 1.3)
                ey2 = (y + 0.5 - cyc) / 4.0
                if ex * ex + ey2 * ey2 <= 1.0 and y <= cyc + 1:
                    cv.set(x, y, "accent")
        for dx, dy in ((-4, -1), (3, -2), (0, 0), (5, 1), (-6, 1)):
            cv.set(16 + dx, int(cyc) + dy, "white")

    # ---- feet -------------------------------------------------------------
    if f.get("feet", "stub") == "stub":
        fp = pose.get("feet", "both")
        if fp != "tuck":
            d = int(round(rx * 0.5))
            fw = 2 if rx < 8 else 3
            lc = 16 - d - fw + 1
            for side in ("left", "right"):
                cols = range(lc, lc + fw) if side == "left" else range(GRID - lc - fw, GRID - lc)
                lifted = fp == side
                for x in cols:
                    by = bottom.get(x, 29)
                    if not lifted:
                        cv.set(x, by + 1, "shade")

    # ---- arms ------------------------------------------------------------
    if f.get("arms", "none") == "nub":
        ar = int(round(cy + ry * 0.15))
        lx = left.get(ar, 8)
        ap = pose.get("arms", "down")
        up = [(lx - 1, ar - 1), (lx - 2, ar - 2), (lx - 1, ar)]
        down = [(lx - 1, ar), (lx - 1, ar + 1)]
        left_pts = up if ap in ("up", "wave") else down
        right_pts = up if ap == "up" else down
        for x, y in left_pts:
            cv.set(x, y, "base")
        for x, y in right_pts:
            cv.set(GRID - 1 - x, y, "base")

    # ---- wings -----------------------------------------------------------
    if f.get("wings"):
        wr = int(round(cy - ry * 0.05))
        lx = left.get(wr, 8)
        flap = pose.get("wing", 0)
        pts = [(lx - 1, wr), (lx - 1, wr + 1), (lx - 2, wr), (lx - 2, wr + 1),
               (lx - 3, wr - 1 if flap else wr + 2), (lx - 2, wr - 1 if flap else wr + 2),
               (lx - 1, wr - 1)]
        for x, y in pts:
            cv.sym(x, y, "light")

    # ---- tail (right side; the sprite naturally faces left) -----------------
    tail = f.get("tail", "none")
    if tail != "none":
        tr = int(round(cy + ry * 0.35)) - pose.get("wag", 0)
        rc = right.get(tr, 22)
        shapes = {
            "curl": [(1, 0), (2, -1), (2, -2), (1, -3), (2, 0)],
            "spike": [(1, 0), (2, 0), (3, -1), (2, -1), (4, -2)],
            "fluff": [(1, -1), (1, 0), (1, 1), (2, -1), (2, 0), (2, 1), (3, 0)],
            "bolt": [(1, 0), (2, 0), (2, -1), (3, -1), (3, -2), (4, -3), (4, -2)],
            "fan": [(1, -1), (1, 0), (1, 1), (2, -2), (2, 2), (2, -1), (2, 1), (3, -3), (3, 3), (3, -2), (3, 2)],
            "whip": [(1, 0), (2, 0), (3, -1), (4, -1), (5, -2), (6, -3), (6, -2)],
        }
        key = {"curl": "base", "spike": "accent", "fluff": "light", "bolt": "accent", "fan": "accent",
               "whip": "shade"}[tail]
        for ox, oy in shapes.get(tail, []):
            cv.set_empty(rc + ox, tr + oy, key)

    # ---- face ------------------------------------------------------------
    eyes = pose.get("eyes", "open")
    eh = {1: 2, 2: 3, 3: 3}[w]

    gx, gy = GAZE.get(pose.get("gaze", ""), (0, 0))

    def draw_eye(x0, right_side):
        style = eyes
        if eyes == "wink":
            style = "open" if right_side else "closed"
        if style == "half":
            for i in range(w):
                cv.set(x0 + i + gx, ey, "eye")
                if w >= 2:
                    cv.set(x0 + i + gx, ey + 1, "eye")
            for i in range(w):
                cv.set(x0 + i, ey - 1, "shade")
            return
        if style in ("open", "wide", "sad", "angry", "grumpy"):
            h = eh + (1 if style == "wide" and w < 3 else 0)
            y0 = ey - h // 2 + (1 if style == "sad" else 0)
            by = y0 - 1
            x0 += gx
            y0 += gy
            for i in range(w):
                for j in range(h):
                    cv.set(x0 + i, y0 + j, "eye")
            if w >= 2:
                cv.set(x0, y0, "white")
            if w == 3:
                cv.set(x0 + 2, y0 + 2, "white")
            x0 -= gx
            inner = x0 if right_side else x0 + w - 1
            outer = x0 + w - 1 if right_side else x0
            if style == "sad":
                cv.set(inner, by - 1, "eye")
                cv.set(outer, by, "eye")
                if not right_side:
                    cv.set(x0, y0 + h, "tear")
            elif style == "angry":
                cv.set(outer, by - 1, "eye")
                cv.set(inner, by, "eye")
            elif style == "grumpy":
                for i in range(w):
                    cv.set(x0 + i, by, "eye")
        elif style in ("closed",):
            for i in range(w):
                cv.set(x0 + i, ey, "eye")
            if w == 1:
                cv.set(x0 + (1 if right_side else -1), ey, "eye")
        elif eyes == "happy":
            for i in range(-1, w + 1):
                cv.set(x0 + i, ey + (1 if i in (-1, w) else 0), "eye")
        elif eyes == "sick":
            c0 = x0 + w // 2
            for ox, oy in ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)):
                cv.set(c0 + ox, ey + oy, "eye")
        elif eyes == "love":
            c0 = x0 + w // 2
            for ox, oy in ((-1, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                cv.set(c0 + ox, ey + oy, "heart")

    draw_eye(a, False)
    draw_eye(bcol, True)

    if f.get("cheeks") or marking == "cheeks" or pose.get("blush"):
        for x, y in ((a - 1, my), (a - 2, my)):
            if (x, y) in cells:
                cv.sym(x, y, "cheek")

    for x, oy, key in MOUTHS.get(pose.get("mouth", "smile"), MOUTHS["smile"]):
        cv.set(x, my + oy, key)

    _outline(cv)

    # ---- after-outline effects -------------------------------------------------
    tw = pose.get("twinkle", 0)
    if tw:
        spots = [(3, 8), (27, 6), (5, 21), (28, 19)]
        x, y = spots[(tw - 1) % 4]
        for ox, oy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.set_empty(x + ox, y + oy, "gold" if (ox, oy) != (0, 0) else "white")
    tilt = pose.get("tilt", 0)
    if tilt:
        # pixel-friendly head tilt: shear the upper body sideways
        pivot = cy + ry * 0.3
        for y in range(GRID):
            n = int(round(tilt * max(0.0, (pivot - y) / (ry * 0.75))))
            n = max(-2, min(2, n))
            if n:
                cv.px[y] = _shift_row(cv.px[y], n)
    g = pose.get("glitch", 0)
    if g:
        rows = range(8 + g * 4, 11 + g * 4)
        shift = 1 if g % 2 else -1
        for y in rows:
            if 0 <= y < GRID:
                row = cv.px[y]
                cv.px[y] = row[-shift:] + row[:-shift] if shift > 0 else row[1:] + row[:1]
    return cv


def build_egg(genome, crack=0, glitch=0):
    cv = Canvas()
    cells = draw_body(cv, 16.0, 29.5 - 9.0, 7.0, 9.0, 2.0, 0.12)
    mut = genome.get("mutation")
    if mut == "chimera":                       # split shell
        for x, y in cells:
            if x >= 16 and cv.get(x, y) != "light":
                cv.set(x, y, "base2")
    if mut == "midnight":                      # void egg: tiny stars
        for x, y in ((12, 14), (18, 17), (14, 22), (20, 24), (16, 12), (11, 20), (19, 20)):
            if (x, y) in cells:
                cv.set(x, y, "mark")
    else:
        for fx, fy in ((-0.4, -0.5), (0.35, -0.2), (-0.25, 0.3), (0.45, 0.5), (0.05, -0.8)):
            x, y = int(16 + fx * 7), int(20.5 + fy * 9)
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                if (x + ox, y + oy) in cells:
                    cv.set(x + ox, y + oy, "mark")
        for x, y in cells:
            if y == 22 + (x % 2):
                cv.set(x, y, "accent")
    if crack >= 1:
        for x, y in ((15, 13), (16, 14), (15, 15), (16, 16)):
            cv.set(x, y, "outline")
    if crack >= 2:
        for x, y in ((13, 17), (14, 16), (17, 16), (18, 17), (19, 16), (12, 18)):
            cv.set(x, y, "outline")
    _outline(cv)
    if glitch:
        for y in range(8 + glitch * 4, 11 + glitch * 4):
            if 0 <= y < GRID:
                cv.px[y] = _shift_row(cv.px[y], 1 if glitch % 2 else -1)
    return cv


def egg_palette(genome):
    hue = genome.get("hue", 200)
    mut = genome.get("mutation")
    pal = {
        "base": (250, 242, 222), "shade": (226, 208, 178), "light": (255, 255, 255),
        "mark": hsv(hue, 0.5, 0.85), "accent": hsv(hue, 0.35, 0.92), "outline": (76, 60, 66),
        "base2": hsv(hue, 0.25, 0.95),
    }
    if mut == "midnight":     # Void egg
        pal.update(base=(44, 38, 72), shade=(28, 24, 50), light=(90, 84, 130),
                   mark=(255, 250, 200), outline=(10, 8, 20))
    elif mut == "shiny":      # Golden egg
        pal.update(base=(255, 214, 90), shade=(214, 160, 50), light=(255, 248, 200),
                   mark=(255, 250, 230), accent=(240, 180, 60), outline=(110, 70, 20))
    elif mut == "pastel":
        pal.update(mark=hsv(hue, 0.25, 0.95), accent=hsv(hue + 60, 0.2, 0.97))
    elif mut == "glitch":
        pal.update(mark=(60, 230, 220), accent=(240, 80, 220))
    elif mut == "chimera":
        h2 = genome.get("chimera", {}).get("hue2", hue + 180)
        pal.update(base=hsv(hue, 0.3, 0.96), base2=hsv(h2, 0.3, 0.96), mark=hsv(h2, 0.55, 0.8))
    return pal


def to_surface(cv, pal, silhouette=None):
    surf = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
    for y in range(GRID):
        row = cv.px[y]
        for x in range(GRID):
            key = row[x]
            if key:
                if silhouette:
                    surf.set_at((x, y), silhouette[1] if key == "outline" else silhouette[0])
                else:
                    surf.set_at((x, y), pal.get(key, (255, 0, 255)))
    return surf


class SpriteRenderer:
    def __init__(self, species_db):
        self.db = species_db
        self.cache = {}

    def _gkey(self, genome):
        chim = genome.get("chimera") or {}
        parts = tuple(sorted((chim.get("parts") or {}).items()))
        return (round(genome.get("hue", 0), 1), genome.get("marking"),
                round(genome.get("marking_hue", 0), 1), genome.get("mutation"),
                round(genome.get("sat", 0.55), 3), parts)

    def _overrides(self, genome, pose):
        over = {}
        chim = genome.get("chimera")
        if genome.get("mutation") == "chimera" and chim:
            over.update(chim.get("parts", {}))
        shape = pose.get("shape")
        if shape and shape in self.db:
            feats = self.db[shape].get("features", {})
            for k in ("ears", "tail", "wings", "arms"):
                over[k] = feats.get(k, "none" if k != "wings" else False)
        return over

    def creature(self, species_id, genome, elder=False, pose=None):
        pose = pose or {}
        key = ("c", species_id, self._gkey(genome), elder, tuple(sorted(pose.items())))
        surf = self.cache.get(key)
        if surf is None:
            if len(self.cache) > 800:
                self.cache.clear()
            sp = self.db[species_id]
            cv = build_creature(sp, pose, genome.get("marking", "none"), self._overrides(genome, pose))
            surf = to_surface(cv, make_palette(sp, genome, elder))
            self.cache[key] = surf
        return surf

    def egg(self, genome, crack=0, glitch=0):
        key = ("egg", self._gkey(genome), crack, glitch)
        surf = self.cache.get(key)
        if surf is None:
            surf = to_surface(build_egg(genome, crack, glitch), egg_palette(genome))
            self.cache[key] = surf
        return surf

    def silhouette(self, species_id):
        key = ("sil", species_id)
        surf = self.cache.get(key)
        if surf is None:
            cv = build_creature(self.db[species_id], {"eyes": "open", "mouth": "flat"}, "none")
            surf = to_surface(cv, {}, silhouette=((70, 66, 92), (44, 40, 62)))
            self.cache[key] = surf
        return surf

    def preview(self, species_id, genome=None):
        genome = genome or {"hue": 330, "sat": 0.55, "marking": "none"}
        return self.creature(species_id, genome, False, {"eyes": "open", "mouth": "smile"})
