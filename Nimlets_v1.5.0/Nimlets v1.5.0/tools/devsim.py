"""Accelerated, seeded development simulation for the learning and rare-event systems.

Runs the real game loop headlessly with a synthetic player whose cursor
moves between buttons and room objects with consistent habits, so you can
check - reproducibly - whether the creature's predictions improve, which
rituals and skills emerge, and which rare events fire (and why).

    python tools/devsim.py --minutes 30 --seed 7
    python tools/devsim.py --minutes 20 --seed 3 --player random
    python tools/devsim.py --minutes 15 --player absent --speed 600     # stress test

Players:
  habitual  always heads to Feed from the pet, to Play from the ball, etc.
  random    clicks things in an unpredictable order
  absent    never touches anything (offline-style autonomy)
"""
import argparse
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

FPS = 30


class SimPlayer:
    """Moves a virtual cursor along waypoints and performs actions on arrival."""

    def __init__(self, game, rng, style="habitual"):
        self.g = game
        self.rng = rng
        self.style = style
        self.pos = None
        self.queue = []
        self.wait = 3.0

    # destinations in window coordinates (from the live layout)
    def at(self, name):
        L = self.g.L
        from game.ui import ACTION_IDS
        if name in ACTION_IDS:
            return L.buttons[ACTION_IDS.index(name)].center
        if name in L.toggles:
            return L.toggles[name].center
        lx = {"pet": self.g.beh.x, "ball": self.g.mind.ball_x, "bowl": 64, "wall": 60}[name]
        ly = {"pet": 85, "ball": 97, "bowl": 96, "wall": 58}[name]
        return (L.lcd.x + lx * L.scale, L.lcd.y + ly * L.scale)

    def routine(self):
        g = self.g
        c = g.c
        if self.style == "absent":
            return []
        if self.style == "random":
            return [(self.rng.choice(["feed", "play", "status", "pet", "ball", "clean", "records"]), None)]
        if c.hunger < 55:
            return [("pet", None), ("feed", "feed")]
        if c.poops:
            return [("pet", None), ("clean", "clean")]
        r = self.rng.random()
        if r < 0.35:
            return [("ball", "ball")]
        if r < 0.6:
            return [("pet", "pet")]
        if r < 0.75:
            return [("status", "status"), ("status", "close")]
        if r < 0.85:
            return [("wall", "draw")]
        return [("pet", None), ("play", "play")]

    def step(self, dt):
        g = self.g
        if g.L is None:
            return
        if self.pos is None:
            self.pos = g.L.lcd.center
        if not self.queue:
            self.wait -= dt
            if self.wait <= 0:
                self.queue = self.routine()
                self.wait = self.rng.uniform(4, 9)
            return
        name, action = self.queue[0]
        tx, ty = self.at(name)
        dx, dy = tx - self.pos[0], ty - self.pos[1]
        d = (dx * dx + dy * dy) ** 0.5
        stepd = 700 * dt
        if d > stepd:
            self.pos = (self.pos[0] + dx / d * stepd, self.pos[1] + dy / d * stepd)
            return
        self.pos = (tx, ty)
        self.queue.pop(0)
        self.act(action)

    def act(self, action):
        g = self.g
        from game.ui import ACTION_IDS
        if action is None:
            return
        if action in ("feed", "clean", "play", "status"):
            g.do_action(ACTION_IDS.index(action))
            if g.menu:
                if action == "feed":
                    g.menu_select(1)
                elif action == "play":
                    g.menu = None
        elif action == "close":
            g.panel = None
        elif action == "ball":
            g.click_lcd(g.mind.ball_x, 97)
        elif action == "pet":
            g.click_lcd(g.beh.x, 85)
        elif action == "draw":
            from game.world import MURAL_RECT
            mx, my, mw, mh = MURAL_RECT
            g.stroke = []
            x0 = self.rng.uniform(mx + 6, mx + mw - 20)
            for i in range(6):
                g.extend_stroke((x0 + i * 2, my + 8 + (i % 3)))
            g.finish_stroke()
        g.mind.on_input()


def run(minutes=20, seed=7, player="habitual", stage="adult", speed=1, quiet=False, save=None):
    from game.app import Game
    save = save or os.path.join("/tmp" if os.name != "nt" else os.environ.get("TEMP", "."), f"devsim_{seed}.json")
    g = Game(["--save", save, "--reset", "--mute", "--seed", str(seed)])
    rng = random.Random(seed)
    order = ["baby", "child", "teen", "adult"]
    for _ in range(order.index(stage) + 1):
        g.c.stage_age = 1e9
        for _ in range(140):
            g.update(1 / FPS)
    lt = time.localtime(g.world_time)
    g.world_time += ((10 - lt.tm_hour) % 24) * 3600
    sim = SimPlayer(g, rng, player)
    g.window_cursor = lambda: sim.pos
    g.lcd_cursor = lambda: (g.lcd_pos(sim.pos) if sim.pos and g.L and g.L.lcd.collidepoint(sim.pos)
                            and not g.panel and not g.menu else None)
    if speed != 1:
        sp = g.speeds()
        if speed not in sp:
            g.settings["test_speeds"] = sorted(sp + [speed])
        g.speed_idx = g.speeds().index(speed)
    frames = int(minutes * 60 * FPS)
    half = frames // 2
    acc_mid = None
    t0 = time.perf_counter()
    for f in range(frames):
        sim.step(1 / FPS)
        c = g.c
        c.hunger = max(c.hunger, 20)
        c.sick = False
        c.energy = max(c.energy, 35)
        if c.asleep and g.speed() == 1:
            c.asleep = False
        g.update(1 / FPS)
        if f % 6 == 0:
            g.draw()
        if f == half:
            o = g.mind.observer.o
            acc_mid = (o["hits"], o["misses"])
    cost = (time.perf_counter() - t0) / frames * 1000
    o = g.mind.observer.o
    first = acc_mid or (0, 0)
    second = (o["hits"] - first[0], o["misses"] - first[1])
    rate = lambda hm: hm[0] / max(1, hm[0] + hm[1])  # noqa: E731
    report = {
        "seed": seed, "player": player, "minutes": minutes, "creature": g.c.name, "species": g.c.species,
        "stage_of_model": g.mind.observer.stage(),
        "predictions_first_half": first, "predictions_second_half": second,
        "accuracy_first": round(rate(first), 2), "accuracy_second": round(rate(second), 2),
        "anticipations": sum(1 for e in g.mind.trace_log.items if e["kind"] == "anticipate"),
        "rituals": {k: v["seq"] for k, v in g.mind.prituals.data["known"].items()},
        "skills": list(g.mind.skills.s["known"]),
        "rare_events": dict(g.mind.uncanny.u["done"]),
        "episodes": len(g.mind.episodes.items),
        "ms_per_frame": round(cost, 2),
        "trace_len": len(g.mind.trace_log.items),
    }
    if not quiet:
        for k, v in report.items():
            print(f"{k:>24}: {v}")
        print("\nRecent reasoning trace:")
        for e in g.mind.trace_log.recent(12):
            print("  ", g.mind.trace_log.line(e))
    g.save()
    return report, g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--player", choices=["habitual", "random", "absent"], default="habitual")
    ap.add_argument("--stage", choices=["baby", "child", "teen", "adult"], default="adult")
    ap.add_argument("--speed", type=int, default=1)
    a = ap.parse_args()
    run(a.minutes, a.seed, a.player, a.stage, a.speed)
    pygame.quit()


if __name__ == "__main__":
    main()
