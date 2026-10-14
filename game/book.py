"""The Records book (v1.8): the in-depth, storybook version of Records.

The quick Records panel inside the screen stays as it was. Its Expand button
opens this book over the whole window: an open journal on a green desk with
six coloured section tabs (Collection, Family, Care, Diary, Bond, Shells).
Everything shown comes from the save; nothing here changes the game except
the buttons (new generation, export report, choosing a shell).

All drawing goes through the UI helpers (text, wrap, font, icon); click
targets go into ui.hit under "book_*" keys for app.py to act on.
"""
import time

import pygame

from . import pointer
from . import shells
from .genetics import MUTATION_NAMES
from .memory import FOODS, GAMES
from .reciprocity import PLAYER_TRAITS, PLAYER_WORDS

SECTIONS = ["Collection", "Family", "Care", "Diary", "Bond", "Shells"]
TAB_COLORS = [(242, 184, 162), (201, 227, 166), (244, 213, 141), (169, 212, 232), (230, 184, 216), (196, 189, 232)]
DESK = (77, 107, 92)
COVER = (138, 90, 60)
PAPER = (247, 240, 225)
INK = (59, 47, 42)
SOFT = (138, 116, 98)
RULE = (216, 200, 173)
BOX = (239, 229, 207)
BAR_BG = (230, 218, 195)
DARK_BTN = (59, 47, 42)
LINE_COLORS = {"land": (140, 198, 138), "water": (143, 123, 196), "secret": (214, 169, 60)}
GIFTS = (("flower", "Flower"), ("leaf", "Leaf"), ("drawing", "Drawing"), ("pebble", "Pebble"))


class Book:
    def __init__(self, ui):
        self.ui = ui

    # ---------------------------------------------------------------- frame
    def draw(self, screen, L, ctx):
        ui = self.ui
        W, H = L.W, L.H
        fs = L.fs
        self.fs = fs
        screen.fill(DESK)
        m = max(12, int(min(W, H) * 0.03))
        tab_h = fs + 18
        bw = min(W - 2 * m, int((H - 2 * m - tab_h) * 1.7))
        bh = H - 2 * m - tab_h
        book = pygame.Rect(0, 0, bw, bh)
        book.midbottom = (W // 2, H - m)
        # section tabs along the top edge
        ui.hit["book_tabs"] = []
        tw = min(int(fs * 7.5), (bw - 2 * fs) // len(SECTIONS) - 6)
        x = book.x + fs * 2
        for i, name in enumerate(SECTIONS):
            cur = i == ctx["tab"]
            h = tab_h + (8 if cur else 0)
            r = pygame.Rect(x, book.y - h + 6, tw, h)
            col = TAB_COLORS[i] if cur else tuple(int(v * 0.86) for v in TAB_COLORS[i])
            pygame.draw.rect(screen, col, r, border_top_left_radius=12, border_top_right_radius=12)
            ui.text(screen, name, (r.centerx, r.y + (tab_h - fs) // 2 - 3), fs - 1, INK, bold=True, align="center",
                    maxw=tw - 8)
            ui.hit["book_tabs"].append(r)
            x += tw + 6
        sh = pygame.Surface(book.size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (20, 30, 25, 90), sh.get_rect(), border_radius=10)
        screen.blit(sh, (book.x, book.y + 12))
        pygame.draw.rect(screen, COVER, book, border_radius=10)
        inner = book.inflate(-20, -20)
        left = pygame.Rect(inner.x, inner.y, inner.w // 2, inner.h)
        right = pygame.Rect(left.right, inner.y, inner.w - left.w, inner.h)
        pygame.draw.rect(screen, PAPER, left, border_top_left_radius=6, border_bottom_left_radius=6)
        pygame.draw.rect(screen, PAPER, right, border_top_right_radius=6, border_bottom_right_radius=6)
        for i in range(10):                               # a soft shadow into the gutter
            k = (10 - i) * 4
            col = tuple(max(0, v - k) for v in PAPER)
            pygame.draw.line(screen, col, (left.right - 10 + i, left.y + 2), (left.right - 10 + i, left.bottom - 2))
            pygame.draw.line(screen, col, (right.x + 9 - i, right.y + 2), (right.x + 9 - i, right.bottom - 2))
        pad = max(16, int(fs * 1.6))
        lp, rp = left.inflate(-2 * pad, -2 * pad), right.inflate(-2 * pad, -2 * pad)
        close = pygame.Rect(0, 0, fs * 2 + 6, fs * 2 + 6)
        close.topright = (rp.right + pad // 2, rp.y - pad // 2)
        pygame.draw.circle(screen, BOX, close.center, close.w // 2)
        c = close.center
        k = close.w // 5
        pygame.draw.line(screen, INK, (c[0] - k, c[1] - k), (c[0] + k, c[1] + k), 3)
        pygame.draw.line(screen, INK, (c[0] + k, c[1] - k), (c[0] - k, c[1] + k), 3)
        ui.hit["book_close"] = close
        for key in ("book_newgen", "book_lab", "book_export", "book_use", "book_match"):
            ui.hit[key] = None
        ui.hit["book_shells"] = []
        page = (self._collection, self._family, self._care, self._diary, self._bond, self._shells)[ctx["tab"]]
        page(screen, lp, rp, ctx, close)
        ui.text(screen, "Esc or C: back to the quick view     Left / Right: turn the page", (W // 2, H - m + 2),
                max(10, fs - 5), (210, 225, 214), align="center")

    # ---------------------------------------------------------------- helpers
    def title(self, screen, r, text, right_text=None, size_up=12):
        ui, fs = self.ui, self.fs
        ui.text(screen, text, (r.x, r.y), fs + size_up, INK, bold=True)
        if right_text:
            ui.text(screen, right_text, (r.right, r.y + size_up), fs - 3, SOFT, bold=True, align="right")
        return r.y + fs + size_up + 14

    def shared_size(self, texts, size, maxw, bold=True):
        """The largest size (down to a floor) at which every label in a group fits, so they match."""
        floor = max(9, size - 6)
        while size > floor and any(self.ui.font(size, bold).size(t)[0] > maxw for t in texts):
            size -= 1
        return size

    def small(self, screen, x, y, text, maxw=None):
        self.ui.text(screen, text.upper(), (x, y), max(10, self.fs - 5), SOFT, bold=True, maxw=maxw)
        return y + self.fs

    def para(self, screen, x, y, w, text, size=None, color=INK, bold=False, bottom=None):
        size = size or self.fs - 1
        for line in self.ui.wrap(text, size, w, bold):
            if bottom and y + size > bottom:
                break
            self.ui.text(screen, line, (x, y), size, color, bold=bold)
            y += size + 4
        return y

    def button(self, screen, r, label, dark=True, on=True):
        hover = r.collidepoint(pointer.hover_pos())
        if dark:
            pygame.draw.rect(screen, (85, 70, 62) if hover else DARK_BTN, r, border_radius=12)
            ink = PAPER
        else:
            pygame.draw.rect(screen, BOX if not hover else (232, 220, 196), r, border_radius=12)
            pygame.draw.rect(screen, INK, r, 2, border_radius=12)
            ink = INK
        if not on:
            ink = SOFT
        self.ui.text(screen, label, (r.centerx, r.y + (r.h - self.fs) // 2 - 2), self.fs, ink, bold=True,
                     align="center", maxw=r.w - 10)

    def bar(self, screen, x, y, w, label, n, total, col):
        fs = self.fs
        self.ui.text(screen, label, (x, y), fs, INK, bold=True)
        self.ui.text(screen, f"{n} / {total}", (x + w, y + 2), fs - 3, SOFT, bold=True, align="right")
        y += fs + 6
        pygame.draw.rect(screen, BAR_BG, (x, y, w, 10), border_radius=5)
        if total:
            pygame.draw.rect(screen, col, (x, y, max(10 if n else 0, int(w * n / total)), 10), border_radius=5)
        return y + 22

    def stat(self, screen, x, y, w, label, value):
        fs = self.fs
        self.ui.text(screen, label, (x, y), fs - 1, INK)
        self.ui.text(screen, str(value), (x + w, y), fs - 1, INK, bold=True, align="right")
        y += fs + 6
        for dx in range(0, w, 6):
            pygame.draw.line(screen, RULE, (x + dx, y), (x + min(w, dx + 3), y))
        return y + 5

    def box(self, screen, r):
        pygame.draw.rect(screen, BOX, r, border_radius=12)

    def sprite(self, screen, img, center, size):
        if img is None:
            return
        s = pygame.transform.scale(img, (size, size))
        screen.blit(s, s.get_rect(center=center))

    # ---------------------------------------------------------------- Collection
    def _collection(self, screen, lp, rp, ctx, close):
        ui, fs, db, rec = self.ui, self.fs, ctx["db"], ctx["records"]
        ids = list(db)
        found = [s for s in ids if s in rec.discovered]
        y = self.title(screen, lp, "Collection", f"{len(found)} of {len(ids)} found")
        avail = lp.bottom - y - fs - 6
        best = None
        for cols in (4, 5, 6, 7, 8):                  # whichever column count gives the biggest creatures
            rows = (len(ids) + cols - 1) // cols
            size = min(lp.w // cols - 8, avail // rows - fs - 10, 96)
            if best is None or size > best[0]:
                best = (size, cols, rows)
        size, cols, rows = best
        size = max(16, size)
        cw, ch = lp.w // cols, avail // rows
        for i, sid in enumerate(ids):
            sp = db[sid]
            cx = lp.x + (i % cols) * cw + cw // 2
            cy = y + (i // cols) * ch
            seen = sid in rec.discovered
            if seen:
                self.sprite(screen, ctx["renderer"].preview(sid), (cx, cy + size // 2), size)
                name, col = sp["name"], INK
            elif sp.get("secret"):
                ui.text(screen, "?", (cx, cy + size // 2 - fs), fs + 8, RULE, bold=True, align="center")
                name, col = "Secret", SOFT
            else:
                self.sprite(screen, ctx["renderer"].silhouette(sid), (cx, cy + size // 2), size)
                name, col = "???", SOFT
            ui.text(screen, name, (cx, cy + size + 2), max(9, fs - 5), col, bold=seen, align="center", maxw=cw - 2)
        ui.text(screen, "Silhouettes are forms you haven't met yet; secrets stay hidden.", (lp.x, lp.bottom - fs + 2),
                max(10, fs - 5), SOFT, bold=True, maxw=lp.w)
        # right page: progress
        y = self.title(screen, rp, "Family lines")
        groups = {"land": [], "water": [], "secret": []}
        for sid in ids:
            sp = db[sid]
            groups["secret" if sp.get("secret") else ("water" if sp.get("line") == "water" else "land")].append(sid)
        for key, label in (("land", "Pipling line"), ("water", "Dewdrop line"), ("secret", "Secrets")):
            n = sum(1 for s in groups[key] if s in rec.discovered)
            y = self.bar(screen, rp.x, y, rp.w, label, n, len(groups[key]), LINE_COLORS[key])
        y += 4
        pygame.draw.line(screen, RULE, (rp.x, y), (rp.right, y), 2)
        y = self.small(screen, rp.x, y + 12, "A hint from the margins")
        secrets_left = [s for s in groups["secret"] if s not in rec.discovered]
        hint = ("Some pets only appear after near-perfect care. Others seem to love collecting little things..."
                if secrets_left else "Every secret has been found. What a family!")
        self.para(screen, rp.x, y + 4, rp.w, hint, fs + 1)
        b = pygame.Rect(rp.x, rp.bottom - fs * 4 - 10, rp.w, fs * 4 + 10)
        self.box(screen, b)
        longest = rec.longest
        half = b.w // 2
        self.small(screen, b.x + 14, b.y + 10, "Longest life")
        self.para(screen, b.x + 14, b.y + fs + 16, half - 20,
                  f"{longest['name']} the {longest['final_name']}, {longest['days']:.1f} days" if longest else "Not yet",
                  fs - 2, bottom=b.bottom - 4)
        self.small(screen, b.x + half + 6, b.y + 10, "Rare finds")
        self.para(screen, b.x + half + 6, b.y + fs + 16, half - 20, ", ".join(rec.rare) if rec.rare else "None yet",
                  fs - 2, bottom=b.bottom - 4)

    # ---------------------------------------------------------------- Family
    def _family(self, screen, lp, rp, ctx, close):
        ui, fs, db, rec, c = self.ui, self.fs, ctx["db"], ctx["records"], ctx["c"]
        gens = len(rec.lineage) + 1
        y = self.title(screen, lp, "Family", f"{gens} generation{'s' if gens > 1 else ''}")
        rows = [{"current": True, "generation": c.generation, "name": c.name, "forms": list(c.forms),
                 "final": c.species, "days": c.age_days, "reason": "current"}]
        rows += [dict(e, current=False) for e in reversed(rec.lineage)]
        row_h = fs * 4 + 6
        icon = row_h - 14
        for i, e in enumerate(rows):
            if y + row_h > lp.bottom:
                ui.text(screen, f"...and {len(rows) - i} earlier generation{'s' if len(rows) - i > 1 else ''}",
                        (lp.x, y), fs - 3, SOFT, bold=True)
                break
            r = pygame.Rect(lp.x - 8, y, lp.w + 16, row_h - 6)
            if e["current"]:
                self.box(screen, r)
                img = ctx["renderer"].egg(c.genome) if c.stage == "egg" else ctx["renderer"].creature(
                    c.species, c.genome, c.elder, {"eyes": "open", "mouth": "smile"})
            else:
                img = ctx["renderer"].preview(e["final"], {"hue": e.get("hue", 200), "sat": 0.55, "marking": "none"}) \
                    if e.get("final") in db else None
            self.sprite(screen, img, (r.x + 8 + icon // 2, r.centery), icon)
            tx = r.x + icon + 22
            line = "Dewdrop" if any(db.get(f, {}).get("line") == "water" for f in e.get("forms", [])) else "Pipling"
            ui.text(screen, e["name"], (tx, r.y + 6), fs + 3, INK, bold=True)
            nw = ui.font(fs + 3, True).size(e["name"])[0]
            ui.text(screen, f"GEN {e['generation']} · {line.upper()} LINE", (tx + nw + 12, r.y + 11), max(9, fs - 5),
                    SOFT, bold=True)
            chain = " > ".join(["Egg"] + [db[f]["name"] for f in e.get("forms", []) if f in db])
            ui.text(screen, chain, (tx, r.y + fs + 12), fs - 3, INK, maxw=r.right - tx - 8)
            how = ("living now" if e["current"] else
                   "set off on a journey" if e["reason"] == "journey" else "departed peacefully as an elder")
            days = e["days"]
            life = f"Day {int(days) + 1} · {how}" if e["current"] else f"{days:.1f} days · {how}"
            ui.text(screen, life, (tx, r.y + 2 * fs + 16), fs - 3, SOFT, maxw=r.right - tx - 8)
            y += row_h
        # right page: the current pet
        y = self.title(screen, rp, c.name)
        big = min(rp.w // 3, int(fs * 6))
        img = ctx["renderer"].egg(c.genome) if c.stage == "egg" else ctx["renderer"].creature(
            c.species, c.genome, c.elder, {"eyes": "open", "mouth": "smile"})
        self.sprite(screen, img, (rp.x + big // 2, y + big // 2), big)
        tx = rp.x + big + 18
        species = "Egg" if c.stage == "egg" else db.get(c.species, {}).get("name", c.species)
        ui.text(screen, f"Seems: {c.personality.hint()}" if c.stage != "egg" else "Not hatched yet",
                (tx, y + big // 2 - fs - 4), fs + 2, INK, bold=True, maxw=rp.right - tx)
        self.small(screen, tx, y + big // 2 + 6, f"{species} · {c.stage} · generation {c.generation}",
                   maxw=rp.right - tx)
        y += big + 12
        if c.stage != "egg":
            g = c.genome
            mut = g.get("mutation")
            for label, value in (("Family line", "Dewdrop (water)" if g.get("line") == "water" else "Pipling (land)"),
                                 ("Markings", str(g.get("marking", "none")).replace("_", " ").capitalize()),
                                 ("Colouring", MUTATION_NAMES.get(mut, str(mut)).capitalize() if mut else "Usual"),
                                 ("Missed calls so far", c.care_mistakes)):
                y = self.stat(screen, rp.x, y, rp.w, label, value)
        y += 8
        pygame.draw.line(screen, RULE, (rp.x, y), (rp.right, y), 2)
        y = self.small(screen, rp.x, y + 12, "Left in the room by the family")
        w = ctx["world"]
        artists = sorted(set(w.mural_artists.values()) - {"you"}) if getattr(w, "mural_artists", None) else []
        bits = []
        if artists:
            bits.append("drawings on the wall by " + ", ".join(artists[:3]))
        if getattr(w, "inventions", None):
            bits.append("games: " + ", ".join(i["id"].replace("_", " ") for i in w.inventions[:3]))
        pile = len(getattr(w, "pile", []) or [])
        if pile:
            bits.append(f"{pile} trinket{'s' if pile > 1 else ''} in the collection")
        y = self.para(screen, rp.x, y + 4, rp.w, " · ".join(bits) if bits else "Nothing yet. The room remembers.",
                      fs - 1)
        ng = ctx.get("can_new_gen")
        if ng is not None:
            r = pygame.Rect(rp.x, rp.bottom - fs * 2 - 16, rp.w, fs * 2 + 16)
            ok = ng is True
            self.button(screen, r, "Begin a new generation" if ok else str(ng), dark=ok, on=ok)
            if ok:
                self.ui.hit["book_newgen"] = r

    # ---------------------------------------------------------------- Care
    def _care(self, screen, lp, rp, ctx, close):
        ui, fs, c, rec = self.ui, self.fs, ctx["c"], ctx["records"]
        y = self.title(screen, lp, "Care", f"{c.name} · this life")
        st = c.stats
        for label, value in (("Meals · snacks", f"{st.get('meals', 0)} · {st.get('snacks', 0)}"),
                             ("Games played · won", f"{st.get('games', 0)} · {st.get('wins', 0)}"),
                             ("Clean-ups", st.get("cleans", 0)), ("Medicine", st.get("medicine", 0)),
                             ("Praised · scolded", f"{st.get('praises', 0)} · {st.get('scolds', 0)}"),
                             ("Times petted", st.get("pets", 0)), ("Missed calls", c.care_mistakes)):
            if y > lp.bottom - fs * 5:
                break
            y = self.stat(screen, lp.x, y, lp.w, label, value)
        food = c.memory.favourite_food() if c.stage != "egg" else None
        game = c.memory.favourite_game() if c.stage != "egg" else None
        bw = (lp.w - 12) // 2
        for i, (label, value) in enumerate((("Favourite food", FOODS[food]["name"] if food else "Still deciding"),
                                            ("Favourite game", GAMES[game] if game else "Still deciding"))):
            b = pygame.Rect(lp.x + i * (bw + 12), lp.bottom - fs * 3 - 10, bw, fs * 3 + 10)
            self.box(screen, b)
            self.small(screen, b.x + 12, b.y + 8, label)
            ui.text(screen, value, (b.x + 12, b.y + fs + 12), fs + 1, INK, bold=True, maxw=b.w - 20)
        # right page: every generation
        y = self.title(screen, rp, "All generations")
        tot = rec.combined_totals(c)
        days = sum(e.get("days", 0) for e in rec.lineage) + c.age_days
        for label, value in (("Generations raised", len(rec.lineage) + 1), ("Meals", tot["meals"]),
                             ("Games played", tot["games"]), ("Days lived, together", f"{days:.1f}")):
            y = self.stat(screen, rp.x, y, rp.w, label, value)
        b = pygame.Rect(rp.x, y + 6, rp.w, fs * 3 + 10)
        self.box(screen, b)
        coins = ctx["info"].get("coins", (0, 0, 0))
        third = b.w // 3
        for i, (label, v) in enumerate((("Coins held", coins[0]), ("Earned", coins[1]), ("Spent", coins[2]))):
            self.small(screen, b.x + 12 + i * third, b.y + 8, label)
            ui.text(screen, str(v), (b.x + 12 + i * third, b.y + fs + 10), fs + 4, INK, bold=True)
        y = self.small(screen, rp.x, b.bottom + 14, "Gifts your pets gave you")
        gw = (rp.w - 3 * 10) // 4
        gh = min(rp.bottom - y - 4, fs * 5)
        gsz = self.shared_size([f"{lb} × {rec.gifts.get(k, 0)}" for k, lb in GIFTS], fs - 3, gw - 6)
        for i, (key, label) in enumerate(GIFTS):
            g = pygame.Rect(rp.x + i * (gw + 10), y + 4, gw, gh)
            self.box(screen, g)
            self._gift_icon(screen, key, (g.centerx, g.y + gh // 3), max(8, gh // 6))
            ui.text(screen, f"{label} × {rec.gifts.get(key, 0)}", (g.centerx, g.bottom - fs - 6), gsz, INK,
                    bold=True, align="center", maxw=g.w - 6)

    def _gift_icon(self, screen, key, c, k):
        x, y = c
        if key == "flower":
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                pygame.draw.circle(screen, (242, 167, 181), (x + dx * k, y + dy * k), k)
            pygame.draw.circle(screen, (246, 211, 106), (x, y), k * 2 // 3)
        elif key == "leaf":
            pygame.draw.ellipse(screen, (111, 174, 106), (x - k * 2, y - k, k * 4, k * 2))
            pygame.draw.line(screen, (79, 138, 76), (x - k * 2, y), (x + k * 2, y), 2)
        elif key == "drawing":
            pygame.draw.rect(screen, (255, 255, 255), (x - k * 2, y - k * 3 // 2, k * 4, k * 3), border_radius=3)
            pygame.draw.rect(screen, SOFT, (x - k * 2, y - k * 3 // 2, k * 4, k * 3), 2, border_radius=3)
            pygame.draw.lines(screen, (143, 123, 196), False,
                              [(x - k * 3 // 2, y + k // 2), (x - k // 2, y - k // 2), (x + k // 2, y + k // 3),
                               (x + k * 3 // 2, y - k // 2)], 2)
        else:
            pygame.draw.ellipse(screen, (170, 158, 146), (x - k * 2, y - k, k * 4, k * 2 + 2))
            pygame.draw.ellipse(screen, (196, 186, 174), (x - k, y - k + 2, k * 2, k // 2 + 2))

    # ---------------------------------------------------------------- Diary
    def _diary(self, screen, lp, rp, ctx, close):
        ui, fs = self.ui, self.fs
        journal = ctx["journal"]
        y = self.title(screen, lp, "Diary", "newest first")
        y = self.small(screen, lp.x, y, "Signals you share")
        book = ctx.get("phrasebook") or []
        if not book:
            y = self.para(screen, lp.x, y + 4, lp.w, "None yet. Answer its little signals and you'll learn each "
                                                     "other's language.", fs - 1, SOFT)
        for sig, meaning in book[:4]:
            ui.text(screen, sig, (lp.x, y + 4), fs - 1, INK, maxw=lp.w * 0.66)
            ui.text(screen, f"= {meaning}", (lp.right, y + 4), fs - 2, SOFT, bold=True, align="right")
            y += fs + 10
            for dx in range(0, lp.w, 6):
                pygame.draw.line(screen, RULE, (lp.x + dx, y), (lp.x + min(lp.w, dx + 3), y))
        y += 14
        imp = [e for e in reversed(journal.entries) if e.get("important")][:6] if journal else []
        b = pygame.Rect(lp.x, y, lp.w, lp.bottom - y)
        if b.h > fs * 4:
            pygame.draw.rect(screen, (227, 238, 243), b, border_radius=12)
            yy = self.small(screen, b.x + 14, b.y + 10, "Moments worth remembering")
            if not imp:
                self.para(screen, b.x + 14, yy + 4, b.w - 28, "They'll gather here as your pet grows.", fs - 1, SOFT)
            for e in imp:
                if yy + fs * 2 > b.bottom:
                    break
                yy = self.para(screen, b.x + 14, yy + 4, b.w - 28, f"{ctx['c'].name} {e['text']}"
                               if not e["text"][:1].isupper() else e["text"], fs - 1, bottom=b.bottom - 6)
        # right page: the entries, grouped by day
        y = rp.y
        entries = (sorted(journal.entries, key=lambda e: e["wt"], reverse=True)[ctx.get("scroll", 0):]
                   if journal else [])
        if not entries:
            self.title(screen, rp, "Today")
            self.para(screen, rp.x, rp.y + fs * 3, rp.w, "Nothing yet. Interesting moments will be written here.",
                      fs, SOFT)
            return
        day = None
        for e in entries:
            d = time.strftime("%A", time.localtime(e["wt"]))
            if d != day:
                if y + fs * 4 > rp.bottom:
                    break
                day = d
                ui.text(screen, d, (rp.x, y), fs + 6, INK, bold=True)
                y += fs + 10
                pygame.draw.line(screen, RULE, (rp.x, y), (rp.right - close.w if y < close.bottom + 4 else rp.right, y), 2)
                y += 8
            text = e["text"] if e["text"][:1].isupper() else f"{ctx['c'].name} {e['text']}"
            if e.get("n", 1) > 1:
                text += f" (x{e['n']})"
            tcol = ui.font(fs - 4, True).size("00:00")[0] + 8         # time column, then the star, then text
            indent = tcol + fs + 8
            lines = ui.wrap(text, fs - 1, rp.w - indent, bool(e.get("important")))
            if y + len(lines) * (fs + 3) > rp.bottom - fs:
                ui.text(screen, "Scroll for more", (rp.x, rp.bottom - fs + 2), max(10, fs - 5), SOFT, bold=True)
                break
            ui.text(screen, time.strftime("%H:%M", time.localtime(e["wt"])), (rp.x, y + 2), fs - 4, SOFT, bold=True)
            if e.get("important"):
                self._star(screen, (rp.x + tcol + fs // 2, y + fs // 2 + 1), fs // 2)
            for i, line in enumerate(lines):
                ui.text(screen, line, (rp.x + indent, y + i * (fs + 3)), fs - 1, INK, bold=bool(e.get("important")))
            y += len(lines) * (fs + 3) + 8

    def _star(self, screen, c, s):
        x, y = c
        pts = [(x, y - s), (x + s * 0.3, y - s * 0.3), (x + s, y), (x + s * 0.3, y + s * 0.3), (x, y + s),
               (x - s * 0.3, y + s * 0.3), (x - s, y), (x - s * 0.3, y - s * 0.3)]
        pygame.draw.polygon(screen, (214, 169, 60), pts)

    # ---------------------------------------------------------------- Bond
    def _bond(self, screen, lp, rp, ctx, close):
        ui, fs = self.ui, self.fs
        bond = ctx.get("bond") or {}
        y = self.title(screen, lp, "Bond", "shared memories")
        mems = bond.get("memories", [])
        if not mems:
            self.para(screen, lp.x, y, lp.w, "Nothing yet. Moments you and your pet share - copying each other, "
                                             "signals you both understand, rituals, drawings - will be kept here.",
                      fs, SOFT)
        else:
            pygame.draw.line(screen, (236, 210, 226), (lp.x + 6, y), (lp.x + 6, lp.bottom - 4), 3)
            start = max(0, len(mems) - 8)
            for m in mems[start:]:
                lines = ui.wrap(m["text"], fs, lp.w - 30)
                if y + fs + len(lines) * (fs + 3) > lp.bottom:
                    break
                pygame.draw.circle(screen, (217, 119, 173), (lp.x + 7, y + fs // 2 + 2), 6)
                self.small(screen, lp.x + 24, y, time.strftime("%a %d %b", time.localtime(m["wt"])))
                for i, line in enumerate(lines):
                    ui.text(screen, line, (lp.x + 24, y + fs + i * (fs + 3)), fs, INK)
                y += fs + len(lines) * (fs + 3) + 10
        # right page
        y = self.title(screen, rp, f"How {ctx['c'].name} sees you")
        lab = dict(bond.get("lab_sections") or [])
        rows = lab.get("How it sees you", [])
        lang = lab.get("Language", [])
        if lang:
            y = self.small(screen, rp.x, y, "Its language")
            y = self.para(screen, rp.x, y + 2, rp.w, lang[0], fs)
            y += 6
        player = bond.get("player") or {}
        if player:
            y = self.small(screen, rp.x, y, "What it has noticed: you...")
            lw = int(rp.w * 0.58)
            for k in PLAYER_TRAITS:
                if y > rp.bottom - fs * 6:
                    break
                v = max(-1.0, min(1.0, float(player.get(k, 0.0))))
                ui.text(screen, PLAYER_WORDS[k], (rp.x, y + 2), fs - 2, INK, maxw=lw - 8)
                bx, bw = rp.x + lw, rp.w - lw
                cy = y + fs // 2 + 3
                pygame.draw.rect(screen, BAR_BG, (bx, cy - 4, bw, 8), border_radius=4)
                mid = bx + bw // 2
                end = mid + int(v * bw / 2)
                pygame.draw.rect(screen, (217, 119, 173) if v >= 0 else SOFT,
                                 (min(mid, end), cy - 4, max(2, abs(end - mid)), 8), border_radius=4)
                pygame.draw.line(screen, SOFT, (mid, cy - 7), (mid, cy + 6), 2)
                y += fs + 9
            ui.text(screen, "rarely", (rp.x + lw, y), max(9, fs - 6), SOFT)
            ui.text(screen, "often", (rp.right, y), max(9, fs - 6), SOFT, align="right")
            y += fs
        rit = [r for r in lab.get("Rituals", []) if r != "none yet"]
        if rit and y < rp.bottom - fs * 7:
            y += 6
            y = self.small(screen, rp.x, y, "Rituals")
            for r in rit[:2]:
                y = self.para(screen, rp.x, y + 2, rp.w, r, fs - 2)
        if not (player or lang):
            self.para(screen, rp.x, y, rp.w, "Still getting to know you.", fs, SOFT)
        gap = 12
        b1 = pygame.Rect(rp.x, rp.bottom - fs * 2 - 16, (rp.w - gap) * 3 // 5, fs * 2 + 16)
        b2 = pygame.Rect(b1.right + gap, b1.y, rp.w - b1.w - gap, b1.h)
        self.button(screen, b1, "Open the Observation Lab")
        self.button(screen, b2, "Export report", dark=False)
        self.ui.hit["book_lab"], self.ui.hit["book_export"] = b1, b2

    # ---------------------------------------------------------------- Shells
    def _shells(self, screen, lp, rp, ctx, close):
        ui, fs = self.ui, self.fs
        rec = ctx["records"]
        have = shells.unlocked(rec)
        y = self.title(screen, lp, "Shells", f"{len(have)} of {len(shells.SHELLS)} unlocked")
        sel = ctx.get("shell_sel") or "classic"
        wearing = ctx.get("shell_now")
        cols = 3 if len(shells.ORDER) <= 9 else 4
        cw = lp.w // cols
        rows = (len(shells.ORDER) + cols - 1) // cols
        ch = (lp.bottom - y) // rows
        sw = min(cw - 16, int((ch - fs * 3 - 10) * 240 / 260))
        names = ["???" if s_ not in have else shells.SHELLS[s_]["name"] + ("  (wearing)" if s_ == wearing else "")
                 for s_ in shells.ORDER]
        nsz = self.shared_size(names, fs - 1, cw - 10)
        shh = int(sw * 260 / 240)
        for i, sid in enumerate(shells.ORDER):
            cx = lp.x + (i % cols) * cw + cw // 2
            cy = y + (i // cols) * ch
            cell = pygame.Rect(cx - cw // 2 + 4, cy, cw - 8, ch - 6)
            if sid == sel:
                self.box(screen, cell)
            r = pygame.Rect(0, 0, sw, shh)
            r.midtop = (cx, cy + 6)
            locked = sid not in have
            self._mini(screen, sid, r, ctx, locked)
            name = "???" if locked else shells.SHELLS[sid]["name"] + ("  (wearing)" if sid == wearing else "")
            ui.text(screen, name, (cx, r.bottom + 4), nsz, INK if not locked else SOFT, bold=True, align="center",
                    maxw=cw - 10)
            ui.text(screen, shells.SHELLS[sid]["hint"], (cx, r.bottom + fs + 6), max(9, fs - 5), SOFT, align="center",
                    maxw=cw - 10)
            ui.hit["book_shells"].append((cell, sid))
        # right page: the selected shell
        locked = sel not in have
        y = self.title(screen, rp, "???" if locked else shells.SHELLS[sel]["name"])
        bw = min(rp.w - 40, int((rp.h - fs * 12) * 240 / 260))
        r = pygame.Rect(0, 0, bw, int(bw * 260 / 240))
        r.midtop = (rp.centerx, y)
        self._mini(screen, sel, r, ctx, locked)
        y = r.bottom + 12
        if locked:
            text = f"Locked. {shells.SHELLS[sel]['hint']} to unlock it."
        elif sel == "classic":
            text = "Where every family starts. It takes the theme colour you pick in Settings."
        else:
            text = f"Unlocked when you {shells.SHELLS[sel]['hint'][0].lower()}{shells.SHELLS[sel]['hint'][1:]}."
        y = self.para(screen, rp.x, y, rp.w, text, fs, INK)
        gap = 12
        b1 = pygame.Rect(rp.x, rp.bottom - fs * 2 - 16, (rp.w - gap) // 2, fs * 2 + 16)
        b2 = pygame.Rect(b1.right + gap, b1.y, rp.w - b1.w - gap, b1.h)
        match = ctx.get("shell_choice") == "match"
        if not locked:
            chosen = ctx.get("shell_choice") == sel
            self.button(screen, b1, "Wearing this shell" if chosen else "Wear this shell", dark=not chosen)
            ui.hit["book_use"] = b1
        self.button(screen, b2, "      Match my pet", dark=False)
        box = pygame.Rect(0, 0, fs + 2, fs + 2)
        lw = ui.font(fs, True).size("      Match my pet")[0]
        box.midleft = (b2.centerx - lw // 2 + 2, b2.centery)
        pygame.draw.rect(screen, PAPER, box, border_radius=4)
        pygame.draw.rect(screen, INK, box, 2, border_radius=4)
        if match:
            pygame.draw.lines(screen, INK, False, [(box.x + 4, box.centery), (box.centerx - 1, box.bottom - 5),
                                                   (box.right - 4, box.y + 4)], 3)
        ui.hit["book_match"] = b2

    def _mini(self, screen, sid, r, ctx, locked):
        """A small shell with the live screen in it (or a padlock if it's still locked)."""
        radii = (int(r.h * 0.28), int(r.h * 0.17))
        if locked:
            pygame.draw.rect(screen, (221, 210, 191), r, border_top_left_radius=radii[0],
                             border_top_right_radius=radii[0], border_bottom_left_radius=radii[1],
                             border_bottom_right_radius=radii[1])
            c = r.center
            k = max(6, r.w // 10)
            pygame.draw.rect(screen, (154, 138, 116), (c[0] - k, c[1] - k // 3, 2 * k, int(1.5 * k)), border_radius=3)
            pygame.draw.arc(screen, (154, 138, 116), (c[0] - k * 2 // 3, c[1] - k * 3 // 2, k * 4 // 3, k * 2), 0, 3.15, 3)
            return
        key = ("mini", sid, r.size, int(ctx.get("hue", 200)) if sid == "classic" else 0)
        cache = self.__dict__.setdefault("_cache", {})
        if key not in cache:
            cache[key] = shells.shell_surface(sid, r.size, radii, ctx.get("hue", 200))
            if len(cache) > 40:
                cache.clear()
                cache[key] = shells.shell_surface(sid, r.size, radii, ctx.get("hue", 200))
        screen.blit(cache[key], r.topleft)
        sw = int(r.w * 0.62)
        scr = pygame.Rect(0, 0, sw, int(sw * 0.7))
        scr.center = (r.centerx, r.centery - r.h // 20)
        pygame.draw.rect(screen, (43, 34, 64), scr.inflate(8, 8), border_radius=6)
        if ctx.get("lcd") is not None:
            screen.blit(pygame.transform.scale(ctx["lcd"], scr.size), scr)
