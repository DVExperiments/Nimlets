"""Care & needs: the core Tamagotchi loop.

`tick` advances needs over simulated time. The action functions return a
Feedback object describing the message, sound and reaction for the UI.
"""
import math

from .memory import FOODS, GAMES


class Feedback:
    def __init__(self, message, sound="button", reaction=None, effect=None, then=None):
        self.message = message
        self.sound = sound
        self.reaction = reaction
        self.effect = effect
        self.then = then


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def is_bedtime(c, hour, settings):
    if c.stage == "egg":
        return False
    start, end = settings["bedtimes"].get(c.stage, [21, 8])
    if getattr(c, "bmut_active", False) and (c.genome.get("bmut") or {}).get("id") == "nocturnal":
        start, end = 8, 16           # night owl: sleeps through the day
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


def need_reason(c):
    """Why the creature is calling for attention right now (or None)."""
    if c.stage == "egg" or c.departed:
        return None
    if c.asleep:
        return "lights" if (c.lights_on and not c.napping) else None
    if c.sick:
        return "sick"
    if c.hunger <= 0.0:
        return "hungry"
    if c.happiness <= 0.0:
        return "bored"
    if not c.lights_on:
        return "dark"       # soft call - never counts as a care mistake
    return None


SOFT_REASONS = ("dark", "fake")


def add_mistake(c):
    c.care_mistakes += 1
    c.stage_mistakes += 1
    c.memory.attachment = clamp(c.memory.attachment - 3)


def _clamp_all(c):
    c.hunger = clamp(c.hunger)
    c.happiness = clamp(c.happiness)
    c.energy = clamp(c.energy)
    c.hygiene = clamp(c.hygiene)
    c.discipline = clamp(c.discipline)
    c.memory.attachment = clamp(c.memory.attachment)
    c.weight = max(1.0, c.weight)


def tick(c, dt, hour, settings, rng, gentle=False):
    """Advance the creature by dt simulated seconds. Returns event names.

    gentle=True is used for offline catch-up: slower decay, lower illness
    risk, and attention timeouts only raise a flag (capped at one mistake
    by the caller).
    """
    events = []
    if c.departed:
        return events
    c.age += dt
    c.stage_age += dt
    if c.stage == "egg":
        return events

    h = dt / 3600.0
    d = settings["decay_per_hour"]
    mult = settings["baby_decay_multiplier"] if c.stage == "baby" else 1.0
    if c.stage == "elder":
        mult *= 0.8
    if gentle:
        mult *= 0.6

    # ---- sleep --------------------------------------------------------
    in_bed = is_bedtime(c, hour, settings)
    if c.asleep:
        if c.napping:
            if in_bed:
                c.napping = False
            elif c.energy >= 85:
                c.asleep = False
                events.append("wake")
        elif not in_bed:
            c.asleep = False
            events.append("wake")
    else:
        if in_bed:
            c.asleep, c.napping = True, False
            events.append("sleep")
        elif c.energy <= 8:
            c.asleep, c.napping = True, True
            events.append("sleep")

    # ---- needs --------------------------------------------------------
    if c.asleep:
        c.hunger -= d["hunger"] * mult * 0.35 * h
        c.happiness -= d["happiness"] * mult * 0.2 * h
        c.energy += d["energy_sleep_recover"] * h
        c.hygiene -= d["hygiene"] * mult * 0.4 * h
    else:
        c.hunger -= d["hunger"] * mult * h
        dark = 2.0 if not c.lights_on else 1.0
        c.happiness -= d["happiness"] * mult * dark * h
        heavy = 1.3 if c.is_overweight() else 1.0
        c.energy -= d["energy_awake"] * heavy * h
        c.hygiene -= d["hygiene"] * mult * h
        # poop
        c.poop_timer += h
        interval = settings["poop_interval_hours"] / (1.5 if c.stage == "baby" else 1.0)
        if c.poop_timer >= interval:
            c.poop_timer = rng.uniform(-0.25, 0.25) * interval
            if c.poops < (3 if gentle else 4):
                c.poops += 1
                c.hygiene -= 15
                events.append("poop")
    _clamp_all(c)

    # ---- health ---------------------------------------------------------
    strain = 0.0
    if c.hunger <= 0:
        strain += 1
    if c.poops >= 3 or c.hygiene <= 10:
        strain += 1
    if c.is_overweight() or c.is_underweight():
        strain += 0.5
    if c.sick:
        strain += 1
    if strain:
        c.health -= 5 * strain * h
    else:
        c.health += 4 * h
    c.health = clamp(c.health, 5, 100)   # never dies of neglect - stays recoverable

    if not c.sick:
        risk = 0.0
        if c.health < 40:
            risk += 0.5
        if c.poops >= 2:
            risk += 0.05 * c.poops
        if c.is_overweight():
            risk += 0.04
        if gentle:
            risk *= 0.3
        if risk and rng.random() < 1 - math.exp(-risk * h):
            c.sick = True
            c.doses = 1 if c.health > 30 else 2
            events.append("sick")

    # ---- history for evolution -------------------------------------------
    c.hist["hunger"] += c.hunger * h
    c.hist["happy"] += c.happiness * h
    c.hist["weight"] += c.weight * h
    c.hist["hours"] += h
    if c.hunger > 50 and c.happiness > 50:
        c.memory.attachment = clamp(c.memory.attachment + 0.3 * h)

    # ---- attention ------------------------------------------------------
    reason = need_reason(c)
    if reason:
        if c.attention != reason:
            c.attention = reason
            c.attention_time = 0.0
            c.attention_counted = False
            events.append("call")
        else:
            c.attention_time += dt
            minutes = settings["lights_timeout_minutes"] if reason == "lights" \
                else settings["attention_timeout_minutes"]
            if (reason not in SOFT_REASONS and not c.attention_counted
                    and c.attention_time >= minutes * 60):
                c.attention_counted = True
                c.personality.nudge("independence", 0.03)
                if gentle:
                    c.offline_neglect = True
                else:
                    add_mistake(c)
                    events.append("mistake")
    elif c.attention == "fake":
        c.attention_time += dt
        if c.attention_time > 10 * 60:
            c.attention = None
    else:
        c.attention = None
        # mischievous "fake" calls - the chance to discipline
        if (not gentle and not c.asleep and c.stage in ("child", "teen", "adult")):
            p = c.personality
            chance = (settings["fake_call_chance_per_hour"]
                      * (0.5 + p["stubbornness"]) * (1.2 - c.discipline / 100.0)
                      * (0.6 + p["sociability"]))
            if rng.random() < chance * h:
                c.attention = "fake"
                c.attention_time = 0.0
                c.attention_counted = False
                events.append("call")
    return events


def tick_real(c, dt):
    """Real-time windows for praise/scold opportunities."""
    c.misbehave_window = max(0.0, c.misbehave_window - dt)
    c.good_window = max(0.0, c.good_window - dt)
    c.praise_cooldown = max(0.0, c.praise_cooldown - dt)
    c.pet_cooldown = max(0.0, c.pet_cooldown - dt)


def _resolve_attention(c):
    """Reward the player for answering a genuine call."""
    if c.attention and c.attention != "fake" and need_reason(c) != c.attention:
        if not c.attention_counted and c.attention != "dark":
            c.memory.attachment = clamp(c.memory.attachment + 2)
            c.personality.nudge("sociability", 0.01)
        c.attention = None


def _egg_check(c):
    if c.stage == "egg":
        return Feedback("It's still an egg. Keep it cozy!", "button")
    return None


# ---------------------------------------------------------------- actions
def feed(c, food_id, rng):
    fb = _egg_check(c)
    if fb:
        return fb
    food = FOODS[food_id]
    if c.asleep:
        return Feedback(f"Shh... {c.name} is fast asleep.")
    if c.sick:
        return Feedback(f"{c.name} feels too sick to eat.", "refuse", "refuse")
    if food["kind"] == "meal" and c.hunger >= 98:
        return Feedback(f"{c.name} is full! It shakes its head.", "refuse", "refuse")
    like = c.memory.likes(food_id)
    refuse_p = c.personality["stubbornness"] * 0.25 * (1 - c.discipline / 100.0)
    if like < -0.3:
        refuse_p += 0.35
    if rng.random() < refuse_p:
        c.misbehave_window = 8.0
        return Feedback(f"{c.name} turns away from the {food['name']}. Hmph!", "refuse", "refuse")

    was_full = c.hunger >= 95
    c.hunger = clamp(c.hunger + food["hunger"])
    happy = food["happy"]
    fav = c.memory.favourite_food()
    then = None
    if food_id == fav:
        happy += 8
        msg = f"{food['name']}! {c.name}'s favourite!"
        then = "love"
    elif like > 0.3:
        happy += 4
        msg = f"{c.name} gobbles up the {food['name']} happily."
        then = "happy"
    elif like < -0.3:
        msg = f"{c.name} eats the {food['name']}... reluctantly. Good effort!"
        c.good_window = 8.0
    else:
        msg = f"{c.name} munches the {food['name']}."
    c.happiness = clamp(c.happiness + happy)
    c.weight += food["weight"] + (1 if was_full else 0)
    c.memory.ate(food_id)
    c.stats["meals" if food["kind"] == "meal" else "snacks"] += 1
    _resolve_attention(c)
    return Feedback(msg, "eat", "eat", effect=("food", food_id), then=then)


def can_play(c, rng):
    """Returns a Feedback if the creature won't play, else None."""
    fb = _egg_check(c)
    if fb:
        return fb
    if c.asleep:
        return Feedback(f"Shh... {c.name} is fast asleep.")
    if c.sick:
        return Feedback(f"{c.name} is too unwell to play.", "refuse", "sick")
    if c.energy < 10:
        return Feedback(f"{c.name} is too tired to play.", "refuse", "sad")
    p = c.personality
    refuse_p = 0.25 * p["stubbornness"] * (1 - c.discipline / 100.0) + 0.1 * (1 - p["playfulness"])
    if c.energy < 25:
        refuse_p += 0.15
    if rng.random() < refuse_p:
        c.misbehave_window = 8.0
        return Feedback(f"{c.name} doesn't feel like playing. It ignores you!", "refuse", "refuse")
    return None


def apply_game(c, game_id, won, rng):
    p = c.personality
    gain = 22 if won else 10
    fav = c.memory.favourite_game()
    if game_id == fav:
        gain += 8
    c.happiness = clamp(c.happiness + gain)
    c.weight = max(c.base_weight() * 0.5, c.weight - 1)
    c.energy = clamp(c.energy - 6)
    c.hunger = clamp(c.hunger - 3)
    c.memory.played(game_id, won)
    c.stats["games"] += 1
    if won:
        c.stats["wins"] += 1
        c.good_window = 8.0
    p.nudge("playfulness", 0.015)
    p.nudge("curiosity", 0.005)
    _resolve_attention(c)
    name = c.name
    extra = " It's its favourite game!" if game_id == fav else ""
    if won:
        if p["playfulness"] > 0.6:
            return Feedback(f"{name} won and does a victory dance!{extra}", "happy", "dance")
        if p["sociability"] > 0.6:
            return Feedback(f"{name} won and beams at you!{extra}", "happy", "love")
        if p["independence"] > 0.6:
            return Feedback(f"{name} won. It looks quietly proud.{extra}", "happy", "proud")
        return Feedback(f"{name} won! Happiness up!{extra}", "happy", "happy")
    if p["stubbornness"] > 0.6:
        return Feedback(f"{name} lost and sulks. It hates losing!", "refuse", "sulk")
    if p["independence"] > 0.6:
        return Feedback(f"{name} lost but shrugs it off.", "button", "idle")
    if p["playfulness"] > 0.5:
        return Feedback(f"{name} lost, but had fun anyway!{extra}", "happy", "happy")
    return Feedback(f"{name} lost. Better luck next time.", "button", "sad")


def clean(c):
    fb = _egg_check(c)
    if fb:
        return fb
    if c.poops == 0 and c.hygiene >= 85:
        return Feedback("Already squeaky clean!")
    c.poops = 0
    c.hygiene = 100.0
    c.happiness = clamp(c.happiness + 3)
    c.stats["cleans"] += 1
    _resolve_attention(c)
    msg = "All clean! Fresh and sparkly." if not c.asleep else "You quietly tidy up."
    return Feedback(msg, "clean", None if c.asleep else "happy", effect="flush")


def medicine(c):
    fb = _egg_check(c)
    if fb:
        return fb
    if not c.sick:
        c.happiness = clamp(c.happiness - 3)
        return Feedback(f"{c.name} isn't sick. Yuck, medicine!", "refuse", "refuse")
    c.doses -= 1
    c.stats["medicine"] += 1
    if c.doses > 0:
        return Feedback(f"{c.name} takes the medicine. One more dose needed.", "button",
                        "medicine", effect="pill")
    c.sick = False
    c.health = max(c.health, 75.0)
    _resolve_attention(c)
    return Feedback(f"{c.name} feels much better!", "heal", "recover", effect="pill")


def praise(c, last_action=None):
    fb = _egg_check(c)
    if fb:
        return fb
    if c.asleep:
        return Feedback(f"{c.name} smiles in its sleep.")
    if c.attention == "fake" or c.misbehave_window > 0:
        c.discipline = clamp(c.discipline - 4)
        c.personality.nudge("stubbornness", 0.02)
        return Feedback(f"{c.name} takes that as encouragement to misbehave...", "praise", "happy")
    if c.good_window > 0:
        c.good_window = 0.0
        c.discipline = clamp(c.discipline + 10)
        c.happiness = clamp(c.happiness + 6)
        c.memory.attachment = clamp(c.memory.attachment + 3)
        c.memory.praises += 1
        c.memory.reinforce_habit(last_action)
        c.stats["praises"] += 1
        return Feedback(f"{c.name} glows with pride!", "praise", "proud", effect="sparkle")
    if c.praise_cooldown > 0:
        return Feedback(f"{c.name} is happy you're here.", "praise", "happy")
    c.praise_cooldown = 20.0
    c.happiness = clamp(c.happiness + 2)
    c.memory.attachment = clamp(c.memory.attachment + 0.5)
    c.memory.reinforce_habit(last_action, 0.15)
    c.stats["praises"] += 1
    return Feedback(f"{c.name} enjoys the kind words.", "praise", "happy")


def scold(c, rng):
    fb = _egg_check(c)
    if fb:
        return fb
    if c.asleep:
        return Feedback(f"{c.name} is asleep. Let it rest.")
    p = c.personality
    if c.attention == "fake" or c.misbehave_window > 0:
        learn = 1.0 + min(c.memory.lessons, 5) * 0.1
        gain = 22 * (1 - 0.5 * p["stubbornness"]) * learn
        c.discipline = clamp(c.discipline + gain)
        if c.attention == "fake":
            c.attention = None
        c.misbehave_window = 0.0
        c.happiness = clamp(c.happiness - 2)
        c.memory.lessons += 1
        c.memory.scolds += 1
        c.stats["scolds"] += 1
        p.nudge("stubbornness", -0.02)
        if p["stubbornness"] > 0.6:
            return Feedback(f"{c.name} pouts... but got the message.", "scold", "sulk")
        return Feedback(f"{c.name} learned a lesson. Discipline up!", "scold", "sad")
    c.happiness = clamp(c.happiness - 10)
    c.memory.attachment = clamp(c.memory.attachment - 4)
    p.nudge("stubbornness", 0.03)
    p.nudge("sociability", -0.01)
    c.stats["scolds"] += 1
    return Feedback(f"{c.name} doesn't understand why it was scolded.", "scold", "confused")


def toggle_lights(c):
    c.lights_on = not c.lights_on
    if c.stage == "egg":
        return Feedback("Lights " + ("on." if c.lights_on else "off. The egg rests quietly."))
    if not c.lights_on:
        if c.asleep:
            _resolve_attention(c)
            return Feedback("Lights out. Sweet dreams.", "sleep")
        return Feedback(f"It's dark... {c.name} looks around nervously.", "button", "confused")
    _resolve_attention(c)
    if c.asleep:
        return Feedback(f"{c.name} squints in the light, still asleep.")
    return Feedback("Lights on!", "button", "happy")


def pet(c, rng):
    """Clicking the creature."""
    if c.stage == "egg":
        return Feedback("The egg feels warm. Something wiggles inside.")
    if c.asleep:
        return Feedback(f"{c.name} snuggles in its sleep. Zzz...")
    if c.pet_cooldown > 0:
        return None
    c.pet_cooldown = 4.0
    c.stats["pets"] += 1
    p = c.personality
    if p["independence"] > 0.7 and rng.random() < 0.35:
        return Feedback(f"{c.name} wriggles away. It wants its own space.", "button", "refuse")
    c.happiness = clamp(c.happiness + 1)
    c.memory.attachment = clamp(c.memory.attachment + 0.2)
    if c.memory.attachment > 70 or p["sociability"] > 0.65:
        return Feedback(f"{c.name} leans into your hand happily.", "praise", "love")
    return Feedback(f"{c.name} giggles.", "praise", "happy")


REASON_TEXT = {
    "hungry": "is hungry!",
    "bored": "is bored and wants to play!",
    "sick": "isn't feeling well...",
    "lights": "is asleep. Turn off the lights?",
    "dark": "doesn't like the dark. Lights?",
    "fake": "is calling for you...",
}

__all__ = ["Feedback", "tick", "tick_real", "feed", "can_play", "apply_game", "clean",
           "medicine", "praise", "scold", "toggle_lights", "pet", "need_reason",
           "REASON_TEXT", "GAMES"]
