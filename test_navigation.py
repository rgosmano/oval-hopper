"""Small game scenarios whose observations change in response to the bot."""

import math
import unittest
from unittest.mock import patch

from bot import Bot
from navigation import GroundGrid
from starter import Bot as StarterBot


BOUNDS = dict(minX=0, minY=0, maxX=100, maxY=100)
STATS = dict(radius=2.5, height=9, step_up=1.2, max_slope_deg=50, walk_speed=11.7)
WALL = dict(ring=[42, 25, 54, 25, 54, 75, 42, 75], holes=[], base=0, top=20)
HELLO = {"config": {"loot": {"pickup_radius": 4}, "mech": STATS}, "map": {"dir": "."}}


def arena(prisms):
    return GroundGrid(BOUNDS, prisms, lambda x, y: 0, STATS)


def player(grid):
    with patch.object(GroundGrid, "load", return_value=grid):
        return Bot(HELLO)


def observation(pos, goal):
    return dict(tick=0, t=0, offer=None, mechs=[], pickups=[], drops=[],
                self=dict(id=1, pos=[*pos, 0], in_zone=True, grounded=True,
                          energy=100, stats=STATS, hp=1400, weapons=[{}, None]),
                zone=dict(next_center=goal, next_radius=40))


def walk(controller):
    # A flat toy arena with one solid rectangle and no opponents or physics.
    goal = (87.5, 52.5)
    obs = observation((12.5, 52.5), goal)
    obs["zone"]["next_radius"] = 0
    for tick in range(240):
        obs.update(t=tick / 10, tick=tick * 2)
        action = controller.act(obs)
        x, y, _ = obs["self"]["pos"]
        dx, dy = action["move"]
        x, y = x + 1.17 * dx, y + 1.17 * dy
        if not (39.5 < x < 56.5 and 22.5 < y < 77.5):
            obs["self"]["pos"] = [x, y, 0]
        if math.dist(goal, obs["self"]["pos"][:2]) <= 2:
            return True
    return False


class NavigationTests(unittest.TestCase):
    def test_detour_beats_straight_line_in_blocked_corridor(self):
        self.assertFalse(walk(StarterBot(HELLO)))
        self.assertTrue(walk(player(arena([WALL]))))

    def test_bridge_with_headroom_is_walkable(self):
        grid = arena([{**WALL, "base": 12}])
        cell = grid.cell((48, 50))
        self.assertEqual(grid.snap[cell], cell)

    def test_enclosed_goal_routes_to_accessible_boundary(self):
        building = dict(ring=[20, 20, 80, 20, 80, 80, 20, 80],
                        holes=[[35, 35, 65, 35, 65, 65, 35, 65]], base=0, top=20)
        grid = arena([building])
        pos = (2.5, 52.5)
        for _ in range(50):
            point = grid.waypoint(pos, (52.5, 52.5))
            if point == pos:
                break
            pos = point
        start_cell = grid.cell((2.5, 52.5))
        self.assertEqual(grid.component[grid.cell(pos)], grid.component[start_cell])
        nearest = min(math.dist(grid.positions[i], (52.5, 52.5))
                      for i in grid.members[grid.component[start_cell]])
        self.assertAlmostEqual(math.dist(pos, (52.5, 52.5)), nearest)
        self.assertEqual(grid.waypoint(pos, (52.5, 52.5)), pos)

    def test_drop_holds_and_releases(self):
        bot = player(arena([]))
        obs = observation((32, 45), [70, 45])
        drop = dict(id=20000, pos=[33, 45, 0], radius=8, holder=1, lands_in=0)
        obs["zone"]["next_radius"] = 60
        obs["drops"] = [drop]
        for tick in range(50):
            obs.update(t=tick / 10, tick=tick * 2)
            self.assertEqual(bot.act(obs)["move"], [0, 0])
        drop["holder"] = 2
        self.assertGreater(math.hypot(*bot.act(obs)["move"]), 0.9)
        drop["holder"] = None
        obs["zone"]["next_radius"] = 10
        self.assertEqual(bot.destination(obs)[0], [70, 45])

    def test_stall_uses_jump_and_then_jet(self):
        bot = player(arena([]))
        obs = observation((12.5, 52.5), [90, 50])
        self.assertFalse(bot.act(obs)["jump"])
        obs["t"] = 1.1
        self.assertTrue(bot.act(obs)["jump"])
        obs["self"]["grounded"] = False
        obs["t"] = 1.2
        self.assertTrue(bot.act(obs)["boost"])


if __name__ == "__main__":
    unittest.main()
