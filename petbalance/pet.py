from dataclasses import dataclass, asdict

from . import config as C


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


@dataclass
class FeedResult:
    hunger_before: float
    hunger_after: float
    overflow: float
    weight_change: float
    happiness_change: float
    hp_change: float
    verdict: str


@dataclass
class Pet:
    name: str = C.PET_NAME
    hp: float = 100.0
    hunger: float = 30.0
    happiness: float = 75.0
    weight: float = C.START_WEIGHT
    last_pet_minute: float = -999
    last_play_minute: float = -999
    vitamins_day: int = -1
    fainted: bool = False

    @property
    def weight_status(self) -> str:
        if self.weight < C.HEALTHY_MIN:
            return "Underweight"
        if self.weight >= C.OBESE_AT:
            return "Obese"
        if self.weight > C.HEALTHY_MAX:
            return "Overweight"
        return "Healthy"

    @property
    def hunger_status(self) -> str:
        if self.hunger >= C.HUNGER_CRITICAL:
            return "Starving"
        if self.hunger >= C.HUNGER_WARNING:
            return "Hungry"
        if self.hunger >= 35:
            return "Peckish"
        return "Full"

    @property
    def mood(self) -> str:
        if self.weight_status in ("Overweight", "Obese"):
            return "overweight"
        if (self.hunger >= C.HUNGER_WARNING or self.hp < 35
                or self.weight_status == "Underweight" or self.happiness < 25):
            return "hungry"
        return "happy"

    def tick(self, minutes: float, asleep: bool = False):
        if self.fainted:
            return
        rate = C.HUNGER_RATE * (C.SLEEP_HUNGER_MULT if asleep else 1)
        self.hunger = clamp(self.hunger + rate * minutes, 0, 100)

        if not asleep:
            decay = C.HAPPINESS_DECAY
            if self.hunger >= C.HUNGER_WARNING:
                decay += C.HAPPINESS_HUNGRY_DECAY
            if self.weight_status != "Healthy":
                decay += 0.02
            self.happiness = clamp(self.happiness - decay * minutes, 0, 100)

        if self.hunger >= 50:
            loss = C.WEIGHT_LOSS_WHEN_HUNGRY * (C.SLEEP_HUNGER_MULT if asleep else 1)
            self.weight = clamp(self.weight - loss * minutes, C.WEIGHT_MIN, C.WEIGHT_MAX)

        drain = 0.0
        if self.hunger >= C.HUNGER_CRITICAL:
            drain += C.HP_DRAIN_STARVING * (0.5 if asleep else 1)
        if self.weight_status != "Healthy" and not asleep:
            drain += C.HP_DRAIN_BAD_WEIGHT * (2 if self.weight_status == "Obese" else 1)
        if self.happiness < 20 and not asleep:
            drain += C.HP_DRAIN_SAD
        if drain > 0:
            self.hp = clamp(self.hp - drain * minutes, 0, 100)
        elif self.hunger < 50 and self.happiness >= 40:
            self.hp = clamp(self.hp + C.HP_REGEN * minutes, 0, 100)

        if self.hp <= 0:
            self.fainted = True

    def preview_feed(self, item: C.Item, servings: float) -> FeedResult:
        satiety = item.satiety * servings
        after = self.hunger - satiety
        overflow = max(0.0, -after)
        after = max(0.0, after)
        weight_change = overflow * C.WEIGHT_PER_OVERFLOW_POINT + item.weight * servings
        if self.hunger - satiety > 15 and item.kind == "food":
            verdict = "too_little"
        elif overflow > 8:
            verdict = "too_much"
        else:
            verdict = "good"
        happy = item.happiness * servings
        if verdict == "too_much":
            happy -= 3
        return FeedResult(self.hunger, after, overflow, weight_change,
                          happy, item.hp * servings, verdict)

    def feed(self, item: C.Item, servings: float) -> FeedResult:
        r = self.preview_feed(item, servings)
        self.hunger = r.hunger_after
        self.weight = clamp(self.weight + r.weight_change, C.WEIGHT_MIN, C.WEIGHT_MAX)
        self.happiness = clamp(self.happiness + r.happiness_change, 0, 100)
        self.hp = clamp(self.hp + r.hp_change, 0, 100)
        return r

    def give_vitamin(self, item: C.Item, day: int) -> bool:
        if self.vitamins_day == day:
            return False
        self.vitamins_day = day
        self.hp = clamp(self.hp + item.hp, 0, 100)
        return True

    def pet_it(self, now: float) -> float:
        if now - self.last_pet_minute < C.PET_COOLDOWN:
            self.happiness = clamp(self.happiness + 1, 0, 100)
            return 1
        self.last_pet_minute = now
        self.happiness = clamp(self.happiness + 8, 0, 100)
        return 8

    def play(self, now: float) -> float:
        if now - self.last_play_minute < C.PLAY_COOLDOWN:
            return 0
        self.last_play_minute = now
        self.happiness = clamp(self.happiness + 15, 0, 100)
        self.hunger = clamp(self.hunger + 6, 0, 100)
        self.weight = clamp(self.weight - 0.03, C.WEIGHT_MIN, C.WEIGHT_MAX)
        return 15

    def revive(self):
        self.fainted = False
        self.hp = 50
        self.hunger = min(self.hunger, 40)
        self.happiness = max(self.happiness, 30)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        p = cls()
        for k, v in d.items():
            if hasattr(p, k):
                setattr(p, k, v)
        return p
