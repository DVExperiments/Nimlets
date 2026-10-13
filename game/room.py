"""The single room: background, window with sky/weather, seasonal decor,
mess, day/night lighting, plus small particle effects."""
import math
import random
import time

import pygame

from .config import LCD_W, LCD_H, FLOOR_Y
from .sprites import hsv

WIN = pygame.Rect(102, 10, 44, 30)


def make_sprite(rows, colors):
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w, len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = colors.get(ch)
            if col:
                surf.set_at((x, y), col)
    return surf


FOOD_ART = {
    "rice": (["..####..", ".#wwww#.", "#wwwwww#", "#wwwwww#", "#kkkkkk#", "#kkkkkk#", ".#kkkk#.", "..####.."],
             {"#": (60, 50, 60), "w": (252, 250, 244), "k": (40, 70, 52)}),
    "fish": (["........", "......#.", ".####.##", "#oooo#o#", "#e.ooooo#", "#oooo#o#", ".####.##", "......#."],
             {"#": (40, 60, 90), "o": (110, 170, 230), "e": (20, 20, 30), ".": None}),
    "berries": (["....gg..", "...g....", ".##.##..", "#rr#rr#.", "#rr#rr#.", ".##.##..", "..##....", ".#rr#...", ".#rr#...", "..##...."],
                {"#": (70, 20, 50), "r": (200, 50, 110), "g": (90, 160, 80)}),
    "cake": (["...rr...", "..#rr#..", ".#wwww#.", "#wwwwww#", "#pppppp#", "#wwwwww#", "#pppppp#", "########"],
             {"#": (90, 60, 60), "w": (255, 246, 236), "p": (246, 160, 180), "r": (230, 40, 60)}),
}

POOP = (["...#....", "..#o#...", ".#ooo#..", ".#o#o##.", "#oooooo#", "#ooooooo#", ".######."],
        {"#": (70, 44, 30), "o": (150, 100, 60)})
HEART = ([".#.#.", "#####", "#####", ".###.", "..#.."], {"#": (236, 72, 104)})
NOTE = (["..##", "..#.", "..#.", "###.", "##.."], {"#": (90, 80, 160)})
ZED = (["####", "..#.", ".#..", "####"], {"#": (200, 210, 255)})
SPARK = ([".#.", "###", ".#."], {"#": (255, 226, 110)})
BUBBLE = ([".#######.", "#wwwwwww#", "#www!www#", "#www!www#", "#www!www#", "#wwwwwww#", "#www!www#",
           ".###.###.", "....#...."],
          {"#": (60, 50, 70), "w": (255, 255, 255), "!": (230, 50, 70)})
DARK_BUBBLE = ([".#######.", "#wwwwwww#", "#ww???ww#", "#wwww?ww#", "#www?www#", "#wwwwwww#", "#www?www#",
                ".###.###.", "....#...."],
               {"#": (60, 50, 70), "w": (255, 255, 255), "?": (80, 90, 200)})
GERM = (["..#.#..", ".#ggg#.", "#g#g#g#", ".#ggg#.", "#.#.#.#"], {"#": (60, 110, 50), "g": (150, 210, 90)})
PILL = (["..####..", ".#rrww#.", "#rrrwww#", ".#rrww#.", "..####.."],
        {"#": (60, 50, 70), "r": (230, 70, 90), "w": (250, 250, 250)})
GIFT_ART = {
    "flower": (["..#.#..", ".#p#p#.", "..#y#..", ".#p#p#.", "..#g#..", "...g...", "..gg..."],
               {"#": (200, 70, 110), "p": (255, 150, 190), "y": (255, 220, 80), "g": (90, 160, 80)}),
    "leaf": (["....##.", "...#ll#", "..#lll#", ".#lll#.", "#lll#..", ".##....", "#......"],
             {"#": (150, 70, 30), "l": (236, 140, 50)}),
    "drawing": (["#######", "#wwwwww#", "#w#w#ww#", "#wwwwww#", "#w#ww#w#", "#ww##ww#", "########"],
                {"#": (120, 110, 140), "w": (255, 252, 240)}),
    "pebble": ([".####..", "#ssssw#", "#sssss#", "#ssssw#", ".#####."],
               {"#": (90, 96, 120), "s": (170, 180, 205), "w": (255, 255, 255)}),
}
DREAM_ART = {
    "fishlegs": (["......#.", "..####.##", ".#oooo#o#", ".#oooooo#", "..####.##", "..#..#...", ".#..#...."],
                 {"#": (40, 60, 90), "o": (110, 170, 230)}),
    "moon": (["..###.", ".##...", "##....", "##....", ".##...", "..###."], {"#": (240, 220, 120)}),
    "ghost": ([".####.", "#o##o#", "######", "######", "#.##.#"], {"#": (200, 200, 230), "o": (40, 40, 60)}),
    "star": ([".#.", "###", ".#."], {"#": (255, 200, 60)}),
    "ball": ([".##.", "#rr#", "#ww#", ".##."], {"#": (150, 40, 50), "r": (230, 70, 80), "w": (255, 255, 255)}),
}

BUBBLE_FX = ([".##.", "#..#", "#.w#", ".##."], {"#": (150, 200, 240), "w": (255, 255, 255)})
LEAF_FX = (["..#", ".##", "#.."], {"#": (90, 160, 80)})
SPECIAL_FOOD = {
    "starfruit": ([".  #  .", "..###..", "#######", ".#####.", "..#.#..", ".#...#."],
                  {"#": (250, 210, 60)}),
    "honey_cake": (["..yy....", ".#yyy#..", "#wwwwww#", "#yyyyyy#", "#wwwwww#", "########"],
                   {"#": (120, 70, 30), "w": (250, 230, 190), "y": (240, 170, 40)}),
    "kelp_crisps": (["#.g..#..", ".gg.#g..", "#g.gg..#", ".gg#.gg.", "g#.gg.#."],
                    {"#": (40, 90, 60), "g": (110, 170, 90)}),
    "fire_pepper": (["....g", "...gg", ".rrr.", "rrrr.", "rrr..", ".r..."],
                    {"g": (80, 150, 70), "r": (230, 50, 40)}),
    "moon_pudding": (["...##...", "..#ww#..", ".#wwyw#.", "#wwwwww#", "########"],
                     {"#": (120, 110, 150), "w": (245, 240, 220), "y": (240, 220, 120)}),
    "golden_apple": (["...g....", "..#g#...", ".#yyy#..", "#yyyyw#.", "#yyyyy#.", ".#yyy#..", "..###..."],
                     {"#": (150, 100, 20), "y": (250, 200, 60), "w": (255, 250, 200), "g": (90, 150, 70)}),
}
TOY_ART = {
    "bubble_wand": (["..##", ".#.#", "..##", ".#..", "#...", "#..."], {"#": (150, 120, 200)}),
    "feather_teaser": (["..w", ".ww", "ww.", "w..", "#.."], {"w": (250, 250, 255), "#": (120, 100, 90)}),
    "music_box": ([".#.....", "######.", "#gggg#.", "#gggg##", "######."], {"#": (120, 70, 40), "g": (230, 180, 90)}),
    "puzzle_cube": (["rrbb", "rrbb", "yygg", "yygg"], {"r": (230, 70, 80), "b": (80, 130, 230),
                                                     "y": (250, 210, 60), "g": (90, 190, 110)}),
    "plush_buddy": (["#..#", "####", "#ww#", "####", "#..#"], {"#": (180, 130, 90), "w": (250, 230, 210)}),
    "yarn_ball": ([".##.", "#pp#", "#pp#", ".##."], {"#": (200, 80, 140), "p": (250, 150, 200)}),
}
BIRD = (["...##..", "..#e#o", ".####o.", "#####..", ".#..#.."], {"#": (70, 110, 210), "o": (250, 180, 60),
                                                                     "e": (255, 255, 255)})

PUMPKIN = (["....g....", "...#g#...", ".##ooo##.", "#oo#o#oo#", "#oo#o#oo#", "#oo#o#oo#", ".#######."],
           {"#": (150, 70, 20), "o": (240, 140, 40), "g": (80, 130, 60)})


class Effects:
    def __init__(self):
        self.parts = []
        self.food = None
        self.flush_t = None
        self.pill = None
        self.sprites = {k: make_sprite(*v) for k, v in
                        {"heart": HEART, "note": NOTE, "zed": ZED, "spark": SPARK, "bubble": BUBBLE_FX,
                         "leaf": LEAF_FX}.items()}
        self.food_sprites = {k: make_sprite(*v) for k, v in FOOD_ART.items()}
        self.pill_sprite = make_sprite(*PILL)

    def add(self, kind, x, y, vx=0.0, vy=-12.0, life=1.3):
        self.parts.append([kind, float(x), float(y), vx, vy, 0.0, life])

    def hearts(self, x, y, n=3):
        for _ in range(n):
            self.add("heart", x + random.uniform(-7, 7), y + random.uniform(-3, 3),
                     random.uniform(-5, 5), random.uniform(-18, -10), 1.4)

    def notes(self, x, y, n=2):
        for _ in range(n):
            self.add("note", x + random.uniform(-8, 8), y, random.uniform(-6, 6), -12, 1.4)

    def sparkles(self, x, y, n=8, spread=30.0):
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(0.3, 1.0) * spread
            self.add("spark", x, y, math.cos(ang) * sp, math.sin(ang) * sp, random.uniform(0.6, 1.2))

    def zzz(self, x, y):
        self.add("zed", x, y, 4, -6, 2.4)

    def show_food(self, food_id, x):
        self.food = [food_id, x, 0.0]

    def flush(self):
        self.flush_t = 0.0

    def show_pill(self, x, y):
        self.pill = [x, y, 0.0]

    def clear(self):
        self.parts.clear()
        self.food = self.pill = self.flush_t = None

    def update(self, dt):
        for p in self.parts:
            p[1] += p[3] * dt
            p[2] += p[4] * dt
            p[5] += dt
        self.parts = [p for p in self.parts if p[5] < p[6]]
        if self.food:
            self.food[2] += dt
            if self.food[2] > 2.4:
                self.food = None
        if self.flush_t is not None:
            self.flush_t += dt
            if self.flush_t > 1.2:
                self.flush_t = None
        if self.pill:
            self.pill[2] += dt
            if self.pill[2] > 1.4:
                self.pill = None

    def draw_floor_layer(self, surf):
        if self.food:
            fid, x, t = self.food
            img = self.food_sprites[fid]
            bites = min(3, int(t / 0.6))
            w = img.get_width()
            keep = max(0, w - bites * 2)
            if keep:
                surf.blit(img, (int(x), FLOOR_Y - img.get_height()), pygame.Rect(0, 0, keep, img.get_height()))
        if self.flush_t is not None:
            x = int(-30 + self.flush_t / 1.2 * (LCD_W + 60))
            wave = pygame.Surface((34, 40), pygame.SRCALPHA)
            wave.fill((150, 210, 255, 170))
            for i in range(0, 34, 4):
                pygame.draw.circle(wave, (230, 245, 255, 220), (i + 2, 3 + (i // 4) % 3), 2)
            surf.blit(wave, (x, FLOOR_Y - 36))

    def draw(self, surf):
        for kind, x, y, vx, vy, age, life in self.parts:
            img = self.sprites[kind]
            if age > life * 0.7:
                img = img.copy()
                img.set_alpha(int(255 * (1 - (age - life * 0.7) / (life * 0.3))))
            surf.blit(img, (int(x), int(y)))
        if self.pill:
            x, y, t = self.pill
            surf.blit(self.pill_sprite, (int(x), int(y - t * 6)))


def sky_color(hour):
    keys = [(0, (22, 28, 64)), (5, (30, 38, 84)), (6.5, (250, 170, 130)), (8, (150, 205, 245)),
            (17, (150, 205, 245)), (18.5, (250, 160, 110)), (20, (40, 48, 96)), (24, (22, 28, 64))]
    for (h0, c0), (h1, c1) in zip(keys, keys[1:]):
        if h0 <= hour <= h1:
            t = (hour - h0) / (h1 - h0)
            return tuple(int(a + (b - a) * t) for a, b in zip(c0, c1))
    return keys[0][1]


def daylight(hour):
    """1 in full day, 0 at night, smooth at dawn/dusk."""
    if 7.5 <= hour <= 17.5:
        return 1.0
    if hour >= 20 or hour <= 5:
        return 0.0
    if hour < 7.5:
        return (hour - 5) / 2.5
    return 1 - (hour - 17.5) / 2.5


SEASONS_NORTH = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
                 6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
FLIP_SEASON = {"winter": "summer", "summer": "winter", "spring": "autumn", "autumn": "spring"}
WEATHER_TABLE = {
    "winter": [("clear", 4), ("cloudy", 3), ("snow", 3)],
    "spring": [("clear", 5), ("cloudy", 2), ("rain", 3)],
    "summer": [("clear", 7), ("cloudy", 2), ("rain", 1)],
    "autumn": [("clear", 4), ("cloudy", 3), ("rain", 3)],
}


class Room:
    def __init__(self, settings):
        self.settings = settings
        self._bg_cache = {}
        self.poop = make_sprite(*POOP)
        self.bubble = make_sprite(*BUBBLE)
        self.dark_bubble = make_sprite(*DARK_BUBBLE)
        self.germ = make_sprite(*GERM)
        self.pumpkin = make_sprite(*PUMPKIN)
        self.gift_sprites = {k: make_sprite(*v) for k, v in GIFT_ART.items()}
        self.dream_sprites = {k: make_sprite(*v) for k, v in DREAM_ART.items()}
        self.food_sprites = {k: make_sprite(*v) for k, v in FOOD_ART.items()}
        self.food_sprites.update({k: make_sprite(*v) for k, v in SPECIAL_FOOD.items()})
        self.toy_sprites = {k: make_sprite(*v) for k, v in TOY_ART.items()}
        self.bird = make_sprite(*BIRD)
        self.anim = {}                 # clickable objects: name -> seconds since poked
        self.dream_sprites.update(self.food_sprites)
        self.dream_sprites["heart"] = make_sprite(*HEART)
        self.dream_sprites["pill"] = make_sprite(*PILL)
        rng = random.Random(4)
        self.stars = [(rng.randint(1, WIN.w - 2), rng.randint(1, WIN.h - 8)) for _ in range(9)]
        self.dirt = [(rng.randint(8, 150), rng.randint(FLOOR_Y - 18, FLOOR_Y + 8)) for _ in range(14)]

    # ---- helpers --------------------------------------------------------------
    def season(self, month):
        s = SEASONS_NORTH[month]
        return FLIP_SEASON[s] if self.settings.get("hemisphere") == "south" else s

    def weather(self, wt, season):
        rng = random.Random(int(wt // 21600) * 7919 + 11)
        table = WEATHER_TABLE[season]
        r = rng.uniform(0, sum(w for _, w in table))
        for name, w in table:
            r -= w
            if r <= 0:
                return name
        return "clear"

    def background(self, hue):
        key = int(hue) // 10
        if key in self._bg_cache:
            return self._bg_cache[key]
        s = pygame.Surface((LCD_W, LCD_H))
        wall, wall_dot = (240, 228, 210), (226, 210, 192)
        s.fill(wall)
        for y in range(4, 74, 8):
            for x in range(4 + (y // 8 % 2) * 4, LCD_W, 8):
                s.set_at((x, y), wall_dot)
        pygame.draw.rect(s, (196, 160, 124), (0, 72, LCD_W, 4))
        pygame.draw.rect(s, (170, 132, 98), (0, 75, LCD_W, 1))
        floor, seam = (214, 170, 128), (186, 142, 104)
        pygame.draw.rect(s, floor, (0, 76, LCD_W, LCD_H - 76))
        for i, y in enumerate(range(76, LCD_H, 7)):
            pygame.draw.line(s, seam, (0, y), (LCD_W, y))
            for x in range((i % 2) * 20, LCD_W, 40):
                pygame.draw.line(s, seam, (x, y), (x, y + 6))
        rug = hsv(hue + 180, 0.25, 0.92)
        rug2 = hsv(hue + 180, 0.35, 0.82)
        pygame.draw.ellipse(s, rug2, (28, FLOOR_Y - 9, 104, 20))
        pygame.draw.ellipse(s, rug, (31, FLOOR_Y - 7, 98, 16))
        pygame.draw.ellipse(s, rug2, (44, FLOOR_Y - 3, 72, 8), 1)
        # picture frame with a little heart
        pygame.draw.rect(s, (150, 106, 74), (12, 16, 24, 20))
        pygame.draw.rect(s, (250, 246, 236), (14, 18, 20, 16))
        s.blit(make_sprite(*HEART), (21, 23))
        # curtains & window sill
        pygame.draw.rect(s, (238, 160, 170), (WIN.x - 6, WIN.y - 3, 6, WIN.h + 8))
        pygame.draw.rect(s, (238, 160, 170), (WIN.right, WIN.y - 3, 6, WIN.h + 8))
        pygame.draw.rect(s, (214, 136, 150), (WIN.x - 6, WIN.y - 3, 1, WIN.h + 8))
        pygame.draw.rect(s, (214, 136, 150), (WIN.right + 5, WIN.y - 3, 1, WIN.h + 8))
        pygame.draw.rect(s, (200, 150, 110), (WIN.x - 4, WIN.bottom + 1, WIN.w + 8, 3))
        self._bg_cache[key] = s
        return s

    # ---- main draw ----------------------------------------------------------
    def draw_scene(self, s, wt, c, t):
        lt = time.localtime(wt)
        hour = lt.tm_hour + lt.tm_min / 60.0
        season = self.season(lt.tm_mon)
        weather = self.weather(wt, season)
        s.blit(self.background(c.genome.get("hue", 0)), (0, 0))
        self.draw_window(s, hour, season, weather, t)
        self.draw_clock(s, lt)
        self.draw_lamp(s, c.lights_on)
        self.draw_decor(s, season, lt.tm_mon, t)
        self.draw_mess(s, c, t)
        return hour, season, weather

    def draw_window(self, s, hour, season, weather, t):
        sky = sky_color(hour)
        if weather != "clear":
            sky = tuple(int(a * 0.6 + b * 0.4) for a, b in zip(sky, (150, 150, 168)))
        s.set_clip(WIN)
        s.fill(sky, WIN)
        dl = daylight(hour)
        if dl < 0.35 and weather == "clear":
            for i, (x, y) in enumerate(self.stars):
                if (int(t * 2) + i) % 5:
                    s.set_at((WIN.x + x, WIN.y + y), (255, 250, 210))
        if 6 <= hour < 19:
            p = (hour - 6) / 13.0
            sx = WIN.x + 4 + p * (WIN.w - 8)
            sy = WIN.bottom - 6 - math.sin(p * math.pi) * (WIN.h - 12)
            if weather != "rain":
                pygame.draw.circle(s, (255, 226, 120), (int(sx), int(sy)), 3)
        else:
            p = ((hour - 19) % 24) / 11.0
            mx = WIN.x + 4 + p * (WIN.w - 8)
            my = WIN.bottom - 6 - math.sin(p * math.pi) * (WIN.h - 12)
            pygame.draw.circle(s, (240, 240, 220), (int(mx), int(my)), 3)
            pygame.draw.circle(s, sky, (int(mx) + 2, int(my) - 1), 2)
        n_clouds = 3 if weather != "clear" else 1
        cloud = (250, 250, 255) if dl > 0.3 else (120, 124, 150)
        for i in range(n_clouds):
            cx = WIN.x + ((t * 2 + i * 19) % (WIN.w + 14)) - 7
            cy = WIN.y + 5 + i * 6
            pygame.draw.ellipse(s, cloud, (cx, cy, 10, 4))
            pygame.draw.ellipse(s, cloud, (cx + 3, cy - 2, 6, 4))
        if weather == "rain":
            for i in range(10):
                x = WIN.x + (i * 9 + int(t * 20)) % WIN.w
                y = WIN.y + (i * 7 + int(t * 50)) % WIN.h
                pygame.draw.line(s, (120, 150, 210), (x, y), (x - 1, y + 3))
        elif weather == "snow":
            for i in range(12):
                x = WIN.x + (i * 11 + int(math.sin(t + i) * 2)) % WIN.w
                y = WIN.y + (i * 5 + int(t * 8)) % WIN.h
                s.set_at((x, y), (255, 255, 255))
        if season == "autumn":
            for i in range(3):
                x = WIN.x + (i * 15 + int(t * 6)) % WIN.w
                y = WIN.y + (i * 9 + int(t * 9)) % WIN.h
                s.fill((226, 120, 50), (x, y, 2, 1))
        s.set_clip(None)
        frame = (160, 112, 78)
        pygame.draw.rect(s, frame, WIN.inflate(4, 4), 2)
        pygame.draw.line(s, frame, (WIN.centerx, WIN.y), (WIN.centerx, WIN.bottom - 1))
        pygame.draw.line(s, frame, (WIN.x, WIN.centery), (WIN.right - 1, WIN.centery))

    def draw_clock(self, s, lt):
        age = self.anim.get("clock")
        cx, cy = 72, 20 - (1 if age is not None and int(age * 8) % 2 == 0 and age < 1.5 else 0)
        if age is not None and age < 1.5:
            for dx in (-12, 12):
                s.set_at((cx + dx, cy - 6 + int(age * 4) % 3), (240, 200, 90))
        pygame.draw.circle(s, (150, 106, 74), (cx, cy), 9)
        pygame.draw.circle(s, (252, 248, 236), (cx, cy), 7)
        h_ang = ((lt.tm_hour % 12) + lt.tm_min / 60.0) / 12.0 * math.tau
        m_ang = lt.tm_min / 60.0 * math.tau
        pygame.draw.line(s, (60, 50, 60), (cx, cy), (cx + math.sin(h_ang) * 4, cy - math.cos(h_ang) * 4))
        pygame.draw.line(s, (200, 70, 80), (cx, cy), (cx + math.sin(m_ang) * 6, cy - math.cos(m_ang) * 6))

    def draw_lamp(self, s, on):
        age = self.anim.get("lamp")
        sway = int(round(math.sin(age * 7) * 3 * max(0.0, 1 - age / 2.5))) if age is not None else 0
        x = 46 + sway
        pygame.draw.line(s, (90, 80, 90), (46, 0), (x, 6))
        pygame.draw.polygon(s, (120, 170, 160) if on else (110, 120, 120),
                            [(x - 6, 12), (x + 6, 12), (x + 3, 6), (x - 3, 6)])
        flicker = age is not None and age < 0.6 and int(age * 20) % 3 == 0
        pygame.draw.circle(s, (255, 236, 150) if on and not flicker else (150, 150, 150), (x, 13), 2)

    def draw_decor(self, s, season, month, t):
        if season == "spring":
            pygame.draw.rect(s, (180, 100, 70), (WIN.x + 2, WIN.bottom - 4, 6, 5))
            pygame.draw.line(s, (90, 160, 80), (WIN.x + 5, WIN.bottom - 4), (WIN.x + 5, WIN.bottom - 9))
            pygame.draw.circle(s, (245, 130, 170), (WIN.x + 5, WIN.bottom - 10), 2)
        elif season == "summer":
            pygame.draw.rect(s, (180, 100, 70), (WIN.x + 2, WIN.bottom - 4, 6, 5))
            pygame.draw.circle(s, (250, 200, 50), (WIN.x + 5, WIN.bottom - 9), 3)
            s.set_at((WIN.x + 5, WIN.bottom - 9), (120, 70, 30))
        elif season == "autumn":
            age = self.anim.get("pumpkin")
            wob = (1 if int(age * 20) % 2 else -1) if age is not None else 0
            s.blit(self.pumpkin, (4 + wob, FLOOR_Y - 22))
        elif season == "winter":
            pygame.draw.rect(s, (255, 255, 255), (WIN.x - 4, WIN.bottom, WIN.w + 8, 2))
        if month == 12:   # festive fairy lights every December
            cols = [(240, 80, 80), (250, 210, 80), (90, 190, 120), (100, 150, 250)]
            for i, x in enumerate(range(4, LCD_W, 8)):
                y = 3 + int(math.sin(x * 0.25) * 1.5)
                on = (i + int(t * 2)) % 3 != 0
                s.set_at((x, y), cols[i % 4] if on else (120, 110, 110))

    def draw_mess(self, s, c, t):
        if c.stage != "egg" and c.hygiene < 45:
            n = int((45 - c.hygiene) / 45 * len(self.dirt)) + 1
            for x, y in self.dirt[:n]:
                s.fill((168, 140, 110), (x, y, 2, 1))
        slots = [126, 112, 138, 100]
        for i in range(min(c.poops, 4)):
            x = slots[i] - 4
            s.blit(self.poop, (x, FLOOR_Y - 7))
            for k in range(2):
                ph = (t * 1.5 + k * 0.5 + i * 0.3) % 1.0
                yy = FLOOR_Y - 10 - int(ph * 6)
                xx = x + 2 + k * 4 + int(math.sin(ph * 6) * 1)
                s.set_at((xx, yy), (130, 150, 110))

    def draw_darkness(self, s, wt, lights_on):
        lt = time.localtime(wt)
        hour = lt.tm_hour + lt.tm_min / 60.0
        if not lights_on:
            alpha = 175
        else:
            alpha = int((1 - daylight(hour)) * 55)
        if alpha <= 0:
            return
        ov = pygame.Surface((LCD_W, LCD_H), pygame.SRCALPHA)
        ov.fill((14, 16, 44, alpha))
        ov.fill((14, 16, 44, alpha // 4), WIN)
        s.blit(ov, (0, 0))

    def draw_status_icons(self, s, c, x, top, t):
        if c.stage == "egg" or c.departed:
            return
        if c.attention and not c.asleep and int(t * 2) % 2 == 0:
            img = self.dark_bubble if c.attention == "dark" else self.bubble
            s.blit(img, (int(x) + 8, int(top) - 8))
        if c.sick:
            s.blit(self.germ, (int(x) - 16, int(top) - 2 + int(math.sin(t * 3) * 2)))

    # ---- living-pet objects ------------------------------------------------------------
    ITEM_ART = {
        "pebble": ([".##.", "#ss#", ".##."], {"#": (90, 96, 120), "s": (170, 180, 205)}),
        "leaf": (["..#", ".#l", "#l."], {"#": (150, 70, 30), "l": (236, 140, 50)}),
        "button": ([".##.", "#oo#", ".##."], {"#": (200, 60, 90), "o": (250, 160, 180)}),
        "feather": (["...#", "..#w", ".#w.", "#..."], {"#": (120, 140, 200), "w": (230, 236, 255)}),
        "bead": ([".#.", "#y#", ".#."], {"#": (60, 140, 120), "y": (120, 230, 200)}),
        "petal": ([".p.", "ppp", ".p."], {"p": (250, 150, 190)}),
    }

    SPONGE = ([".######.", "#yyyyyy#", "#yoyyoy#", "#yyoyyy#", "#oyyyoy#", ".######."],
              {"#": (176, 128, 40), "y": (255, 214, 96), "o": (222, 170, 64)})

    def draw_sponge(self, s, pos, wiping):
        """The wall-cleaning sponge, drawn at the cursor."""
        if not hasattr(self, "sponge_sprite"):
            self.sponge_sprite = make_sprite(*self.SPONGE)
        x, y = int(pos[0]), int(pos[1])
        if wiping:
            pygame.draw.circle(s, (230, 240, 255), (x, y), 3, 1)
        s.blit(self.sponge_sprite, (x - 4, y - 3 + (0 if wiping else -1)))

    def draw_objects(self, s, mind, c, t, hue):
        from .living import BOWL_X
        w = mind.world
        if not hasattr(self, "item_sprites"):
            self.item_sprites = {k: make_sprite(*v) for k, v in self.ITEM_ART.items()}
        # wall drawing (persistent, may be several generations old)
        for px in w.mural:
            s.set_at((px[0], px[1]), tuple(px[2]))
        # scratch marks at the left edge of the room
        for i in range(min(8, w.marks.get("left", 0))):
            pygame.draw.line(s, (170, 140, 115), (1, 60 + i * 3), (3, 58 + i * 3))
        bx = int(w.bed_x)
        # nest ring
        if w.nest:
            for i in range(14):
                a = i / 14 * math.tau
                s.set_at((bx + int(math.cos(a) * 17), FLOOR_Y - 3 + int(math.sin(a) * 5)), (150, 110, 70))
        rim, cushion = hsv(hue + 200, 0.35, 0.72), hsv(hue + 200, 0.18, 0.95)
        puff = self.anim.get("bed")
        if puff is not None:
            pygame.draw.ellipse(s, rim, (bx - 15, FLOOR_Y - 10 + int(puff * 4), 30, 12))
        pygame.draw.ellipse(s, (90, 70, 80), (bx - 15, FLOOR_Y - 8, 30, 11))
        pygame.draw.ellipse(s, rim, (bx - 14, FLOOR_Y - 7, 28, 9))
        pygame.draw.ellipse(s, cushion, (bx - 10, FLOOR_Y - 6, 20, 5))
        # collection pile
        px = int(w.pile["x"])
        for i, kind in enumerate(w.pile["items"]):
            img = self.item_sprites.get(kind)
            if img:
                ox = (i % 4) * 4 - 6
                oy = -(i // 4) * 2
                s.blit(img, (px + ox, FLOOR_Y - img.get_height() + oy))
        # food bowl (with food in it when you feed; it wobbles when nudged)
        x = BOWL_X + (1 if int(t * 20) % 2 else -1) * (1 if mind.bowl_wobble > 0 else 0)
        pygame.draw.polygon(s, (60, 70, 110), [(x - 7, FLOOR_Y - 6), (x + 7, FLOOR_Y - 6),
                                                (x + 5, FLOOR_Y), (x - 5, FLOOR_Y)])
        pygame.draw.polygon(s, (110, 150, 220), [(x - 6, FLOOR_Y - 5), (x + 6, FLOOR_Y - 5),
                                                  (x + 4, FLOOR_Y - 1), (x - 4, FLOOR_Y - 1)])
        pygame.draw.line(s, (200, 220, 250), (x - 6, FLOOR_Y - 5), (x + 6, FLOOR_Y - 5))
        food = w.bowl_food
        if food:
            img = self.food_sprites.get(food["id"])
            if img:
                bites = min(3, int(food.get("eaten", 0.0) * 4))
                keep = max(0, img.get_width() - bites * 2)
                if keep:
                    s.blit(img, (x - img.get_width() // 2, FLOOR_Y - 12), pygame.Rect(0, 0, keep, img.get_height()))
        # ball (it can end up in the bowl!)
        bxp = int(mind.ball_x)
        by = FLOOR_Y - (7 if w.ball_in_bowl else 3)
        pygame.draw.circle(s, (70, 30, 40), (bxp, by), 4)
        pygame.draw.circle(s, (230, 70, 80), (bxp, by), 3)
        ang = mind.ball_rot
        sx, sy = int(round(math.cos(ang) * 2)), int(round(math.sin(ang) * 2))
        pygame.draw.line(s, (255, 255, 255), (bxp - sx, by - sy), (bxp + sx, by + sy))
        if w.ball_in_bowl:
            pygame.draw.line(s, (200, 220, 250), (x - 6, FLOOR_Y - 5), (x + 6, FLOOR_Y - 5))
        # temporary symbols drawn on the floor (a way of "talking")
        for fx, life in mind.floor_marks:
            col = (120, 90, 70) if life > 3 else (190, 150, 115)
            for ox, oy in ((0, 0), (1, -1), (2, 0), (1, 1)):
                s.set_at((int(fx) + ox, FLOOR_Y + 2 + oy), col)
        # trinkets lying loose (some may have rolled under the plant)
        for it in w.loose:
            img = self.item_sprites.get(it["kind"])
            if img:
                s.blit(img, (int(it["x"]) - 2, FLOOR_Y - img.get_height()))
        # its hidden stash, behind the plant (drawn before the plant, so mostly hidden)
        for i, kind in enumerate(w.stash["items"][:8]):
            img = self.item_sprites.get(kind)
            if img:
                s.blit(img, (int(w.stash["x"]) + (i % 4) * 2 - 3, FLOOR_Y - img.get_height() - (i // 4) * 2))
        # the caretaker experiment's little figure
        if w.figure:
            self.draw_figure(s, w.figure, t)
        # gift on the floor
        if mind.gift:
            img = self.gift_sprites[mind.gift["kind"]]
            bob = 1 if int(t * 2) % 2 else 0
            s.blit(img, (int(mind.gift["x"]) - img.get_width() // 2, FLOOR_Y - img.get_height() - bob))

    def draw_figure(self, s, f, t):
        x = int(f["x"])
        y = FLOOR_Y
        anim = f.get("anim")
        dy = -3 if anim == "jump" and f["t"] < 0.6 else 0
        dx = (1 if int(t * 12) % 2 else -1) if anim == "wobble" else 0
        squash = 1 if anim == "bob" and int(t * 8) % 2 else 0
        flip = anim == "spin" and int(f["t"] * 8) % 2
        body, head, leaf, ink = (150, 158, 180), (236, 180, 120), (110, 180, 90), (60, 60, 80)
        bx = x - 2 + dx
        pygame.draw.rect(s, ink, (bx - 1, y - 7 + dy + squash, 6, 7 - squash))
        pygame.draw.rect(s, body, (bx, y - 6 + dy + squash, 4, 5 - squash))
        pygame.draw.rect(s, ink, (bx, y - 10 + dy, 4, 4))
        pygame.draw.rect(s, head, (bx + 1, y - 9 + dy, 2, 2))
        s.set_at((bx + (3 if flip else 0), y - 11 + dy), leaf)
        s.set_at((bx + (2 if flip else 1), y - 9 + dy), ink)

    def draw_mirror(self, s, x, reflection=None, rel=0.0):
        """A standing mirror; `reflection` is the pet's current sprite (already facing correctly)."""
        glass = pygame.Rect(int(x) - 6, FLOOR_Y - 30, 12, 28)
        pygame.draw.rect(s, (120, 90, 70), glass.inflate(4, 4))
        pygame.draw.rect(s, (196, 214, 226), glass)
        pygame.draw.line(s, (236, 246, 252), (glass.x + 2, glass.y + 3), (glass.x + 5, glass.y + 1))
        pygame.draw.rect(s, (120, 90, 70), (int(x) - 5, FLOOR_Y - 1, 10, 2))
        if reflection is not None:
            img = pygame.transform.flip(reflection, True, False)
            img = pygame.transform.scale(img, (20, 20))
            img.set_alpha(170)
            s.set_clip(glass)
            s.blit(img, (glass.centerx - 10 + int(rel), glass.bottom - 20))
            s.set_clip(None)

    def draw_memory_frame(self, s, sprite):
        """The picture on the wall shows its first form."""
        pygame.draw.rect(s, (250, 246, 236), (14, 18, 20, 16))
        if sprite is not None:
            s.blit(pygame.transform.scale(sprite, (16, 16)), (16, 18))

    def draw_carried(self, s, kind, x, top):
        if not hasattr(self, "item_sprites"):
            self.item_sprites = {k: make_sprite(*v) for k, v in self.ITEM_ART.items()}
        img = self.item_sprites.get(kind)
        if img:
            s.blit(img, (int(x) - 2, int(top) - 5))

    def draw_glass(self, s, mind):
        """Fingerprints and breath on the inside of the screen."""
        if not mind.smudges:
            return
        glass = pygame.Surface((LCD_W, LCD_H), pygame.SRCALPHA)
        for x, y, life in mind.smudges:
            a = int(min(1.0, life / 10.0) * 70)
            pygame.draw.circle(glass, (255, 255, 255, a), (int(x), int(y)), 3)
            pygame.draw.circle(glass, (255, 255, 255, a // 2), (int(x) + 2, int(y) + 2), 2)
        s.blit(glass, (0, 0))

    def gift_rect(self, mind):
        if not mind.gift:
            return None
        img = self.gift_sprites[mind.gift["kind"]]
        r = img.get_rect()
        r.midbottom = (int(mind.gift["x"]), FLOOR_Y)
        return r.inflate(6, 6)

    # ---- clickable room objects ----------------------------------------------------------
    POKE_TIME = {"plant": 0.8, "lamp": 2.5, "clock": 1.5, "bird": 5.0, "star": 1.2, "bed": 0.5,
                 "pumpkin": 0.6, "mirror": 0.8, "bowl": 0.6, "frame": 0.4, "window": 0.6}

    def poke(self, name):
        self.anim[name] = 0.0

    def update(self, dt):
        for k in list(self.anim):
            self.anim[k] += dt
            if self.anim[k] > self.POKE_TIME.get(k, 1.0):
                self.anim.pop(k)

    def hit_object(self, lx, ly, mind, season):
        """Which clickable object (if any) is at this LCD point."""
        w = mind.world
        if mind.mirror_on and abs(lx - w.mirror_x) <= 7 and FLOOR_Y - 31 <= ly <= FLOOR_Y:
            return "mirror"
        if 140 <= lx <= 161 and FLOOR_Y - 40 <= ly <= FLOOR_Y + 2:
            return "plant"
        if WIN.inflate(4, 4).collidepoint(lx, ly):
            return "window"
        if 38 <= lx <= 54 and 0 <= ly <= 16:
            return "lamp"
        if (lx - 72) ** 2 + (ly - 20) ** 2 <= 100:
            return "clock"
        if 10 <= lx <= 38 and 14 <= ly <= 38:
            return "frame"
        if abs(lx - 64) <= 8 and FLOOR_Y - 9 <= ly <= FLOOR_Y + 1:
            return "bowl"
        if season == "autumn" and 3 <= lx <= 14 and FLOOR_Y - 23 <= ly <= FLOOR_Y - 14:
            return "pumpkin"
        return None

    def draw_extras(self, s, mind, t):
        """Animated bits: a visiting bird, a shooting star, the tilted picture, toys."""
        w = mind.world
        age = self.anim.get("bird")
        if age is not None:
            hop = -1 if int(age * 4) % 3 == 0 else 0
            x, y = WIN.centerx - 2, WIN.bottom - 5 + hop
            if age > 4.0:
                x, y = x + int((age - 4) * 30), y - int((age - 4) * 24)
            s.set_clip(WIN)
            s.blit(self.bird if int(age * 2) % 4 else pygame.transform.flip(self.bird, True, False), (x, y))
            s.set_clip(None)
        age = self.anim.get("star")
        if age is not None:
            s.set_clip(WIN)
            x = WIN.x + int(age / 1.2 * WIN.w)
            pygame.draw.line(s, (255, 250, 200), (x, WIN.y + 4 + int(age * 6)), (x - 6, WIN.y + 1 + int(age * 6)))
            s.set_clip(None)
        if w.frame_tilt:
            region = pygame.Rect(10, 14, 28, 24)
            pic = s.subsurface(region).copy()
            s.fill((240, 228, 210), region)
            rot = pygame.transform.rotate(pic, w.frame_tilt)
            s.blit(rot, rot.get_rect(center=region.center))
        toy = w.active_toy
        if toy:
            img = self.toy_sprites.get(toy["id"])
            if img:
                if toy["id"] == "feather_teaser":
                    fx = toy.get("fx", toy["x"])
                    s.blit(img, (int(fx), FLOOR_Y - 26 + int(math.sin(t * 5) * 4)))
                else:
                    rot = toy["id"] == "yarn_ball" and abs(toy.get("vx", 0)) > 1 and int(t * 10) % 2
                    s.blit(pygame.transform.flip(img, True, False) if rot else img,
                           (int(toy["x"]) - img.get_width() // 2, FLOOR_Y - img.get_height()))
            if toy["id"] == "music_box" and int(t * 3) % 2 and toy.get("tier") in ("love", "like"):
                s.set_at((int(toy["x"]) + 3, FLOOR_Y - 8 - int(t * 6) % 6), (90, 80, 160))

    def draw_foreground(self, s):
        """A big potted plant the pet can hide behind."""
        age = self.anim.get("plant")
        shake = int(round(math.sin(age * 45) * 2 * max(0.0, 1 - age / 0.8))) if age is not None else 0
        leaf, leaf2 = (84, 150, 90), (60, 120, 74)
        for (lx, ly, w, h, col) in ((141, FLOOR_Y - 34, 10, 16, leaf2), (150, FLOOR_Y - 38, 10, 18, leaf),
                                     (144, FLOOR_Y - 26, 12, 14, leaf), (153, FLOOR_Y - 27, 9, 14, leaf2),
                                     (139, FLOOR_Y - 20, 10, 10, leaf), (148, FLOOR_Y - 18, 12, 10, leaf2)):
            off = shake if ly < FLOOR_Y - 22 else shake // 2
            pygame.draw.ellipse(s, (40, 80, 50), (lx - 1 + off, ly - 1, w + 2, h + 2))
            pygame.draw.ellipse(s, col, (lx + off, ly, w, h))
        pygame.draw.rect(s, (120, 66, 44), (142, FLOOR_Y - 11, 18, 12))
        pygame.draw.rect(s, (190, 104, 70), (143, FLOOR_Y - 10, 16, 10))
        pygame.draw.rect(s, (210, 128, 90), (141, FLOOR_Y - 12, 20, 3))

    def draw_dream(self, s, icon, x, top, t):
        bx, by = int(x) + 6, int(top) - 4
        for i, (ox, oy, r) in enumerate(((0, 0, 1), (3, -4, 2))):
            pygame.draw.circle(s, (250, 250, 255), (bx + ox, by + oy), r)
        cloud = pygame.Rect(bx, by - 21, 20, 14)
        pygame.draw.ellipse(s, (90, 90, 130), cloud.inflate(2, 2))
        pygame.draw.ellipse(s, (250, 250, 255), cloud)
        img = self.dream_sprites.get(icon) or self.dream_sprites["star"]
        if img.get_width() > 10:
            img = pygame.transform.scale(img, (8, max(4, img.get_height() * 8 // img.get_width())))
        s.blit(img, img.get_rect(center=(cloud.centerx, cloud.centery + (1 if int(t * 2) % 2 else 0))))

    def draw_thought(self, s, text_dots, x, top):
        """'...' for pondering."""
        for i in range(text_dots):
            pygame.draw.rect(s, (90, 80, 110), (int(x) + 6 + i * 3, int(top) - 6, 2, 2))
