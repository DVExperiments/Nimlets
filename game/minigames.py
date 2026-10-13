"""Three tiny mini-games, each under a minute.

Games draw onto the LCD surface. Text is appended to a `texts` list as
(text, lcd_x, lcd_y, lcd_size, colour, align) and rendered crisply by the UI
after the LCD has been scaled up. `draw_pet(surf, x, floor_y, state, facing)`
draws the creature in a given behaviour state.
"""
import math

import pygame

INK = (56, 48, 76)
BG = (246, 238, 222)
CARD = (255, 252, 246)
GOOD = (90, 180, 110)
BAD = (220, 90, 100)
ACCENT = (240, 170, 70)


class MiniGame:
    game_id = ""
    title = "Game"
    rounds = 5
    need = 3
    help = ""

    def __init__(self, creature, rng):
        self.c = creature
        self.rng = rng
        self.score = 0
        self.round = 1
        self.phase = "guess"
        self.pt = 0.0
        self.t = 0.0
        self.done = False
        self.won = False
        self.closed = False
        self.end_t = 0.0
        self.result = None
        self.mood = "idle"
        self.sound_done = False

    # --- shared logic --------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.pt += dt
        if self.done:
            self.end_t += dt
            if self.end_t > 2.2:
                self.closed = True
            return
        if self.phase == "reveal" and self.pt > 1.2:
            if self.round >= self.rounds:
                self.finish()
            else:
                self.round += 1
                self.next_round()
                self.phase = "guess"
                self.pt = 0.0
                self.mood = "idle"

    def next_round(self):
        pass

    def score_point(self, correct):
        self.result = correct
        if correct:
            self.score += 1
        self.mood = "happy" if correct else "sad"
        self.phase = "reveal"
        self.pt = 0.0
        return "point" if correct else "miss"

    def finish(self):
        self.done = True
        self.won = self.score >= self.need
        p = self.c.personality
        if self.won:
            self.mood = "dance" if p["playfulness"] > 0.55 else "happy"
        else:
            self.mood = "sulk" if p["stubbornness"] > 0.6 else "sad"

    def on_input(self, cmd):
        return None

    def buttons(self):
        return []

    # --- drawing helpers ---------------------------------------------------
    def draw_header(self, surf, texts):
        surf.fill(BG)
        pygame.draw.rect(surf, (232, 220, 200), (0, 0, surf.get_width(), 14))
        texts.append((self.title, 4, 2, 9, INK, "left"))
        texts.append((f"Round {min(self.round, self.rounds)}/{self.rounds}   Score {self.score}",
                      156, 2, 9, INK, "right"))

    def draw_buttons(self, surf, texts):
        for rect, cmd, label in self.buttons():
            pygame.draw.rect(surf, INK, rect.inflate(2, 2), border_radius=4)
            pygame.draw.rect(surf, CARD, rect, border_radius=3)
            texts.append((label, rect.centerx, rect.y + 3, 8, INK, "center"))

    def draw_result(self, surf, texts):
        if not self.done:
            return
        panel = pygame.Rect(30, 34, 100, 30)
        pygame.draw.rect(surf, INK, panel.inflate(2, 2), border_radius=6)
        pygame.draw.rect(surf, CARD, panel, border_radius=5)
        texts.append(("YOU WIN!" if self.won else "Nice try!", 80, 38, 11,
                      GOOD if self.won else BAD, "center"))
        texts.append((f"{self.score} / {self.rounds}", 80, 52, 8, INK, "center"))


class HigherLower(MiniGame):
    game_id = "higher_lower"
    title = "Higher or Lower"
    help = "Will the next number be higher or lower?"

    def __init__(self, creature, rng):
        super().__init__(creature, rng)
        self.cur = rng.randint(2, 8)
        self.nxt = None

    def next_round(self):
        self.cur = self.nxt
        self.nxt = None

    def buttons(self):
        return [(pygame.Rect(6, 94, 46, 13), "left", "< LOWER"),
                (pygame.Rect(108, 94, 46, 13), "right", "HIGHER >")]

    def on_input(self, cmd):
        if self.done or self.phase != "guess" or cmd not in ("left", "right"):
            return None
        n = self.rng.randint(1, 9)
        while n == self.cur:
            n = self.rng.randint(1, 9)
        self.nxt = n
        return self.score_point(n < self.cur if cmd == "left" else n > self.cur)

    def draw(self, surf, texts, draw_pet):
        self.draw_header(surf, texts)
        for i, (x, val) in enumerate(((22, self.cur), (104, self.nxt))):
            r = pygame.Rect(x, 20, 34, 42)
            col = INK
            if i == 1 and self.phase == "reveal":
                col = GOOD if self.result else BAD
            pygame.draw.rect(surf, col, r.inflate(4, 4), border_radius=6)
            pygame.draw.rect(surf, CARD, r, border_radius=5)
            label = "?" if val is None else str(val)
            texts.append((label, r.centerx, r.y + 9, 24, col if i else INK, "center"))
        texts.append(("next", 121, 64, 7, INK, "center"))
        texts.append(("now", 39, 64, 7, INK, "center"))
        draw_pet(surf, 80, 98, self.mood if self.phase == "reveal" or self.done else "idle", -1)
        self.draw_buttons(surf, texts)
        self.draw_result(surf, texts)


class Direction(MiniGame):
    game_id = "direction"
    title = "Which Way?"
    help = "Guess which way your pet will look."

    def __init__(self, creature, rng):
        super().__init__(creature, rng)
        self.face = -1
        self.last = None
        self.choice = None

    def buttons(self):
        return [(pygame.Rect(6, 94, 46, 13), "left", "< LEFT"),
                (pygame.Rect(108, 94, 46, 13), "right", "RIGHT >")]

    def on_input(self, cmd):
        if self.done or self.phase != "guess" or cmd not in ("left", "right"):
            return None
        # stubborn pets tend to repeat themselves - a readable personality quirk
        if self.last and self.c.personality["stubbornness"] > 0.6 and self.rng.random() < 0.6:
            d = self.last
        else:
            d = self.rng.choice(("left", "right"))
        self.last = d
        self.choice = cmd
        self.face = -1 if d == "left" else 1
        return self.score_point(d == cmd)

    def draw(self, surf, texts, draw_pet):
        self.draw_header(surf, texts)
        bob = int(math.sin(self.t * 4) * 2)
        for side, x in (("left", 24), ("right", 136)):
            col = ACCENT if self.choice == side and self.phase == "reveal" else (200, 190, 175)
            pts = [(x - 10 if side == "left" else x + 10, 50 + bob), (x, 38 + bob), (x, 62 + bob)] \
                if side == "left" else [(x + 10, 50 + bob), (x, 38 + bob), (x, 62 + bob)]
            pygame.draw.polygon(surf, col, pts)
        if self.phase == "guess" and not self.done:
            texts.append(("Which way will it look?", 80, 18, 8, INK, "center"))
            state, facing = "idle", -1 if int(self.t * 3) % 2 else 1
        else:
            state, facing = ("look_fixed", self.face)
            if self.done:
                state = self.mood
            texts.append(("Got it!" if self.result else "Wrong way!", 80, 18, 9,
                          GOOD if self.result else BAD, "center"))
        draw_pet(surf, 80, 90, state, facing)
        self.draw_buttons(surf, texts)
        self.draw_result(surf, texts)


class Timing(MiniGame):
    game_id = "timing"
    title = "Timing Star"
    rounds = 3
    need = 2
    help = "Press SPACE when the star is in the glowing zone."

    def __init__(self, creature, rng):
        super().__init__(creature, rng)
        self.phase = "run"
        self.pos = 0.0
        self.dir = 1
        self.next_round()
        self.phase = "run"

    def next_round(self):
        self.zone = self.rng.uniform(0.25, 0.75)
        self.width = 0.2 if self.c.stage in ("baby", "child") else 0.16
        self.speed = 0.7 + 0.25 * self.round
        self.pos = 0.0
        self.dir = 1

    def update(self, dt):
        if self.phase == "run" and not self.done:
            self.pos += self.dir * self.speed * dt
            if self.pos >= 1.0:
                self.pos, self.dir = 1.0, -1
            elif self.pos <= 0.0:
                self.pos, self.dir = 0.0, 1
        was_guess = self.phase
        super().update(dt)
        if was_guess == "reveal" and self.phase == "guess":
            self.phase = "run"

    def buttons(self):
        return [(pygame.Rect(50, 94, 60, 13), "action", "STOP! (Space)")]

    def on_input(self, cmd):
        if self.done or self.phase != "run":
            return None
        return self.score_point(abs(self.pos - self.zone) <= self.width / 2)

    def draw(self, surf, texts, draw_pet):
        self.draw_header(surf, texts)
        bar = pygame.Rect(14, 30, 132, 10)
        pygame.draw.rect(surf, INK, bar.inflate(2, 2), border_radius=4)
        pygame.draw.rect(surf, CARD, bar, border_radius=3)
        zx = bar.x + (self.zone - self.width / 2) * bar.w
        glow = (255, 220, 120) if int(self.t * 4) % 2 else (255, 200, 90)
        pygame.draw.rect(surf, glow, (zx, bar.y, self.width * bar.w, bar.h))
        sx = bar.x + self.pos * bar.w
        star = [(sx, bar.y - 5), (sx + 2, bar.y - 1), (sx + 6, bar.y - 1), (sx + 3, bar.y + 2),
                (sx + 4, bar.y + 6), (sx, bar.y + 3), (sx - 4, bar.y + 6), (sx - 3, bar.y + 2),
                (sx - 6, bar.y - 1), (sx - 2, bar.y - 1)]
        pygame.draw.polygon(surf, (250, 180, 40), star)
        pygame.draw.polygon(surf, INK, star, 1)
        if self.phase == "reveal" and not self.done:
            texts.append(("Perfect!" if self.result else "Missed!", 80, 46, 10,
                          GOOD if self.result else BAD, "center"))
        state = self.mood if (self.phase == "reveal" or self.done) else "idle"
        if state == "happy":
            state = "jump"
        draw_pet(surf, 80, 92, state, -1)
        self.draw_buttons(surf, texts)
        self.draw_result(surf, texts)


GAME_CLASSES = {cls.game_id: cls for cls in (HigherLower, Direction, Timing)}
