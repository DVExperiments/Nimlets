"""Branching evolution tree.

    Egg -> Pipling (baby)
    Pipling -> Bobbit (good care) | Grumpkin (care mistakes)
    Child -> Sprouty (disciplined) | Zippit (playful) | Scruff (otherwise)
    Teen -> Luminelle, Mochimaru, Frolicat, Hootle, Grumblin, Thornback
            + secrets: Celestine (near-perfect care), Glitchling (rare genes)
    Adult -> Elder (same form, greyer, calmer) -> departs, leaving an egg
"""
from .creature import BASE_WEIGHT

ORDER = ["egg", "baby", "child", "teen", "adult", "elder"]


def stage_duration(stage, settings):
    return settings["stage_hours"].get(stage, 24.0) * 3600.0


def is_due(c, settings):
    if c.departed:
        return False
    return c.stage_age >= stage_duration(c.stage, settings)


def avg(c, key):
    hours = c.hist.get("hours", 0.0)
    if hours <= 0:
        return {"hunger": c.hunger, "happy": c.happiness, "weight": c.weight}[key]
    return c.hist.get(key, 0.0) / hours


def choose_next(c, rng):
    """Returns (species_id, stage). stage == 'depart' ends the life."""
    st = c.stage
    p = c.personality
    water = c.genome.get("line") == "water"
    if st == "egg":
        return ("dewdrop" if water else "pipling"), "baby"
    if st == "baby":
        good = c.stage_mistakes <= 1 and avg(c, "happy") >= 30
        if c.species == "dewdrop":
            return ("puddle" if good else "mudlet"), "child"
        return ("bobbit" if good else "grumpkin"), "child"
    if st == "child" and c.species in ("puddle", "mudlet"):
        if c.stage_mistakes >= 5:
            return "murkle", "teen"
        if c.discipline >= 50 and c.stage_mistakes <= 2:
            return "ripplet", "teen"
        if p["playfulness"] >= 0.55 or (c.species == "puddle" and rng.random() < 0.5):
            return "splashy", "teen"
        return "murkle", "teen"
    if st == "child":
        if c.stage_mistakes >= 5:
            return "scruff", "teen"
        if c.discipline >= 50 and c.stage_mistakes <= 2:
            return "sprouty", "teen"
        if p["playfulness"] >= 0.55 or (c.species == "bobbit" and rng.random() < 0.5):
            return "zippit", "teen"
        return "scruff", "teen"
    if st == "teen":
        return choose_adult(c, rng), "adult"
    if st == "adult":
        return c.species, "elder"
    return None, "depart"


def choose_adult(c, rng):
    p = c.personality
    happy = avg(c, "happy")
    heavy = avg(c, "weight") / BASE_WEIGHT["teen"]
    mutation = c.genome.get("mutation")

    # rare secrets first
    if (mutation == "glitch" and rng.random() < 0.6) or rng.random() < 0.02:
        return "glitchling"
    if (c.care_mistakes <= 2 and c.discipline >= 75 and c.memory.attachment >= 65
            and happy >= 55):
        chance = 0.3 + (0.4 if mutation == "shiny" else 0.0)
        if rng.random() < chance:
            return "aurora" if c.species in ("ripplet", "splashy", "murkle") else "celestine"

    collector = (c.genome.get("bmut") or {}).get("id") == "collector"
    if rng.random() < (0.5 if collector else 0.03 + 0.05 * max(0.0, p["curiosity"] - 0.7)):
        return "mycelia"           # a gentle secret for pets that gather things
    water = c.species in ("ripplet", "splashy", "murkle")
    if c.stage_mistakes >= 7 or c.care_mistakes >= 12:
        return "bogsworth" if water else "grumblin"   # a rough upbringing shows, whatever the teen form
    if water:
        return _water_adult(c, rng, happy, heavy)

    if c.species == "sprouty":
        if c.discipline >= 75 and c.stage_mistakes <= 3:
            return "luminelle"
        if heavy > 1.25:
            return "mochimaru"
        if p["curiosity"] + p["independence"] > 1.15:
            return "hootle"
        if p["playfulness"] >= 0.5:
            return "frolicat"
        return "luminelle" if c.discipline >= 50 else "hootle"
    if c.species == "zippit":
        if heavy > 1.25:
            return "mochimaru"
        if p["stubbornness"] >= 0.6 and c.discipline < 50:
            return "thornback"
        if p["playfulness"] >= 0.5:
            return "frolicat"
        return "hootle"
    # scruff (or anything unexpected)
    if c.stage_mistakes >= 5 or c.care_mistakes >= 8:
        return "grumblin"
    if heavy > 1.25:
        return "mochimaru"
    if p["stubbornness"] >= 0.55:
        return "thornback"
    return "hootle" if p["curiosity"] >= 0.5 else "grumblin"


def _water_adult(c, rng, happy, heavy):
    p = c.personality
    if c.species == "ripplet":
        if c.discipline >= 75 and c.stage_mistakes <= 3:
            return "lumifin"
        if heavy > 1.25:
            return "tidepup"
        if p["curiosity"] + p["independence"] > 1.15:
            return "coralie"
        return "lumifin" if c.discipline >= 50 else "coralie"
    if c.species == "splashy":
        if heavy > 1.25:
            return "tidepup"
        if p["stubbornness"] >= 0.6 and c.discipline < 50:
            return "gloomfin"
        if p["playfulness"] >= 0.5:
            return "bubbleroo"
        return "tidepup"
    if c.stage_mistakes >= 5:
        return "bogsworth"
    if heavy > 1.25:
        return "tidepup"
    if p["stubbornness"] >= 0.55:
        return "gloomfin"
    return "coralie" if p["curiosity"] >= 0.5 else "bogsworth"


def apply(c, species_id, stage, species_db=None):
    old_base = BASE_WEIGHT.get(c.stage, 10)
    new_base = BASE_WEIGHT.get(stage, 10)
    if c.stage == "egg":
        c.weight = float(new_base)
    else:
        c.weight = max(1.0, round(c.weight * new_base / old_base))
    if stage == "elder":
        c.elder = True
    else:
        c.forms.append(species_id)
    c.species = species_id
    c.stage = stage
    c.stage_age = 0.0
    c.stage_mistakes = 0
    c.hist = {"hunger": 0.0, "happy": 0.0, "weight": 0.0, "hours": 0.0}
    if species_db and species_id in species_db:
        for trait, amount in species_db[species_id].get("nudges", {}).items():
            c.personality.nudge(trait, amount)
    if stage == "baby":
        c.hunger, c.happiness = 60.0, 70.0
