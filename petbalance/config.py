from dataclasses import dataclass, field

SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
TITLE = "PetBalance"

DAY_START = 6 * 60
DAY_END = 22 * 60
SLEEP_HUNGER_MULT = 0.4
OFFLINE_HP_FLOOR = 10
OFFLINE_MAX_DAYS = 7
AWAY_REPORT_MIN = 10
AUTOSAVE_SECONDS = 60

CURRENCY_SYMBOL = "₱"
STARTING_MONEY = 500
DAILY_ALLOWANCE = 90
LOW_BUDGET_THRESHOLD = 100
PRICE_INCREASE_PER_DAY = 0.05
VET_COST = 250

PET_NAME = "Mochi"

HUNGER_RATE = 0.09
HUNGER_WARNING = 55
HUNGER_CRITICAL = 75

HAPPINESS_DECAY = 0.035
HAPPINESS_HUNGRY_DECAY = 0.06

HP_DRAIN_STARVING = 0.10
HP_DRAIN_BAD_WEIGHT = 0.02
HP_DRAIN_SAD = 0.01
HP_REGEN = 0.04

START_WEIGHT = 4.1
HEALTHY_MIN = 3.6
HEALTHY_MAX = 4.6
OBESE_AT = 5.2
WEIGHT_PER_OVERFLOW_POINT = 0.004
WEIGHT_LOSS_WHEN_HUNGRY = 0.0006
WEIGHT_MIN = 2.5
WEIGHT_MAX = 7.0

PET_COOLDOWN = 30
PLAY_COOLDOWN = 45

@dataclass
class MealSlot:
    name: str
    time: int


MEAL_SCHEDULE = [
    MealSlot("Breakfast", 8 * 60),
    MealSlot("Lunch", 12 * 60 + 30),
    MealSlot("Dinner", 18 * 60 + 30),
]
EARLY_WINDOW = 30
ON_TIME_WINDOW = 45
MISSED_AFTER = 120
DEFAULT_REMINDER_LEAD = 10

PORTIONS = {
    "Small": 0.5,
    "Regular": 1.0,
    "Large": 1.5,
}


@dataclass
class Item:
    key: str
    name: str
    price: int
    servings: float
    kind: str
    desc: str
    satiety: float = 0
    happiness: float = 0
    hp: float = 0
    weight: float = 0
    color: tuple = (200, 200, 200)
    tags: list = field(default_factory=list)
    coin_price: int = 0
    coin_only: bool = False


ITEMS = [
    Item("kibble", "Dry Kibble", 120, 5, "food",
         "Budget-friendly bag. 5 servings. Balanced, no extras.",
         satiety=34, happiness=1, color=(214, 160, 92), coin_price=30),
    Item("wetfood", "Wet Food Can", 45, 1, "food",
         "Tasty single can. Pets love it.",
         satiety=36, happiness=5, color=(196, 108, 84), coin_price=12),
    Item("fish", "Fresh Fish", 70, 1, "food",
         "Filling and healthy. Restores a little HP.",
         satiety=44, happiness=6, hp=3, color=(110, 160, 200), coin_price=18),
    Item("premium", "Premium Mix", 180, 3, "food",
         "Vet-formula mix. 3 servings. Great for recovery.",
         satiety=38, happiness=4, hp=5, color=(150, 120, 190), coin_price=45),
    Item("treats", "Cat Treats", 60, 6, "treat",
         "6 treats. Big smiles, tiny meal, adds weight.",
         satiety=6, happiness=8, weight=0.03, color=(236, 130, 160), coin_price=15),
    Item("vitamins", "Vitamins", 90, 3, "supply",
         "3 doses. +15 HP each. Max one per day.",
         hp=15, color=(120, 190, 120), coin_price=25),
    Item("toy", "Toy Mouse", 80, 10, "supply",
         "Unlocks Play. 10 play sessions.",
         color=(160, 160, 170), coin_price=20),
    Item("goldfish", "Golden Fish", 0, 1, "food",
         "A rare feast. Very filling, big happiness and +10 HP.",
         satiety=44, happiness=14, hp=10, color=(240, 190, 70), coin_price=25, coin_only=True),
    Item("catbed", "Cozy Cat Bed", 0, 1, "decor",
         "Placed in the room. Happiness drops 25% slower.",
         color=(150, 120, 190), coin_price=120, coin_only=True),
    Item("plant", "Potted Plant", 0, 1, "decor",
         "A leafy friend for the corner. Purely cozy.",
         color=(104, 176, 120), coin_price=60, coin_only=True),
    Item("lights", "Fairy Lights", 0, 1, "decor",
         "Twinkly string lights across the wall.",
         color=(240, 196, 72), coin_price=90, coin_only=True),
]
ITEMS_BY_KEY = {i.key: i for i in ITEMS}
CATBED_HAPPINESS_SAVE = 0.25

COIN_NAME = "Study Coins"
CHECKIN_EARLY = 10
DEFAULT_CLASS_REMINDER = 10
CLASS_BASE_COINS = 5
CLASS_COINS_PER_HOUR = 3
STREAK_BONUS_PER_CLASS = 1
STREAK_BONUS_CAP = 5
MAX_CLASSES = 20
CATCH_UP_DAYS = 14
CLASS_COLORS = [(232, 136, 98), (108, 152, 210), (104, 176, 120), (150, 120, 190),
                (236, 130, 160), (236, 176, 74), (90, 170, 170)]

STARTING_INVENTORY = {"kibble": 2}

NOTIFY_COOLDOWN = {
    "hungry": 60,
    "starving": 45,
    "hp_low": 60,
    "weight": 180,
    "budget": 240,
    "happy_low": 120,
}
TOAST_SECONDS = 4.0

C_BG = (250, 243, 232)
C_ROOM_WALL = (246, 226, 205)
C_ROOM_FLOOR = (222, 190, 158)
C_PANEL = (255, 251, 245)
C_PANEL_EDGE = (226, 206, 184)
C_TEXT = (74, 56, 46)
C_TEXT_DIM = (140, 120, 104)
C_ACCENT = (232, 136, 98)
C_ACCENT_DARK = (198, 104, 70)
C_GOOD = (104, 176, 120)
C_WARN = (236, 176, 74)
C_BAD = (222, 96, 96)
C_INFO = (108, 152, 210)
C_HP = (230, 104, 112)
C_HUNGER = (236, 160, 76)
C_HAPPY = (240, 196, 72)
C_WEIGHT = (120, 168, 200)
C_SHADOW = (0, 0, 0, 40)
