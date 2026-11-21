"""Reactive game-mechanic tests. Run as a script for the paired comparison."""

import math
import random
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import Bot
from navigation import GroundGrid
from test_navigation import HELLO, STATS, observation


def trial(controller, grid, seed, crowded):
    """Forty simulated seconds in a flat arena. Each move updates the next observation."""
    rng = random.Random(seed)
    spawn = [rng.uniform(-40, 40), rng.uniform(-40, 40)]
    obs = observation(spawn, [0, 0])
    obs["zone"].update(radius=175, center=[0, 0], next_radius=120, shrink_end=70)
    items = [dict(id=5000 + i, pos=[rng.uniform(-45, 45), rng.uniform(-45, 45), 0])
             for i in range(8)]
    # One slow tagger measures crowding without inventing a combat or placement model.
    tagger = [spawn[0] + 30, spawn[1]]
    with patch.object(GroundGrid, "load", return_value=grid):
        bot = controller(HELLO)
    me = obs["self"]
    me.update(max_energy=100, max_hp=1400, cubes=0)
    close_ticks = 0
    near_zone = 0
    last_boost = -100
    for tick in range(400):
        obs.update(t=tick / 10, tick=tick * 2)
        pos = me["pos"]
        obs["cubes"] = [item for item in items if math.dist(pos, item["pos"]) < 65]
        if crowded:
            obs["mechs"] = [dict(kind="mech", pos=[*tagger, 0])]
        action = bot.act(obs)
        speed = 19.5 if action["boost"] and me["energy"] > 0 else STATS["walk_speed"]
        if speed == 19.5:
            last_boost = tick
            me["energy"] = max(0, me["energy"] - 1.7)
        elif tick - last_boost > 6:
            me["energy"] = min(100, me["energy"] + 1.8)
        for axis in range(2):
            pos[axis] += speed * action["move"][axis] / 10
        distance = math.dist(tagger, pos[:2])
        if crowded and distance:
            for axis in range(2):
                tagger[axis] += min(0.8, distance) * (pos[axis] - tagger[axis]) / distance
        close_ticks += int(crowded and distance < 25)
        near_zone += int(math.hypot(*pos[:2]) <= obs["zone"]["next_radius"])
        remaining = [item for item in items if math.dist(pos, item["pos"]) > 3.5]
        me["cubes"] += len(items) - len(remaining)
        items = remaining
    return me["cubes"], close_ticks / 10, near_zone / 10


def test_grid():
    return GroundGrid(dict(minX=-175, minY=-175, maxX=175, maxY=175), [], lambda x, y: 0, STATS)


class PolicyTests(unittest.TestCase):
    def test_wide_circle_mobility(self):
        _, crowded_seconds, inside_seconds = trial(Bot, test_grid(), 7, True)
        self.assertLess(crowded_seconds, 10)
        self.assertEqual(inside_seconds, 40)

    def test_collects_loose_cubes(self):
        cubes, _, _ = trial(Bot, test_grid(), 7, False)
        self.assertGreaterEqual(cubes, 3)

    def test_vertical_loot_and_offer_priority(self):
        with patch.object(GroundGrid, "load", return_value=test_grid()):
            bot = Bot(HELLO)
        obs = observation([0, 0], [0, 0])
        obs.update(pickups=[dict(id=8000, pos=[1, 0, 25], kind="lightning")],
                   offer=dict(choices=[dict(id="sensors"), dict(id="armor"), dict(id="nanites")]))
        action = bot.act(obs)
        self.assertNotIn("take", action)
        self.assertEqual(action["pick"], 2)

    def test_healing_avoids_resetting_timer(self):
        with patch.object(GroundGrid, "load", return_value=test_grid()):
            bot = Bot(HELLO)
        obs = observation([0, 0], [0, 0])
        obs["self"].update(hp=400, max_hp=1400)
        obs["mechs"] = [dict(kind="mech", pos=[85, 0, 0])]
        self.assertEqual(bot.act(obs)["fire"], [False, False])


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    code = subprocess.check_output(["git", "show", "d8e123a:bot.py"], cwd=folder)
    baseline = {"__name__": "submitted_v1"}
    exec(compile(code, "submitted_v1.py", "exec"), baseline)
    grid = test_grid()
    for name, controller in (("submitted v1", baseline["Bot"]), ("candidate", Bot)):
        quiet = [trial(controller, grid, seed, False) for seed in range(12)]
        crowded = [trial(controller, grid, seed, True) for seed in range(12)]
        print(f"{name}: {sum(r[0] for r in quiet)}/96 cubes collected; "
              f"{sum(r[1] for r in crowded) / 12:.1f}/40 s near tagger; "
              f"{sum(r[2] for r in crowded) / 12:.1f}/40 s inside next circle")
