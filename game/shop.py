"""Coins and the shop: one-time treats and toys.

Coins are earned by *winning* games (the three mini-games, plus a little for
games your pet starts itself). Spend them in the shop (the Shop button at
the bottom of the Feed and Play lists). Every item is used straight away.

Each pet has hidden tastes for every item, shaped by its personality, its
family line and a dash of individuality. What it actually experiences also
depends on novelty, boredom (the same toy every day gets old) and its mood -
so it *learns* what it likes over time, and two pets can react to the same
gift completely differently. Once it has tried something a couple of times,
the shop shows whether it seems to love it or isn't keen.
"""
import random
import time

from .behaviour import act, move
from .config import FLOOR_Y, X_MAX, X_MIN

ITEMS = {
    # ---- special food --------------------------------------------------------------------
    "starfruit": {"name": "Starfruit", "kind": "food", "price": 6, "desc": "Sweet, tangy and star-shaped.",
                  "hunger": 18, "happy": 14, "traits": {"curiosity": 0.5, "playfulness": 0.2}},
    "honey_cake": {"name": "Honey Cake", "kind": "food", "price": 8, "desc": "Rich, sticky, hard to resist.",
                   "hunger": 15, "happy": 22, "weight": 2, "traits": {"sociability": 0.4, "playfulness": 0.3}},
    "kelp_crisps": {"name": "Kelp Crisps", "kind": "food", "price": 5, "desc": "Salty snacks from the sea.",
                    "hunger": 20, "happy": 10, "line": "water", "traits": {"independence": 0.3}},
    "fire_pepper": {"name": "Fire Pepper", "kind": "food", "price": 4, "desc": "Some love it. Some really don't.",
                    "hunger": 8, "happy": 20, "divisive": True, "traits": {"stubbornness": 0.5, "curiosity": 0.3}},
    "moon_pudding": {"name": "Moon Pudding", "kind": "food", "price": 10, "desc": "Soft and soothing. Restores energy.",
                     "hunger": 15, "happy": 12, "energy": 25, "traits": {"independence": 0.4}},
    "golden_apple": {"name": "Golden Apple", "kind": "food", "price": 15, "desc": "Rare and wholesome. Good for health.",
                     "hunger": 25, "happy": 15, "health": 20, "sick_ok": True, "traits": {}},
    # ---- toys -----------------------------------------------------------------------------
    "bubble_wand": {"name": "Bubble Wand", "kind": "toy", "price": 6, "desc": "Bubbles to chase and pop.",
                    "happy": 20, "energy": -6, "traits": {"playfulness": 0.6}},
    "feather_teaser": {"name": "Feather Teaser", "kind": "toy", "price": 7,
                       "desc": "A feather that flutters just out of reach.",
                       "happy": 22, "energy": -8, "traits": {"playfulness": 0.5, "curiosity": 0.2}},
    "music_box": {"name": "Music Box", "kind": "toy", "price": 9, "desc": "A little tune to dance or doze to.",
                  "happy": 16, "energy": 5, "traits": {"sociability": 0.3, "independence": 0.3}},
    "puzzle_cube": {"name": "Puzzle Cube", "kind": "toy", "price": 10, "desc": "Something to figure out.",
                    "happy": 18, "energy": -3, "traits": {"curiosity": 0.7, "stubbornness": 0.2}},
    "plush_buddy": {"name": "Plush Buddy", "kind": "toy", "price": 12, "desc": "A soft little friend to cuddle.",
                    "happy": 20, "traits": {"sociability": 0.6}},
    "yarn_ball": {"name": "Yarn Ball", "kind": "toy", "price": 5, "desc": "Rolls, tangles, unravels.",
                  "happy": 18, "energy": -6, "traits": {"playfulness": 0.4, "independence": 0.3}},
}
TIERS = ((0.55, "love"), (0.15, "like"), (-0.2, "meh"), (-9, "dislike"))
TIER_SCALE = {"love": 1.3, "like": 1.0, "meh": 0.4, "dislike": -0.3}
COINS_FOR_WIN = 3


def ensure(c):
    if not isinstance(getattr(c, "shop", None), dict) or "taste" not in c.shop:
        c.shop = {"taste": {}, "like": {}, "uses": {}, "days": {}, "favourite": None}
    return c.shop


def taste(c, item_id):
    """Hidden, stable taste for an item: personality + family line + individuality."""
    s = ensure(c)
    if item_id not in s["taste"]:
        it = ITEMS[item_id]
        p = c.personality
        t = sum(w * (p[trait] - 0.5) * 2 for trait, w in it.get("traits", {}).items())
        line = c.genome.get("line", "land")
        if it.get("line"):
            t += 0.4 if it["line"] == line else -0.25
        rnd = random.Random(f"{c.name}|{c.generation}|{item_id}")
        t += rnd.uniform(-0.4, 0.4) * (2.0 if it.get("divisive") else 1.0)
        s["taste"][item_id] = round(max(-1.0, min(1.0, t + 0.15)), 3)
    return s["taste"][item_id]


def known_preference(c, item_id):
    """What the shop shows, once the pet has tried something a couple of times."""
    s = ensure(c)
    if s["uses"].get(item_id, 0) < 2:
        return None
    like = s["like"].get(item_id, 0.0)
    if like >= 0.45:
        return "loves this"
    if like <= -0.15:
        return "not keen"
    return None


def can_use(c, item_id):
    """(ok, reason) - items are used immediately, so the pet has to be able to use it now."""
    it = ITEMS[item_id]
    if c.stage == "egg":
        return False, "Wait until it hatches."
    if c.asleep:
        return False, "It's asleep."
    if c.sick and not it.get("sick_ok"):
        return False, "It's too unwell."
    return True, ""


def experience(mind, item_id):
    """How much the pet enjoys this item *this time*. Returns (value, tier, notes)."""
    c = mind.c
    s = ensure(c)
    it = ITEMS[item_id]
    t = taste(c, item_id)
    uses = s["uses"].get(item_id, 0)
    lt = time.localtime(mind.world_time)
    day = lt.tm_year * 400 + lt.tm_yday
    recent = [d for d in s["days"].get(item_id, []) if day - d <= 3]
    novelty = 0.3 if uses == 0 else 0.0
    boredom = 0.12 * len(recent) if it["kind"] == "toy" else 0.05 * len(recent)
    mood = 0.1 if c.happiness > 60 else (-0.1 if c.happiness < 30 else 0.0)
    mood -= 0.2 if mind.emo.get("grumpy", 0) > 0.4 else 0.0
    value = t + novelty - boredom + mood + mind.rng.uniform(-0.15, 0.15)
    tier = next(name for limit, name in TIERS if value > limit)
    return value, tier, {"taste": t, "novelty": novelty, "boredom": boredom, "mood": mood}


def apply(mind, item_id):
    """Apply an item's effects and update what the pet has learned. Returns (tier, message)."""
    c = mind.c
    s = ensure(c)
    it = ITEMS[item_id]
    value, tier, notes = experience(mind, item_id)
    scale = TIER_SCALE[tier]
    c.happiness = max(0.0, min(100.0, c.happiness + it.get("happy", 0) * scale))
    if it["kind"] == "food":
        bite = 1.0 if tier != "dislike" else 0.4
        c.hunger = min(100.0, c.hunger + it.get("hunger", 0) * bite)
        c.weight += it.get("weight", 0) * bite
    c.energy = max(0.0, min(100.0, c.energy + it.get("energy", 0)))
    if it.get("health"):
        c.health = min(100.0, c.health + it["health"])
        if c.sick and tier != "dislike":
            c.sick = False
    first = s["uses"].get(item_id, 0) == 0
    s["uses"][item_id] = s["uses"].get(item_id, 0) + 1
    lt = time.localtime(mind.world_time)
    day = lt.tm_year * 400 + lt.tm_yday
    s["days"].setdefault(item_id, []).append(day)
    s["days"][item_id] = s["days"][item_id][-6:]
    old = s["like"].get(item_id, 0.0)
    s["like"][item_id] = round(old + 0.35 * (value - old), 3)
    if tier == "love":
        mind.emo["excited"] = min(1.0, mind.emo["excited"] + 0.5)
        mind.emo["affectionate"] = min(1.0, mind.emo["affectionate"] + 0.3)
        c.memory.attachment = min(100.0, c.memory.attachment + 1.5)
    for trait in it.get("traits", {}):
        c.personality.nudge(trait, 0.01 if tier in ("love", "like") else -0.005)
    name = it["name"]
    msg = {
        "love": f"{c.name} adores the {name}!",
        "like": f"{c.name} enjoys the {name}.",
        "meh": f"{c.name} gives the {name} a sniff... it's fine, apparently.",
        "dislike": f"{c.name} isn't keen on the {name} at all.",
    }[tier]
    if first:
        mind.log("shop", f"tried the {name} for the first time - " +
                 {"love": "and loved it.", "like": "and liked it.", "meh": "and didn't make much of it.",
                  "dislike": "and didn't care for it."}[tier], "star")
    like = s["like"][item_id]
    if like >= 0.5 and s["uses"][item_id] >= 3 and s.get("favourite") != item_id:
        best = max(s["like"], key=s["like"].get)
        if best == item_id:
            s["favourite"] = item_id
            mind.log("shop", f"has a new favourite: the {name}.", "heart", important=True)
            mind.episodes.add("object", f"fav:{item_id}", f"its favourite {name}", 0.6, {"item": item_id})
    mind.trace([f"Received {name}", f"Taste {notes['taste']:+.2f}, novelty {notes['novelty']:+.2f}, "
                f"boredom {-notes['boredom']:+.2f}, mood {notes['mood']:+.2f}",
                f"Experienced {value:+.2f} -> {tier}", f"Liking now {like:+.2f}"], "shop")
    return tier, msg


def toy_plan(mind, item_id, tier):
    """How it plays with a toy - depends on the toy and how much it likes it this time."""
    beh = mind.beh
    x = max(X_MIN + 10, min(X_MAX - 10, beh.x + (18 if beh.x < 80 else -18)))
    face = 1 if x > beh.x else -1
    mind.world.active_toy = {"id": item_id, "x": float(x), "t": 0.0, "vx": 0.0, "tier": tier}
    tag = "toy"
    if tier == "dislike":
        return [act("look", 1.0, face=face, tag=tag), act("refuse", 1.2, tag=tag),
                move(max(X_MIN, min(X_MAX, beh.x - face * 25)), tag=tag), act("sit", 2.0, tag=tag),
                act("idle", 0.3, fx="toy:done", tag=tag)]
    if tier == "meh":
        return [act("look", 1.0, face=face, tag=tag), move(x - face * 10, tag=tag),
                act("inspect", 1.6, face=face, tag=tag), act("idle", 1.0, tag=tag),
                act("idle", 0.3, fx="toy:done", tag=tag)]
    big = tier == "love"
    if item_id == "bubble_wand":
        steps = [act("excited", 0.8, face=face, fx="toy:bubbles", tag=tag)]
        steps += [act("jump", 0.7, tag=tag), act("look", 0.4, tag=tag)] * (4 if big else 2)
        end = "dance" if big else "happy"
    elif item_id == "feather_teaser":
        steps = [act("excited", 0.8, face=face, tag=tag)]
        for i in range(4 if big else 2):
            tx = max(X_MIN, min(X_MAX, x + (16 if i % 2 else -16)))
            steps += [move(tx, speed=1.8, walk="zoom", tag=tag), act("jump", 0.7, tag=tag)]
        end = "happy"
    elif item_id == "music_box":
        p = mind.c.personality
        if p["playfulness"] > p["independence"]:
            steps = [act("notice", 0.6, face=face, fx="toy:tune", tag=tag), act("dance", 2.4, tag=tag)]
            steps += [act("dance", 2.4, tag=tag)] if big else []
            end = "happy"
        else:
            steps = [act("notice", 0.6, face=face, fx="toy:tune", tag=tag), act("hum", 3.0, tag=tag)]
            steps += [act("doze", 3.0, tag=tag)] if big else []
            end = "proud"
    elif item_id == "puzzle_cube":
        steps = [move(x - face * 10, tag=tag)]
        steps += [act("inspect", 1.2, face=face, tag=tag), act("tap", 0.8, face=face, fx="snd:tap", tag=tag),
                  act("ponder", 1.4, tag=tag)] * (2 if big else 1)
        steps.append(act("proud", 1.2, fx="toy:solved" if big or mind.rng.random() < 0.5 else None, tag=tag))
        end = "happy"
    elif item_id == "plush_buddy":
        steps = [move(x - face * 9, tag=tag), act("love", 2.0, face=face, fx="toy:hearts", tag=tag),
                 act("sit", 3.0 if big else 1.8, face=face, tag=tag)]
        end = "love" if big else "happy"
    else:  # yarn ball
        steps = [act("excited", 0.6, face=face, tag=tag)]
        for _ in range(3 if big else 2):
            steps += [move(x - face * 8, speed=1.6, tag=tag), act("push", 0.4, face=face, fx="toy:roll", tag=tag),
                      act("look", 0.6, tag=tag)]
        end = "happy"
    return steps + [act(end, 1.4, tag=tag), act("idle", 0.3, fx="toy:done", tag=tag)]


def toy_fx(mind, kind):
    w = mind.world
    toy = w.active_toy
    beh = mind.beh
    if kind == "done":
        if toy and mind.effects:
            mind.effects.sparkles(toy["x"], FLOOR_Y - 6, 8, 16)
        w.active_toy = None
        return
    if not toy:
        return
    if kind == "bubbles" and mind.effects:
        for i in range(10):
            mind.effects.add("bubble", toy["x"] + mind.rng.uniform(-12, 12), FLOOR_Y - 10 - i * 2,
                             mind.rng.uniform(-4, 4), mind.rng.uniform(-10, -5), mind.rng.uniform(3, 6))
    elif kind == "tune":
        mind._play("tune")
        if mind.effects:
            mind.effects.notes(toy["x"], FLOOR_Y - 20, 4)
    elif kind == "solved":
        if mind.effects:
            mind.effects.sparkles(toy["x"], FLOOR_Y - 8, 10, 20)
        toy["solved"] = True
        if mind.first("solved_cube"):
            mind.log("shop", "worked out the Puzzle Cube!", "star", important=True)
    elif kind == "hearts" and mind.effects:
        mind.effects.hearts(toy["x"], FLOOR_Y - 20, 3)
    elif kind == "roll":
        toy["vx"] = (1 if toy["x"] > beh.x else -1) * mind.rng.uniform(30, 50)


def toy_tick(mind, dt):
    toy = mind.world.active_toy
    if not toy:
        return
    toy["t"] += dt
    if toy["id"] == "feather_teaser":
        import math
        toy["fx"] = mind.beh.x + math.sin(toy["t"] * 1.7) * 20
    if abs(toy.get("vx", 0)) > 0.5:
        toy["x"] = max(X_MIN, min(X_MAX, toy["x"] + toy["vx"] * dt))
        toy["vx"] *= 0.96 ** (dt * 30)
    if toy["t"] > 40:                 # safety: never leave a toy lying around forever
        mind.world.active_toy = None
