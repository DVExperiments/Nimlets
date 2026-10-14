"""Main game loop: input, simulation stepping, evolution/generation flow, drawing."""
import argparse
import math
import os
import random
import shutil
import sys
import time

import pygame

from . import care, config, evolution, genetics
from .audio import Audio
from .behaviour import Behaviour, act, move, pose_for
from .config import LCD_W, LCD_H, FLOOR_Y
from .creature import Creature
from .memory import FOODS, GAMES
from .minigames import GAME_CLASSES
from . import learning
from .escape import SOUVENIRS, Trip
from .journal import Journal
from .living import BOWL_X, GIFTS, Mind
from .observation import export_log
from .observer import heading_target
from . import shop
from . import shells
from .book import Book, SECTIONS as BOOK_SECTIONS
from . import welcome as welcome_mod
from .reciprocity import PLAYER_INK
from .version import VERSION
from .world import MURAL_RECT, World
from .records import Records
from .room import Room, Effects
from .save import save_game, load_game, load_prefs, save_prefs
from .sprites import SpriteRenderer
from .ui import UI, Menu, ACTION_IDS, THEME_SWATCHES

MIN_W, MIN_H = 640, 520


def parse_args(argv):
    ap = argparse.ArgumentParser(description="Nimlets")
    ap.add_argument("--speed", type=float, default=None,
                    help="start at this test speed multiplier (e.g. 600)")
    ap.add_argument("--fast", action="store_true", help="shortcut for --speed 600")
    ap.add_argument("--reset", action="store_true", help="start a fresh game (old save is backed up)")
    ap.add_argument("--save", default=None, help="path to the save file")
    ap.add_argument("--test-save", action="store_true",
                    help="use the separate test save (test_save.json) in the Nimlets data folder")
    ap.add_argument("--mute", action="store_true", help="start with sound off")
    ap.add_argument("--smoke-test", type=int, default=0, metavar="FRAMES",
                    help="run N frames headlessly-friendly and exit (for testing)")
    ap.add_argument("--screenshot", default=None, help="save a screenshot at the end of a smoke test")
    ap.add_argument("--seed", type=int, default=None, help="seed the random generator (reproducible runs)")
    return ap.parse_args(argv)


class Game:
    def __init__(self, argv=None):
        t0 = time.time()
        self.args = parse_args(argv or [])
        self.settings = config.load_settings()
        self.species = config.load_species()
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(f"Nimlets v{VERSION}")
        try:                                       # the egg icon, drawn in code (game/icon.py)
            from .icon import icon_surface
            pygame.display.set_icon(icon_surface(32))
        except Exception as exc:
            print(f"[icon] {exc}")
        w = max(MIN_W, int(self.settings["window_width"]))
        h = max(MIN_H, int(self.settings["window_height"]))
        if config.WEB and pygame.display.get_surface() is not None:
            self.screen = pygame.display.get_surface()      # keep the browser's canvas, don't replace it
        else:
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        weblog(f"[nimlets] window ready ({time.time() - t0:.1f}s)")
        self.clock = pygame.time.Clock()
        self.rng = random.Random(self.args.seed)
        self.renderer = SpriteRenderer(self.species)
        self.ui = UI(self.renderer, self.species)
        self.room = Room(self.settings)
        self.effects = Effects()
        self.audio = Audio(self.settings.get("sound_enabled", True) and not self.args.mute, lazy=config.WEB)
        weblog(f"[nimlets] sound ready ({time.time() - t0:.1f}s)")
        self.lcd = pygame.Surface((LCD_W, LCD_H))
        self.beh = Behaviour(self.rng)
        self.world = World()
        self.journal = Journal()
        self.mind = Mind(self.rng, self.effects, self.say, self.play, self.log_entry, self.add_rare)
        self.mind._coins = self.earn
        self.shop_tab, self.shop_sel = "food", 0
        self.mind.weather_at = lambda wt: self.room.weather(wt, self.room.season(time.localtime(wt).tm_mon))
        self.confirm = None
        self.trip = None
        self.away = None
        self.diary_scroll = 0
        self.in_catch_up = False
        self.ui.diary_icons = {}
        self.stroke = None          # your current drawing stroke on the wall
        self.sponge = None          # wall-cleaning tool: {"wiping", "removed", "last", "pos"}
        self.sel_tab = 0            # the action tab the A/B/C buttons point at
        self.abc_t = 0.0
        self.wall_hint = False
        self.lab_open = False
        self.neg_retry = False

        self.menu = None
        self.panel = None
        self.records_tab = 0
        self.book_tab = 0           # the expanded Records book (v1.8)
        self.book_scroll = 0
        self.book_shell = None
        self.minigame = None
        self.evolving = None
        self.departing = None
        self.message, self.msg_t = "", 0.0
        self.paused = False
        self.speed_idx = 0
        self.autosave_t = 0.0
        self.zzz_t = 0.0
        self.hover = None
        self.L = None
        self.moved_saves = []
        if self.args.save:
            self.save_path = self.args.save
        else:
            self.moved_saves = [] if config.WEB else config.migrate_legacy_saves()
            self.save_path = os.path.join(config.SAVE_DIR, "test_save.json") if self.args.test_save \
                else config.SAVE_PATH
        self.prefs_path = (os.path.join(os.path.dirname(os.path.abspath(self.save_path)), "preferences.json")
                           if self.args.save else config.PREFS_PATH)
        self.prefs = load_prefs(self.prefs_path)
        self.mind.allow_roam = bool(self.prefs.get("wander", True))
        self.mind.experimental_on = bool(self.prefs.get("experimental", True))
        self.mind.mirror_on = bool(self.prefs.get("mirror", False))
        self.mind.species_db = self.species
        self.obs_mode = False
        self.obs_page = 0
        self.drag_bed = None
        self.cursor_prev = None
        self.cursor_vel = (0.0, 0.0)
        self.was_speed = 1
        self.ui.diary_icons = dict(self.room.dream_sprites)
        self.ui.diary_icons.update(self.room.gift_sprites)
        self.ui.diary_icons.update({"belief": self.room.dream_sprites["star"], "note": self.room.dream_sprites["star"],
                                    "drawing": self.room.gift_sprites["drawing"],
                                    "pebble": self.room.gift_sprites["pebble"]})
        self.started = time.strftime("%Y-%m-%d")

        if self.args.reset:
            if os.path.exists(self.save_path):
                shutil.copyfile(self.save_path, self.save_path + ".reset-backup")
            for path in (self.save_path, self.save_path + ".bak"):
                if os.path.exists(path):
                    os.remove(path)
        loaded = self.load()
        if not loaded:
            self.new_game()
        weblog(f"[nimlets] {'save loaded' if loaded else 'new egg'} ({time.time() - t0:.1f}s)")
        self.welcome_page = 0
        self.hint_t = 0.0
        if not self.prefs.get("welcomed"):
            if loaded or os.environ.get("NIMLETS_SKIP_WELCOME"):
                self.set_pref("welcomed", True)          # an existing player: no tour, no hints
            else:
                self.set_pref("hints", True)             # a brand-new player: tour now, hints later
                self.open_welcome()
        speeds = self.speeds()
        target = 600 if self.args.fast else self.args.speed
        if target:
            if target not in speeds:
                speeds.append(target)
                speeds.sort()
                self.settings["test_speeds"] = speeds
            self.speed_idx = speeds.index(target)
        if self.moved_saves:
            print(f"[save] copied {len(self.moved_saves)} file(s) from the old saves folder to {config.SAVE_DIR}")
            self.say("Your saves now live in your Nimlets folder (Settings, Open folder).")

    # ------------------------------------------------------------------ state

    def speeds(self):
        if not self.settings.get("allow_test_speeds", True):
            return [1]
        return list(self.settings["test_speeds"])

    def speed(self):
        sp = self.speeds()
        return sp[min(self.speed_idx, len(sp) - 1)]

    def new_game(self):
        genome = genetics.random_genome(self.rng)
        self.c = Creature(genetics.make_name(self.rng), genome, 1, self.rng)
        self.records = Records()
        self.records.note_mutation(genome.get("mutation"))
        self.world_time = time.time()
        self.world = World()
        self.journal = Journal()
        self.beh.reset()
        self.mind.reset_for(self.c)
        self.mind.attach(self.c, self.beh, self.world)
        self.mind.worldmodel.learn_room()
        self.wire_mind()
        self.announce_egg(first=True)

    def load(self):
        data = load_game(self.save_path)
        if not data:
            return False
        try:
            self.c = Creature.from_dict(data["creature"])
            self.records = Records.from_dict(data.get("records", {}))
            self.world_time = float(data.get("world_time", time.time()))
            self.paused = bool(data.get("paused", False))
            self.speed_idx = int(data.get("speed_idx", 0))
            self.audio.enabled = bool(data.get("sound", True)) and not self.args.mute
            self.started = data.get("started", self.started)
            self.world = World.from_dict(data.get("world"))
            self.journal = Journal.from_dict(data.get("journal"))
            self.mind.attach(self.c, self.beh, self.world)
            self.wire_mind()
            self.mind.load(data.get("living"))
        except (KeyError, TypeError, ValueError) as exc:
            print(f"[save] save file unusable ({exc}); starting fresh")
            return False
        away = max(0.0, time.time() - float(data.get("saved_at", time.time())))
        if not self.paused and away > 5:
            self.catch_up(away)
        else:
            self.say(f"Welcome back! {self.c.name} is happy to see you.")
        return True

    def catch_up(self, away):
        """Capped, gentle offline progression."""
        scale = self.settings["base_time_scale"]
        cap = self.settings["offline_cap_hours"] * 3600.0
        sim = min(away, cap) * scale
        start = self.world_time
        c = self.c
        c.offline_neglect = False
        self.journal.mark_seen()
        self.in_catch_up = True
        elapsed = 0.0
        while elapsed < sim:
            step = min(60.0, sim - elapsed)
            events = care.tick(c, step, self.hour_at(start + elapsed), self.settings, self.rng, gentle=True)
            elapsed += step
            if "sick" in events:
                self.mind.offline_wt = start + elapsed
                self.log_entry("care", f"{c.name} started feeling unwell.", "pill", True)
            if "poop" in events and c.poops >= 3:
                self.mind.offline_wt = start + elapsed
                self.log_entry("care", f"{c.name}'s room got rather messy.", "ghost", False)
        self.mind.offline_wt = None
        self.mind.offline_agenda(start, sim)
        self.in_catch_up = False
        if c.offline_neglect:
            care.add_mistake(c)       # at most one mistake for a whole absence
            self.mind.on_mistake()
            c.offline_neglect = False
        self.mind.update_sim(sim)
        self.world_time = start + away * scale
        hrs = away / 3600.0
        span = f"{int(hrs)}h {int((hrs % 1) * 60)}m" if hrs >= 1 else f"{int(away / 60)} min"
        if c.stage == "egg":
            self.say(f"You were away {span}. The egg is still warm.")
        elif c.hunger <= 0 or c.happiness <= 0:
            self.say(f"You were away {span}. {c.name} missed you - check on it!")
        else:
            self.say(f"Welcome back! You were away {span}. {c.name} missed you.")
        self.open_away(f"While you were away ({span})...")

    # ------------------------------------------------------------ living helpers
    def wire_mind(self):
        c = self.c
        self.mind.is_bedtime = lambda hour: care.is_bedtime(c, hour, self.settings)

    def play(self, name):
        self.audio.play(name)

    def log_entry(self, kind, text, icon=None, important=False):
        wt = self.mind.offline_wt or self.world_time
        self.journal.add(kind, text, wt, icon, important=important)

    def add_rare(self, label):
        self.records.add_rare(label)

    def announce_egg(self, first=False):
        kind = genetics.egg_name(self.c.genome)
        if kind:
            self.say(f"A {kind} egg! Something unusual is inside...")
            self.log_entry("egg", f"A {kind} egg appeared.", "star", True)
            self.records.add_rare(f"{kind} egg")
        elif first:
            self.say("A new egg! Keep it warm - it will hatch soon.")

    def open_away(self, title):
        unseen = self.journal.unseen()
        if not unseen or self.minigame:
            return
        important = [e for e in unseen if e.get("important")]
        rest = [e for e in reversed(unseen) if not e.get("important")]
        show = (list(reversed(important)) + rest)[:6]
        self.away = {"title": title, "entries": show, "more": max(0, len(unseen) - len(show))}
        self.menu = None
        self.panel = "away"

    def close_away(self, diary=False):
        self.away = None
        self.journal.mark_seen()
        self.panel = "records" if diary else None
        if diary:
            self.records_tab = 3
            self.diary_scroll = 0

    def check_away(self, seconds):
        if seconds >= 120 and self.panel is None and not self.blocked():
            mins = int(seconds // 60)
            span = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins} min"
            self.open_away(f"While you were away ({span})...")

    def feed_at_bowl(self, food_id, then):
        """Food goes into the bowl and the pet trots over to eat it."""
        self.world.bowl_food = {"id": food_id, "eaten": 0.0, "t": 0.0}
        self.world.ball_in_bowl = False
        if abs(self.mind.ball_x - BOWL_X) < 6:
            self.mind.ball_x = BOWL_X + 12
        beh = self.beh
        side = -1 if beh.x < BOWL_X else 1
        self.mind.prituals.credit("eat")
        ritual = self.mind.prituals.steps_for("eat") if self.mind.experimental() else []
        for st in ritual:
            st["tag"] = "reaction"
        steps = ritual + [move(BOWL_X + side * 11, speed=1.8, tag="reaction"),
                          act("eat", 2.4, face=-side, tag="reaction")]
        if then:
            steps.append(act(then, 1.8, tag="reaction"))
        beh.interject(steps)

    # ------------------------------------------------------------ escape trips
    def start_trip(self, roam, variant="ui"):
        c = self.c
        self.menu = None
        self.trip = Trip(self.rng, roam=roam, contact=c.frontier.get("stage", 0) >= 3, variant=variant)
        self.trip_started = self.world_time
        self.mind.escape_started(roam)
        self.beh.start_plan([act("outside", 1e9, tag="outside")])
        self.say(f"{c.name} climbed out of its room!" if c.frontier["escapes"] <= 1
                 else f"{c.name} is exploring outside its room again.")
        self.audio.play("hatch")

    def end_trip(self, hurried=False):
        if not self.trip:
            return
        self.trip = None
        self.beh.x = 80.0
        self.beh.z = 0.3
        self.beh.start_plan([act("dropin", 0.9, tag="reaction"),
                             act("happy" if not hurried else "notice", 1.2, tag="reaction")])
        if hurried:
            self.say(f"{self.c.name} hurries back into its room.")

    def update_trip(self, dt):
        trip = self.trip
        if not trip or not self.L:
            return
        cursor = pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
        self.trip_state = trip.update(dt, self.L, cursor)
        for ev, arg in trip.events:
            m = self.mind
            if ev == "poked":
                m.learn("time_control" if arg == "speed" else "pause_button", 1.0, 0.2)
                if m.first(f"poked_{arg}"):
                    m.log("time", f"pressed the {arg} button itself. Nothing happened - for it.", "ghost",
                          important=True)
                m.trace([f"Outside its room, beside the {arg} control", "Pressed it",
                         "The world did not change for it", "Remembered that"], "time")
            elif ev == "souvenir" and trip.roam:
                trip.souvenir = self.rng.choice(SOUVENIRS)
            elif ev == "edge":
                if m.first("app_edge"):
                    m.log("frontier", "walked to the very edge of the window and pressed against it.", "ghost",
                          important=True)
                m.trace(["Followed the interface to its outer edge", "Pressed against the window boundary"],
                        "frontier")
        trip.events.clear()
        if trip.done and trip.roam:
            souvenir = getattr(trip, "souvenir", None) or self.rng.choice(SOUVENIRS)
            self.mind.roam_returned(souvenir, max(1.0, self.world_time - getattr(self, "trip_started", self.world_time)))
            self.end_trip()
            self.say(f"{self.c.name} is back from a wander around the device with {souvenir}!")
            self.audio.play("happy")
            return
        if trip.done:
            self.end_trip()

    def save(self, announce=False):
        data = {
            "world_time": self.world_time,
            "paused": self.paused,
            "speed_idx": self.speed_idx,
            "sound": self.audio.enabled,
            "started": self.started,
            "creature": self.c.to_dict(),
            "records": self.records.to_dict(),
            "living": self.mind.to_dict(),
            "world": self.world.to_dict(),
            "journal": self.journal.to_dict(),
        }
        try:
            save_game(self.save_path, data)
            if announce:
                self.say("Game saved.")
        except OSError as exc:
            self.say(f"Could not save: {exc}")
        self.autosave_t = 0.0

    @staticmethod
    def hour_at(wt):
        lt = time.localtime(wt)
        return lt.tm_hour + lt.tm_min / 60.0

    def sp(self, sid=None):
        sid = sid or self.c.species
        return self.species.get(sid, {"features": {}, "body": {}})

    def say(self, text):
        self.message, self.msg_t = text, 5.0

    def blocked(self):
        return bool(self.evolving or self.departing or self.minigame)

    # ------------------------------------------------------------------ loop
    def frame(self):
        """One frame: events, update, draw. Returns False when it's time to quit."""
        running = True
        dt = min(self.clock.tick(self.settings.get("fps", 30)) / 1000.0, 0.25)
        for ev in pygame.event.get():
            if not self.handle(ev):
                running = False
        self.update(dt)
        self.draw()
        self.frames = getattr(self, "frames", 0) + 1
        if self.args.smoke_test and self.frames >= self.args.smoke_test:
            if self.args.screenshot:
                pygame.image.save(pygame.display.get_surface(), self.args.screenshot)
            running = False
        return running

    def finish(self):
        self.save()
        pygame.quit()

    def run(self):
        while self.frame():
            pass
        self.finish()

    async def run_async(self):
        """The same loop for the web version: hand control back to the browser after every frame."""
        import asyncio
        start, next_report = time.time(), 0.0
        while self.frame():
            if self.frames == 1:
                weblog("[nimlets] first frame drawn")
            elapsed = time.time() - start
            if elapsed >= next_report and next_report <= 30:      # a few heartbeats while it settles in
                weblog(f"[nimlets] running: {self.frames} frames in {elapsed:.1f}s")
                next_report += 5
            await asyncio.sleep(0)
        self.finish()

    def held(self):
        """Paused, or holding still while the welcome tour is open (without touching the saved pause)."""
        return self.paused or self.panel == "welcome"

    def update(self, dt):
        c = self.c
        if self.abc_t > 0:
            self.abc_t -= dt
            if self.abc_t <= 0:
                self.ui.abc_pressed = None
        if self.sponge and (self.menu or self.panel or self.blocked() or self.trip):
            self.sponge = None
        self.hint_t -= dt
        if self.prefs.get("hints") and self.hint_t <= 0:
            self.hint_t = 1.0
            if self.msg_t <= 0 and not (self.panel or self.menu or self.blocked() or self.trip):
                hid = welcome_mod.hint_due(self)
                if hid:
                    self.say(welcome_mod.HINTS[hid])
                    self.set_pref("hints_seen", list(self.prefs.get("hints_seen", [])) + [hid])
        care.tick_real(c, dt)
        if not self.held():
            sim = dt * self.settings["base_time_scale"] * self.speed()
            self.step_sim(sim)
            self.mind.update_sim(sim)
        if not self.held():                    # paused means everything stops - the pet too
            self.update_mind(dt)
            self.mind.observer.on_rapid(dt, self.speed())
        if self.evolving:
            self.update_evolution(dt)
        elif self.departing:
            self.update_depart(dt)
        elif (not self.held() and not self.minigame and evolution.is_due(c, self.settings)):
            self.start_evolution()
        self.mind.pace = 1.0 if self.speed() <= 1 else min(8.0, self.speed() ** 0.4)
        if self.mind.escape_request and not self.trip and not self.blocked():
            req, self.mind.escape_request = self.mind.escape_request, None
            self.start_trip(req.get("roam", False), req.get("variant", "ui"))
        elif self.mind.escape_request and self.blocked():
            self.mind.escape_request = None
        if self.trip and (c.asleep or c.sick):
            self.end_trip(hurried=True)
        if self.trip:
            self.update_trip(dt)
        if not self.evolving and not self.departing and not self.held():
            self.beh.update(dt, c, self.sp())
        food = self.world.bowl_food
        if food:
            food["t"] += dt
            if self.beh.state == "eat" and abs(self.beh.x - BOWL_X) < 16:
                food["eaten"] = max(food["eaten"], min(1.0, self.beh.t / max(0.1, self.beh.dur)))
            if food["eaten"] >= 0.99 or food["t"] > 20 or (food["eaten"] > 0 and self.beh.state != "eat"):
                self.world.bowl_food = None
        if self.mind.watched and self.panel != "away" and not self.in_catch_up:
            self.journal.mark_seen()
        self.effects.update(dt)
        self.room.update(dt)
        if c.asleep and not self.minigame:
            self.zzz_t += dt
            if self.zzz_t > 1.3:
                self.zzz_t = 0.0
                self.effects.zzz(self.beh.x + 6, FLOOR_Y - 26)
        if self.minigame:
            mg = self.minigame
            mg.update(dt)
            if mg.done and not mg.sound_done:
                mg.sound_done = True
                self.audio.play("success" if mg.won else "fail")
            if mg.closed:
                self.minigame = None
                self.apply(care.apply_game(c, mg.game_id, mg.won, self.rng))
                if mg.won:
                    self.earn(shop.COINS_FOR_WIN + max(0, mg.score - mg.need), "winning " + mg.title)
                self.mind.note_action("game", mg.won)
        self.msg_t -= dt
        self.autosave_t += dt
        if self.autosave_t >= self.settings["autosave_seconds"]:
            self.save()

    def step_sim(self, sim):
        while sim > 0:
            step = min(sim, 30.0)
            sim -= step
            events = care.tick(self.c, step, self.hour_at(self.world_time), self.settings, self.rng)
            self.world_time += step
            for e in events:
                self.on_event(e)

    def on_event(self, e):
        c = self.c
        if e == "call":
            self.audio.play("call")
            self.say(f"{c.name} {care.REASON_TEXT.get(c.attention, 'wants attention!')}")
        elif e == "poop":
            self.audio.play("poop")
            self.say(f"{c.name} made a little mess. Time to clean!")
            if not self.beh.reaction and not self.blocked():
                self.beh.react("poop")
        elif e == "sick":
            self.log_entry("care", f"{c.name} started feeling unwell.", "pill", True)
            self.audio.play("sick")
            self.say(f"Oh no, {c.name} is sick! Give it some medicine.")
        elif e == "sleep":
            self.audio.play("sleep")
            self.say(f"{c.name} {'takes a little nap' if c.napping else 'fell asleep'}. Zzz...")
        elif e == "mistake":
            self.mind.on_mistake()
        elif e == "wake":
            self.audio.play("happy")
            self.say(f"{c.name} woke up!" + ("" if c.lights_on else " It's dark in here..."))

    # ------------------------------------------------------- evolution & life
    def start_evolution(self):
        c = self.c
        self.end_trip()
        target, stage = evolution.choose_next(c, self.rng)
        self.menu = self.panel = self.confirm = None
        self.away = None
        if stage == "depart":
            self.start_depart("elder")
            return
        self.evolving = {"t": 0.0, "dur": 3.2 if c.stage == "egg" else 4.2, "target": target,
                         "stage": stage, "applied": False, "old": c.species}
        self.audio.play("hatch" if c.stage == "egg" else "evolve")
        self.say("The egg is hatching!" if c.stage == "egg" else f"Something is happening to {c.name}...")

    def update_evolution(self, dt):
        e, c = self.evolving, self.c
        e["t"] += dt
        if not e["applied"] and e["t"] >= e["dur"] * 0.72:
            e["applied"] = True
            was_egg = c.stage == "egg"
            evolution.apply(c, e["target"], e["stage"], self.species)
            self.mind.recip.on_evolve()
            had = set(shells.unlocked(self.records))
            new = self.records.discover(e["target"], self.species)
            new_shells = [sid for sid in shells.unlocked(self.records) if sid not in had]
            self.effects.sparkles(80, FLOOR_Y - 16, 16, 40)
            name = self.species[e["target"]]["name"]
            if was_egg:
                self.say(f"The egg hatched! Say hello to {c.name} the {name}!")
                self.log_entry("evolve", f"The egg hatched into {c.name} the {name}.", "star", True)
            elif e["stage"] == "elder":
                self.say(f"{c.name} has grown into a wise elder.")
            else:
                self.say(f"{c.name} evolved into {name}!" + ("  New discovery!" if new else ""))
                self.log_entry("evolve", f"{c.name} evolved into {name}.", "star", True)
            for sid in new_shells:
                nm = shells.SHELLS[sid]["name"]
                self.say(self.message + f"  New shell: {nm}!")
                self.log_entry("shell", f"You unlocked the {nm} shell. (Settings, Shell)", "star", True)
            self.audio.play("happy")
            self.save()
        if e["t"] >= e["dur"]:
            self.evolving = None
            self.beh.reset()
            self.beh.react("happy")
            self.effects.hearts(self.beh.x, FLOOR_Y - 30, 4)

    def can_new_generation(self):
        """True, a reason string (shown greyed), or None (button hidden)."""
        c = self.c
        if c.stage not in ("adult", "elder"):
            return None
        need = self.settings["new_generation_min_adult_hours"] * 3600.0
        if c.stage == "elder" or c.stage_age >= need:
            return True
        left = (need - c.stage_age) / 3600.0
        return f"Available after {left:.1f} more hours as an adult"

    def start_depart(self, reason):
        if self.departing or (self.evolving and reason != "elder"):
            return
        self.end_trip()
        self.menu = self.panel = self.confirm = None
        self.away = None
        self.departing = {"t": 0.0, "dur": 5.0, "reason": reason}
        self.audio.play("depart")
        if reason == "elder":
            self.say(f"{self.c.name} has lived a long, happy life...")
        else:
            self.say(f"{self.c.name} is ready to set off on a journey...")

    def update_depart(self, dt):
        d = self.departing
        d["t"] += dt
        if self.rng.random() < dt * 10:
            self.effects.sparkles(self.beh.x, FLOOR_Y - 20 - d["t"] * 12, 2, 20)
        if d["t"] < d["dur"]:
            return
        old = self.c
        self.records.add_lineage(old, self.species, "elder" if d["reason"] == "elder" else "journey")
        genome, notes = genetics.inherit(old.genome, old.personality.traits, self.rng)
        self.records.note_mutation(genome.get("mutation"))
        self.c = Creature(genetics.make_name(self.rng), genome, old.generation + 1, self.rng)
        self.departing = None
        self.effects.clear()
        self.beh.reset()
        self.mind.reset_for(self.c)
        self.mind.attach(self.c, self.beh, self.world)
        self.mind.worldmodel.learn_room()
        self.wire_mind()
        self.log_entry("generation", f"{old.name} left an egg behind. Generation {self.c.generation} began.",
                       "heart", True)
        self.announce_egg()
        extra = f" It has {notes[0]}!" if notes else ""
        self.say(f"{old.name} left behind a new egg. Generation {self.c.generation} begins!{extra}")
        self.audio.play("hatch")
        self.save()

    # ---------------------------------------------------------------- actions
    def apply(self, fb):
        if fb is None:
            return
        self.say(fb.message)
        self.audio.play(fb.sound)
        c = self.c
        self.mind.on_player_sound(fb.sound)
        is_food = isinstance(fb.effect, tuple) and fb.effect[0] == "food"
        if is_food and not c.asleep and c.stage != "egg":
            self.feed_at_bowl(fb.effect[1], fb.then)
        elif fb.reaction and not c.asleep and c.stage != "egg":
            if fb.reaction == "idle":
                self.beh.set("idle")
            else:
                self.beh.react(fb.reaction, fb.then)
        x, top = self.beh.x, FLOOR_Y - 30
        if fb.effect == "flush":
            self.effects.flush()
        elif fb.effect == "pill":
            self.effects.show_pill(x + 8, top)
        elif fb.effect == "sparkle":
            self.effects.sparkles(x, top + 10, 10)
        if fb.reaction in ("love",) or fb.then == "love":
            self.effects.hearts(x, top, 3)
        elif fb.reaction in ("happy", "dance", "proud", "recover"):
            self.effects.notes(x, top, 2)

    def do_action(self, idx):
        if self.blocked():
            return
        action = ACTION_IDS[idx]
        c = self.c
        self.sel_tab = idx
        self.audio.play("button")
        if self.sponge:
            self.end_sponge()
            if action == "clean":
                return
        self.mind.observer.on_action(action)
        if self.trip and action not in ("status", "records"):
            self.end_trip(hurried=True)
        self.panel = None if action not in ("status", "records") else self.panel
        self.menu = None
        if action == "feed":
            if c.stage == "egg" or c.asleep:
                self.apply(care.feed(c, "rice", self.rng))
                return
            fav = c.memory.favourite_food()
            items = [(f["name"], fid, ("favourite!  " if fid == fav else "") + f["kind"])
                     for fid, f in FOODS.items()]
            items.append(("Shop", "__shop__", f"{self.records.coins} coins"))
            self.menu = Menu("feed", "What's for dinner?", items)
        elif action == "play":
            fb = care.can_play(c, self.rng)
            if fb:
                self.apply(fb)
                return
            neg = self.mind.recip.play_negotiation()
            if neg:
                self.say(neg[0])
                if neg[1]:
                    return
            self.neg_retry = False
            fav = c.memory.favourite_game()
            items = [(name, gid, "favourite!" if gid == fav else "") for gid, name in GAMES.items()]
            items.append(("Shop", "__shop__", f"{self.records.coins} coins"))
            self.menu = Menu("play", "Let's play!", items)
        elif action == "clean":
            messy = c.poops > 0 or c.hygiene < 85
            if messy or not self.world.mural:
                self.apply(care.clean(c))
                self.mind.note_action("clean")
                if messy and self.world.mural and not self.wall_hint and c.stage != "egg":
                    self.wall_hint = True
                    self.say(self.message + "  Press Clean again to wipe the wall.")
            else:
                self.menu = Menu("clean", "Clean the wall?", [
                    ("Sponge", "sponge", "wipe away bits"),
                    ("Wipe it all", "wipe_all", "a fresh, blank wall")],
                    hint="The room is already tidy.  Esc to close.")
        elif action == "medicine":
            was_sick = c.sick
            self.apply(care.medicine(c))
            if was_sick:
                self.mind.note_action("medicine")
        elif action == "discipline":
            if c.stage == "egg":
                self.apply(care.praise(c))
                return
            self.menu = Menu("discipline", "Training", [
                ("Praise", "praise", "for good behaviour"),
                ("Scold", "scold", "for mischief")])
        elif action == "lights":
            was_off = not c.lights_on
            self.apply(care.toggle_lights(c))
            self.mind.note_action("lights_on_asleep" if (was_off and c.asleep) else "lights")
        elif action == "status":
            self.panel = None if self.panel == "status" else "status"
        elif action == "records":
            self.panel = None if self.panel == "records" else "records"

    def menu_select(self, idx=None):
        menu = self.menu
        if idx is not None:
            menu.sel = idx
        label, value, _ = menu.items[menu.sel]
        self.menu = None
        c = self.c
        self.audio.play("button")
        if value == "__shop__":
            self.open_shop("food" if menu.kind == "feed" else "toy")
            return
        if menu.kind == "feed":
            declined = self.mind.recip.food_check(value, FOODS[value]["kind"])
            if declined:
                msg, sound, reaction = declined
                self.apply(care.Feedback(msg, sound, reaction))
                return
            fb = care.feed(c, value, self.rng)
            self.apply(fb)
            if fb.reaction == "eat":
                self.mind.note_action("feed", value)
        elif menu.kind == "play":
            alt = None if self.neg_retry else self.mind.recip.game_choice(value, c.memory.favourite_game())
            if alt:
                self.neg_retry = True
                self.say(f"{c.name} glances over hopefully - it would rather play {GAMES[alt]}.")
                items = [(name, gid, "it seems to prefer this" if gid == alt else "") for gid, name in GAMES.items()]
                self.menu = Menu("play", "Let's play!", items)
                self.menu.sel = list(GAMES).index(alt)
                return
            self.minigame = GAME_CLASSES[value](c, self.rng)
            self.mind.prituals.credit("play")
            self.say(self.minigame.help)
        elif menu.kind == "clean":
            if value == "sponge":
                self.start_sponge()
            else:
                self.ask("wipe_all")
        elif menu.kind == "discipline":
            if value == "praise":
                self.apply(care.praise(c, self.beh.last_idle))
                self.mind.note_action("praise")
            else:
                self.apply(care.scold(c, self.rng))
                self.mind.note_action("scold")

    def toggle(self, name):
        if name in ("speed", "pause", "settings"):
            self.mind.observer.on_action(name)
        if name == "sound":
            on = self.audio.toggle()
            self.say("Sound on." if on else "Sound off.")
            self.audio.play("button")
        elif name == "pause":
            self.paused = not self.paused
            self.say("Time paused." if self.paused else "Time resumed.")
            if not self.paused:
                self.mind.observer.on_unpause()
        elif name == "speed":
            sp = self.speeds()
            old = self.speed()
            self.speed_idx = (self.speed_idx + 1) % len(sp)
            s = self.speed()
            self.say("Normal speed." if s == 1 else f"Test speed: {s}x (time flies!)")
            self.mind.observer.on_speed(s, old)
            if s == 1:
                self.mind.observer.on_slowdown()
        elif name == "save":
            self.save(announce=True)
            self.audio.play("praise")
        elif name == "settings":
            self.menu = None
            self.panel = None if self.panel == "settings" else "settings"

    # ------------------------------------------------------------ living mind
    def lcd_cursor(self):
        if not self.L or not pygame.mouse.get_focused():
            return None
        pos = pygame.mouse.get_pos()
        if not self.L.lcd.collidepoint(pos) or self.menu or self.panel or self.minigame:
            return None
        return self.lcd_pos(pos)

    def pet_floor(self):
        return FLOOR_Y + int(round(self.beh.z * 6))

    def over_pet(self, lx, ly):
        floor = self.pet_floor()
        return abs(lx - self.beh.x) < 13 and floor - 30 < ly < floor + 2

    def window_cursor(self):
        """Cursor position inside this game window only (None when outside or unfocused)."""
        if not pygame.mouse.get_focused():
            return None
        return pygame.mouse.get_pos()

    def cursor_zone(self, dt):
        """Which part of the interface the cursor is in, and which button it is heading toward."""
        L = self.L
        pos = self.window_cursor()
        if L is None or pos is None or self.panel or self.menu:
            self.cursor_prev = None
            return None, None
        if self.cursor_prev is not None and dt > 0:
            vx = (pos[0] - self.cursor_prev[0]) / dt
            vy = (pos[1] - self.cursor_prev[1]) / dt
            self.cursor_vel = (0.6 * self.cursor_vel[0] + 0.4 * vx, 0.6 * self.cursor_vel[1] + 0.4 * vy)
        self.cursor_prev = pos
        zone = None
        for i, r in enumerate(L.buttons):
            if r.collidepoint(pos):
                zone = ACTION_IDS[i]
        for name, r in L.toggles.items():
            if r.collidepoint(pos):
                zone = name
        if zone is None and L.lcd.collidepoint(pos):
            lx, ly = self.lcd_pos(pos)
            mx, my, mw, mh = MURAL_RECT
            if self.over_pet(lx, ly):
                zone = "room:pet"
            elif mx <= lx < mx + mw and my <= ly < my + mh:
                zone = "room:wall"
            else:
                obj = self.mind.recip.obj_at(lx, ly)
                zone = f"room:{obj}" if obj else "room"
        if zone is None and getattr(L, "hearts_rect", None) is not None and L.hearts_rect.collidepoint(pos):
            zone = "hearts"
        targets = {ACTION_IDS[i]: r for i, r in enumerate(L.buttons)}
        if L.lcd.collidepoint(pos):
            # the tabs sit right beside the room, so almost any sweep across the room points
            # at one: only count a tab once the cursor is in the half of the room nearest it
            left = pos[0] < L.lcd.centerx
            targets = {k: r for k, r in targets.items() if (r.centerx < L.lcd.centerx) == left}
        targets.update({k: v for k, v in L.toggles.items() if k in ("speed", "pause")})
        heading = heading_target(pos, self.cursor_vel, targets) if zone not in targets else None
        return zone or "shell", heading

    def update_mind(self, dt):
        cursor = self.lcd_cursor()
        hover_pet = bool(cursor and self.over_pet(*cursor))
        hover_button = ACTION_IDS[self.hover] if self.hover is not None and not self.blocked() else None
        lt = time.localtime(self.world_time)
        weather = self.room.weather(self.world_time, self.room.season(lt.tm_mon))
        zone, heading = self.cursor_zone(dt)
        if not self.evolving and not self.departing and not self.minigame:
            pressed = bool(pygame.mouse.get_pressed()[0]) or self.stroke is not None
            self.mind.update(dt, cursor, hover_button, hover_pet, lt.tm_hour + lt.tm_min / 60.0,
                             weather, self.world_time, pressed, zone, heading)
        else:
            self.mind.update(dt, None, None, False, lt.tm_hour + lt.tm_min / 60.0, weather, self.world_time)

    # ---------------------------------------------------------------- settings
    def theme_hue(self):
        choice = self.prefs.get("theme_hue", "pet")
        return self.c.genome.get("hue", 200) if choice == "pet" else float(choice)

    def set_pref(self, key, value):
        self.prefs[key] = value
        save_prefs(self.prefs_path, self.prefs)

    def cycle_theme(self, d):
        values = [v for v, _ in THEME_SWATCHES]
        cur = self.prefs.get("theme_hue", "pet")
        i = values.index(cur) if cur in values else 0
        self.set_pref("theme_hue", values[(i + d) % len(values)])
        self.audio.play("select")

    def ask(self, kind):
        texts = {
            "newgen": ("Begin a new generation?", [
                f"{self.c.name} will set off on a journey,",
                "leaving behind an egg that inherits its colours",
                "and a little of its personality."], "Yes (Y)", False, "records"),
            "reset_soft": ("Start over with a new egg?", [
                f"{self.c.name} will be gone for good - it won't join the family tree.",
                "Your collection, family history and gifts are kept."], "Start over", True, "settings"),
            "reset_hard": ("Erase everything?", [
                "Your pet, collection, family history and records will all be deleted.",
                "A backup copy of the old save is kept in your Nimlets folder."], "Erase", True, "settings"),
        }
        if kind == "wipe_all":
            gens = [g for g in self.world.mural_generations() if g != self.c.generation]
            lines = ["Every mark on the wall will be wiped away - yours and your pet's."]
            if gens:
                names = [self.world.mural_artists.get(str(g), "an old pet") for g in gens][:3]
                lines.append("That includes drawings left by " + ", ".join(names) + ".")
            lines.append("This can't be undone.")
            texts["wipe_all"] = ("Wipe the whole wall?", lines, "Wipe it", True, None)
        title, lines, yes, danger, under = texts[kind]
        self.confirm = {"kind": kind, "title": title, "lines": lines, "yes": yes,
                        "danger": danger, "under": under}
        self.panel = "confirm"
        self.audio.play("button")

    def confirm_answer(self, yes):
        ctx, self.confirm = self.confirm, None
        if not ctx:
            self.panel = None
            return
        if not yes:
            self.panel = ctx["under"]
            return
        self.panel = None
        if ctx["kind"] == "newgen":
            self.start_depart("journey")
        elif ctx["kind"] == "wipe_all":
            removed = self.world.wipe_all()
            self.audio.play("clean")
            self.effects.sparkles(74, 60, 14, 60)
            self.say(self.mind.on_wall_wiped(removed, all_at_once=True) or "A fresh, clean wall.")
        else:
            self.reset_game(keep_records=ctx["kind"] == "reset_soft")

    def reset_game(self, keep_records):
        if os.path.exists(self.save_path):
            shutil.copyfile(self.save_path, self.save_path + ".reset-backup")
        records, world, journal = self.records, self.world, self.journal
        self.end_trip()
        self.menu = self.minigame = self.evolving = self.departing = self.away = None
        self.effects.clear()
        self.new_game()
        if keep_records:
            self.records, self.world, self.journal = records, world, journal
            self.mind.attach(self.c, self.beh, self.world)
            self.records.note_mutation(self.c.genome.get("mutation"))
            self.log_entry("generation", "You started over with a new egg.", "heart", True)
        self.paused = False
        self.save()
        self.say("Erased. A brand-new egg appears!" if not keep_records
                 else "A fresh start! A new egg appears. Your records are safe.")
        self.audio.play("hatch")

    # ---------------------------------------------------------------- input
    def handle(self, ev):
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.VIDEORESIZE:
            if ev.w < MIN_W or ev.h < MIN_H:
                pygame.display.set_mode((max(MIN_W, ev.w), max(MIN_H, ev.h)), pygame.RESIZABLE)
        elif ev.type == getattr(pygame, "WINDOWFOCUSGAINED", -1):
            away = self.mind.away_t
            self.mind.on_focus(True)
            self.check_away(away)
        elif ev.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.save()                 # a browser tab or phone app can be closed without warning
            self.mind.on_focus(False)
        elif ev.type == getattr(pygame, "WINDOWENTER", -1):
            self.mind.on_mouse_window(True)
        elif ev.type == getattr(pygame, "WINDOWLEAVE", -1):
            self.mind.on_mouse_window(False)
        elif ev.type == pygame.KEYDOWN:
            self.user_input()
            self.on_key(ev.key)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.user_input()
            self.on_click(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3 and self.sponge:
            self.end_sponge()
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.finish_stroke()
        elif ev.type == pygame.MOUSEWHEEL:
            if self.panel == "book" and self.book_tab == 3:
                self.scroll_book(-ev.y * 2)
            if self.panel == "records" and self.records_tab == 3:
                limit = max(0, len(self.journal.entries) - 3)
                self.diary_scroll = max(0, min(limit, self.diary_scroll - ev.y * 2))
        elif ev.type == pygame.MOUSEMOTION:
            self.user_input()
            if self.stroke is not None and self.L:
                self.extend_stroke(self.lcd_pos(ev.pos))
            if self.sponge and self.L:
                self.move_sponge(self.lcd_pos(ev.pos))
            if self.drag_bed and self.L:
                from .world import BED_RANGE
                lx = self.lcd_pos(ev.pos)[0]
                self.world.bed_x = max(BED_RANGE[0], min(BED_RANGE[1], lx - self.drag_bed["dx"]))
            if self.L:
                self.hover = next((i for i, r in enumerate(self.L.buttons) if r.collidepoint(ev.pos)), None)
        return True

    def user_input(self):
        idle = self.mind.idle_t
        self.mind.on_input()
        self.check_away(idle)

    def on_key(self, key):
        if key == pygame.K_F9:
            self.obs_mode = not self.obs_mode
            return
        if self.obs_mode:
            if key in (pygame.K_ESCAPE,):
                self.obs_mode = False
            elif key in (pygame.K_LEFT, pygame.K_RIGHT):
                n = len(self.ui.OBS_PAGES)
                self.obs_page = (self.obs_page + (1 if key == pygame.K_RIGHT else -1)) % n
            elif key == pygame.K_e:
                self.export_observation()
            return
        abc = {pygame.K_a: "a", pygame.K_b: "b", pygame.K_c: "c"}.get(key)
        if abc and not self.minigame:
            self.press_abc(abc)
            return
        if self.sponge and key == pygame.K_ESCAPE:
            self.end_sponge()
            return
        if self.panel == "away":
            if key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                self.close_away()
            elif key in (pygame.K_d, pygame.K_8):
                self.close_away(diary=True)
            return
        if self.panel == "confirm":
            if key in (pygame.K_y, pygame.K_RETURN):
                self.confirm_answer(True)
            elif key in (pygame.K_n, pygame.K_ESCAPE):
                self.confirm_answer(False)
            return
        if self.minigame:
            cmd = {pygame.K_LEFT: "left", pygame.K_a: "left", pygame.K_RIGHT: "right",
                   pygame.K_d: "right", pygame.K_SPACE: "action", pygame.K_RETURN: "action"}.get(key)
            if key == pygame.K_ESCAPE:
                self.minigame = None
                self.say("Game cancelled.")
                return
            if cmd == "action" and self.minigame.game_id != "timing":
                return
            if cmd:
                self.audio.play(self.minigame.on_input(cmd) or "select")
            return
        if self.menu:
            if key in (pygame.K_UP, pygame.K_w):
                self.menu.move(-1)
                self.audio.play("select")
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu.move(1)
                self.audio.play("select")
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.menu_select()
            elif key == pygame.K_ESCAPE:
                self.menu = None
            elif pygame.K_1 <= key <= pygame.K_9 and key - pygame.K_1 < len(self.menu.items):
                self.menu_select(key - pygame.K_1)
            return
        if self.panel == "shop":
            items = self.shop_items()
            if key == pygame.K_ESCAPE:
                self.panel = None
            elif key == pygame.K_TAB:
                self.shop_tab = "toy" if self.shop_tab == "food" else "food"
                self.shop_sel = 0
            elif key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                d = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -3, pygame.K_DOWN: 3}[key]
                self.shop_sel = (self.shop_sel + d) % len(items)
                self.audio.play("select")
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self.buy(items[self.shop_sel])
            return
        if self.panel == "settings":
            if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_o):
                self.panel = None
            elif key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.cycle_theme(-1 if key == pygame.K_LEFT else 1)
            elif key == pygame.K_d:
                self.set_pref("dark", not self.prefs.get("dark"))
            elif key == pygame.K_m:
                self.toggle("sound")
            return
        if self.panel == "welcome":
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT, pygame.K_KP_ENTER):
                self.turn_welcome(1)
            elif key == pygame.K_LEFT:
                self.turn_welcome(-1)
            elif key == pygame.K_ESCAPE:
                self.close_welcome()
            return
        if self.panel == "book":
            if key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.close_book()
            elif key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_LEFT):
                self.turn_page(-1 if key == pygame.K_LEFT else 1)
            elif key in (pygame.K_UP, pygame.K_DOWN) and self.book_tab == 3:
                self.scroll_book(1 if key == pygame.K_DOWN else -1)
            return
        if self.panel == "records" and key == pygame.K_e:
            self.open_book()
            return
        if self.panel:
            if key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.panel = None
                return
            if self.panel == "records" and key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_LEFT):
                d = -1 if key == pygame.K_LEFT else 1
                self.records_tab = (self.records_tab + d) % 5
                if self.records_tab == 3:
                    self.journal.mark_seen()
                    self.diary_scroll = 0
                return
            if self.panel == "records" and self.records_tab == 3 and key in (pygame.K_UP, pygame.K_DOWN):
                limit = max(0, len(self.journal.entries) - 3)
                self.diary_scroll = max(0, min(limit, self.diary_scroll + (1 if key == pygame.K_DOWN else -1)))
                return
        if pygame.K_1 <= key <= pygame.K_8:
            self.do_action(key - pygame.K_1)
        elif key == pygame.K_m:
            self.toggle("sound")
        elif key == pygame.K_p:
            self.toggle("pause")
        elif key == pygame.K_t:
            self.toggle("speed")
        elif key in (pygame.K_s, pygame.K_F5):
            self.toggle("save")
        elif key in (pygame.K_o, pygame.K_COMMA, pygame.K_F2):
            self.toggle("settings")

    def lcd_pos(self, pos):
        L = self.L
        return ((pos[0] - L.lcd.x) / L.scale, (pos[1] - L.lcd.y) / L.scale)

    def on_click(self, pos):
        L = self.L
        if L is None:
            return
        hit = self.ui.hit
        if self.obs_mode:
            for i, r in enumerate(hit.get("obs_tabs", [])):
                if r.collidepoint(pos):
                    self.obs_page = i
            if hit.get("obs_export") and hit["obs_export"].collidepoint(pos):
                self.export_observation()
            return
        if self.panel == "away":
            if hit.get("away_diary") and hit["away_diary"].collidepoint(pos):
                self.close_away(diary=True)
            elif hit.get("away_ok") and hit["away_ok"].collidepoint(pos):
                self.close_away()
            return
        if self.trip and self.trip.hit(pos, 32 * self.outside_scale()):
            self.trip.startled = True
            self.trip.recall()
            self.say(f"{self.c.name} jumps in surprise and scurries home!")
            self.audio.play("refuse")
            return
        if self.panel == "confirm":
            if hit.get("yes") and hit["yes"].collidepoint(pos):
                self.confirm_answer(True)
            elif hit.get("no") and hit["no"].collidepoint(pos):
                self.confirm_answer(False)
            return
        for name, rect in (L.abc.items() if not self.panel else ()):
            if rect.collidepoint(pos):
                self.press_abc(name)
                return
        for name, rect in (L.toggles.items() if not self.panel or self.panel == "settings" else ()):
            if rect.collidepoint(pos) and not (self.panel and self.ui.hit.get("settings_panel", pygame.Rect(0, 0, 0, 0)).collidepoint(pos)):
                if self.trip and name == "settings" and self.trip.steps[self.trip.i]["at"][0] == "settings":
                    self.trip.startled = True
                    self.trip.recall()
                    self.say(f"{self.c.name} was sitting on that button! It hops off.")
                self.toggle(name)
                return
        if self.minigame:
            lx, ly = self.lcd_pos(pos)
            for rect, cmd, _ in self.minigame.buttons():
                if rect.collidepoint(lx, ly):
                    self.audio.play(self.minigame.on_input(cmd) or "select")
            return
        if self.menu:
            for i, r in enumerate(self.menu.rects):
                if r.collidepoint(pos):
                    self.menu_select(i)
                    return
            if not hit.get("menu_panel") or not hit["menu_panel"].collidepoint(pos):
                self.menu = None
            return
        if self.panel:
            if hit.get("close") and hit["close"].collidepoint(pos):
                self.panel = None
                return
            if self.panel == "shop":
                for i, r in enumerate(hit.get("shop_tabs", [])):
                    if r.collidepoint(pos):
                        self.shop_tab = ("food", "toy")[i]
                        self.shop_sel = 0
                        self.audio.play("select")
                        return
                for item_id, card, btn in hit.get("shop_cards", []):
                    if btn.collidepoint(pos):
                        self.buy(item_id)
                        return
                    if card.collidepoint(pos):
                        self.shop_sel = self.shop_items().index(item_id)
                        return
                if L.bezel.inflate(40, 40).collidepoint(pos):
                    return
                self.panel = None
                return
            if self.panel == "settings":
                for rect, value in hit.get("swatches", []):
                    if rect.collidepoint(pos):
                        self.set_pref("theme_hue", value)
                        self.audio.play("select")
                        return
                if hit.get("light") and hit["light"].collidepoint(pos):
                    self.set_pref("dark", False)
                    return
                if hit.get("dark") and hit["dark"].collidepoint(pos):
                    self.set_pref("dark", True)
                    return
                if hit.get("text_btn") and hit["text_btn"].collidepoint(pos):
                    self.set_pref("pixel_text", not self.prefs.get("pixel_text", True))
                    self.audio.play("select")
                    return
                if hit.get("tour_btn") and hit["tour_btn"].collidepoint(pos):
                    self.open_welcome()
                    return
                if hit.get("folder_btn") and hit["folder_btn"].collidepoint(pos):
                    self.open_data_folder()
                    return
                if hit.get("shell_btn") and hit["shell_btn"].collidepoint(pos):
                    self.cycle_shell(-1 if pos[0] < hit["shell_btn"].centerx else 1)
                    return
                if hit.get("exp_btn") and hit["exp_btn"].collidepoint(pos):
                    on = not self.prefs.get("experimental", True)
                    self.set_pref("experimental", on)
                    self.mind.experimental_on = on
                    if not on:
                        self.mind.escape_request = None
                        self.end_trip()
                    self.say("Unusual behaviours on." if on else
                             "Unusual behaviours off - just a normal, cute pet now.")
                    return
                if hit.get("mirror_btn") and hit["mirror_btn"].collidepoint(pos):
                    on = not self.prefs.get("mirror", False)
                    self.set_pref("mirror", on)
                    self.mind.mirror_on = on
                    self.say("A mirror now stands in the room." if on else "The mirror has been put away.")
                    return
                if hit.get("obs_btn") and hit["obs_btn"].collidepoint(pos):
                    self.panel = None
                    self.obs_mode = True
                    return
                if hit.get("roam_btn") and hit["roam_btn"].collidepoint(pos):
                    self.set_pref("wander", not self.prefs.get("wander", True))
                    self.mind.allow_roam = bool(self.prefs["wander"])
                    self.say("Wandering allowed. Your pet may explore the whole device now and then."
                             if self.prefs["wander"] else "Wandering switched off. It will stay near its room.")
                    return
                if hit.get("reset_soft") and hit["reset_soft"].collidepoint(pos):
                    self.ask("reset_soft")
                    return
                if hit.get("reset_hard") and hit["reset_hard"].collidepoint(pos):
                    self.ask("reset_hard")
                    return
            if self.panel == "welcome":
                for key, d in (("welcome_next", 1), ("welcome_back", -1)):
                    if hit.get(key) and hit[key].collidepoint(pos):
                        self.turn_welcome(d)
                        return
                if hit.get("welcome_skip") and hit["welcome_skip"].collidepoint(pos):
                    self.close_welcome()
                return
            if self.panel == "book":
                self.click_book(pos)
                return
            if self.panel == "records":
                if hit.get("expand") and hit["expand"].collidepoint(pos):
                    self.open_book()
                    return
                for i, r in enumerate(hit.get("tabs", [])):
                    if r.collidepoint(pos):
                        self.records_tab = i
                        if i == 3:
                            self.journal.mark_seen()
                            self.diary_scroll = 0
                        self.audio.play("page")
                        return
                if hit.get("newgen") and hit["newgen"].collidepoint(pos):
                    self.ask("newgen")
                    return
                if hit.get("lab_btn") and hit["lab_btn"].collidepoint(pos):
                    self.lab_open = not self.lab_open
                    self.audio.play("page")
                    return
                if hit.get("export_btn") and hit["export_btn"].collidepoint(pos):
                    if config.WEB:
                        self.say("Reports can't be saved from the browser version yet.")
                        return
                    folder = os.path.dirname(os.path.abspath(self.save_path))
                    path = self.mind.recip.report(folder)
                    self.say(f"Report saved: {os.path.basename(path)} (in your Nimlets folder: Settings, Open folder)")
                    return
            if L.bezel.collidepoint(pos):
                return
            self.panel = None
        for i, r in enumerate(L.buttons):
            if r.collidepoint(pos):
                self.do_action(i)
                return
        if L.lcd.collidepoint(pos) and not self.blocked():
            self.click_lcd(*self.lcd_pos(pos))

    def click_lcd(self, lx, ly):
        c, mind = self.c, self.mind
        if self.sponge:
            mx, my, mw, mh = MURAL_RECT
            if mx - 4 <= lx < mx + mw + 4 and my - 4 <= ly < my + mh + 4:
                self.sponge["wiping"] = True
                self.sponge["last"] = None
                self.audio.play("clean")
                self.move_sponge((lx, ly))
            else:
                self.end_sponge()
            return
        gift = self.room.gift_rect(mind)
        if gift and gift.collidepoint(lx, ly):
            kind = mind.collect_gift()
            if kind:
                self.records.gifts[kind] = self.records.gifts.get(kind, 0) + 1
                self.effects.sparkles(lx, ly, 8, 18)
                self.audio.play("happy")
                self.say(f"You keep {GIFTS[kind]}. {c.name} looks very proud.")
            return
        if self.over_pet(lx, ly):
            if c.asleep and c.stage != "egg":
                msg = mind.on_click_sleeping()
                self.say(msg or f"{c.name} snuggles in its sleep. Zzz...")
                return
            if c.stage != "egg" and mind.grumpy_refuse():
                self.apply(care.Feedback(f"{c.name} grumbles. Not now!", "refuse", "refuse"))
                return
            fb = care.pet(c, self.rng)
            self.apply(fb)
            mind.observer.on_action("pet")
            if fb:
                mind.note_action("pet")
            return
        if abs(lx - mind.ball_x) < 6 and FLOOR_Y - 10 < ly < FLOOR_Y + 2:
            mind.on_click_ball(lx)
            mind.observer.on_action("ball")
            self.audio.play("select")
            return
        bx = self.world.bed_x
        if abs(lx - bx) < 15 and FLOOR_Y - 9 < ly < FLOOR_Y + 3 and c.stage != "egg":
            self.drag_bed = {"start": bx, "dx": lx - bx}      # you can move the bed
            return
        obj = self.room.hit_object(lx, ly, mind, self.room.season(time.localtime(self.world_time).tm_mon))
        if obj:
            self.poke_object(obj)
            return
        mx, my, mw, mh = MURAL_RECT
        if mx <= lx < mx + mw and my <= ly < my + mh and c.stage != "egg":
            self.stroke = []                    # start drawing on the wall
            self.extend_stroke((lx, ly))
            return
        mind.on_click_room(lx, ly)

    def export_observation(self):
        if config.WEB:
            self.say("Logs can't be saved from the browser version yet.")
            return
        if self.c.stage == "egg":
            return
        folder = os.path.dirname(os.path.abspath(self.save_path))
        path = export_log(self.mind, folder)
        self.say(f"Observation log saved: {os.path.basename(path)} (in your Nimlets folder: Settings, Open folder)")

    # ---------------------------------------------------------------- coins & shop
    def earn(self, n, why=""):
        if n <= 0:
            return
        self.records.coins += n
        self.records.coins_earned += n
        self.audio.play("coin")
        self.say(f"+{n} coin{'s' if n != 1 else ''} for {why}! (You have {self.records.coins}.)")

    def open_shop(self, tab):
        self.panel = "shop"
        self.shop_tab = tab
        self.shop_sel = 0
        self.mind.observer.on_action("shop")
        self.audio.play("shop")

    def shop_items(self, tab=None):
        tab = tab or self.shop_tab
        return [k for k, it in shop.ITEMS.items() if it["kind"] == tab]

    def buy(self, item_id):
        """Buy an item: it is used straight away."""
        c = self.c
        it = shop.ITEMS[item_id]
        if self.records.coins < it["price"]:
            self.say(f"Not enough coins - win some games first. ({self.records.coins}/{it['price']})")
            self.audio.play("refuse")
            return False
        ok, why = shop.can_use(c, item_id)
        if not ok or self.blocked():
            self.say(why or "Not right now.")
            self.audio.play("refuse")
            return False
        self.records.coins -= it["price"]
        self.records.coins_spent += it["price"]
        self.records.bought[item_id] = self.records.bought.get(item_id, 0) + 1
        self.panel = None
        self.end_trip()
        tier, msg = shop.apply(self.mind, item_id)
        self.audio.play("coin")
        if it["kind"] == "food":
            self.feed_at_bowl(item_id, {"love": "love", "like": "happy", "meh": "look",
                                        "dislike": "refuse"}[tier])
            self.mind.note_action("feed", item_id)
        else:
            self.beh.start_plan(shop.toy_plan(self.mind, item_id, tier))
            self.mind.note_action("game", tier in ("love", "like"))
        self.say(msg)
        if tier == "love":
            self.effects.hearts(self.beh.x, FLOOR_Y - 30, 3)
        return True

    # ---------------------------------------------------------------- room objects
    def poke_object(self, obj):
        room, mind = self.room, self.mind
        lt = time.localtime(self.world_time)
        if obj == "window":
            from .room import daylight
            if daylight(lt.tm_hour + lt.tm_min / 60.0) > 0.3:
                room.poke("bird")
                self.audio.play("bird")
            else:
                room.poke("star")
                self.audio.play("chime")
        else:
            room.poke(obj)
        if obj == "plant":
            self.audio.play("rustle")
            for _ in range(3):
                self.effects.add("leaf", self.rng.uniform(140, 156), FLOOR_Y - 34, self.rng.uniform(-6, 6),
                                 self.rng.uniform(8, 14), 1.6)
        elif obj == "clock":
            self.audio.play("chime")
        elif obj in ("bowl", "mirror"):
            self.audio.play("clink")
            if obj == "bowl":
                mind.bowl_wobble = 0.6
        elif obj == "frame":
            self.world.frame_tilt = 0 if self.world.frame_tilt else self.rng.choice((-8, 8))
            self.audio.play("tap")
        elif obj in ("bed", "pumpkin", "lamp"):
            self.audio.play("puff" if obj != "lamp" else "tap")
        msg = mind.on_room_poke(obj)
        if msg:
            self.say(msg)

    # ---------------------------------------------------------------- the welcome tour
    def open_welcome(self):
        self.menu = None
        self.welcome_page = 0
        self.panel = "welcome"

    def turn_welcome(self, d):
        page = self.welcome_page + d
        if page >= len(welcome_mod.PAGES):
            self.close_welcome()
            return
        self.welcome_page = max(0, page)
        self.audio.play("page")

    def close_welcome(self):
        self.panel = None
        self.set_pref("welcomed", True)
        self.audio.play("happy")
        if self.c.stage == "egg":
            self.say("Your egg is warm. It will hatch very soon!")

    def open_data_folder(self):
        """Show the folder with saves and exported reports in the system's file browser."""
        if config.WEB:
            self.say("In the browser version your pet is saved in the browser itself.")
            return
        folder = os.path.dirname(os.path.abspath(self.save_path))
        os.makedirs(folder, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(folder)                                  # noqa: the Windows file browser
            else:
                import subprocess
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", folder])
            self.say("Opened your Nimlets folder.")
        except Exception:
            self.say(f"Your Nimlets folder: {folder}")
        self.audio.play("select")

    # ---------------------------------------------------------------- the Records book
    QUICK_TO_BOOK = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}

    def open_book(self, tab=None):
        """Expand the quick Records panel into the full storybook."""
        self.book_tab = self.QUICK_TO_BOOK.get(self.records_tab, 0) if tab is None else tab
        self.book_scroll = 0
        self.book_shell = shells.current(self.prefs, self.records, self.c)
        if self.book_tab == 3:
            self.journal.mark_seen()
        self.panel = "book"
        self.audio.play("page")

    def close_book(self):
        """Back to the quick view, on the matching tab where there is one."""
        back = {v: k for k, v in self.QUICK_TO_BOOK.items()}
        self.records_tab = back.get(self.book_tab, self.records_tab)
        self.panel = "records"
        self.audio.play("button")

    def turn_page(self, d):
        self.book_tab = (self.book_tab + d) % len(BOOK_SECTIONS)
        self.book_scroll = 0
        if self.book_tab == 3:
            self.journal.mark_seen()
        self.audio.play("page")

    def scroll_book(self, d):
        limit = max(0, len(self.journal.entries) - 3)
        self.book_scroll = max(0, min(limit, self.book_scroll + d))

    def draw_book(self, screen, L, info):
        c = self.c
        if not hasattr(self, "book"):
            self.book = Book(self.ui)
        bond = {"memories": self.mind.recip.b["memories"] if c.stage != "egg" else [],
                "player": dict(self.mind.recip.b["player"]) if c.stage != "egg" else {},
                "lab_sections": self.mind.recip.lab() if (c.stage != "egg" and self.book_tab == 4) else []}
        ctx = {"tab": self.book_tab, "c": c, "db": self.species, "records": self.records, "renderer": self.renderer,
               "world": self.world, "journal": self.journal, "phrasebook": info.get("phrasebook"), "info": info,
               "bond": bond, "scroll": self.book_scroll, "can_new_gen": self.can_new_generation(),
               "shell_sel": self.book_shell or shells.current(self.prefs, self.records, c),
               "shell_now": shells.current(self.prefs, self.records, c), "shell_choice": self.shell_choice(),
               "hue": self.theme_hue(), "lcd": self.lcd}
        self.book.draw(screen, L, ctx)

    def click_book(self, pos):
        hit = self.ui.hit
        if hit.get("book_close") and hit["book_close"].collidepoint(pos):
            self.close_book()
            return
        for i, r in enumerate(hit.get("book_tabs", [])):
            if r.collidepoint(pos):
                if i != self.book_tab:
                    self.turn_page(i - self.book_tab)
                return
        for r, sid in hit.get("book_shells", []):
            if r.collidepoint(pos):
                self.book_shell = sid
                self.audio.play("select")
                return
        if hit.get("book_use") and hit["book_use"].collidepoint(pos):
            self.set_pref("shell", self.book_shell)
            self.audio.play("happy")
            return
        if hit.get("book_match") and hit["book_match"].collidepoint(pos):
            on = self.shell_choice() != "match"
            self.set_pref("shell", "match" if on else shells.current(self.prefs, self.records, self.c))
            self.audio.play("select")
            return
        if hit.get("book_newgen") and hit["book_newgen"].collidepoint(pos):
            self.ask("newgen")
            return
        if hit.get("book_lab") and hit["book_lab"].collidepoint(pos):
            self.records_tab, self.lab_open, self.panel = 4, True, "records"
            self.audio.play("page")
            return
        if hit.get("book_export") and hit["book_export"].collidepoint(pos):
            if config.WEB:
                self.say("Reports can't be saved from the browser version yet.")
                return
            folder = os.path.dirname(os.path.abspath(self.save_path))
            path = self.mind.recip.report(folder)
            self.say(f"Report saved: {os.path.basename(path)} (in your Nimlets folder: Settings, Open folder)")

    # ---------------------------------------------------------------- shells & A/B/C
    def shell_choice(self):
        choice = self.prefs.get("shell", "match")
        return choice if choice in shells.options(self.records) else "match"

    def cycle_shell(self, d):
        opts = shells.options(self.records)
        i = opts.index(self.shell_choice())
        self.set_pref("shell", opts[(i + d) % len(opts)])
        self.audio.play("select")

    def press_abc(self, name):
        """The three device buttons: A moves along the tabs, B selects, C goes back."""
        self.ui.abc_pressed, self.abc_t = name, 0.15
        self.user_input()
        if self.sponge:
            if name == "c":
                self.end_sponge()
            return
        if self.panel == "confirm":
            if name == "c":
                self.confirm_answer(False)
            elif name == "b" and self.confirm and not self.confirm.get("danger"):
                self.confirm_answer(True)
            return
        if self.panel == "away":
            if name in ("b", "c"):
                self.close_away()
            return
        if self.minigame:
            cmd = {"a": "left", "b": "action", "c": "right"}[name]
            if cmd != "action" or self.minigame.game_id == "timing":
                self.audio.play(self.minigame.on_input(cmd) or "select")
            return
        if self.menu:
            if name == "a":
                self.menu.move(1)
                self.audio.play("select")
            elif name == "b":
                self.menu_select()
            else:
                self.menu = None
            return
        if self.panel == "welcome":
            self.turn_welcome(-1 if name == "c" else 1)
            return
        if self.panel == "book":
            if name == "c":
                self.close_book()
            elif name == "a":
                self.turn_page(1)
            return
        if self.panel:
            if name == "c":
                self.panel = None
                self.audio.play("button")
            return
        if name == "a":
            self.sel_tab = (self.sel_tab + 1) % len(ACTION_IDS)
            self.audio.play("select")
        elif name == "b":
            self.do_action(self.sel_tab)
        else:
            self.msg_t = min(self.msg_t, 0.3)       # C: dismiss the message
            self.audio.play("button")

    # ---------------------------------------------------------------- wall cleaning
    def start_sponge(self):
        self.sponge = {"wiping": False, "removed": [], "last": None, "pos": None}
        self.say("Drag the sponge across the wall. Right-click, Esc or Clean when you're done.")

    def end_sponge(self):
        if not self.sponge:
            return
        if self.sponge["wiping"]:
            self.finish_stroke()
        self.sponge = None
        self.say("Sponge away.")

    def move_sponge(self, lpos):
        sp = self.sponge
        sp["pos"] = lpos
        if not sp["wiping"]:
            return
        x, y = lpos
        lx, ly = sp["last"] or lpos
        n = max(1, int(max(abs(x - lx), abs(y - ly)) // 2))
        for i in range(1, n + 1):
            px, py = lx + (x - lx) * i / n, ly + (y - ly) * i / n
            gone = self.world.wipe(px, py, 3.2)
            if gone:
                sp["removed"] += gone
                if self.rng.random() < 0.5:
                    self.effects.add("bubble", px, py, self.rng.uniform(-6, 6), -self.rng.uniform(6, 14), 0.9)
        sp["last"] = lpos

    # ---------------------------------------------------------------- wall drawing
    def extend_stroke(self, lpos):
        if self.stroke is None or len(self.stroke) >= 60:
            return
        mx, my, mw, mh = MURAL_RECT
        x, y = int(lpos[0]), int(lpos[1])
        if not (mx <= x < mx + mw and my <= y < my + mh):
            return
        pts = [(x, y)]
        if self.stroke:
            lx, ly = self.stroke[-1]
            n = max(abs(x - lx), abs(y - ly))
            pts = [(round(lx + (x - lx) * i / n), round(ly + (y - ly) * i / n)) for i in range(1, n + 1)] if n else []
        new = [p for p in pts if p not in self.stroke][: 60 - len(self.stroke)]
        if new:
            self.world.add_mural([(px, py, PLAYER_INK) for px, py in new], 0, "you")
            self.stroke += new

    def finish_stroke(self):
        if self.sponge and self.sponge["wiping"]:
            self.sponge["wiping"] = False
            removed, self.sponge["removed"] = self.sponge["removed"], []
            msg = self.mind.on_wall_wiped(removed)
            if msg:
                self.say(msg)
            return
        if self.drag_bed:
            drag, self.drag_bed = self.drag_bed, None
            if abs(self.world.bed_x - drag["start"]) > 6:
                self.mind.observer.on_action("arrange")
                self.mind.worldmodel.player_moved("bed", drag["start"], self.world.bed_x)
            else:
                self.poke_object("bed")              # a click, not a drag: the cushion puffs up
            return
        stroke, self.stroke = self.stroke, None
        if stroke:
            self.mind.observer.on_action("draw")
            self.mind.recip.on_wall_stroke(stroke)
            self.mind.on_input()

    # ---------------------------------------------------------------- drawing
    def creature_surface(self, state, st, facing, species=None, stage_override=None, live=False):
        c = self.c
        sid = species or c.species
        at = self.beh.anim_t
        if sid == "egg":
            dur = evolution.stage_duration("egg", self.settings)
            p = min(1.0, c.stage_age / dur) if dur else 1.0
            crack = 0 if p < 0.6 else (1 if p < 0.9 else 2)
            if self.evolving:
                crack = 2
            wob = math.sin(at * (3 + 9 * p)) if (at % (3.0 - 2 * p)) < 0.6 + p else 0.0
            g = 0
            if c.genome.get("mutation") == "glitch" and int(at * 12) % 40 < 2:
                g = int(at * 12) % 3 + 1
            return self.renderer.egg(c.genome, crack, g), 0.0, False, round(wob * (0.6 + p))
        sp = self.sp(sid)
        if state == "ritual":
            state = getattr(self.beh, "ritual_state", "spin")
        if state == "look_clock":
            state = "notice"
        pose, y, flip = pose_for(state, st, at, c, sp, facing)
        if self.mind.shape_id and sid == c.species:
            pose["shape"] = self.mind.shape_id
        if live:
            mind, beh = self.mind, self.beh
            if state == "sleep":
                if mind.stir_t > 0:
                    pose.update(eyes="angry", mouth="frown")
                elif mind.peek_t > 0:
                    pose["eyes"] = "wink"
            gaze = mind.gaze()
            if gaze is None and beh.step and beh.step.get("gaze") is not None:
                gaze = beh.step["gaze"]
            if gaze is None:
                gaze = pose.get("gaze")
            if gaze and pose["eyes"] in ("open", "wide", "grumpy", "sad", "angry", "half"):
                if flip and gaze:
                    gaze = gaze.replace("l", "#").replace("r", "l").replace("#", "r")
                pose["gaze"] = gaze
            else:
                pose.pop("gaze", None)
        else:
            pose.pop("gaze", None)
        surf = self.renderer.creature(sid, c.genome, c.elder, pose)
        return surf, y, flip, 0

    def draw_pet(self, surf, x, floor_y, state, facing, species=None):
        img, y, flip, xo = self.creature_surface(state, self.beh.anim_t, facing, species)
        if flip:
            img = pygame.transform.flip(img, True, False)
        shadow_w = 18
        sh = pygame.Surface((shadow_w, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (60, 40, 30, 60), sh.get_rect())
        surf.blit(sh, (int(x) - shadow_w // 2, floor_y - 2))
        surf.blit(img, (int(x) - 16 + xo, floor_y - 31 + int(y)))
        return floor_y - 31 + int(y)

    def draw_room(self, t):
        c, s, beh, mind = self.c, self.lcd, self.beh, self.mind
        self.room.draw_scene(s, self.world_time, c, t)
        if len(c.forms) >= 2:
            self.room.draw_memory_frame(s, self.renderer.creature(c.forms[0], c.genome, False,
                                                                   {"eyes": "open", "mouth": "smile"}))
        self.room.draw_objects(s, mind, c, t, c.genome.get("hue", 0))
        self.room.draw_extras(s, mind, t)
        if mind.mirror_on:
            near = (mind.world.mirror_x - 36 < beh.x < mind.world.mirror_x + 4 and beh.tag != "outside"
                    and c.species != "egg")
            self.room.draw_mirror(s, mind.world.mirror_x, getattr(self, "last_pet_img", None) if near else None,
                                  (mind.world.mirror_x - beh.x - 14) * 0.3)
        self.effects.draw_floor_layer(s)
        x = beh.x
        floor = self.pet_floor()
        top = floor - 26
        if self.evolving:
            e = self.evolving
            ph = e["t"] / e["dur"]
            show_new = e["applied"] or math.sin((e["t"] ** 2) * 5) > 0
            sid = c.species if e["applied"] else (e["target"] if show_new else e["old"])
            self.draw_pet(s, 80, FLOOR_Y, "evolve", -1, species=sid)
            flash = int(255 * max(0.0, 1 - abs(ph - 0.72) / 0.25)) if ph > 0.45 else 0
            if flash:
                ov = pygame.Surface((LCD_W, LCD_H), pygame.SRCALPHA)
                ov.fill((255, 255, 255, min(255, flash)))
                s.blit(ov, (0, 0))
        elif self.departing:
            d = self.departing
            rise = d["t"] / d["dur"]
            img, _, _, _ = self.creature_surface("depart", d["t"], -1)
            img = img.copy()
            img.set_alpha(int(255 * (1 - rise ** 2)))
            yy = floor - 31 - int(rise * 60)
            s.blit(img, (int(x) - 16, yy))
            pygame.draw.ellipse(s, (255, 226, 120), (int(x) - 7, yy + 2, 14, 4), 1)
        elif beh.tag == "outside":
            top = floor - 26          # the room is empty: the pet is out exploring
        else:
            st = beh.t if beh.state != "egg" else beh.anim_t
            img, y, flip, xo = self.creature_surface(beh.state, st, beh.facing, live=True)
            if beh.state == "press":              # face squashed against the glass
                ph = min(1.0, beh.t / 0.6)
                k = 1.0 + 0.3 * ph
                img = pygame.transform.scale(img, (int(32 * k), int(32 * k)))
                xo -= int(16 * (k - 1))
                y -= int(31 * (k - 1)) - 2
            if flip:
                img = pygame.transform.flip(img, True, False)
            if (abs(x - self.world.bed_x) < 8 and beh.z < 0.2
                    and beh.state in ("sleep", "sit", "doze", "hum", "fakesleep", "wait")):
                y -= 3                       # on the cushion
            if beh.state in ("balance",) and abs(x - BOWL_X) < 4:
                y -= 1
            sh = pygame.Surface((20, 4), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (70, 40, 30, max(20, 70 + int(y) * 4)), sh.get_rect())
            s.blit(sh, (int(x) - 10, floor - 2))
            s.blit(img, (int(x) - 16 + xo, floor - 31 + int(y)))
            self.last_pet_img = img
            top = floor - 26 + int(y)
            if c.species != "egg":
                bbox = img.get_bounding_rect()
                top = floor - 31 + int(y) + bbox.y
            if mind.carrying and beh.state not in ("sleep",):
                self.room.draw_carried(s, mind.carrying, x, top)
        self.room.draw_foreground(s)
        self.room.draw_darkness(s, self.world_time, c.lights_on)
        self.effects.draw(s)
        self.room.draw_glass(s, mind)
        if self.sponge and self.sponge["pos"]:
            self.room.draw_sponge(s, self.sponge["pos"], self.sponge["wiping"])
        if not self.evolving and not self.departing:
            if beh.state == "sleep" and mind.dream:
                self.room.draw_dream(s, mind.dream["icon"], x, top, t)
            elif beh.state == "ponder":
                self.room.draw_thought(s, 1 + int(beh.t * 1.5) % 3, x, top)
            if beh.x < 142 and beh.tag != "outside":     # icons would float over the plant otherwise
                self.room.draw_status_icons(s, c, x, top, t)

    def outside_scale(self):
        return 2 if (self.L is None or self.L.scale <= 5) else 3

    def draw_outside(self, screen, L):
        trip = self.trip
        if not trip or not trip.pos:
            return
        k = self.outside_scale()
        state = getattr(self, "trip_state", "walk")
        img, y, flip, _ = self.creature_surface(state, trip.t, trip.facing)
        if flip:
            img = pygame.transform.flip(img, True, False)
        big = pygame.transform.scale(img, (32 * k, 32 * k))
        x, feet = trip.pos
        sh = pygame.Surface((18 * k, 4 * k), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 50), sh.get_rect())
        screen.blit(sh, (x - 9 * k, feet - 2 * k))
        screen.blit(big, (x - 16 * k, feet - 31 * k + y * k))

    def info(self):
        c = self.c
        sp = self.species.get(c.species)
        days = c.age_days
        if c.stage == "egg":
            subtitle = f"Egg  -  Gen {c.generation}"
            age = "Egg"
        else:
            subtitle = f"{sp['name']}{' (Elder)' if c.elder else ''}  -  Gen {c.generation}"
            age = f"Day {int(days) + 1}"
        hours = c.age / 3600.0
        age_long = f"{days:.1f} days" if days >= 1 else f"{hours:.1f} hours"
        return {
            "name": c.name, "subtitle": subtitle, "age": age, "age_long": age_long,
            "clock": time.strftime("%a %H:%M", time.localtime(self.world_time)),
            "hunger": c.hearts(c.hunger, int(self.settings.get("heart_slots", 6))),
            "happy": c.hearts(c.happiness, int(self.settings.get("heart_slots", 6))),
            "show_hearts": c.stage != "egg",
            "attention": bool(c.attention and c.attention not in ("dark",) and not c.asleep) or
                         (c.attention == "lights"),
            "speed": self.speed(), "paused": self.paused, "sound": self.audio.enabled,
            "started": self.started,
            "slots": int(self.settings.get("heart_slots", 6)),
            "health": c.hearts(c.health, int(self.settings.get("heart_slots", 6))),
            "poke": self.trip.poke if self.trip else 0.0,
            "poke_toggle": self.trip.poke_toggle if self.trip else None,
            "journal": self.journal, "phrasebook": learning.phrasebook(c),
            "diary_scroll": self.diary_scroll,
            "inventions": ", ".join(f"{i['id'].replace('_', ' ')} (by {i['by']})" for i in self.world.inventions),
            "souvenirs": ", ".join(self.world.souvenirs[-4:]),
            "coins": (self.records.coins, self.records.coins_earned, self.records.coins_spent),
            "bond": {"memories": self.mind.recip.b["memories"] if c.stage != "egg" else [],
                     "lab": self.mind.recip.lab() if (self.lab_open and c.stage != "egg") else None,
                     "lab_open": self.lab_open},
        }

    def draw(self):
        screen = pygame.display.get_surface()
        W, H = screen.get_size()
        L = self.L = self.ui.layout(W, H)
        c = self.c
        t = self.beh.anim_t
        self.ui.hit = {}
        self.ui.set_theme(self.theme_hue(), self.prefs.get("dark", False))
        self.ui.pixel = self.prefs.get("pixel_text", True)
        self.ui.set_shell(shells.current(self.prefs, self.records, c), self.theme_hue(), self.prefs.get("dark", False))
        self.ui.draw_frame(screen, L)
        texts = []
        if self.minigame:
            self.minigame.draw(self.lcd, texts,
                               lambda surf, x, fy, state, facing: self.draw_pet(surf, x, fy, state, facing))
        else:
            self.draw_room(t)
        screen.blit(pygame.transform.scale(self.lcd, L.lcd.size), L.lcd.topleft)
        self.ui.draw_lcd_texts(screen, L, texts)
        if self.paused:
            self.ui.text(screen, "PAUSED", (L.lcd.centerx, L.lcd.y + 10), L.fs + 6, (255, 255, 255),
                         bold=True, align="center")
        info = self.info()
        self.ui.draw_top(screen, L, info)
        disabled = set()
        if self.blocked():
            disabled = set(ACTION_IDS)
        elif c.stage == "egg":
            disabled = {"feed", "play", "clean", "medicine", "discipline"}
        flash = None
        if c.attention and not c.asleep and int(t * 2) % 2 == 0:
            flash = {"hungry": "feed", "bored": "play", "sick": "medicine", "dark": "lights"}.get(c.attention)
        elif c.attention == "lights" and int(t * 2) % 2 == 0:
            flash = "lights"
        self.ui.draw_buttons(screen, L, disabled, self.hover, flash, self.sel_tab)
        self.ui.draw_message(screen, L, self.message, min(1.0, self.msg_t))
        self.draw_outside(screen, L)
        under = self.confirm["under"] if (self.panel == "confirm" and self.confirm) else self.panel
        if under == "status":
            info["sprite"] = (self.renderer.egg(c.genome) if c.species == "egg" else
                              self.renderer.creature(c.species, c.genome, c.elder,
                                                     {"eyes": "open", "mouth": "smile"}))
            self.ui.draw_status(screen, L, c, info)
        elif under == "records":
            self.ui.draw_records(screen, L, self.records, c, self.records_tab,
                                 self.can_new_generation(), info)
        elif under == "settings":
            have = shells.unlocked(self.records)
            prefs = dict(self.prefs, _version=VERSION, _web=config.WEB,
                         _shell_label=shells.label(self.shell_choice()),
                         _shell_hint=f"{len(have)} of {len(shells.SHELLS)} shells unlocked. More appear as your family grows.")
            prefs.setdefault("experimental", True)
            self.ui.draw_settings(screen, L, prefs, c.genome.get("hue", 200), self.audio.enabled)
        if self.panel == "book":
            self.draw_book(screen, L, info)
        if self.panel == "welcome":
            if not hasattr(self, "welcome"):
                self.welcome = welcome_mod.Welcome(self.ui)
            self.welcome.draw(screen, L, self.welcome_page, {"renderer": self.renderer, "c": c})
        if self.panel == "shop":
            items = []
            for k in self.shop_items():
                ok, why = shop.can_use(c, k)
                items.append({"id": k, **shop.ITEMS[k], "tag": shop.known_preference(c, k),
                              "afford": self.records.coins >= shop.ITEMS[k]["price"], "usable": ok, "why": why})
            icons = self.room.food_sprites if self.shop_tab == "food" else self.room.toy_sprites
            self.ui.draw_shop(screen, L, items, icons, self.records.coins, self.shop_tab, self.shop_sel, c.name)
        if self.panel == "away" and self.away:
            self.ui.draw_away(screen, L, self.away["title"], self.away["entries"], self.away["more"])
        if self.panel == "confirm" and self.confirm:
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 70))
            screen.blit(dim, (0, 0))
            cf = self.confirm
            self.ui.draw_confirm(screen, L, cf["title"], cf["lines"], cf["yes"], cf["danger"])
        if self.menu:
            self.ui.draw_menu(screen, L, self.menu)
        if self.obs_mode and c.stage != "egg":
            snap = self.mind.observation_snapshot()
            lines = [self.mind.trace_log.line(e) for e in self.mind.trace_log.recent(60)]
            self.ui.draw_observation(screen, L, snap, self.obs_page, lines)
        pygame.display.flip()


def main(argv=None):
    Game(argv).run()


def weblog(msg, error=False):
    """Print, and in the browser also write to its developer console (pygbag keeps print() to itself)."""
    print(msg)
    if config.WEB:
        try:
            import platform as _p
            (_p.window.console.error if error else _p.window.console.log)(msg)
        except Exception:
            pass


def _web_screen(lines, colour=(245, 240, 255)):
    """Draw a few lines of text on a plain screen, using only the game's own pixel font."""
    from .pixelfont import PixelFont
    screen = pygame.display.get_surface()
    if screen is None:
        return
    screen.fill((43, 34, 64))
    W = screen.get_width()
    size = 16 if W >= 700 else 10
    f = PixelFont(size)
    y = 24
    for line in lines:
        while line and y < screen.get_height() - 20:          # wrap long lines to the window
            cut = len(line)
            while cut > 1 and f.size(line[:cut])[0] > W - 40:
                cut -= 1
            screen.blit(f.render(line[:cut], True, colour), (20, y))
            line = line[cut:]
            y += f.get_linesize()
        y += 4
    pygame.display.flip()


async def main_async(argv=None, error_frames=None):
    """Entry point for the web version (see main.py).

    Shows a loading screen straight away, and if anything goes wrong, shows the error
    on screen (as well as in the browser's console) instead of leaving a blank page.
    """
    import asyncio
    import traceback
    try:
        weblog("[nimlets] starting")
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((960, 760), pygame.RESIZABLE)
        _web_screen(["Loading Nimlets...", "", "Hatching the code. This can take a little while the first time."])
        await asyncio.sleep(0)                      # let the browser show it before the heavy lifting
        game = Game(argv or [])
        weblog("[nimlets] game ready, starting the loop")
        await game.run_async()
    except BaseException:                           # anything at all, so it's never silently grey
        text = traceback.format_exc()
        weblog(text, error=True)
        lines = ["Sorry - Nimlets hit a problem while starting.", "",
                 "Please send this to the developer (a screenshot is perfect):", ""] + text.strip().splitlines()
        frames = 0
        while error_frames is None or frames < error_frames:
            try:
                _web_screen(lines, (255, 220, 200))
            except Exception as exc:                # even drawing failed: the console still has it
                print(f"[nimlets] could not draw the error: {exc}")
            await asyncio.sleep(0.25)
            frames += 1
