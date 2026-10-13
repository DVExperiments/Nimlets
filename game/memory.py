"""Lightweight creature memory: small persistent counters, nothing more."""
from .config import X_MIN, X_MAX

FOODS = {
    "rice": {"name": "Rice Ball", "kind": "meal", "hunger": 30, "happy": 2, "weight": 1},
    "fish": {"name": "Fish", "kind": "meal", "hunger": 35, "happy": 3, "weight": 1},
    "berries": {"name": "Berries", "kind": "meal", "hunger": 22, "happy": 6, "weight": 0},
    "cake": {"name": "Cake", "kind": "snack", "hunger": 10, "happy": 20, "weight": 2},
}

GAMES = {
    "higher_lower": "Higher or Lower",
    "direction": "Which Way?",
    "timing": "Timing Star",
}

SPOT_BINS = 8


class Memory:
    def __init__(self):
        self.food_likes = {f: 0.0 for f in FOODS}     # hidden taste, -1..1
        self.food_counts = {f: 0 for f in FOODS}
        self.game_counts = {g: 0 for g in GAMES}
        self.game_wins = {g: 0 for g in GAMES}
        self.attachment = 20.0                        # 0..100 bond with player
        self.lessons = 0                              # successful disciplines
        self.habits = {}                              # idle action -> extra weight
        self.spots = [0] * SPOT_BINS                  # where it likes to rest
        self.praises = 0
        self.scolds = 0

    @classmethod
    def new(cls, rng):
        m = cls()
        for f in FOODS:
            m.food_likes[f] = rng.uniform(-0.55, 0.3)
        fav = rng.choice(sorted(FOODS))
        m.food_likes[fav] = rng.uniform(0.45, 0.7)
        return m

    # ---- food -------------------------------------------------------------
    def ate(self, food):
        self.food_counts[food] = self.food_counts.get(food, 0) + 1
        # familiarity breeds (a little) fondness
        self.food_likes[food] = min(1.0, self.food_likes.get(food, 0.0) + 0.03)

    def likes(self, food):
        return self.food_likes.get(food, 0.0)

    def favourite_food(self):
        """Only 'known' once it has actually been eaten a couple of times."""
        best = max(self.food_likes, key=self.food_likes.get)
        if self.food_likes[best] >= 0.4 and self.food_counts.get(best, 0) >= 2:
            return best
        return None

    # ---- games ------------------------------------------------------------
    def played(self, game, won):
        self.game_counts[game] = self.game_counts.get(game, 0) + 1
        if won:
            self.game_wins[game] = self.game_wins.get(game, 0) + 1

    def favourite_game(self):
        if sum(self.game_counts.values()) < 3:
            return None
        score = {g: self.game_counts.get(g, 0) + 2 * self.game_wins.get(g, 0) for g in GAMES}
        best = max(score, key=score.get)
        return best if self.game_counts.get(best, 0) >= 2 else None

    # ---- habits -----------------------------------------------------------
    def reinforce_habit(self, action, amount=0.4):
        if action:
            self.habits[action] = min(4.0, self.habits.get(action, 0.0) + amount)

    def favourite_habit(self):
        if not self.habits:
            return None
        best = max(self.habits, key=self.habits.get)
        return best if self.habits[best] >= 1.0 else None

    def record_spot(self, x):
        idx = int((x - X_MIN) / (X_MAX - X_MIN + 1) * SPOT_BINS)
        idx = max(0, min(SPOT_BINS - 1, idx))
        self.spots[idx] += 1

    def favourite_spot(self):
        best = max(range(SPOT_BINS), key=lambda i: self.spots[i])
        avg = sum(self.spots) / SPOT_BINS
        if self.spots[best] < 12 or self.spots[best] < 1.6 * avg:
            return None
        width = (X_MAX - X_MIN) / SPOT_BINS
        return X_MIN + (best + 0.5) * width

    # ---- persistence ------------------------------------------------------
    def to_dict(self):
        return dict(vars(self))

    @classmethod
    def from_dict(cls, data):
        m = cls()
        for key, value in (data or {}).items():
            if hasattr(m, key):
                if isinstance(getattr(m, key), dict) and isinstance(value, dict):
                    getattr(m, key).update(value)
                else:
                    setattr(m, key, value)
        if len(m.spots) != SPOT_BINS:
            m.spots = [0] * SPOT_BINS
        return m
