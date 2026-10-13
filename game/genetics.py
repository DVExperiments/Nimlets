"""Simplified single-pet genetics: colour, markings, tendencies, mutations."""
from .personality import TRAITS

MARKINGS = ["none", "spots", "stripes", "cheeks", "mask"]
MUTATIONS = ["shiny", "pastel", "midnight", "glitch", "chimera"]
MUTATION_NAMES = {"shiny": "Shiny", "pastel": "Pastel", "midnight": "Midnight", "glitch": "Glitched",
                  "chimera": "Chimera"}
EGG_NAMES = {"shiny": "Golden", "pastel": "Pastel", "midnight": "Void", "glitch": "Glitch",
             "chimera": "Chimera"}

# Behavioural mutations: hidden at hatching, they *emerge* days later.
BEHAVIOURS = {
    "nocturnal": "Nocturnal - more active at night",
    "mimic": "Mimic - copies your cursor and sounds",
    "wanderer": "Wanderer - fascinated by the edges of its world",
    "collector": "Collector - gathers little things into a pile",
    "dreamer": "Dreamer - vivid dreams, sometimes sleepwalks",
    "shapeshifter": "Shapeshifter - briefly changes its shape",
    "echo": "Echo - repeats sounds it hears",
    "inventor": "Inventor - keeps inventing games with objects",
    "trickster": "Trickster - loves hiding and pretending",
}
NEW_BEHAVIOUR_CHANCE = 0.18
KEEP_BEHAVIOUR_CHANCE = 0.3
CHIMERA_PARTS = {"ears": ["cat", "bunny", "round", "horns", "owl", "crest", "antenna", "sprout"],
                 "tail": ["curl", "spike", "fluff", "bolt", "none"]}


def chimera_parts(rng, hue):
    return {"parts": {"ears": rng.choice(CHIMERA_PARTS["ears"]),
                      "tail": rng.choice(CHIMERA_PARTS["tail"]),
                      "wings": rng.random() < 0.4},
            "hue2": (hue + rng.uniform(90, 270)) % 360}


def behaviour_mutation(rng):
    return {"id": rng.choice(sorted(BEHAVIOURS)), "emerge_days": round(rng.uniform(1.0, 4.0), 2)}

NAME_A = ["Pi", "Mo", "Nu", "Ko", "Ta", "Lu", "Bo", "Mi", "Ki", "Po", "Fu", "Ri",
          "Yu", "Chi", "Ne", "Pu", "Sora", "Hana", "Toto", "Kuro"]
NAME_B = ["pi", "mo", "ko", "ri", "chi", "no", "ru", "mi", "ta", "ppo", "nyan",
          "bu", "ki", "lo", "chan", "suke", ""]

NEW_MUTATION_CHANCE = 0.04
KEEP_MUTATION_CHANCE = 0.35


def make_name(rng):
    name = rng.choice(NAME_A) + rng.choice(NAME_B)
    return name if len(name) >= 3 else name + rng.choice(NAME_B[:-1])


def random_genome(rng):
    hue = rng.uniform(0, 360)
    genome = {
        "hue": hue,
        "sat": rng.uniform(0.45, 0.68),
        "marking": rng.choice(MARKINGS),
        "marking_hue": (hue + rng.uniform(120, 240)) % 360,
        "tendencies": {t: rng.uniform(0.3, 0.7) for t in TRAITS},
        "mutation": rng.choice(MUTATIONS) if rng.random() < NEW_MUTATION_CHANCE else None,
        "bmut": behaviour_mutation(rng) if rng.random() < NEW_BEHAVIOUR_CHANCE else None,
        "line": "water" if rng.random() < 0.45 else "land",      # which family tree it hatches into
    }
    if genome["mutation"] == "chimera":
        genome["chimera"] = chimera_parts(rng, hue)
    return genome


def inherit(parent_genome, parent_traits, rng):
    """Returns (child_genome, notes) - notes describe anything special."""
    notes = []
    hue = (parent_genome.get("hue", 0) + rng.gauss(0, 18)) % 360
    marking = parent_genome.get("marking", "none")
    if rng.random() > 0.75:
        marking = rng.choice(MARKINGS)
        if marking != parent_genome.get("marking"):
            notes.append("new markings")
    tendencies = {}
    for t in TRAITS:
        tendencies[t] = 0.6 * parent_traits.get(t, 0.5) + 0.4 * rng.uniform(0.25, 0.75)
    mutation = None
    if parent_genome.get("mutation") and rng.random() < KEEP_MUTATION_CHANCE:
        mutation = parent_genome["mutation"]
        notes.append(f"inherited {MUTATION_NAMES[mutation]} colouring")
    elif rng.random() < NEW_MUTATION_CHANCE:
        mutation = rng.choice(MUTATIONS)
        notes.append(f"a rare {MUTATION_NAMES[mutation]} mutation")
    bmut = None
    if parent_genome.get("bmut") and rng.random() < KEEP_BEHAVIOUR_CHANCE:
        bmut = {"id": parent_genome["bmut"]["id"], "emerge_days": round(rng.uniform(1.0, 4.0), 2)}
    elif rng.random() < NEW_BEHAVIOUR_CHANCE:
        bmut = behaviour_mutation(rng)
    child = {
        "hue": hue,
        "sat": max(0.35, min(0.75, parent_genome.get("sat", 0.55) + rng.uniform(-0.05, 0.05))),
        "marking": marking,
        "marking_hue": (parent_genome.get("marking_hue", hue + 180) + rng.gauss(0, 20)) % 360,
        "tendencies": tendencies,
        "mutation": mutation,
        "bmut": bmut,          # hidden: not mentioned in notes - it emerges later
        "line": (parent_genome.get("line", "land") if rng.random() < 0.85
                 else ("water" if parent_genome.get("line", "land") == "land" else "land")),
    }
    if mutation == "chimera":
        child["chimera"] = parent_genome.get("chimera") or chimera_parts(rng, hue)
    return child, notes


def egg_name(genome):
    return EGG_NAMES.get(genome.get("mutation"), "")
