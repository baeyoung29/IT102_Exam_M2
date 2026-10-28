import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta

from . import config as C

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saves")
PLANNER_PATH = os.path.join(SAVE_DIR, "classes.json")

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def fmt_clock(minute: int) -> str:
    m = int(minute) % (24 * 60)
    h, mm = divmod(m, 60)
    return f"{h % 12 or 12}:{mm:02d} {'AM' if h < 12 else 'PM'}"


def fmt_duration(minutes: float) -> str:
    minutes = max(0, int(minutes))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m:02d}m"
    return f"{h}h" if h else f"{m} min"


def days_label(days) -> str:
    days = sorted(set(days))
    if days == [0, 1, 2, 3, 4]:
        return "Weekdays"
    if days == list(range(7)):
        return "Every day"
    return " · ".join(WEEKDAYS[d] for d in days)


@dataclass
class ClassEntry:
    id: str
    name: str
    days: list
    start: int
    end: int
    room: str = ""
    color: int = 0
    active_from: str = ""

    @property
    def duration(self) -> int:
        return self.end - self.start

    @property
    def rgb(self):
        return C.CLASS_COLORS[self.color % len(C.CLASS_COLORS)]

    def time_label(self) -> str:
        return f"{fmt_clock(self.start)} – {fmt_clock(self.end)}"

    def start_dt(self, d: date) -> datetime:
        return datetime.combine(d, time()) + timedelta(minutes=self.start)

    def end_dt(self, d: date) -> datetime:
        return datetime.combine(d, time()) + timedelta(minutes=self.end)

    def active_from_dt(self) -> datetime:
        try:
            return datetime.fromisoformat(self.active_from)
        except (TypeError, ValueError):
            return datetime.min


@dataclass
class Attendance:
    class_id: str
    date: str
    name: str
    status: str
    coins: int = 0
    at: str = ""


def validate(name, days, start, end):
    if not name.strip():
        return "Give the class a name."
    if not days:
        return "Pick at least one day."
    if end <= start:
        return "The class has to end after it starts."
    if end - start > 8 * 60:
        return "A class can be at most 8 hours long."
    return None


class Planner:
    def __init__(self, path=PLANNER_PATH):
        self.path = path
        self.classes: list[ClassEntry] = []
        self.records: dict[str, Attendance] = {}
        self.coins = 0
        self.total_earned = 0
        self.streak = 0
        self.best_streak = 0
        self.history: list[dict] = []
        self.last_check = datetime.now()
        self.version = 0
        self._reminded: set[str] = set()
        self._alerted: set[str] = set()

    @staticmethod
    def key(entry, d: date) -> str:
        return f"{entry.id}|{d.isoformat()}"

    def get(self, class_id):
        for c in self.classes:
            if c.id == class_id:
                return c
        return None

    def sessions_on(self, d: date):
        return sorted((c for c in self.classes if d.weekday() in c.days), key=lambda c: (c.start, c.name))

    def status(self, entry, d: date, now: datetime) -> str:
        rec = self.records.get(self.key(entry, d))
        if rec:
            return rec.status
        if entry.end_dt(d) <= entry.active_from_dt():
            return "untracked"
        if now < entry.start_dt(d) - timedelta(minutes=C.CHECKIN_EARLY):
            return "upcoming"
        if now < entry.end_dt(d):
            return "open"
        return "missed"

    def reward_for(self, entry) -> int:
        bonus = min(C.STREAK_BONUS_CAP, self.streak * C.STREAK_BONUS_PER_CLASS)
        return C.CLASS_BASE_COINS + (entry.duration // 60) * C.CLASS_COINS_PER_HOUR + bonus

    def open_sessions(self, now: datetime):
        d = now.date()
        return [c for c in self.sessions_on(d) if self.status(c, d, now) == "open"]

    def next_session(self, now: datetime):
        for i in range(8):
            d = now.date() + timedelta(days=i)
            for c in self.sessions_on(d):
                st = self.status(c, d, now)
                if st in ("open", "upcoming"):
                    return c, d, st
        return None

    def week_stats(self, today: date):
        monday = today - timedelta(days=today.weekday())
        att = mis = coins = 0
        for r in self.records.values():
            try:
                d = date.fromisoformat(r.date)
            except ValueError:
                continue
            if monday <= d <= today:
                if r.status == "attended":
                    att += 1
                    coins += r.coins
                elif r.status == "missed":
                    mis += 1
        return {"attended": att, "missed": mis, "coins": coins}

    def add(self, name, days, start, end, room="", color=None, now=None):
        if len(self.classes) >= C.MAX_CLASSES:
            return None, f"You can have up to {C.MAX_CLASSES} classes."
        err = validate(name, days, start, end)
        if err:
            return None, err
        now = now or datetime.now()
        if color is None:
            color = len(self.classes) % len(C.CLASS_COLORS)
        e = ClassEntry(uuid.uuid4().hex[:10], name.strip()[:28], sorted(set(days)), int(start), int(end),
                       room.strip()[:24], color, now.isoformat(timespec="seconds"))
        self.classes.append(e)
        self._changed()
        return e, f"Added {e.name}."

    def update_class(self, class_id, name, days, start, end, room="", color=0, now=None):
        e = self.get(class_id)
        if not e:
            return None, "That class no longer exists."
        err = validate(name, days, start, end)
        if err:
            return None, err
        now = now or datetime.now()
        if (e.start, e.end, sorted(e.days)) != (int(start), int(end), sorted(set(days))):
            e.active_from = now.isoformat(timespec="seconds")
            for k in [k for k in self._reminded | self._alerted if k.startswith(e.id + "|")]:
                self._reminded.discard(k)
                self._alerted.discard(k)
        e.name, e.days, e.start, e.end = name.strip()[:28], sorted(set(days)), int(start), int(end)
        e.room, e.color = room.strip()[:24], color
        self._changed()
        return e, f"Saved {e.name}."

    def remove(self, class_id):
        e = self.get(class_id)
        if e:
            self.classes.remove(e)
            self._changed()
            return True, f"Removed {e.name}."
        return False, "That class no longer exists."

    def update(self, now: datetime, reminder_lead: int = C.DEFAULT_CLASS_REMINDER):
        events, changed = [], False
        first = max(self.last_check.date(), now.date() - timedelta(days=C.CATCH_UP_DAYS))
        d = first
        while d <= now.date():
            for c in self.sessions_on(d):
                k = self.key(c, d)
                st = self.status(c, d, now)
                if st == "missed" and k not in self.records:
                    self.records[k] = Attendance(c.id, d.isoformat(), c.name, "missed")
                    self.streak = 0
                    changed = True
                    events.append(("missed", c, d))
                elif d == now.date() and st in ("upcoming", "open"):
                    start = c.start_dt(d)
                    if (reminder_lead > 0 and k not in self._reminded
                            and start - timedelta(minutes=reminder_lead) <= now < start):
                        self._reminded.add(k)
                        mins = max(1, int((start - now).total_seconds() // 60) + 1)
                        events.append(("reminder", c, min(mins, reminder_lead)))
                    if st == "open" and now >= start and k not in self._alerted:
                        self._alerted.add(k)
                        self._reminded.add(k)
                        events.append(("start", c, None))
            d += timedelta(days=1)
        self.last_check = now
        if changed:
            self._changed()
        return events

    def check_in(self, class_id, now: datetime):
        e = self.get(class_id)
        if not e:
            return False, "That class no longer exists.", 0
        d = now.date()
        if d.weekday() not in e.days:
            return False, f"{e.name} doesn't meet today.", 0
        st = self.status(e, d, now)
        if st == "attended":
            return False, f"You already checked in to {e.name} today.", 0
        if st == "upcoming":
            opens = e.start - C.CHECKIN_EARLY
            return False, f"Check-in for {e.name} opens at {fmt_clock(opens)}.", 0
        if st in ("missed", "untracked"):
            return False, f"{e.name} is already over for today.", 0
        reward = self.reward_for(e)
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        self.coins += reward
        self.total_earned += reward
        self.records[self.key(e, d)] = Attendance(e.id, d.isoformat(), e.name, "attended", reward,
                                                  now.strftime("%H:%M"))
        self._alerted.add(self.key(e, d))
        self._log(now, f"Attended {e.name}", reward)
        self._changed()
        msg = f"Checked in to {e.name}! +{reward} {C.COIN_NAME}"
        if self.streak >= 2:
            msg += f" (streak {self.streak})"
        return True, msg, reward

    def can_afford(self, amount) -> bool:
        return self.coins >= amount

    def spend(self, amount, label, now=None) -> bool:
        if amount <= 0 or self.coins < amount:
            return False
        self.coins -= amount
        self._log(now or datetime.now(), label, -amount)
        self._changed()
        return True

    def _log(self, now, label, amount):
        self.history.append({"when": now.strftime("%a %I:%M %p").replace(" 0", " "),
                             "label": label, "amount": amount})
        self.history = self.history[-100:]

    def _changed(self):
        self.version += 1
        try:
            self.save()
        except OSError as e:
            print("Could not save classes:", e)

    def to_dict(self):
        return {
            "version": 1,
            "classes": [asdict(c) for c in self.classes],
            "records": [asdict(r) for r in self.records.values()][-1500:],
            "coins": self.coins, "total_earned": self.total_earned,
            "streak": self.streak, "best_streak": self.best_streak,
            "history": self.history,
            "last_check": self.last_check.isoformat(timespec="seconds"),
        }

    def save(self, path=None):
        path = path or self.path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=1)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path=PLANNER_PATH):
        p = cls(path)
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return p
        try:
            p.classes = [ClassEntry(**c) for c in d.get("classes", [])]
            for r in d.get("records", []):
                a = Attendance(**r)
                p.records[f"{a.class_id}|{a.date}"] = a
            p.coins = int(d.get("coins", 0))
            p.total_earned = int(d.get("total_earned", 0))
            p.streak = int(d.get("streak", 0))
            p.best_streak = int(d.get("best_streak", 0))
            p.history = list(d.get("history", []))
            p.last_check = datetime.fromisoformat(d.get("last_check")) if d.get("last_check") else datetime.now()
        except (TypeError, ValueError, KeyError) as e:
            print("Could not read classes.json:", e)
        return p
