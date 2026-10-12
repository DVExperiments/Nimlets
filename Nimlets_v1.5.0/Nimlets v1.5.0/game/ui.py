"""Modern handheld-style interface around the retro LCD.

Everything here is drawing + hit-testing. Game logic lives in app.py.
All colours come from the active Theme (light/dark x any hue).
"""
import pygame

from .config import LCD_W, LCD_H
from .memory import FOODS, GAMES
from .sprites import hsv

WHITE = (255, 255, 255)
HEART_RED = (236, 72, 104)

THEME_SWATCHES = [("pet", "Pet colour"), (18, "Peach"), (46, "Lemon"), (150, "Mint"),
                  (200, "Sky"), (262, "Lavender"), (335, "Rose")]


class Theme:
    def __init__(self, hue, dark=False):
        h = hue
        self.dark = dark
        if not dark:
            self.bg_top = hsv(h, 0.35, 0.20)
            self.bg_bottom = hsv(h + 25, 0.32, 0.32)
            self.shell = hsv(h, 0.18, 0.97)
            self.shell_edge = hsv(h, 0.24, 0.90)
            self.bezel = (46, 42, 60)
            self.bezel_edge = (70, 64, 88)
            self.panel = (255, 255, 255)
            self.panel_alt = hsv(h, 0.05, 0.96)
            self.ink = (30, 26, 44)
            self.ink_soft = (74, 66, 94)
            self.button = (255, 255, 255)
            self.button_hover = hsv(h, 0.08, 1.0)
            self.button_off = (236, 232, 238)
            self.select = hsv(h, 0.14, 1.0)
            self.select_edge = hsv(h, 0.45, 0.92)
            self.tab_on = hsv(h, 0.22, 1.0)
            self.heart_empty = (216, 208, 224)
            self.bar_bg = (236, 230, 240)
            self.msg_bg = (255, 255, 255, 235)
            self.icon_ink = (30, 26, 44)
            self.shadow = (0, 0, 0, 70)
        else:
            self.bg_top = (12, 12, 20)
            self.bg_bottom = hsv(h, 0.35, 0.13)
            self.shell = hsv(h, 0.28, 0.22)
            self.shell_edge = hsv(h, 0.32, 0.33)
            self.bezel = (16, 14, 24)
            self.bezel_edge = hsv(h, 0.25, 0.30)
            self.panel = hsv(h, 0.20, 0.18)
            self.panel_alt = hsv(h, 0.18, 0.26)
            self.ink = (248, 246, 252)
            self.ink_soft = (208, 202, 226)
            self.button = hsv(h, 0.22, 0.30)
            self.button_hover = hsv(h, 0.26, 0.37)
            self.button_off = hsv(h, 0.14, 0.24)
            self.select = hsv(h, 0.35, 0.36)
            self.select_edge = hsv(h, 0.55, 0.85)
            self.tab_on = hsv(h, 0.40, 0.42)
            self.heart_empty = (88, 82, 110)
            self.bar_bg = hsv(h, 0.15, 0.30)
            self.msg_bg = hsv(h, 0.25, 0.28) + (240,)
            self.icon_ink = (238, 234, 246)
            self.shadow = (0, 0, 0, 120)


ICONS = {
    "feed": ["......#.....", ".....#......", "..###o###...", ".#########..", ".##o######..",
             ".#o#######..", ".#########..", ".#########..", "..#######...", "...##.##....",
             "............", "............"],
    "play": ["....####....", "..##oooo##..", ".#oooooooo#.", ".##########.", "############",
             "#oooooooooo#", "#oooooooooo#", "############", ".##########.", ".#oooooooo#.",
             "..##oooo##..", "....####...."],
    "clean": [".....#......", ".....#......", "....###.....", "....###.....", "...#####....",
              "..###o###...", "..##o####...", "..##o####...", "..#######...", "...#####....",
              ".........o..", "........o.o."],
    "medicine": ["....####....", "....#oo#....", "....#oo#....", "#####oo#####", "#oooooooooo#",
                 "#oooooooooo#", "#####oo#####", "....#oo#....", "....#oo#....", "....####....",
                 "............", "............"],
    "discipline": [".....##.....", ".....##.....", "....#oo#....", "#####oo#####", ".#oooooooo#.",
                   "..#oooooo#..", "...#oooo#...", "..#oo##oo#..", "..#o#..#o#..", ".##......##.",
                   "............", "............"],
    "lights": ["....####....", "..##oooo##..", ".#oooooooo#.", ".#oooooooo#.", ".#oooooooo#.",
               "..#oooooo#..", "...#oooo#...", "....####....", "....####....", "....####....",
               ".....##.....", "............"],
    "status": ["............", ".###....###.", "#ooo#..#ooo#", "#oooo##oooo#", "#oooooooooo#",
               ".#oooooooo#.", "..#oooooo#..", "...#oooo#...", "....#oo#....", ".....##.....",
               "............", "............"],
    "records": ["............", ".####..####.", "#oooo##oooo#", "#o##o##o##o#", "#oooo##oooo#",
                "#o##o##o##o#", "#oooo##oooo#", "#oooo##oooo#", ".####..####.", "............",
                "............", "............"],
    "sound_on": ["...#....", "..##..#.", "####.#..", "####.#.#", "####.#.#", "####.#..",
                 "..##..#.", "...#...."],
    "sound_off": ["...#....", "..##....", "####.#.#", "####..#.", "####..#.", "####.#.#",
                  "..##....", "...#...."],
    "pause": ["........", ".##..##.", ".##..##.", ".##..##.", ".##..##.", ".##..##.",
              ".##..##.", "........"],
    "resume": ["........", ".#......", ".###....", ".#####..", ".######.", ".#####..",
               ".###....", ".#......"],
    "save": ["#######.", "#o###o##", "#o###o.#", "#ooooo.#", "#......#", "#.####.#",
             "#.####.#", "########"],
    "settings": ["...##...", ".#.##.#.", "########", ".##..##.", ".##..##.", "########",
                 ".#.##.#.", "...##..."],
    "speed": ["........", "#...#...", "##..##..", "###.###.", "########", "###.###.",
              "##..##..", "#...#..."],
}
ICON_COLORS = {
    "feed": ((200, 60, 70), (255, 170, 170)), "play": ((70, 110, 210), (255, 220, 110)),
    "clean": ((70, 150, 220), (210, 240, 255)), "medicine": ((210, 70, 90), (255, 255, 255)),
    "discipline": ((220, 150, 40), (255, 220, 110)), "lights": ((110, 100, 70), (255, 226, 120)),
    "status": ((210, 60, 100), (255, 140, 170)), "records": ((120, 80, 170), (250, 245, 255)),
}
HEART_ROWS = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]
COIN_ROWS = [".####.", "#oo#o#", "#o#oo#", "#o#oo#", "#oo#o#", ".####."]

ACTION_IDS = ["feed", "play", "clean", "medicine", "discipline", "lights", "status", "records"]
ACTION_LABELS = ["Feed", "Play", "Clean", "Medicine", "Train", "Lights", "Status", "Records"]
TOGGLES = ("settings", "save", "speed", "pause", "sound")


def pixel_icon(rows, main, second, scale):
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w * scale, len(rows) * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = main if ch == "#" else second if ch == "o" else None
            if col:
                surf.fill(col, (x * scale, y * scale, scale, scale))
    return surf


class Menu:
    def __init__(self, kind, title, items, hint=""):
        self.kind = kind
        self.title = title
        self.items = items      # list of (label, value, note)
        self.sel = 0
        self.hint = hint
        self.rects = []

    def move(self, d):
        self.sel = (self.sel + d) % len(self.items)


class Layout:
    pass


class UI:
    def __init__(self, renderer, species_db):
        self.r = renderer
        self.db = species_db
        self._fonts = {}
        self._icons = {}
        self._themes = {}
        self.hit = {}
        self._bg = None
        self._bg_key = None
        self.t = self.theme_for(200, False)

    # ---- theme -----------------------------------------------------------------------
    def theme_for(self, hue, dark):
        key = (int(hue) % 360, bool(dark))
        if key not in self._themes:
            self._themes[key] = Theme(key[0], key[1])
        return self._themes[key]

    def set_theme(self, hue, dark):
        self.t = self.theme_for(hue, dark)

    # ---- primitives -----------------------------------------------------------------
    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self._fonts:
            try:
                f = pygame.font.SysFont("segoeui,verdana,arial,helvetica,dejavusans", size, bold=bold)
            except Exception:
                f = pygame.font.Font(None, int(size * 1.3))
            self._fonts[key] = f
        return self._fonts[key]

    def text(self, surf, s, pos, size, color=None, bold=False, align="left", maxw=None):
        color = color or self.t.ink
        f = self.font(size, bold)
        if maxw and f.size(s)[0] > maxw:
            while len(s) > 1 and f.size(s + "...")[0] > maxw:
                s = s[:-1]
            s = s.rstrip() + "..."
        img = f.render(s, True, color)
        r = img.get_rect()
        setattr(r, {"left": "topleft", "center": "midtop", "right": "topright"}[align], pos)
        surf.blit(img, r)
        return r

    def icon(self, name, scale, colors=None):
        key = (name, scale, colors)
        if key not in self._icons:
            main, second = colors or ICON_COLORS.get(name, (self.t.icon_ink, WHITE))
            self._icons[key] = pixel_icon(ICONS[name], main, second, scale)
        return self._icons[key]

    def hearts(self, surf, x, y, n, scale, slots=4, color=HEART_RED, wobble=0.0):
        for i in range(slots):
            col = color if i < n else self.t.heart_empty
            key = ("heart", col, scale)
            if key not in self._icons:
                self._icons[key] = pixel_icon(HEART_ROWS, col, col, scale)
            dy = int(round(wobble * 3 * ((-1) ** i))) if wobble else 0
            surf.blit(self._icons[key], (x + i * (8 * scale), y + dy))
        return pygame.Rect(x, y, slots * 8 * scale, 6 * scale)

    def panel(self, surf, rect, color=None, radius=16, shadow=True):
        color = color or self.t.panel
        if shadow:
            sh = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(sh, self.t.shadow, sh.get_rect(), border_radius=radius)
            surf.blit(sh, (rect.x + 4, rect.y + 6))
        pygame.draw.rect(surf, color, rect, border_radius=radius)

    def pill_button(self, surf, rect, label, size, on=False, enabled=True, danger=False):
        t = self.t
        if danger:
            col = (240, 120, 120) if not t.dark else (150, 60, 70)
        else:
            col = t.tab_on if on else t.panel_alt
        if not enabled:
            col = t.button_off
        if rect.collidepoint(pygame.mouse.get_pos()) and enabled:
            pygame.draw.rect(surf, t.select_edge, rect.inflate(4, 4), 2, border_radius=rect.h // 2 + 2)
        pygame.draw.rect(surf, col, rect, border_radius=rect.h // 2)
        ink = (255, 255, 255) if danger else (t.ink if enabled else t.ink_soft)
        self.text(surf, label, (rect.centerx, rect.y + (rect.h - size) // 2 - 2), size, ink,
                  bold=True, align="center", maxw=rect.w - 12)

    # ---- layout -----------------------------------------------------------------------
    def layout(self, W, H):
        L = Layout()
        m = max(10, int(min(W, H) * 0.02))
        L.W, L.H = W, H
        L.shell = pygame.Rect(m, m, W - 2 * m, H - 2 * m)
        L.fs = max(13, min(22, int(H * 0.022)))
        top_h = max(66, int(H * 0.1))
        btn_h = max(64, int(H * 0.12))
        msg_h = max(26, int(L.fs * 1.9))
        inner_x, inner_w = L.shell.x + 18, L.shell.w - 36
        L.top = pygame.Rect(inner_x, L.shell.y + 10, inner_w, top_h)
        area = pygame.Rect(inner_x, L.top.bottom + 8, inner_w,
                           L.shell.h - top_h - btn_h - msg_h - 46)
        L.scale = max(1, min((area.w - 24) // LCD_W, (area.h - 24) // LCD_H))
        L.lcd = pygame.Rect(0, 0, LCD_W * L.scale, LCD_H * L.scale)
        L.lcd.center = area.center
        L.bezel = L.lcd.inflate(24, 24)
        L.msg = pygame.Rect(inner_x, L.bezel.bottom + 6, inner_w, msg_h)
        gap = 8
        bw = (inner_w - gap * 7) / 8.0
        by = L.shell.bottom - btn_h - 12
        L.buttons = [pygame.Rect(int(inner_x + i * (bw + gap)), by, int(bw), btn_h) for i in range(8)]
        ts = max(28, min(top_h - 18, 46, int(W * 0.055)))
        L.toggles = {}
        for i, name in enumerate(reversed(TOGGLES)):
            L.toggles[name] = pygame.Rect(L.top.right - (i + 1) * (ts + 6), L.top.y + (top_h - ts) // 2, ts, ts)
        return L

    # ---- frame --------------------------------------------------------------------------
    def draw_frame(self, screen, L):
        t = self.t
        key = (L.W, L.H, t.bg_top, t.bg_bottom)
        if self._bg is None or self._bg_key != key:
            self._bg = pygame.Surface((L.W, L.H))
            for y in range(L.H):
                k = y / max(1, L.H - 1)
                col = tuple(int(a + (b - a) * k) for a, b in zip(t.bg_top, t.bg_bottom))
                pygame.draw.line(self._bg, col, (0, y), (L.W, y))
            self._bg_key = key
        screen.blit(self._bg, (0, 0))
        self.panel(screen, L.shell, t.shell, radius=34)
        pygame.draw.rect(screen, t.shell_edge, L.shell, 3, border_radius=34)
        pygame.draw.rect(screen, t.bezel, L.bezel, border_radius=20)
        pygame.draw.rect(screen, t.bezel_edge, L.bezel, 3, border_radius=20)

    def draw_lcd_texts(self, screen, L, texts):
        for text, x, y, size, color, align in texts:
            px = max(8, int(size * L.scale * 0.95))
            self.text(screen, text, (L.lcd.x + x * L.scale, L.lcd.y + y * L.scale), px, color,
                      bold=True, align=align)

    def draw_top(self, screen, L, info):
        t = self.t
        fs = L.fs
        x, y = L.top.x + 6, L.top.y + 4
        self.text(screen, info["name"], (x, y + 2), fs + 5, t.ink, bold=True, maxw=L.top.w * 0.22)
        self.text(screen, info["subtitle"], (x, y + fs + 14), fs - 2, t.ink_soft, maxw=L.top.w * 0.24)
        hx = L.top.x + int(L.top.w * (0.22 if L.W < 800 else 0.25))
        slots = info.get("slots", 6)
        row_h = max(16, (L.top.h - 6) // 3)
        sc = max(2, min(3, (row_h - 4) // 6))
        if L.W < 800:
            sc = 2
        label_w = int(fs * 4.6)
        L.hearts_rect = pygame.Rect(hx, y, label_w + slots * 8 * sc, row_h * 3)
        if info["show_hearts"]:
            rows = (("Hunger", info["hunger"], HEART_RED), ("Happy", info["happy"], (240, 110, 170)),
                    ("Health", info["health"], (80, 190, 130)))
            for r, (label, n, col) in enumerate(rows):
                ry = y + r * row_h
                self.text(screen, label, (hx, ry + (row_h - fs) // 2 - 1), fs - 2, t.ink_soft, bold=True)
                self.hearts(screen, hx + label_w, ry + (row_h - 6 * sc) // 2, n, sc, slots, col,
                            info.get("poke", 0.0))
        ax = L.hearts_rect.right + 12
        if info["attention"]:
            r = pygame.Rect(ax, y + row_h - 4, fs + 10, fs + 10)
            pygame.draw.rect(screen, (240, 90, 100), r, border_radius=8)
            self.text(screen, "!", (r.centerx, r.y + 1), fs + 2, WHITE, bold=True, align="center")
        first = min(r.x for r in L.toggles.values())
        tx = first - 12
        f = self.font(fs - 2)
        if tx - f.size(info["clock"])[0] > L.hearts_rect.right + fs + 22:
            a = self.text(screen, info["age"], (tx, y + 4), fs - 1, t.ink, bold=True, align="right")
            cl = self.text(screen, info["clock"], (tx, y + fs + 12), fs - 2, t.ink_soft, align="right")
            L.clock_rect = a.union(cl)
        else:      # narrow window: keep the clock, drop the weekday
            short = info["clock"].split()[-1]
            cl = self.text(screen, short, (tx, y + fs // 2 + 6), fs - 2, t.ink, bold=True, align="right")
            L.clock_rect = cl
        mouse = pygame.mouse.get_pos()
        for name, rect in L.toggles.items():
            if info.get("poke_toggle") == name:
                rect = rect.move(0, 2 if int(pygame.time.get_ticks() / 90) % 2 else 0)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(screen, t.button_hover if hover else t.button, rect, border_radius=10)
            pygame.draw.rect(screen, t.shell_edge, rect, 2, border_radius=10)
            if name == "sound":
                icon = "sound_on" if info["sound"] else "sound_off"
            elif name == "pause":
                icon = "resume" if info["paused"] else "pause"
            else:
                icon = name
            sc2 = max(2, (rect.w - 10) // 8)
            img = self.icon(icon, sc2, (t.icon_ink, (190, 200, 230)))
            screen.blit(img, img.get_rect(center=rect.center))
            if info.get("poke_toggle") == name:          # your pet is pressing this button
                pygame.draw.rect(screen, (255, 210, 120), rect, 3, border_radius=10)
            if name == "speed" and info["speed"] != 1:
                self.text(screen, f"{info['speed']}x", (rect.centerx, rect.bottom + 1), fs - 4,
                          (220, 80, 90), bold=True, align="center")

    def draw_buttons(self, screen, L, disabled, hover, flash=None):
        t = self.t
        fs = L.fs
        for i, rect in enumerate(L.buttons):
            name = ACTION_IDS[i]
            off = name in disabled
            col = t.button if not off else t.button_off
            if hover == i and not off:
                col = t.button_hover
            r = rect.move(0, -2) if hover == i and not off else rect
            self.panel(screen, r, col, radius=16, shadow=not off)
            if flash == name:
                pygame.draw.rect(screen, (250, 120, 120), r, 3, border_radius=16)
            sc = max(2, min(4, int(r.h * 0.45) // 12))
            img = self.icon(name, sc)
            if off:
                img = img.copy()
                img.set_alpha(80)
            screen.blit(img, img.get_rect(midtop=(r.centerx, r.y + int(r.h * 0.12))))
            self.text(screen, ACTION_LABELS[i], (r.centerx, r.bottom - fs - 8), fs - 1,
                      t.ink if not off else t.ink_soft, bold=True, align="center")
            self.text(screen, str(i + 1), (r.x + 8, r.y + 4), fs - 5, t.ink_soft)

    def draw_message(self, screen, L, text, alpha):
        if not text or alpha <= 0:
            return
        f = self.font(L.fs, True)
        img = f.render(text, True, self.t.ink)
        if img.get_width() > L.msg.w - 30:
            img = pygame.transform.smoothscale(
                img, (L.msg.w - 30, int(img.get_height() * (L.msg.w - 30) / img.get_width())))
        box = img.get_rect(center=L.msg.center).inflate(30, 10)
        bubble = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(bubble, self.t.msg_bg, bubble.get_rect(), border_radius=box.h // 2)
        bubble.blit(img, img.get_rect(center=(box.w // 2, box.h // 2)))
        bubble.set_alpha(int(alpha * 255))
        screen.blit(bubble, box)

    # ---- menus -------------------------------------------------------------------------------
    def draw_menu(self, screen, L, menu):
        t = self.t
        fs = L.fs + 2
        row = int(fs * 2.1)
        w = min(int(L.lcd.w * 0.72), 460)
        h = int(fs * 2.6) + row * len(menu.items) + int(fs * 2.0)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = L.lcd.center
        self.panel(screen, rect, radius=20)
        self.text(screen, menu.title, (rect.centerx, rect.y + 12), fs + 2, t.ink, bold=True, align="center")
        menu.rects = []
        y = rect.y + int(fs * 2.6)
        mouse = pygame.mouse.get_pos()
        for i, (label, value, note) in enumerate(menu.items):
            r = pygame.Rect(rect.x + 14, y, rect.w - 28, row - 6)
            if r.collidepoint(mouse):
                menu.sel = i
            if value == "__shop__":
                pygame.draw.line(screen, t.panel_alt, (r.x, r.y - 3), (r.right, r.y - 3), 2)
                pygame.draw.rect(screen, (255, 226, 150) if not t.dark else (110, 90, 40), r.inflate(-4, -4),
                                 border_radius=12)
                if i == menu.sel:
                    pygame.draw.rect(screen, (230, 170, 50), r.inflate(-4, -4), 2, border_radius=12)
                cw = self.coin(screen, r.x + 16, r.y + (r.h - 12) // 2, 2)
                self.text(screen, f"{i + 1}.  Shop", (r.x + 24 + cw, r.y + (r.h - fs) // 2 - 2), fs, t.ink, bold=True)
                self.text(screen, note, (r.right - 14, r.y + (r.h - fs) // 2), fs - 3, t.ink, bold=True, align="right")
                menu.rects.append(r)
                y += row
                continue
            if i == menu.sel:
                pygame.draw.rect(screen, t.select, r, border_radius=12)
                pygame.draw.rect(screen, t.select_edge, r, 2, border_radius=12)
            self.text(screen, f"{i + 1}.  {label}", (r.x + 14, r.y + (r.h - fs) // 2 - 2), fs, t.ink, bold=True)
            if note:
                self.text(screen, note, (r.right - 14, r.y + (r.h - fs) // 2), fs - 3, t.ink_soft, align="right")
            menu.rects.append(r)
            y += row
        self.text(screen, menu.hint or "Click, or Up/Down + Enter.  Esc to close.",
                  (rect.centerx, rect.bottom - int(fs * 1.6)), fs - 4, t.ink_soft, align="center")
        self.hit["menu_panel"] = rect

    def coin(self, surf, x, y, scale=2):
        key = ("coin", scale)
        if key not in self._icons:
            self._icons[key] = pixel_icon(COIN_ROWS, (200, 140, 30), (255, 214, 90), scale)
        surf.blit(self._icons[key], (x, y))
        return self._icons[key].get_width()

    def draw_shop(self, screen, L, items, icons, coins, tab, sel, pet_name):
        """A separate shop window: pick a treat or toy; it's used straight away."""
        t = self.t
        fs = L.fs
        rect = pygame.Rect(L.shell.x + 30, L.top.bottom + 10, L.shell.w - 60, L.shell.bottom - L.top.bottom - 40)
        dim = pygame.Surface((L.W, L.H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 90))
        screen.blit(dim, (0, 0))
        self.panel(screen, rect, radius=24)
        pygame.draw.rect(screen, t.select_edge, rect, 3, border_radius=24)
        self._close_button(screen, rect, fs)
        x, y = rect.x + 26, rect.y + 18
        self.text(screen, "Shop", (x, y), fs + 8, t.ink, bold=True)
        cx = x + self.font(fs + 8, True).size("Shop")[0] + 24
        w = self.coin(screen, cx, y + 8, max(2, fs // 6))
        self.text(screen, f"{coins} coins", (cx + w + 8, y + 6), fs + 1, t.ink, bold=True)
        self.text(screen, f"Everything is used straight away. Win games to earn coins.  ({pet_name} may have "
                  "opinions.)", (x, y + fs + 20), fs - 3, t.ink_soft, maxw=rect.w - 60)
        self.hit["shop_tabs"] = []
        tx = x
        ty = y + 2 * fs + 34
        for name, key in (("Treats", "food"), ("Toys", "toy")):
            wdt = self.font(fs, True).size(name)[0] + 34
            r = pygame.Rect(tx, ty, wdt, fs + 16)
            pygame.draw.rect(screen, t.tab_on if key == tab else t.panel_alt, r, border_radius=12)
            self.text(screen, name, (r.centerx, r.y + 7), fs, t.ink, bold=True, align="center")
            self.hit["shop_tabs"].append(r)
            tx += wdt + 8
        self.text(screen, "Arrows choose, Enter buys, Tab switches, Esc closes", (rect.right - 26, ty + 8), fs - 4,
                  t.ink_soft, align="right")
        grid = pygame.Rect(x, ty + fs + 28, rect.w - 52, rect.bottom - ty - fs - 44)
        cols = 3
        rows = (len(items) + cols - 1) // cols
        gap = 14
        cw = (grid.w - gap * (cols - 1)) // cols
        ch = (grid.h - gap * (rows - 1)) // max(1, rows)
        self.hit["shop_cards"] = []
        mouse = pygame.mouse.get_pos()
        for i, it in enumerate(items):
            card = pygame.Rect(grid.x + (i % cols) * (cw + gap), grid.y + (i // cols) * (ch + gap), cw, ch)
            if card.collidepoint(mouse):
                sel = i
            col = t.select if i == sel else t.panel_alt
            pygame.draw.rect(screen, col, card, border_radius=16)
            if i == sel:
                pygame.draw.rect(screen, t.select_edge, card, 2, border_radius=16)
            img = icons.get(it["id"])
            k = max(2, min(6, (ch - 3 * fs - 30) // 10))
            if img:
                big = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))
                screen.blit(big, big.get_rect(midtop=(card.x + 18 + 4 * k, card.y + 14)))
            tx = card.x + 30 + 8 * k
            self.text(screen, it["name"], (tx, card.y + 12), fs, t.ink, bold=True, maxw=card.right - tx - 10)
            cw2 = self.coin(screen, tx, card.y + fs + 20, 2)
            self.text(screen, str(it["price"]), (tx + cw2 + 6, card.y + fs + 16), fs - 1,
                      t.ink if it["afford"] else (210, 90, 90), bold=True)
            if it.get("tag"):
                tag_col = (220, 80, 120) if it["tag"] == "loves this" else t.ink_soft
                self.text(screen, f"{pet_name} {it['tag']}", (tx + cw2 + 40, card.y + fs + 17), fs - 4, tag_col,
                          bold=True, maxw=card.right - tx - cw2 - 46)
            lines = self.wrap(it["desc"], fs - 3, card.w - 24)
            ly = card.y + 2 * fs + 26
            for line in lines[:2]:
                if ly < card.bottom - fs - 24:
                    self.text(screen, line, (card.x + 14, ly), fs - 3, t.ink_soft)
                ly += fs
            btn = pygame.Rect(0, 0, min(card.w - 28, fs * 8), fs + 12)
            btn.bottomright = (card.right - 12, card.bottom - 10)
            enabled = it["afford"] and it["usable"]
            label = "Buy & use" if enabled else (it["why"] or "Not enough coins") if it["afford"] else "Not enough coins"
            self.pill_button(screen, btn, label, fs - 3, on=enabled, enabled=enabled)
            self.hit["shop_cards"].append((it["id"], card, btn))

    def _panel_rect(self, L):
        return L.bezel.inflate(-10, -10)

    def _close_button(self, screen, rect, fs):
        cb = pygame.Rect(rect.right - fs * 2 - 10, rect.y + 10, fs * 2, fs * 2)
        pygame.draw.rect(screen, self.t.panel_alt, cb, border_radius=10)
        self.text(screen, "x", (cb.centerx, cb.y + fs // 4), fs, self.t.ink, bold=True, align="center")
        self.hit["close"] = cb

    def draw_status(self, screen, L, c, info):
        t = self.t
        fs = L.fs
        rect = self._panel_rect(L)
        self.panel(screen, rect, radius=22)
        self._close_button(screen, rect, fs)
        x, y = rect.x + 26, rect.y + 18
        self.text(screen, f"{c.name}", (x, y), fs + 8, t.ink, bold=True)
        self.text(screen, info["subtitle"], (x, y + fs + 16), fs - 1, t.ink_soft)
        img = info.get("sprite")
        if img is not None:
            k = max(2, min(5, rect.h // 110))
            big = pygame.transform.scale(img, (32 * k, 32 * k))
            screen.blit(big, (rect.right - 32 * k - 30, rect.y + fs * 3))
        sc = max(2, fs // 6)
        y += int(fs * 3.6)
        if c.stage == "egg":
            self.text(screen, "A warm egg. It will hatch soon!", (x, y), fs + 1, t.ink)
            return
        col2 = x + int(fs * 7)
        slots = info.get("slots", 6)
        for label, val, col in (("Hunger", c.hunger, HEART_RED), ("Happy", c.happiness, (240, 110, 170)),
                                ("Health", c.health, (80, 190, 130))):
            self.text(screen, label, (x, y), fs, t.ink, bold=True)
            self.hearts(screen, col2, y + 2, c.hearts(val, slots), sc, slots, col)
            y += int(fs * 1.9)
        y += int(fs * 0.3)
        bar_w = min(int(rect.w * 0.34), 260)

        def bar(label, value, color, y):
            self.text(screen, label, (x, y), fs, t.ink, bold=True)
            r = pygame.Rect(col2, y + 3, bar_w, fs - 2)
            pygame.draw.rect(screen, t.bar_bg, r, border_radius=8)
            fill = r.copy()
            fill.w = max(0, int(r.w * value / 100.0))
            if fill.w:
                pygame.draw.rect(screen, color, fill, border_radius=8)

        bar("Discipline", c.discipline, (240, 170, 70), y)
        y += int(fs * 1.9)
        bar("Energy", c.energy, (110, 190, 140), y)
        y += int(fs * 1.9)
        bar("Hygiene", c.hygiene, (110, 170, 230), y)
        y += int(fs * 2.3)
        rows = [
            ("Age", info["age_long"]),
            ("Weight", f"{int(c.weight)} g" + ("  (chubby!)" if c.is_overweight() else
                                               "  (a bit thin)" if c.is_underweight() else "")),
            ("Condition", "Sick - needs medicine" if c.sick else ("Sleeping" if c.asleep else "Healthy")),
            ("Seems", c.personality.hint()),
        ]
        fav_food = c.memory.favourite_food()
        fav_game = c.memory.favourite_game()
        if fav_food:
            rows.append(("Loves", FOODS[fav_food]["name"]))
        if fav_game:
            rows.append(("Fave game", GAMES[fav_game]))
        for label, value in rows:
            if y > rect.bottom - fs * 2:
                break
            self.text(screen, label, (x, y), fs - 1, t.ink_soft)
            self.text(screen, value, (col2, y), fs - 1, t.ink, bold=True)
            y += int(fs * 1.6)

    def draw_records(self, screen, L, records, c, tab, can_new_gen, info):
        t = self.t
        fs = L.fs
        rect = self._panel_rect(L)
        self.panel(screen, rect, radius=22)
        self._close_button(screen, rect, fs)
        tabs = ["Collection", "Family", "Records", "Diary", "Bond"]
        self.hit["tabs"] = []
        tx = rect.x + 20
        for i, name in enumerate(tabs):
            f = self.font(fs, True)
            w = f.size(name)[0] + 30
            r = pygame.Rect(tx, rect.y + 14, w, fs + 16)
            pygame.draw.rect(screen, t.tab_on if i == tab else t.panel_alt, r, border_radius=12)
            self.text(screen, name, (r.centerx, r.y + 7), fs, t.ink, bold=True, align="center")
            self.hit["tabs"].append(r)
            tx += w + 8
        body = pygame.Rect(rect.x + 20, rect.y + fs + 44, rect.w - 40, rect.h - fs - 60)
        self.hit["newgen"] = None
        if tab == 0:
            self._draw_collection(screen, body, records, fs)
        elif tab == 1:
            self._draw_family(screen, body, records, c, fs, can_new_gen)
        elif tab == 2:
            self._draw_stats(screen, body, records, c, fs, info)
        elif tab == 3:
            self._draw_diary(screen, body, info.get("journal"), info.get("phrasebook", []), fs,
                             info.get("diary_scroll", 0))
        else:
            self._draw_bond(screen, body, info.get("bond") or {}, fs)

    def _draw_collection(self, screen, body, records, fs):
        t = self.t
        order = {"baby": 0, "child": 1, "teen": 2, "adult": 3}
        ids = sorted(self.db, key=lambda sid: (order.get(self.db[sid]["stage"], 9),
                                              bool(self.db[sid].get("secret")),
                                              self.db[sid].get("line", "land") == "water"))
        found = sum(1 for s in ids if s in records.discovered)
        self.text(screen, f"Discovered {found} / {len(ids)}", (body.x, body.y), fs, t.ink_soft, bold=True)
        avail = body.h - fs - 12
        cols, size, label = 7, 32, True
        for cols in (7, 10, 14):                       # fit all forms, whatever the window size
            rows = (len(ids) + cols - 1) // cols
            cw = body.w // cols
            label = avail // rows >= 34 + fs and cw >= 48
            size = min(cw - 10, avail // rows - (fs + 4 if label else 6) - 8, 128)
            if size >= 28:
                break
        size = max(14, size)
        ch = avail // rows
        y0 = body.y + fs + 12
        for i, sid in enumerate(ids):
            sp = self.db[sid]
            cx = body.x + (i % cols) * cw + cw // 2
            cy = y0 + (i // cols) * ch
            seen = sid in records.discovered
            if seen:
                img, name = self.r.preview(sid), sp["name"]
            elif sp.get("secret"):
                img, name = None, "???"
            else:
                img, name = self.r.silhouette(sid), "???"
            box = pygame.Rect(0, 0, size + 6, size + 6)
            box.midtop = (cx, cy)
            pygame.draw.rect(screen, t.panel_alt if seen else t.button_off, box, border_radius=8)
            if img is not None:
                screen.blit(pygame.transform.scale(img, (size, size)), (box.x + 3, box.y + 3))
            else:
                self.text(screen, "?", (box.centerx, box.y + box.h // 2 - fs // 2 - 2), fs, t.ink_soft,
                          bold=True, align="center")
            if label:
                text = name + (" *" if sp.get("secret") and seen else "")
                self.text(screen, text, (cx, box.bottom + 2), fs - 3, t.ink if seen else t.ink_soft,
                          bold=seen, align="center", maxw=cw - 4)

    def _draw_family(self, screen, body, records, c, fs, can_new_gen):
        t = self.t
        y = body.y
        rows = [{"generation": c.generation, "name": c.name, "forms": c.forms,
                 "days": round(c.age_days, 2), "reason": "current"}]
        rows += list(reversed(records.lineage))
        for e in rows:
            if y > body.bottom - fs * 4:
                self.text(screen, "...", (body.x, y), fs, t.ink_soft)
                break
            forms = [self.db[f]["name"] for f in e.get("forms", []) if f in self.db]
            chain = " > ".join(["Egg"] + forms)
            tag = "(now)" if e["reason"] == "current" else ("journeyed on" if e["reason"] == "journey"
                                                            else "lived a full life")
            self.text(screen, f"Gen {e['generation']}  {e['name']}", (body.x, y), fs, t.ink, bold=True)
            self.text(screen, f"{e['days']:.1f} days  {tag}", (body.right, y), fs - 2, t.ink_soft, align="right")
            self.text(screen, chain, (body.x + 18, y + fs + 5), fs - 3, t.ink_soft, maxw=body.w - 30)
            y += int(fs * 3.0)
        if can_new_gen is not None:
            r = pygame.Rect(0, 0, min(body.w, fs * 22), fs + 22)
            r.midbottom = (body.centerx, body.bottom)
            ok = can_new_gen is True
            self.pill_button(screen, r, "Begin a new generation" if ok else can_new_gen, fs - 1,
                             on=ok, enabled=ok)
            if ok:
                self.hit["newgen"] = r

    def _draw_stats(self, screen, body, records, c, fs, info):
        t = self.t
        tot = records.combined_totals(c)
        longest = records.longest
        gifts = records.gifts
        gift_text = ", ".join(f"{n} {k}{'s' if n > 1 else ''}" for k, n in gifts.items() if n) or "None yet"
        rows = [
            ("Generations raised", str(len(records.lineage) + 1)),
            ("Longest-lived", f"{longest['name']} ({longest['final_name']}), {longest['days']:.1f} days"
             if longest else "-"),
            ("Rare discoveries", ", ".join(records.rare) if records.rare else "None yet"),
            ("Gifts received", gift_text),
            ("Coins (have / earned / spent)", "%d / %d / %d" % info.get("coins", (0, 0, 0))),
            ("Invented games", info.get("inventions") or "None yet"),
            ("Souvenirs", info.get("souvenirs") or "None yet"),
            ("Meals / snacks", f"{tot['meals']} / {tot['snacks']}"),
            ("Games played / won", f"{tot['games']} / {tot['wins']}"),
            ("Clean-ups", str(tot["cleans"])),
            ("Medicine given", str(tot["medicine"])),
            ("Praise / scolding", f"{tot['praises']} / {tot['scolds']}"),
            ("Care mistakes (this life)", str(c.care_mistakes)),
            ("Started", info.get("started", "-")),
        ]
        y = body.y
        for label, value in rows:
            if y > body.bottom - fs:
                break
            self.text(screen, label, (body.x, y), fs - 1, t.ink_soft)
            self.text(screen, value, (body.x + int(body.w * 0.42), y), fs - 1, t.ink, bold=True,
                      maxw=int(body.w * 0.58))
            y += int(fs * 1.75)

    # ---- diary -----------------------------------------------------------------------------
    def wrap(self, text, size, maxw, bold=False):
        f = self.font(size, bold)
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if f.size(trial)[0] <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def diary_icon(self, name, k=2):
        icons = getattr(self, "diary_icons", {}) or {}
        img = icons.get(name) or icons.get("star")
        if img is None:
            return None
        key = ("diary", name, k)
        if key not in self._icons:
            w, h = img.get_size()
            scale = k if max(w, h) <= 8 else max(1, (8 * k) // max(w, h))
            self._icons[key] = pygame.transform.scale(img, (w * scale, h * scale))
        return self._icons[key]

    def _entry_rows(self, screen, x, y, w, entries, fs, bottom, stamp, label):
        t = self.t
        for e in entries:
            lines = self.wrap(label(e), fs - 2, w - 120)
            h = max(fs + 6, len(lines) * (fs + 2)) + 8
            if y + h > bottom:
                return y, False
            icon = self.diary_icon(e.get("icon", "star"))
            if icon:
                screen.blit(icon, icon.get_rect(center=(x + 10, y + fs // 2 + 3)))
            self.text(screen, stamp(e), (x + 26, y + 1), fs - 4, t.ink_soft)
            for i, line in enumerate(lines):
                self.text(screen, line, (x + 110, y + i * (fs + 2)), fs - 2,
                          t.ink, bold=bool(e.get("important")))
            y += h
        return y, True

    def _draw_diary(self, screen, body, journal, phrasebook, fs, scroll):
        t = self.t
        y = body.y
        if phrasebook:
            self.text(screen, "Signals you share", (body.x, y), fs - 1, t.ink, bold=True)
            y += fs + 6
            for sig, meaning in phrasebook:
                self.text(screen, f"{sig}  =  wants {meaning}", (body.x + 16, y), fs - 3, t.ink_soft)
                y += fs + 2
            y += 6
        if journal is None or not journal.entries:
            self.text(screen, "Nothing yet. Interesting moments will be written here.", (body.x, y), fs - 2,
                      t.ink_soft)
            return
        entries = journal.recent(200)[scroll:]
        if body.w > 620 and not phrasebook:
            self.text(screen, "Newest first.  Scroll with the mouse wheel.", (body.right, body.y), fs - 4,
                      t.ink_soft, align="right")
            y = max(y, body.y + fs)
        from .journal import Journal
        self._entry_rows(screen, body.x, y, body.w, entries, fs, body.bottom, Journal.stamp, Journal.label)

    def draw_away(self, screen, L, title, entries, more):
        from .journal import Journal
        t = self.t
        fs = L.fs
        rect = self._panel_rect(L).inflate(-40, -30)
        self.panel(screen, rect, radius=22)
        pygame.draw.rect(screen, t.select_edge, rect, 2, border_radius=22)
        self.text(screen, title, (rect.x + 24, rect.y + 18), fs + 6, t.ink, bold=True)
        bottom = rect.bottom - fs * 3 - 20
        y, _ = self._entry_rows(screen, rect.x + 24, rect.y + fs * 3 + 20, rect.w - 48, entries, fs, bottom,
                                Journal.stamp, Journal.label)
        if more:
            self.text(screen, f"...and {more} more in the diary.", (rect.x + 24, y + 4), fs - 3, t.ink_soft)
        ok = pygame.Rect(0, 0, fs * 6, fs + 20)
        diary = pygame.Rect(0, 0, fs * 10, fs + 20)
        ok.bottomright = (rect.right - 24, rect.bottom - 18)
        diary.bottomright = (ok.left - 12, rect.bottom - 18)
        self.pill_button(screen, diary, "Open diary", fs - 1)
        self.pill_button(screen, ok, "OK", fs - 1, on=True)
        self.hit["away_ok"], self.hit["away_diary"] = ok, diary

    # ---- observation mode (developer view) --------------------------------------------------
    OBS_PAGES = (("Now", ("Now", "Model of you")),
                 ("Memory", ("Memories", "Rituals", "Beliefs")),
                 ("Learning", ("Signals and experiments", "Object skills")),
                 ("World", ("Room as it remembers it", "Rare events", "Eligible right now", "Mirror")),
                 ("Trace", ()))

    def draw_observation(self, screen, L, snapshot, page, trace_lines):
        fs = max(12, L.fs - 2)
        W, H = L.W, L.H
        over = pygame.Surface((W, H), pygame.SRCALPHA)
        over.fill((10, 12, 20, 236))
        screen.blit(over, (0, 0))
        ink, soft, accent = (220, 235, 225), (140, 170, 160), (120, 230, 170)
        self.text(screen, "Observation Mode", (24, 16), fs + 6, accent, bold=True)
        self.text(screen, "Developer view of the creature's internal state.  Left/Right pages,  E export log,  "
                  "F9 or Esc close", (24, 16 + fs + 12), fs - 2, soft)
        self.hit["obs_tabs"] = []
        tx = 24
        for i, (name, _) in enumerate(self.OBS_PAGES):
            w = self.font(fs, True).size(name)[0] + 24
            r = pygame.Rect(tx, 16 + 2 * fs + 26, w, fs + 12)
            pygame.draw.rect(screen, (40, 80, 64) if i == page else (30, 36, 44), r, border_radius=8)
            self.text(screen, name, (r.centerx, r.y + 5), fs, ink, bold=True, align="center")
            self.hit["obs_tabs"].append(r)
            tx += w + 8
        exp = pygame.Rect(W - 24 - fs * 9, 16, fs * 9, fs + 12)
        pygame.draw.rect(screen, (40, 80, 64), exp, border_radius=8)
        self.text(screen, "Export log (E)", (exp.centerx, exp.y + 5), fs - 1, ink, bold=True, align="center")
        self.hit["obs_export"] = exp
        top = 16 + 3 * fs + 50
        body = pygame.Rect(24, top, W - 48, H - top - 20)
        if page == len(self.OBS_PAGES) - 1:
            self.text(screen, "Reasoning trace (newest first) - why each behaviour happened", (body.x, body.y),
                      fs, accent, bold=True)
            y = body.y + fs + 10
            for line in trace_lines:
                for part in self.wrap(line, fs - 2, body.w - 10):
                    if y > body.bottom - fs:
                        return
                    self.text(screen, part, (body.x, y), fs - 2, ink)
                    y += fs + 1
                y += 3
            return
        wanted = self.OBS_PAGES[page][1]
        sections = [(t, rows) for t, rows in snapshot if t in wanted]
        col_w = (body.w - 30) // 2
        cols = [body.y, body.y]
        for title, rows in sections:
            col = 0 if cols[0] <= cols[1] else 1
            x, y = body.x + col * (col_w + 30), cols[col]
            self.text(screen, title, (x, y), fs + 1, accent, bold=True)
            y += fs + 8
            for row in rows:
                for part in self.wrap(row, fs - 2, col_w - 10):
                    if y > body.bottom - fs:
                        break
                    self.text(screen, part, (x + 8, y), fs - 2, ink)
                    y += fs + 1
            cols[col] = y + 14

    # ---- bond: shared memories & observation lab ----------------------------------------------
    def _draw_bond(self, screen, body, bond, fs):
        import time as _time
        t = self.t
        lab_open = bond.get("lab_open")
        btn = pygame.Rect(0, 0, fs * 11, fs + 14)
        btn.topright = (body.right, body.y - 2)
        self.pill_button(screen, btn, "Back to memories" if lab_open else "Observation Lab", fs - 3,
                         on=lab_open)
        self.hit["lab_btn"] = btn
        self.hit["export_btn"] = None
        if not lab_open:
            self.text(screen, "Shared Memories", (body.x, body.y), fs, t.ink, bold=True)
            y = body.y + fs + 14
            mems = list(reversed(bond.get("memories", [])))
            if not mems:
                for line in self.wrap("Nothing yet. Moments you and your pet share - copying each other, "
                                      "signals you both understand, rituals, drawings - will be kept here.",
                                      fs - 2, body.w - 20):
                    self.text(screen, line, (body.x, y), fs - 2, t.ink_soft)
                    y += fs + 2
                return
            for m in mems:
                lines = self.wrap(m["text"], fs - 2, body.w - 130)
                if y + len(lines) * (fs + 2) > body.bottom:
                    self.text(screen, "...", (body.x, y), fs - 2, t.ink_soft)
                    break
                self.text(screen, _time.strftime("%d %b %H:%M", _time.localtime(m["wt"])), (body.x, y + 1),
                          fs - 4, t.ink_soft)
                for i, line in enumerate(lines):
                    self.text(screen, line, (body.x + 110, y + i * (fs + 2)), fs - 2, t.ink)
                y += len(lines) * (fs + 2) + 8
            return
        exp = pygame.Rect(0, 0, fs * 9, fs + 14)
        exp.topright = (btn.left - 10, body.y - 2)
        self.pill_button(screen, exp, "Export report", fs - 3)
        self.hit["export_btn"] = exp
        self.text(screen, "Observation Lab", (body.x, body.y), fs, t.ink, bold=True)
        sections = bond.get("lab") or []
        col_w = (body.w - 20) // 2
        cols = [body.y + fs + 14, body.y + fs + 14]
        size = max(10, fs - 4)
        for title, rows in sections:
            need = (len(rows) + 1) * (size + 3) + 8
            col = 0 if cols[0] <= cols[1] else 1
            x = body.x + col * (col_w + 20)
            y = cols[col]
            if y + need > body.bottom + size * 2:
                other = 1 - col
                if cols[other] + need <= body.bottom + size * 2:
                    col = other
                    x = body.x + col * (col_w + 20)
                    y = cols[col]
                else:
                    continue
            self.text(screen, title, (x, y), size + 1, t.ink, bold=True, maxw=col_w)
            y += size + 5
            for row in rows:
                if y > body.bottom - size:
                    break
                self.text(screen, row, (x + 8, y), size, t.ink_soft, maxw=col_w - 8)
                y += size + 3
            cols[col] = y + 8

    # ---- settings ----------------------------------------------------------------------------
    def draw_settings(self, screen, L, prefs, pet_hue, sound_on):
        t = self.t
        fs = L.fs
        rect = pygame.Rect(L.shell.x + 14, L.top.bottom + 6, L.shell.w - 28, L.shell.bottom - L.top.bottom - 20)
        gap = fs + (34 if rect.h > 520 else 22)
        self.panel(screen, rect, radius=22)
        self._close_button(screen, rect, fs)
        x, y = rect.x + 28, rect.y + 18
        self.text(screen, "Settings", (x, y), fs + 8, t.ink, bold=True)
        y += int(fs * (3.2 if rect.h > 520 else 2.4))

        # theme colour swatches
        self.text(screen, "Theme colour", (x, y), fs + 1, t.ink, bold=True)
        y += int(fs * 2.0)
        size = max(26, min(56, (rect.w - 60) // len(THEME_SWATCHES) - 14, rect.h // 11))
        self.hit["swatches"] = []
        sx = x
        for value, label in THEME_SWATCHES:
            hue = pet_hue if value == "pet" else value
            r = pygame.Rect(sx, y, size, size)
            selected = prefs.get("theme_hue", "pet") == value
            if selected:
                pygame.draw.rect(screen, t.select_edge, r.inflate(8, 8), 3, border_radius=size // 2 + 4)
            pygame.draw.circle(screen, hsv(hue, 0.30, 0.95), r.center, size // 2)
            pygame.draw.circle(screen, hsv(hue, 0.55, 0.75), r.center, size // 2, 3)
            if value == "pet":
                paw = self.icon("status", max(1, size // 24), (hsv(hue, 0.6, 0.6), hsv(hue, 0.4, 0.85)))
                screen.blit(paw, paw.get_rect(center=r.center))
            self.text(screen, label, (r.centerx, r.bottom + 6), fs - 4, t.ink_soft if not selected else t.ink,
                      bold=selected, align="center")
            self.hit["swatches"].append((r.inflate(8, 8), value))
            sx += size + 18
        y += size + fs + (22 if rect.h > 520 else 12)

        # light / dark
        self.text(screen, "Appearance", (x, y + 6), fs + 1, t.ink, bold=True)
        bx = x + int(fs * 9)
        bw = max(fs * 5, 90)
        light = pygame.Rect(bx, y, bw, fs + 18)
        dark = pygame.Rect(bx + bw + 10, y, bw, fs + 18)
        self.pill_button(screen, light, "Light", fs - 1, on=not prefs.get("dark"))
        self.pill_button(screen, dark, "Dark", fs - 1, on=bool(prefs.get("dark")))
        self.hit["light"], self.hit["dark"] = light, dark
        y += gap

        # sound
        self.text(screen, "Sound", (x, y + 6), fs + 1, t.ink, bold=True)
        snd = pygame.Rect(bx, y, bw * 2 + 10, fs + 18)
        self.pill_button(screen, snd, "Sound on  (M)" if sound_on else "Sound off  (M)", fs - 1, on=sound_on)
        self.hit["sound_btn"] = snd
        y += gap

        # desktop roaming (opt-in, Windows only)
        self.text(screen, "Desktop roaming", (x, y + 6), fs + 1, t.ink, bold=True)
        roam = pygame.Rect(bx, y, bw * 2 + 10, fs + 18)
        supported = prefs.get("_roam_supported", False)
        label = ("Allowed" if prefs.get("roam") else "Not allowed") if supported else "Windows only"
        self.pill_button(screen, roam, label, fs - 1, on=bool(prefs.get("roam")) and supported,
                         enabled=supported)
        self.hit["roam_btn"] = roam if supported else None
        if roam.right + 20 < rect.right - 200:
            self.text(screen, "Lets your pet wander onto your desktop now and then.",
                      (roam.right + 14, y + 8), fs - 4, t.ink_soft, maxw=rect.right - roam.right - 40)
        y += gap

        # experimental behaviours, the mirror, observation mode
        self.text(screen, "Experiments", (x, y + 6), fs + 1, t.ink, bold=True)
        ex = pygame.Rect(bx, y, bw, fs + 18)
        mi = pygame.Rect(bx + bw + 10, y, bw, fs + 18)
        ob = pygame.Rect(bx + 2 * (bw + 10), y, int(bw * 1.4), fs + 18)
        self.pill_button(screen, ex, "Unusual: on" if prefs.get("experimental", True) else "Unusual: off", fs - 3,
                         on=prefs.get("experimental", True))
        self.pill_button(screen, mi, "Mirror: on" if prefs.get("mirror") else "Mirror: off", fs - 3,
                         on=bool(prefs.get("mirror")))
        self.pill_button(screen, ob, "Observation (F9)", fs - 3)
        self.hit["exp_btn"], self.hit["mirror_btn"], self.hit["obs_btn"] = ex, mi, ob
        y += gap

        # reset
        pygame.draw.line(screen, t.panel_alt, (x, y), (rect.right - 28, y), 2)
        y += 14
        self.text(screen, "Reset", (x, y + 6), fs + 1, t.ink, bold=True)
        rw = max(fs * 11, 200)
        soft = pygame.Rect(bx, y, rw, fs + 18)
        hard = pygame.Rect(bx + rw + 10, y, rw, fs + 18)
        if hard.right > rect.right - 20:            # stack on narrow windows
            hard = pygame.Rect(bx, y + fs + 26, rw, fs + 18)
        self.pill_button(screen, soft, "New egg (keep records)", fs - 2)
        self.pill_button(screen, hard, "Erase everything", fs - 2, danger=True)
        self.hit["reset_soft"], self.hit["reset_hard"] = soft, hard
        hint_y = max(hard.bottom, soft.bottom) + 14
        if hint_y < rect.bottom - fs * 3 and rect.h > 520:
            self.text(screen, "A backup of your save is always kept in the saves folder.",
                      (x, hint_y), fs - 4, t.ink_soft)
        self.text(screen, "Keys: O settings, Left/Right theme, D dark mode, Esc close",
                  (rect.centerx, rect.bottom - fs - 10), fs - 4, t.ink_soft, align="center")
        if prefs.get("_version"):
            self.text(screen, f"v{prefs['_version']}", (rect.right - 20, rect.bottom - fs - 10), fs - 4,
                      t.ink_soft, align="right")

    def draw_confirm(self, screen, L, title, lines, yes_label="Yes (Y)", danger=False):
        t = self.t
        fs = L.fs
        rect = pygame.Rect(0, 0, min(L.lcd.w - 40, 540), fs * (len(lines) * 2 + 9))
        rect.center = L.lcd.center
        self.panel(screen, rect, radius=20)
        pygame.draw.rect(screen, t.select_edge, rect, 2, border_radius=20)
        self.text(screen, title, (rect.centerx, rect.y + 16), fs + 3, t.ink, bold=True, align="center")
        y = rect.y + fs * 3 + 10
        for line in lines:
            self.text(screen, line, (rect.centerx, y), fs - 1, t.ink_soft, align="center", maxw=rect.w - 30)
            y += int(fs * 1.7)
        yes = pygame.Rect(0, 0, fs * 9, fs + 20)
        no = yes.copy()
        yes.bottomright = (rect.centerx - 8, rect.bottom - 16)
        no.bottomleft = (rect.centerx + 8, rect.bottom - 16)
        self.pill_button(screen, yes, yes_label, fs - 1, on=True, danger=danger)
        self.pill_button(screen, no, "No (N)", fs - 1)
        self.hit["yes"], self.hit["no"] = yes, no
