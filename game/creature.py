"""The creature model: plain data plus (de)serialisation."""
import math
import random
import time

from .memory import Memory
from .learning import new_beliefs
from .personality import Personality, assign_quirks

RITUAL_MOVES = ("spin", "jump", "look", "dance", "sit", "wave")

STAGES = ["egg", "baby", "child", "teen", "adult", "elder"]
BASE_WEIGHT = {"egg": 5, "baby": 5, "child": 10, "teen": 18, "adult": 28, "elder": 26}


class Creature:
    FIELDS = [
        "name", "generation", "genome", "species", "stage", "age", "stage_age",
        "hunger", "happiness", "energy", "hygiene", "health", "weight",
        "discipline", "care_mistakes", "stage_mistakes", "sick", "doses", "poops",
        "asleep", "napping", "lights_on", "attention", "attention_time",
        "attention_counted", "poop_timer", "hist", "stats", "forms", "elder",
        "departed", "offline_neglect", "born_at",
        # living-pet memory (hidden)
        "quirks", "routine", "routine_mark", "routine_day", "wariness", "assoc", "last_gift_age",
        # artificial-life layer (hidden)
        "beliefs", "signals", "frontier", "bmut_active", "ritual", "ritual_day", "firsts",
        # reciprocal intelligence (hidden)
        "bond",
        # the observer update (hidden)
        "observer", "episodes", "prituals", "spatial", "skills", "mirror", "uncanny",
        # shop treats and toys: hidden tastes and what it has learned it likes
        "shop",
    ]

    def __init__(self, name, genome, generation=1, rng=None):
        rng = rng or random.Random()
        self._defaults()
        self.name = name
        self.genome = genome
        self.generation = generation
        self.personality = Personality.from_tendencies(genome.get("tendencies", {}), rng)
        self.memory = Memory.new(rng)
        self.quirks = assign_quirks(self.personality, rng)
        self.ritual = rng.sample(RITUAL_MOVES, rng.randint(2, 3))

    def _defaults(self):
        self.name = "Egg"
        self.generation = 1
        self.genome = {}
        self.species = "egg"
        self.stage = "egg"
        self.age = 0.0            # simulated seconds alive (incl. egg)
        self.stage_age = 0.0      # simulated seconds in current stage
        self.hunger = 80.0
        self.happiness = 80.0
        self.energy = 100.0
        self.hygiene = 100.0
        self.health = 100.0
        self.weight = 5.0
        self.discipline = 0.0
        self.care_mistakes = 0
        self.stage_mistakes = 0
        self.sick = False
        self.doses = 0
        self.poops = 0
        self.asleep = False
        self.napping = False
        self.lights_on = True
        self.attention = None
        self.attention_time = 0.0
        self.attention_counted = False
        self.poop_timer = 0.0
        self.hist = {"hunger": 0.0, "happy": 0.0, "weight": 0.0, "hours": 0.0}
        self.stats = {"meals": 0, "snacks": 0, "games": 0, "wins": 0, "cleans": 0,
                      "medicine": 0, "praises": 0, "scolds": 0, "pets": 0}
        self.forms = []
        self.elder = False
        self.departed = False
        self.offline_neglect = False
        self.born_at = time.time()
        self.quirks = []
        self.routine = [0.0] * 24        # how often the player visits at each hour
        self.routine_mark = ""
        self.routine_day = 0
        self.wariness = 0.0              # remembers neglect, fades with time
        self.assoc = {"medicine": 0.0, "food": 0.0, "ball": 0.0}
        self.last_gift_age = 0.0
        self.beliefs = new_beliefs()
        self.signals = {"style": "gesture", "assoc": {}, "learned": {}, "responses": {}}
        self.frontier = {"stage": 0, "progress": 0, "escapes": 0, "roams": 0}
        self.bmut_active = False
        self.ritual = ["spin", "look"]
        self.ritual_day = -1
        self.firsts = []                 # one-off diary moments already logged
        self.bond = {}                   # language, rituals, model of the player, shared memories
        self.observer = {}               # its model of the cursor: zones, transitions, predictions
        self.episodes = []               # episodic memories
        self.prituals = {}               # rituals it invented itself
        self.spatial = {}                # where it thinks things are
        self.skills = {}                 # object experiments and learned skills
        self.mirror = {}                 # mirror sessions
        self.uncanny = {}                # rare-event history and cooldowns
        self.shop = {}                   # tastes and learned preferences for shop items
        self.personality = Personality()
        self.memory = Memory()
        # real-time interaction windows (not saved)
        self.misbehave_window = 0.0
        self.good_window = 0.0
        self.praise_cooldown = 0.0
        self.pet_cooldown = 0.0

    # ---- helpers ----------------------------------------------------------
    @staticmethod
    def hearts(value, slots=4):
        return max(0, min(slots, math.ceil(value / (100.0 / slots) - 1e-9)))

    @property
    def age_days(self):
        return self.age / 86400.0

    def base_weight(self):
        return BASE_WEIGHT.get(self.stage, 10)

    def is_overweight(self):
        return self.stage != "egg" and self.weight > self.base_weight() * 1.5

    def is_underweight(self):
        return self.stage != "egg" and self.weight < self.base_weight() * 0.6

    # ---- persistence ------------------------------------------------------
    def to_dict(self):
        data = {f: getattr(self, f) for f in self.FIELDS}
        data["personality"] = self.personality.to_dict()
        data["memory"] = self.memory.to_dict()
        return data

    @classmethod
    def from_dict(cls, data):
        c = cls.__new__(cls)
        c._defaults()
        for f in cls.FIELDS:
            if f in data:
                setattr(c, f, data[f])
        c.personality = Personality.from_dict(data.get("personality", {}))
        c.memory = Memory.from_dict(data.get("memory", {}))
        if not c.quirks:   # saves from before the living-pet update
            c.quirks = assign_quirks(c.personality, random.Random(c.name + str(c.generation)))
        if len(c.routine) != 24:
            c.routine = [0.0] * 24
        for k in ("medicine", "food", "ball"):
            c.assoc.setdefault(k, 0.0)
        for k, v in new_beliefs().items():
            c.beliefs.setdefault(k, v)
        for k, v in {"stage": 0, "progress": 0, "escapes": 0, "roams": 0}.items():
            c.frontier.setdefault(k, v)
        return c

    def bmut(self):
        """Active behavioural mutation id, or None (hidden until it emerges)."""
        b = self.genome.get("bmut")
        return b["id"] if b and self.bmut_active else None
