import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, time, timedelta

from . import config as C
from .economy import Wallet, Inventory, price_for, buy
from .notifications import Notifier
from .pet import Pet
from .schedule import Schedule, fmt_time

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saves")
SAVE_PATH = os.path.join(SAVE_DIR, "savegame.json")
SETTINGS_PATH = os.path.join(SAVE_DIR, "settings.json")


def money(amount) -> str:
    return f"{C.CURRENCY_SYMBOL}{int(amount):,}"


@dataclass
class Settings:
    reminder_lead: int = C.DEFAULT_REMINDER_LEAD
    pause_in_menus: bool = True
    sound: bool = True
    volume: float = 0.6
    show_tutorial: bool = True
    toasts: bool = True
    class_reminder_lead: int = C.DEFAULT_CLASS_REMINDER

    def save(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls):
        s = cls()
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    if hasattr(s, k):
                        setattr(s, k, v)
        except (OSError, ValueError):
            pass
        return s


def daily_goal(day: int):
    if day == 1:
        return ("Tutorial", "Feed all three meals today.",
                lambda s, r: r["missed"] == 0)
    if day == 2:
        return ("Routine challenge", "Feed every meal on time.",
                lambda s, r: r["on_time"] == 3)
    if day == 3:
        limit = 220
        return ("Budget challenge", f"Keep the pet healthy and spend no more than {money(limit)}.",
                lambda s, r: r["spent"] <= limit and r["hp"] >= 60)
    if day % 2 == 0:
        return ("Balance challenge", "Keep a healthy weight and HP of 70 or more.",
                lambda s, r: r["weight_status"] == "Healthy" and r["hp"] >= 70)
    target = 200
    return ("Saver's goal", f"Finish the day with at least {money(target)} and no missed meals.",
            lambda s, r: r["balance"] >= target and r["missed"] == 0)


def minute_of(dt: datetime) -> float:
    return dt.hour * 60 + dt.minute + dt.second / 60


def is_night(minute: float) -> bool:
    return minute >= C.DAY_END or minute < C.DAY_START


class GameState:
    def __init__(self, settings: Settings | None = None, now: datetime | None = None):
        now = now or datetime.now()
        self.settings = settings or Settings()
        self.clock = now
        self.day = 1
        self.minute = minute_of(now)
        self.speed = 1
        self.pet = Pet()
        self.wallet = Wallet()
        self.inv = Inventory()
        for k, q in C.STARTING_INVENTORY.items():
            self.inv.add(k, q)
        self.schedule = Schedule(start_minute=self.minute)
        self.notifier = Notifier()
        self.day_over = False
        self.day_unstarted = False
        self.summary = None
        self.summary_pending = False
        self.history = []
        self.day_stats = self._fresh_stats()
        self.planner = None
        self.away_report = None
        self._away = False
        if self.minute >= C.DAY_END:
            self.day_over = True
            self.day_unstarted = True
            msg = f"Welcome! It's late, so {self.pet.name} is asleep. Day 1 starts at midnight."
        else:
            nxt = self.schedule.next_meal(self.minute)
            when = f"{nxt.name} is at {fmt_time(nxt.time)}." if nxt else "The next meal is breakfast tomorrow."
            msg = f"Welcome! {self.pet.name} is counting on you. {when}"
        self.notifier.push("info", "info", msg, self.day, self.minute)

    @staticmethod
    def _fresh_stats():
        return {"overfeeds": 0, "underfeeds": 0, "extra_meals": 0, "treats": 0,
                "plays": 0, "pets": 0, "vet": 0}

    @property
    def paused(self):
        return False

    @property
    def asleep(self) -> bool:
        return is_night(self.minute)

    @property
    def abs_minute(self) -> float:
        return self.day * 24 * 60 + self.minute

    def update(self, real_dt: float = 0, menu_open: bool = False):
        now = datetime.now()
        gap = (now - self.clock).total_seconds() / 60
        self.sync(now, away=gap >= C.AWAY_REPORT_MIN)

    def sync(self, now: datetime, away: bool = False):
        if now <= self.clock:
            return
        gap = (now - self.clock).total_seconds() / 60
        if gap > C.OFFLINE_MAX_DAYS * 24 * 60:
            self.clock = now - timedelta(days=C.OFFLINE_MAX_DAYS)
            self.minute = minute_of(self.clock)
        if away:
            self._begin_away(gap)
        while self.clock < now:
            nxt = min(now, self.clock + timedelta(minutes=1))
            if nxt.date() != self.clock.date():
                midnight = datetime.combine(nxt.date(), time())
                self._advance((midnight - self.clock).total_seconds() / 60, 24 * 60)
                self.clock = midnight
                self._new_date()
                continue
            self._advance((nxt - self.clock).total_seconds() / 60, minute_of(nxt))
            self.clock = nxt
        if away:
            self._end_away()

    def _advance(self, minutes: float, new_minute: float):
        if minutes <= 0:
            self.minute = new_minute
            return
        self.minute = new_minute
        night = is_night(min(new_minute, 24 * 60 - 0.01))
        self.pet.tick(minutes, asleep=night)
        if self._away and self.pet.hp < C.OFFLINE_HP_FLOOR:
            self.pet.hp = C.OFFLINE_HP_FLOOR
            self.pet.fainted = False
        if self.inv.has("catbed") and not self.pet.fainted and not night:
            self.pet.happiness = min(100, self.pet.happiness
                                     + C.HAPPINESS_DECAY * C.CATBED_HAPPINESS_SAVE * minutes)
        if not self.day_over:
            for event, meal in self.schedule.update(self.minute, self.settings.reminder_lead):
                self._schedule_event(event, meal)
            if not night and not self._away:
                self._check_alerts()
        if self.pet.fainted and not self._fainted_reported:
            self._fainted_reported = True
            self.notifier.push("hp_low", "bad",
                               f"{self.pet.name} fainted! A vet visit is needed.",
                               self.day, self.minute)
        if self.minute >= C.DAY_END and not self.day_over:
            self.end_day()

    _fainted_reported = False
    _away_missed: list = []

    def _new_date(self):
        if not self.day_over:
            self.end_day()
        self.next_day()

    def _begin_away(self, gap_minutes):
        self._away = True
        self.notifier.quiet = True
        p = self.pet
        self._away_start = {"minutes": gap_minutes, "day": self.day, "hp": p.hp, "hunger": p.hunger,
                            "happiness": p.happiness, "weight": p.weight, "balance": self.wallet.balance,
                            }
        self._away_missed = []

    def _end_away(self):
        self._away = False
        self.notifier.quiet = False
        a, p = self._away_start, self.pet
        missed = list(self._away_missed)
        self.away_report = {
            "minutes": a["minutes"], "days": self.day - a["day"],
            "hp": (a["hp"], p.hp), "hunger": (a["hunger"], p.hunger),
            "happiness": (a["happiness"], p.happiness), "weight": (a["weight"], p.weight),
            "money": (a["balance"], self.wallet.balance), "missed": missed,
            "weak": p.hp <= C.OFFLINE_HP_FLOOR + 0.01,
        }
        if a["minutes"] < C.AWAY_REPORT_MIN:
            self.away_report = None
        if self.summary is None or self.summary.get("day") != self.day:
            self.summary_pending = False

    def _schedule_event(self, event, meal):
        n, d, m = self.pet.name, self.day, self.minute
        if event == "reminder":
            mins = max(1, int(round(meal.time - m)))
            self.notifier.push("reminder", "info",
                               f"{meal.name} time is in {mins} minutes.", d, m)
        elif event == "overdue":
            self.notifier.push("reminder", "warn",
                               f"{meal.name} is overdue! {n} is waiting by the bowl.", d, m)
        elif event == "missed":
            if self._away:
                self._away_missed.append(f"{self.clock.strftime('%a')} {meal.name}")
            self.pet.happiness = max(0, self.pet.happiness - 10)
            self.notifier.push("reminder", "bad",
                               f"{meal.name} was missed. {n} is upset.", d, m)

    def _check_alerts(self):
        p, d, m, n = self.pet, self.day, self.minute, self.pet.name
        if p.hunger >= C.HUNGER_CRITICAL:
            self.notifier.push("hungry", "bad",
                               f"{n} is starving! Health is dropping.", d, m, "starving")
        elif p.hunger >= C.HUNGER_WARNING:
            self.notifier.push("hungry", "warn", f"{n} is hungry.", d, m, "hungry")
        if p.hp < 30 and not p.fainted:
            self.notifier.push("hp_low", "bad",
                               f"{n}'s health is critically low!", d, m, "hp_low")
        ws = p.weight_status
        if ws == "Underweight":
            self.notifier.push("weight", "warn",
                               f"{n} may be underweight. Try regular meals.", d, m, "weight:under")
        elif ws in ("Overweight", "Obese"):
            self.notifier.push("weight", "warn",
                               f"{n} may be {ws.lower()}. Try smaller portions and play.",
                               d, m, "weight:over")
        if p.happiness < 25:
            self.notifier.push("info", "warn",
                               f"{n} seems sad. Some petting or play might help.",
                               d, m, "happy_low")
        self._check_budget()

    def _check_budget(self):
        if self.wallet.balance < C.LOW_BUDGET_THRESHOLD:
            self.notifier.push("budget", "warn",
                               f"Your budget is getting low ({money(self.wallet.balance)} left).",
                               self.day, self.minute, "budget")

    def price(self, key) -> int:
        return price_for(C.ITEMS_BY_KEY[key], self.day)

    def buy(self, key):
        item = C.ITEMS_BY_KEY[key]
        if item.coin_only:
            return False, f"{item.name} can only be bought with {C.COIN_NAME}."
        cost = self.price(key)
        if not buy(item, self.wallet, self.inv, self.day, self.minute):
            return False, f"Not enough money for {item.name} ({money(cost)})."
        self._check_budget()
        return True, f"Bought {item.name} for {money(cost)}."

    def buy_with_coins(self, key):
        item = C.ITEMS_BY_KEY[key]
        if self.planner is None or item.coin_price <= 0:
            return False, f"{item.name} can't be bought with {C.COIN_NAME}."
        if item.kind == "decor" and self.inv.has(key):
            return False, f"You already have the {item.name}."
        if not self.planner.spend(item.coin_price, f"Bought {item.name}"):
            return False, (f"Not enough {C.COIN_NAME} for {item.name} ({item.coin_price}). "
                           "Check in to your classes to earn more.")
        self.inv.add(item.key, item.servings)
        if item.kind == "decor":
            return True, f"{item.name} is now in {self.pet.name}'s room!"
        return True, f"Bought {item.name} for {item.coin_price} {C.COIN_NAME}."

    def feed(self, key, portion_label):
        item = C.ITEMS_BY_KEY[key]
        servings = C.PORTIONS[portion_label] if item.kind == "food" else 1
        if not self.inv.has(key, servings):
            return False, f"Not enough {item.name} in your inventory."
        self.inv.use(key, servings)
        r = self.pet.feed(item, servings)
        n = self.pet.name

        if item.kind == "treat":
            self.day_stats["treats"] += 1
            msg = f"{n} loved the treat! (+{r.happiness_change:.0f} happiness)"
            if self.day_stats["treats"] > 3:
                msg += " Careful, lots of treats today."
            return True, msg

        meal, status = self.schedule.record_feeding(self.minute)
        if r.verdict == "too_much":
            self.day_stats["overfeeds"] += 1
        elif r.verdict == "too_little":
            self.day_stats["underfeeds"] += 1

        if status == "on_time":
            self.pet.happiness = min(100, self.pet.happiness + 6)
            msg = f"{meal.name} served on time!"
        elif status == "late":
            self.pet.happiness = max(0, self.pet.happiness - 3)
            msg = f"{meal.name} served late."
        else:
            self.day_stats["extra_meals"] += 1
            msg = "Extra meal outside the schedule."

        if r.verdict == "too_much":
            msg += f" That was too much — +{r.weight_change:.2f} kg."
            self.notifier.push("weight", "warn",
                               f"Large portion: {n} is stuffed. Watch the weight.",
                               self.day, self.minute, toast=False)
        elif r.verdict == "too_little":
            msg += f" {n} is still hungry."
        else:
            msg += " Good portion."
        return True, msg

    def give_vitamin(self):
        item = C.ITEMS_BY_KEY["vitamins"]
        if not self.inv.has("vitamins"):
            return False, "No vitamins. Buy some in the shop."
        if not self.pet.give_vitamin(item, self.day):
            return False, "Already gave vitamins today."
        self.inv.use("vitamins")
        return True, f"Vitamins given. +{item.hp:.0f} HP."

    def pet_action(self):
        if self.asleep:
            self.pet.happiness = min(100, self.pet.happiness + 1)
            return True, f"{self.pet.name} is sleeping. A gentle pat... (+1)"
        gained = self.pet.pet_it(self.abs_minute)
        self.day_stats["pets"] += 1
        if gained >= 8:
            return True, f"{self.pet.name} purrs happily. +{gained:.0f} happiness"
        return True, f"{self.pet.name} enjoys it. (+1 — wait a bit for a bigger boost)"

    def play_action(self):
        if self.asleep:
            return False, f"{self.pet.name} is asleep. Play after {fmt_time(C.DAY_START)}."
        if not self.inv.has("toy"):
            return False, "You need a Toy Mouse to play. Find one in the shop."
        mins_left = C.PLAY_COOLDOWN - (self.abs_minute - self.pet.last_play_minute)
        if mins_left > 0:
            return False, f"{self.pet.name} is tired. Play again in {int(mins_left) + 1} min."
        self.inv.use("toy")
        self.pet.play(self.abs_minute)
        self.day_stats["plays"] += 1
        return True, f"Play time! +15 happiness, a little weight burned."

    def vet_visit(self):
        cost = C.VET_COST
        if self.wallet.balance >= cost:
            self.wallet.spend(cost, "Vet visit", self.day, self.minute)
        else:
            paid = self.wallet.balance
            if paid:
                self.wallet.spend(paid, "Vet visit (partial)", self.day, self.minute)
        self.pet.revive()
        self._fainted_reported = False
        self.day_stats["vet"] += 1
        self.notifier.push("good", "good", f"The vet patched {self.pet.name} up. HP is 50.",
                           self.day, self.minute)

    def end_day(self):
        if self.day_over:
            return
        self.schedule.finish_day()
        self.summary = self._build_summary()
        self.history.append(self.summary)
        self.day_over = True
        self.summary_pending = True
        if not self._away:
            self.save()

    def _build_summary(self):
        p = self.pet
        c = self.schedule.counts()
        r = {
            "day": self.day,
            "hp": round(p.hp), "happiness": round(p.happiness),
            "weight": round(p.weight, 2), "weight_status": p.weight_status,
            "on_time": c["on_time"], "late": c["late"], "missed": c["missed"],
            "skipped": c.get("skipped", 0),
            "spent": self.wallet.spent_on(self.day),
            "earned": self.wallet.earned_on(self.day),
            "balance": self.wallet.balance,
            **self.day_stats,
        }
        score = 0
        score += 30 * p.hp / 100
        score += 10 * c["on_time"] + 5 * c["late"] + 10 * c.get("skipped", 0)
        score += {"Healthy": 15, "Underweight": 7, "Overweight": 7}.get(p.weight_status, 0)
        score += 15 * p.happiness / 100
        if self.wallet.balance >= C.LOW_BUDGET_THRESHOLD:
            score += 10
        elif self.wallet.balance > 0:
            score += 5
        score -= 5 * r["vet"]
        score -= 5 * r["overfeeds"]
        score -= 3 * max(0, r["treats"] - 3)
        score = max(0, min(100, round(score)))
        r["score"] = score
        if score >= 85:
            r["rating"], r["stars"] = "Excellent", 3
        elif score >= 65:
            r["rating"], r["stars"] = "Good", 2
        elif score >= 45:
            r["rating"], r["stars"] = "Okay", 1
        else:
            r["rating"], r["stars"] = "Needs more care", 0

        title, desc, check = daily_goal(self.day)
        r["goal_title"], r["goal_desc"] = title, desc
        r["goal_met"] = bool(check(self, r))

        good, improve = [], []
        if c["on_time"] and c["on_time"] + c.get("skipped", 0) == 3:
            good.append("Every meal was on time.")
        if c["missed"]:
            improve.append(f"{c['missed']} meal(s) missed — watch the reminders.")
        elif c["late"]:
            improve.append(f"{c['late']} meal(s) were late.")
        if p.weight_status == "Healthy":
            good.append("Weight stayed in the healthy range.")
        elif p.weight_status == "Underweight":
            improve.append("Weight is low — use Regular portions at each meal.")
        else:
            improve.append("Weight is high — use smaller portions and fewer treats.")
        if r["overfeeds"]:
            improve.append(f"{r['overfeeds']} oversized portion(s) today.")
        if p.hp >= 80:
            good.append("Health is strong.")
        elif p.hp < 50:
            improve.append("Health is low — consider vitamins or premium food.")
        if p.happiness >= 70:
            good.append(f"{p.name} is very happy.")
        elif p.happiness < 40:
            improve.append("Happiness is low — pet and play more often.")
        if self.wallet.balance >= C.LOW_BUDGET_THRESHOLD:
            good.append(f"You kept {money(self.wallet.balance)} in reserve.")
        else:
            improve.append("Money is running low — compare cost per serving.")
        r["good"], r["improve"] = good, improve
        return r

    def next_day(self):
        if self.day_unstarted:
            self.day_unstarted = False
        else:
            self.day += 1
        self.minute = 0.0
        self.day_over = False
        self.summary_pending = False
        self.schedule.reset()
        self.day_stats = self._fresh_stats()
        if self.day == 1:
            return
        self.wallet.earn(C.DAILY_ALLOWANCE, "Daily allowance", self.day, self.minute)
        title, desc, _ = daily_goal(self.day)
        self.notifier.push("info", "info",
                           f"Day {self.day} — {title}: {desc} (+{money(C.DAILY_ALLOWANCE)} allowance)",
                           self.day, self.minute)
        if not self._away:
            self.save()

    def to_dict(self):
        return {
            "version": 2,
            "clock": self.clock.isoformat(timespec="seconds"),
            "day_unstarted": self.day_unstarted, "summary_pending": self.summary_pending,
            "day": self.day, "minute": self.minute, "speed": self.speed,
            "pet": self.pet.to_dict(), "wallet": self.wallet.to_dict(),
            "inventory": self.inv.to_dict(), "schedule": self.schedule.to_dict(),
            "notifier": self.notifier.to_dict(), "day_over": self.day_over,
            "summary": self.summary, "history": self.history, "day_stats": self.day_stats,
        }

    def save(self, path=None):
        path = path or SAVE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=1)
        os.replace(tmp, path)

    @classmethod
    def load(cls, settings=None, path=None, now=None):
        path = path or SAVE_PATH
        now = now or datetime.now()
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        g = cls(settings, now)
        g.notifier = Notifier.from_dict(d["notifier"])
        g.day = d["day"]
        g.pet = Pet.from_dict(d["pet"])
        g.wallet = Wallet.from_dict(d["wallet"])
        g.inv = Inventory.from_dict(d["inventory"])
        g.history = d.get("history", [])
        g.day_stats = {**cls._fresh_stats(), **d.get("day_stats", {})}
        if d.get("clock"):
            g.clock = datetime.fromisoformat(d["clock"])
            g.minute = minute_of(g.clock)
            g.schedule = Schedule.from_dict(d["schedule"])
            g.day_over = d.get("day_over", False)
            g.day_unstarted = d.get("day_unstarted", False)
            g.summary = d.get("summary")
            g.summary_pending = d.get("summary_pending", False)
        else:
            g.pet.last_pet_minute = g.pet.last_play_minute = -999
            g.summary = None
        return g

    @staticmethod
    def has_save(path=None):
        path = path or SAVE_PATH
        return os.path.exists(path)
