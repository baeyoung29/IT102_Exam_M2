import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, time as dtime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from petbalance import config as C, game_state as gs
from petbalance.pet import Pet
from petbalance.economy import Wallet, Inventory, price_for
from petbalance.schedule import Schedule


class PetTests(unittest.TestCase):
    def test_hunger_rises_over_time(self):
        p = Pet(hunger=10)
        p.tick(100)
        self.assertAlmostEqual(p.hunger, 10 + C.HUNGER_RATE * 100, places=3)

    def test_overfeeding_adds_weight(self):
        p = Pet(hunger=10)
        w = p.weight
        r = p.feed(C.ITEMS_BY_KEY["fish"], 1.5)
        self.assertEqual(r.verdict, "too_much")
        self.assertGreater(p.weight, w)
        self.assertEqual(p.hunger, 0)

    def test_underfeeding_verdict(self):
        p = Pet(hunger=70)
        self.assertEqual(p.preview_feed(C.ITEMS_BY_KEY["kibble"], 0.5).verdict, "too_little")

    def test_starving_drains_hp(self):
        p = Pet(hunger=C.HUNGER_CRITICAL + 5)
        p.tick(60)
        self.assertLess(p.hp, 100)

    def test_weight_status(self):
        self.assertEqual(Pet(weight=3.0).weight_status, "Underweight")
        self.assertEqual(Pet(weight=4.0).weight_status, "Healthy")
        self.assertEqual(Pet(weight=4.8).weight_status, "Overweight")
        self.assertEqual(Pet(weight=5.5).weight_status, "Obese")


class EconomyTests(unittest.TestCase):
    def test_cannot_overspend(self):
        w = Wallet(balance=50)
        self.assertFalse(w.spend(60, "x", 1, 0))
        self.assertEqual(w.balance, 50)

    def test_inventory_half_servings(self):
        inv = Inventory()
        inv.add("kibble", 1)
        self.assertTrue(inv.use("kibble", 0.5))
        self.assertTrue(inv.has("kibble", 0.5))
        self.assertFalse(inv.has("kibble", 1))

    def test_prices_rise(self):
        it = C.ITEMS_BY_KEY["kibble"]
        self.assertGreater(price_for(it, 5), price_for(it, 1))


class ScheduleTests(unittest.TestCase):
    def test_on_time_late_missed(self):
        s = Schedule()
        breakfast = s.meals[0].time
        s.update(breakfast + 5, 10)
        self.assertEqual(s.record_feeding(breakfast + 5)[1], "on_time")
        s.update(s.meals[1].time + C.ON_TIME_WINDOW + 10, 10)
        self.assertEqual(s.record_feeding(s.meals[1].time + C.ON_TIME_WINDOW + 10)[1], "late")
        events = s.update(s.meals[2].time + C.MISSED_AFTER + 1, 10)
        self.assertIn("missed", [e for e, _ in events])

    def test_reminder_fires_once(self):
        s = Schedule()
        t = s.meals[0].time - 5
        self.assertEqual([e for e, _ in s.update(t, 10)], ["reminder"])
        self.assertEqual(s.update(t + 1, 10), [])


START = datetime(2026, 10, 26, 6, 0)


class GameStateTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "save.json")
        gs.SAVE_PATH = self.path

    def play_day(self, g, portion="Regular"):
        t = g.clock
        end = t.replace(hour=22, minute=1)
        while t < end:
            t += timedelta(minutes=5)
            g.sync(t)
            if g.pet.fainted:
                g.vet_visit()
            m = g.schedule.current_meal(g.minute)
            if portion and m and m.status == "due" and g.minute >= m.time:
                if not g.inv.has("kibble", C.PORTIONS[portion]):
                    g.buy("kibble")
                g.feed("kibble", portion)

    def sleep_until_morning(self, g):
        g.sync(datetime.combine(g.clock.date() + timedelta(days=1), dtime(6, 0)))

    def test_careful_player_does_well(self):
        g = gs.GameState(now=START)
        for _ in range(3):
            self.play_day(g)
            self.assertTrue(g.day_over)
            self.assertEqual(g.summary["missed"], 0)
            self.assertGreaterEqual(g.summary["score"], 75)
            self.sleep_until_morning(g)
        self.assertEqual(g.day, 4)
        self.assertEqual(g.pet.weight_status, "Healthy")

    def test_neglect_is_punished(self):
        g = gs.GameState(now=START)
        self.play_day(g, portion=None)
        self.assertEqual(g.summary["missed"], 3)
        self.assertLess(g.summary["score"], 50)

    def test_midnight_starts_new_day_with_allowance(self):
        g = gs.GameState(now=START)
        money_before = g.wallet.balance
        g.sync(START.replace(hour=23, minute=59))
        self.assertEqual(g.day, 1)
        self.assertTrue(g.day_over)
        g.sync(START + timedelta(days=1, hours=-5, minutes=1))
        self.assertEqual(g.day, 2)
        self.assertFalse(g.day_over)
        self.assertEqual(g.wallet.balance, money_before + C.DAILY_ALLOWANCE)

    def test_sleeping_is_slower(self):
        awake, asleep = gs.GameState(now=START.replace(hour=10)), gs.GameState(now=START.replace(hour=22, minute=30))
        for g in (awake, asleep):
            g.pet.hunger, g.pet.happiness = 10, 80
            g.sync(g.clock + timedelta(hours=1))
        self.assertLess(asleep.pet.hunger, awake.pet.hunger)
        self.assertEqual(asleep.pet.happiness, 80)

    def test_late_start_skips_past_meals(self):
        g = gs.GameState(now=START.replace(hour=15))
        statuses = [m.status for m in g.schedule.meals]
        self.assertEqual(statuses, ["skipped", "skipped", "upcoming"])
        self.play_day(g)
        self.assertEqual(g.summary["missed"], 0)
        self.assertTrue(g.summary["goal_met"])

    def test_started_at_night_day_one_is_tomorrow(self):
        g = gs.GameState(now=START.replace(hour=23))
        self.assertTrue(g.day_over)
        self.sleep_until_morning(g)
        self.assertEqual(g.day, 1)
        self.assertEqual([m.status for m in g.schedule.meals], ["upcoming"] * 3)

    def test_time_passes_while_closed(self):
        g = gs.GameState(now=START)
        g.save(self.path)
        later = START + timedelta(days=2, hours=4)
        h = gs.GameState.load(path=self.path, now=later)
        h.sync(later, away=True)
        self.assertEqual(h.day, 3)
        r = h.away_report
        self.assertIsNotNone(r)
        self.assertEqual(r["days"], 2)
        self.assertGreaterEqual(len(r["missed"]), 6)
        self.assertFalse(h.pet.fainted)
        self.assertGreaterEqual(h.pet.hp, C.OFFLINE_HP_FLOOR)
        self.assertEqual(h.notifier.drain_toasts(), [])

    def test_save_and_load_roundtrip(self):
        g = gs.GameState(now=START)
        g.buy("fish")
        g.sync(START + timedelta(minutes=30))
        g.save(self.path)
        h = gs.GameState.load(path=self.path, now=g.clock)
        self.assertEqual(h.wallet.balance, g.wallet.balance)
        self.assertEqual(h.inv.stock, g.inv.stock)
        self.assertAlmostEqual(h.minute, g.minute)
        self.assertAlmostEqual(h.pet.hunger, g.pet.hunger)
        self.assertEqual(h.clock, g.clock)


if __name__ == "__main__":
    unittest.main()
