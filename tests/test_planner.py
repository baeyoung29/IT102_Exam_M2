import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from petbalance import config as C, game_state as gs
from petbalance.planner import Planner

MORNING = datetime(2026, 10, 28, 7, 0)
WED = MORNING.weekday()


def at(h, m=0, day=MORNING):
    return day.replace(hour=h, minute=m)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "classes.json")
        self.p = Planner(self.path)
        self.p.last_check = MORNING
        self.c, _ = self.p.add("IT102", [WED], 9 * 60, 10 * 60 + 30, "Room 301", now=MORNING)

    def test_validation(self):
        self.assertIsNone(self.p.add("", [WED], 60, 120, now=MORNING)[0])
        self.assertIsNone(self.p.add("Math", [], 60, 120, now=MORNING)[0])
        self.assertIsNone(self.p.add("Math", [WED], 120, 60, now=MORNING)[0])

    def test_reminder_then_start_popup(self):
        self.assertEqual(self.p.update(at(8, 40)), [])
        ev = self.p.update(at(8, 51))
        self.assertEqual([e[0] for e in ev], ["reminder"])
        self.assertEqual(self.p.update(at(8, 55)), [])
        ev = self.p.update(at(9, 0))
        self.assertEqual([e[0] for e in ev], ["start"])
        self.assertEqual(self.p.update(at(9, 5)), [])

    def test_check_in_pays_coins_once(self):
        ok, _, coins = self.p.check_in(self.c.id, at(9, 3))
        self.assertTrue(ok)
        self.assertEqual(coins, C.CLASS_BASE_COINS + C.CLASS_COINS_PER_HOUR * 1)
        self.assertEqual(self.p.coins, coins)
        self.assertFalse(self.p.check_in(self.c.id, at(9, 10))[0])
        self.assertEqual(self.p.coins, coins)

    def test_check_in_window(self):
        self.assertFalse(self.p.check_in(self.c.id, at(8, 30))[0])
        self.assertTrue(self.p.check_in(self.c.id, at(8, 52))[0])

    def test_cannot_check_in_after_class(self):
        self.assertFalse(self.p.check_in(self.c.id, at(10, 31))[0])

    def test_missed_resets_streak(self):
        self.p.streak = 4
        ev = self.p.update(at(10, 31))
        self.assertIn("missed", [e[0] for e in ev])
        self.assertEqual(self.p.streak, 0)
        self.assertEqual(self.p.status(self.c, MORNING.date(), at(11)), "missed")

    def test_streak_bonus(self):
        base = self.p.reward_for(self.c)
        self.p.streak = 3
        self.assertEqual(self.p.reward_for(self.c), base + 3 * C.STREAK_BONUS_PER_CLASS)
        self.p.streak = 50
        self.assertEqual(self.p.reward_for(self.c), base + C.STREAK_BONUS_CAP)

    def test_class_added_after_it_ended_is_not_missed(self):
        late = Planner(os.path.join(tempfile.mkdtemp(), "c.json"))
        late.last_check = at(12)
        c, _ = late.add("Early", [WED], 8 * 60, 9 * 60, now=at(12))
        self.assertEqual(late.update(at(12, 1)), [])
        self.assertEqual(late.status(c, MORNING.date(), at(12, 1)), "untracked")

    def test_days_closed_are_caught_up(self):
        next_week = at(8, 0, MORNING + timedelta(days=7))
        ev = self.p.update(next_week)
        self.assertEqual([e[0] for e in ev], ["missed"])

    def test_save_and_load(self):
        self.p.check_in(self.c.id, at(9, 1))
        q = Planner.load(self.path)
        self.assertEqual(q.coins, self.p.coins)
        self.assertEqual(len(q.classes), 1)
        self.assertEqual(q.status(q.classes[0], MORNING.date(), at(9, 30)), "attended")

    def test_spend(self):
        self.p.coins = 10
        self.assertFalse(self.p.spend(11, "x"))
        self.assertTrue(self.p.spend(10, "x"))
        self.assertEqual(self.p.coins, 0)


class CoinShopTests(unittest.TestCase):
    def setUp(self):
        gs.SAVE_PATH = os.path.join(tempfile.mkdtemp(), "save.json")
        self.g = gs.GameState()
        self.g.planner = Planner(os.path.join(tempfile.mkdtemp(), "classes.json"))

    def test_buy_with_coins(self):
        self.g.planner.coins = 100
        ok, _ = self.g.buy_with_coins("fish")
        self.assertTrue(ok)
        self.assertEqual(self.g.planner.coins, 100 - C.ITEMS_BY_KEY["fish"].coin_price)
        self.assertTrue(self.g.inv.has("fish"))

    def test_not_enough_coins(self):
        self.g.planner.coins = 5
        self.assertFalse(self.g.buy_with_coins("catbed")[0])
        self.assertEqual(self.g.planner.coins, 5)

    def test_decor_bought_once_and_not_for_pesos(self):
        self.g.planner.coins = 500
        self.assertFalse(self.g.buy("catbed")[0])
        self.assertTrue(self.g.buy_with_coins("catbed")[0])
        self.assertFalse(self.g.buy_with_coins("catbed")[0])

    def test_cat_bed_slows_sadness(self):
        noon = datetime(2026, 10, 28, 9, 0)
        a = gs.GameState(now=noon)
        b = gs.GameState(now=noon)
        b.inv.add("catbed", 1)
        for g in (a, b):
            g.pet.hunger = 0
            g.sync(noon + timedelta(hours=1))
        self.assertGreater(b.pet.happiness, a.pet.happiness)


if __name__ == "__main__":
    unittest.main()
