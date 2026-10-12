"""Collection & lineage records - the replayability layer."""
from .genetics import MUTATION_NAMES

TOTAL_KEYS = ("meals", "snacks", "games", "wins", "cleans", "medicine", "praises", "scolds", "pets")


class Records:
    def __init__(self):
        self.discovered = []      # species ids seen
        self.lineage = []         # finished lives, oldest first
        self.totals = {k: 0 for k in TOTAL_KEYS}
        self.longest = None       # lineage entry of the longest-lived creature
        self.rare = []            # rare discoveries (secret forms, mutations)
        self.gifts = {"flower": 0, "leaf": 0, "drawing": 0, "pebble": 0}
        self.coins = 0             # earned by winning games, spent in the shop
        self.coins_earned = 0
        self.coins_spent = 0
        self.bought = {}

    def discover(self, species_id, species_db):
        """Returns True if this is a brand-new discovery."""
        if species_id in self.discovered or species_id not in species_db:
            return False
        self.discovered.append(species_id)
        if species_db[species_id].get("secret"):
            self.add_rare(species_db[species_id]["name"])
        return True

    def add_rare(self, label):
        if label not in self.rare:
            self.rare.append(label)

    def note_mutation(self, mutation):
        if mutation:
            self.add_rare(f"{MUTATION_NAMES.get(mutation, mutation)} colouring")

    def add_lineage(self, c, species_db, reason):
        entry = {
            "generation": c.generation,
            "name": c.name,
            "forms": list(c.forms),
            "final": c.species,
            "final_name": species_db.get(c.species, {}).get("name", c.species),
            "days": round(c.age_days, 2),
            "care_mistakes": c.care_mistakes,
            "reason": reason,
            "hue": c.genome.get("hue", 0),
            "mutation": c.genome.get("mutation"),
        }
        self.lineage.append(entry)
        for k in TOTAL_KEYS:
            self.totals[k] = self.totals.get(k, 0) + c.stats.get(k, 0)
        if self.longest is None or entry["days"] > self.longest["days"]:
            self.longest = dict(entry)
        return entry

    def combined_totals(self, c):
        return {k: self.totals.get(k, 0) + c.stats.get(k, 0) for k in TOTAL_KEYS}

    def to_dict(self):
        return {"discovered": self.discovered, "lineage": self.lineage, "totals": self.totals,
                "longest": self.longest, "rare": self.rare, "gifts": self.gifts, "coins": self.coins,
                "coins_earned": self.coins_earned, "coins_spent": self.coins_spent, "bought": self.bought}

    @classmethod
    def from_dict(cls, data):
        r = cls()
        data = data or {}
        r.discovered = list(data.get("discovered", []))
        r.lineage = list(data.get("lineage", []))
        r.totals.update(data.get("totals", {}))
        r.longest = data.get("longest")
        r.rare = list(data.get("rare", []))
        r.gifts.update(data.get("gifts", {}))
        r.coins = int(data.get("coins", 0))
        r.coins_earned = int(data.get("coins_earned", 0))
        r.coins_spent = int(data.get("coins_spent", 0))
        r.bought = dict(data.get("bought", {}))
        return r
