from dataclasses import dataclass, asdict

from . import config as C


def fmt_time(minute: float) -> str:
    m = int(minute) % (24 * 60)
    h, mm = divmod(m, 60)
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{mm:02d} {suffix}"


@dataclass
class MealRecord:
    name: str
    time: int
    status: str = "upcoming"
    fed_at: int = -1
    reminded: bool = False
    overdue_alerted: bool = False

    @property
    def done(self) -> bool:
        return self.status in ("on_time", "late", "missed", "skipped")


class Schedule:
    def __init__(self, start_minute=None):
        self.meals = [MealRecord(s.name, s.time) for s in C.MEAL_SCHEDULE]
        if start_minute is not None:
            for m in self.meals:
                if start_minute >= m.time + C.ON_TIME_WINDOW:
                    m.status = "skipped"

    def reset(self):
        self.__init__()

    def update(self, now: float, reminder_lead: int):
        events = []
        for m in self.meals:
            if m.done:
                continue
            if not m.reminded and m.time - reminder_lead <= now < m.time:
                m.reminded = True
                events.append(("reminder", m))
            if now < m.time - C.EARLY_WINDOW:
                m.status = "upcoming"
            elif now <= m.time + C.ON_TIME_WINDOW:
                m.status = "due"
            elif now <= m.time + C.MISSED_AFTER:
                m.status = "overdue"
                if not m.overdue_alerted:
                    m.overdue_alerted = True
                    events.append(("overdue", m))
            else:
                m.status = "missed"
                events.append(("missed", m))
        return events

    def current_meal(self, now: float):
        for m in self.meals:
            if not m.done and m.time - C.EARLY_WINDOW <= now <= m.time + C.MISSED_AFTER:
                return m
        return None

    def next_meal(self, now: float):
        for m in self.meals:
            if not m.done and m.time + C.MISSED_AFTER >= now:
                return m
        return None

    def record_feeding(self, now: float):
        m = self.current_meal(now)
        if m is None:
            return None, "extra"
        m.fed_at = int(now)
        m.status = "on_time" if now <= m.time + C.ON_TIME_WINDOW else "late"
        return m, m.status

    def finish_day(self):
        for m in self.meals:
            if not m.done:
                m.status = "missed"

    def counts(self):
        out = {"on_time": 0, "late": 0, "missed": 0, "skipped": 0}
        for m in self.meals:
            if m.status in out:
                out[m.status] += 1
        return out

    def to_dict(self):
        return [asdict(m) for m in self.meals]

    @classmethod
    def from_dict(cls, data):
        s = cls()
        s.meals = [MealRecord(**d) for d in data]
        return s
