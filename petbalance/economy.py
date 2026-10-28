from dataclasses import dataclass, field, asdict

from . import config as C


@dataclass
class Expense:
    day: int
    minute: int
    label: str
    amount: int


@dataclass
class Wallet:
    balance: int = C.STARTING_MONEY
    history: list = field(default_factory=list)

    def can_afford(self, amount: int) -> bool:
        return self.balance >= amount

    def spend(self, amount: int, label: str, day: int, minute: int) -> bool:
        if not self.can_afford(amount):
            return False
        self.balance -= amount
        self.history.append(Expense(day, int(minute), label, -amount))
        return True

    def earn(self, amount: int, label: str, day: int, minute: int):
        self.balance += amount
        self.history.append(Expense(day, int(minute), label, amount))

    def spent_on(self, day: int) -> int:
        return -sum(e.amount for e in self.history if e.day == day and e.amount < 0)

    def earned_on(self, day: int) -> int:
        return sum(e.amount for e in self.history if e.day == day and e.amount > 0)

    def to_dict(self):
        return {"balance": self.balance, "history": [asdict(e) for e in self.history]}

    @classmethod
    def from_dict(cls, d):
        return cls(d["balance"], [Expense(**e) for e in d.get("history", [])])


def price_for(item: C.Item, day: int) -> int:
    return int(round(item.price * (1 + C.PRICE_INCREASE_PER_DAY * (day - 1))))


def cost_per_serving(item: C.Item, day: int) -> float:
    return price_for(item, day) / item.servings


@dataclass
class Inventory:
    stock: dict = field(default_factory=dict)

    def add(self, key: str, servings: float):
        self.stock[key] = round(self.stock.get(key, 0) + servings, 2)

    def has(self, key: str, servings: float = 1) -> bool:
        return self.stock.get(key, 0) + 1e-9 >= servings

    def use(self, key: str, servings: float = 1) -> bool:
        if not self.has(key, servings):
            return False
        self.stock[key] = round(self.stock[key] - servings, 2)
        if self.stock[key] <= 1e-9:
            del self.stock[key]
        return True

    def count(self, key: str) -> float:
        return self.stock.get(key, 0)

    def items(self, kinds=None):
        out = []
        for key, qty in self.stock.items():
            it = C.ITEMS_BY_KEY.get(key)
            if it and (kinds is None or it.kind in kinds):
                out.append((it, qty))
        return sorted(out, key=lambda t: C.ITEMS.index(t[0]))

    def owns(self, key: str) -> bool:
        return self.stock.get(key, 0) > 0

    def food_servings(self) -> float:
        return sum(q for it, q in self.items(("food",)))

    def to_dict(self):
        return dict(self.stock)

    @classmethod
    def from_dict(cls, d):
        return cls(dict(d))


def buy(item: C.Item, wallet: Wallet, inv: Inventory, day: int, minute: int) -> bool:
    cost = price_for(item, day)
    if not wallet.spend(cost, f"Bought {item.name}", day, minute):
        return False
    inv.add(item.key, item.servings)
    return True
