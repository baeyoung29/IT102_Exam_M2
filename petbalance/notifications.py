from dataclasses import dataclass, asdict

from . import config as C


@dataclass
class Notification:
    kind: str
    level: str
    text: str
    day: int
    minute: int
    read: bool = False


class Notifier:
    def __init__(self):
        self.log: list[Notification] = []
        self.pending_toasts: list[Notification] = []
        self._last: dict[str, float] = {}
        self.quiet = False

    @staticmethod
    def _abs(day, minute):
        return day * 24 * 60 + minute

    def push(self, kind, level, text, day, minute, cooldown_key=None, toast=True):
        if cooldown_key:
            cd = C.NOTIFY_COOLDOWN.get(cooldown_key.split(":")[0], 0)
            last = self._last.get(cooldown_key)
            now = self._abs(day, minute)
            if last is not None and now - last < cd:
                return None
            self._last[cooldown_key] = now
        n = Notification(kind, level, text, day, int(minute))
        self.log.append(n)
        if toast and not self.quiet:
            self.pending_toasts.append(n)
        return n

    def drain_toasts(self):
        out, self.pending_toasts = self.pending_toasts, []
        return out

    def unread(self) -> int:
        return sum(1 for n in self.log if not n.read)

    def mark_all_read(self):
        for n in self.log:
            n.read = True

    def to_dict(self):
        return {"log": [asdict(n) for n in self.log[-200:]], "last": self._last}

    @classmethod
    def from_dict(cls, d):
        n = cls()
        n.log = [Notification(**x) for x in d.get("log", [])]
        n._last = {k: float(v) for k, v in d.get("last", {}).items()}
        return n
