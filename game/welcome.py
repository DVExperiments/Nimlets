"""The first-time welcome (v2.1).

A five-page storybook tour shown once, the first time someone plays: what the
egg is, looking after it, the buttons, how the pet notices you, and how time
works. It explains the device without spoiling the pet's hidden behaviours;
the point is to make new players curious, not to list every system.

Game time is held while the tour is open (the egg can't hatch mid-tour), and
Settings -> Welcome tour shows it again. Players who already have a save never
see it automatically.

After the tour, a handful of one-time hints appear in the message line the first
time something important happens. They only show for players who took the tour,
never interrupt another message, and each appears once (remembered in preferences).
"""
import pygame

from .book import BOX, COVER, DESK, INK, PAPER, SOFT

PAGES = [
    {"title": "Welcome to Nimlets",
     "art": "egg",
     "text": ["This is your egg. Soon it will hatch into a little creature that lives in this device.",
              "Look after it, and it will grow up into one of 28 different forms, shaped by how you "
              "raise it. Some of them are secret."]},
    {"title": "Looking after it",
     "art": "hearts",
     "text": ["The hearts above the screen show how hungry, happy and healthy it is.",
              "When it needs you, the light beside its name turns red and a tab flashes. Feed it, play "
              "games, clean up, give medicine when it's poorly, praise or scold it, and turn the lights "
              "off when it sleeps."]},
    {"title": "The buttons",
     "art": "abc",
     "text": ["Click a tab, or press 1 to 8. You can also use the buttons along the bottom:",
              "A moves along the tabs, B chooses, C goes back. Beside them: Settings, sound, speed "
              "and pause. Records shows its history, and Expand opens the whole storybook."]},
    {"title": "It notices you",
     "art": "pet",
     "text": ["Your Nimlet isn't just waiting for you. It has a mind of its own, and it's curious "
              "about you too.",
              "Try clicking things in the room, drawing on the lower part of the wall, or simply "
              "watching what it does. There's a lot to discover, and no wrong way to play."]},
    {"title": "Time keeps going",
     "art": "moon",
     "text": ["Your Nimlet lives in real time, and life carries on gently while the game is closed. "
              "It can get hungry or grumpy, but it never dies of neglect.",
              "One day it will grow old, set off, and leave an egg for the next generation."]},
]

# one-time hints: id -> message (shown the first time the condition is true)
HINTS = {
    "attention": "It's calling you! The flashing tab shows what it needs.",
    "mess": "A little mess. Clean (3) tidies it up.",
    "sleep": "It's fallen asleep. Light (6) turns the lights off for it.",
    "drawing": "It drew on the wall! Drag along the lower wall to draw back.",
    "grown": "It's growing up! Records (8), then Expand, opens its storybook.",
}


def hint_due(app):
    """Which hint (if any) should show right now."""
    c = app.c
    if c is None or c.stage == "egg":
        return None
    seen = set(app.prefs.get("hints_seen", []))
    checks = (("attention", bool(c.attention) and c.attention not in ("lights", "dark") and not c.asleep),
              ("mess", c.poops > 0),
              ("sleep", c.asleep and c.lights_on),
              ("drawing", any(p[3] == c.generation for p in app.world.mural)),
              ("grown", c.stage not in ("egg", "baby")))
    for hid, ok in checks:
        if ok and hid not in seen:
            return hid
    return None


class Welcome:
    def __init__(self, ui):
        self.ui = ui

    def draw(self, screen, L, page, ctx):
        ui, fs = self.ui, L.fs
        W, H = L.W, L.H
        screen.fill(DESK)
        m = max(14, int(min(W, H) * 0.04))
        w = min(W - 2 * m, int(H * 1.05), 820)
        h = min(H - 2 * m, int(w * 0.78))
        card = pygame.Rect(0, 0, w, h)
        card.center = (W // 2, H // 2)
        sh = pygame.Surface(card.size, pygame.SRCALPHA)
        pygame.draw.rect(sh, (20, 30, 25, 90), sh.get_rect(), border_radius=14)
        screen.blit(sh, (card.x, card.y + 10))
        pygame.draw.rect(screen, COVER, card, border_radius=14)
        inner = card.inflate(-20, -20)
        pygame.draw.rect(screen, PAPER, inner, border_radius=10)
        pad = max(18, fs + 6)
        body = inner.inflate(-2 * pad, -2 * pad)
        p = PAGES[page]
        ui.text(screen, p["title"], (body.centerx, body.y), fs + 12, INK, bold=True, align="center",
                maxw=body.w, fit=True)
        # the words matter more than the picture: shrink the picture first, the text only if it must
        bottom = body.bottom - fs * 3 - 10
        top = body.y + fs + 30
        size = fs
        for frac in (0.40, 0.32, 0.24, 0.18):
            art_h = int(body.h * frac)
            lines = []
            for para in p["text"]:
                lines += ui.wrap(para, size, body.w - 20) + [""]
            lh = ui.font(size).get_height() + 4
            if top + art_h + 14 + len(lines) * lh <= bottom:
                break
        else:
            while size > max(10, fs - 4):
                size -= 1
                lines = []
                for para in p["text"]:
                    lines += ui.wrap(para, size, body.w - 20) + [""]
                lh = ui.font(size).get_height() + 4
                if top + art_h + 14 + len(lines) * lh <= bottom:
                    break
        art = pygame.Rect(0, 0, body.w, art_h)
        art.midtop = (body.centerx, top)
        self._art(screen, p["art"], art, ctx, fs)
        y = art.bottom + 14
        for line in lines:
            if line:
                ui.text(screen, line, (body.centerx, y), size, INK, align="center")
            y += lh if line else lh // 2
        # page dots
        n = len(PAGES)
        dy = body.bottom - fs * 2 - 18
        for i in range(n):
            cx = body.centerx + (i - (n - 1) / 2) * 18
            pygame.draw.circle(screen, INK if i == page else (214, 200, 176), (int(cx), dy), 5)
        # buttons
        bh = fs * 2 + 10
        nxt = pygame.Rect(0, 0, max(150, ui.font(fs, True).size("Let's begin!")[0] + 40), bh)
        nxt.bottomright = (body.right, body.bottom + 6)
        back = pygame.Rect(0, 0, nxt.w * 3 // 4, bh)
        back.bottomleft = (body.x, body.bottom + 6)
        last = page == n - 1
        self._button(screen, nxt, "Let's begin!" if last else "Next", fs, dark=True)
        if page > 0:
            self._button(screen, back, "Back", fs, dark=False)
        skip = None
        if not last:
            skip = pygame.Rect(0, 0, ui.font(fs - 3, True).size("Skip the tour")[0] + 20, fs + 10)
            skip.midbottom = (body.centerx, body.bottom + 4)
            ui.text(screen, "Skip the tour", (skip.centerx, skip.y + 3), fs - 3, SOFT, bold=True, align="center")
        ui.hit["welcome_next"], ui.hit["welcome_back"] = nxt, (back if page > 0 else None)
        ui.hit["welcome_skip"] = skip
        ui.text(screen, "Enter or B: next     Left or C: back     Esc: skip", (W // 2, H - m + 2),
                max(10, fs - 5), (210, 225, 214), align="center")

    def _button(self, screen, r, label, fs, dark):
        hover = r.collidepoint(pygame.mouse.get_pos())
        if dark:
            pygame.draw.rect(screen, (85, 70, 62) if hover else INK, r, border_radius=12)
            ink = PAPER
        else:
            pygame.draw.rect(screen, (232, 220, 196) if hover else BOX, r, border_radius=12)
            pygame.draw.rect(screen, INK, r, 2, border_radius=12)
            ink = INK
        h = self.ui.font(fs, True).get_height()
        self.ui.text(screen, label, (r.centerx, r.centery - h // 2), fs, ink, bold=True, align="center")

    def _art(self, screen, kind, r, ctx, fs):
        """A small picture for each page, drawn from the game's own pieces."""
        ui = self.ui
        rend, c = ctx["renderer"], ctx["c"]
        k = max(3, min(9, r.h // 22))
        if kind == "egg":
            img = rend.egg(c.genome)
            img = img.subsurface(img.get_bounding_rect()).copy()
            img = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))
            pygame.draw.ellipse(screen, (226, 214, 190), (r.centerx - img.get_width() // 2, r.bottom - 18,
                                                          img.get_width(), 16))
            screen.blit(img, img.get_rect(midbottom=(r.centerx, r.bottom - 8)))
        elif kind == "hearts":
            box = pygame.Rect(0, 0, min(r.w - 40, 480), max(40, fs * 2 + 10))
            box.center = (r.centerx + 14, r.centery)
            pygame.draw.rect(screen, (43, 34, 64), box, border_radius=10)
            sec = box.w // 3
            for i, (name, n, col) in enumerate((("HUNGER", 4, (230, 70, 90)), ("HAPPY", 5, (240, 110, 170)),
                                                 ("HEALTH", 6, (90, 210, 150)))):
                x0 = box.x + i * sec
                lw = ui.font(fs - 5, True).size(name)[0]
                sc = max(1, min(2, (sec - lw - 14) // 48))
                x = x0 + (sec - (lw + 6 + 48 * sc)) // 2
                ui.text(screen, name, (x, box.centery - ui.font(fs - 5, True).get_height() // 2), fs - 5,
                        (245, 240, 255), bold=True)
                ui.hearts(screen, x + lw + 6, box.centery - 3 * sc, n, sc, 6, col, empty=(93, 81, 120))
            led = (box.x - 18, box.centery)
            pygame.draw.circle(screen, (255, 90, 110), led, 9)
            ui.text(screen, "!", (led[0], led[1] - ui.font(fs - 2, True).get_height() // 2), fs - 2,
                    (255, 255, 255), bold=True, align="center")
        elif kind == "abc":
            d = min(r.h - 10, 74)
            cols = (((244, 211, 106), (210, 173, 62), (92, 69, 16)), ((255, 138, 155), (217, 99, 122), (90, 26, 40)),
                    ((143, 217, 192), (95, 183, 155), (22, 74, 58)))
            for i, (col, lip, ink) in enumerate(cols):
                size = d if i == 1 else int(d * 0.85)
                cx = r.centerx + (i - 1) * int(d * 1.35)
                cy = r.centery
                pygame.draw.circle(screen, lip, (cx, cy), size // 2)
                pygame.draw.circle(screen, col, (cx, cy - 4), size // 2 - 1)
                h = ui.font(fs + 6, True).get_height()
                ui.text(screen, "ABC"[i], (cx, cy - 4 - h // 2), fs + 6, ink, bold=True, align="center")
        elif kind == "pet":
            look = {"hue": 20, "sat": 0.6, "marking": "cheeks", "marking_hue": 340, "mutation": None}
            img = rend.creature("pipling", look, False, {"eyes": "open", "mouth": "smile"})
            img = img.subsurface(img.get_bounding_rect()).copy()
            img = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))
            screen.blit(img, img.get_rect(midbottom=(r.centerx, r.bottom - 6)))
            ax, ay = r.centerx + img.get_width() // 2 + 26, r.y + r.h // 3
            pts = [(ax, ay), (ax, ay + 26), (ax + 7, ay + 20), (ax + 12, ay + 31), (ax + 17, ay + 29),
                   (ax + 12, ay + 18), (ax + 21, ay + 18)]        # your cursor, which it is watching
            pygame.draw.polygon(screen, (255, 255, 255), pts)
            pygame.draw.polygon(screen, INK, pts, 2)
        elif kind == "moon":
            cx, cy, rad = r.centerx, r.centery, min(r.h // 2 - 6, 56)
            pygame.draw.circle(screen, (43, 34, 64), (cx, cy), rad + 10)
            pygame.draw.circle(screen, (246, 231, 168), (cx - 6, cy), rad // 2 + 8)
            pygame.draw.circle(screen, (43, 34, 64), (cx + 8, cy - 6), rad // 2 + 4)
            for dx, dy, s in ((-30, -24, 4), (26, 22, 3), (34, -18, 3), (-22, 28, 2)):
                pygame.draw.circle(screen, (255, 255, 255), (cx + dx, cy + dy), s)
