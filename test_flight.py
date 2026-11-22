import unittest
from math import hypot

from flight import Bot


class FlightTests(unittest.TestCase):
    def setUp(self):
        self.bot = Bot({"slot": 3})
        self.me = dict(pos=[90, 0, 0], vel=[0, 0, 0], grounded=True, id=3,
                       energy=100, max_energy=100)
        self.obs = dict(tick=0, self=self.me, zone=dict(next_center=[0, 0], next_radius=50))

    def test_flight_cycle(self):
        self.assertTrue(self.bot.act(self.obs)["jump"])
        self.me.update(grounded=False, energy=70)
        self.assertTrue(self.bot.act(self.obs)["boost"])
        self.me["energy"] = 9
        self.assertFalse(self.bot.act(self.obs)["boost"])
        self.me.update(grounded=True, energy=40)
        self.assertFalse(self.bot.act(self.obs)["jump"])

    def test_ring_and_final_point(self):
        move = self.bot.act(self.obs)["move"]
        self.assertLess(move[0], 0)
        self.assertAlmostEqual(hypot(*move), 1)
        self.obs["zone"]["next_radius"] = 0
        self.me.update(pos=[0, 0, 0], vel=[2, 0, 0])
        self.assertLess(self.bot.act(self.obs)["move"][0], 0)
