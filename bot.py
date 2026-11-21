import math

import mechfight as mf
from navigation import GroundGrid
from starter import Bot as StarterBot


class Bot(StarterBot):
    name = "Oval Hopper"

    def __init__(self, hello):
        super().__init__(hello)
        self.grid = GroundGrid.load(hello["map"]["dir"], hello["config"]["mech"])
        self.anchor = None
        self.check_at = 0
        self.recover_until = 0
        self.side = 1

    def destination(self, obs):
        me, zone = obs["self"], obs["zone"]
        pos = me["pos"][:2]
        center = zone["next_center"]
        options = []
        if me["in_zone"]:
            for drop in obs.get("drops", []):
                point = drop["pos"][:2]
                if drop["holder"] not in (None, me["id"]):
                    continue
                if math.dist(point, center) + drop["radius"] > zone["next_radius"]:
                    continue
                distance = math.dist(pos, point)
                travel = distance / max(1, me["stats"]["walk_speed"])
                if distance <= 150 and drop["lands_in"] <= travel + 4:
                    options.append((distance, drop["id"], point, drop["radius"] * 0.55))
        if options:
            _, _, point, stop_radius = min(options)
            return point, stop_radius
        return center, min(2.0, zone["next_radius"] * 0.1)

    def act(self, obs):
        action = super().act(obs)
        goal, stop_radius = self.destination(obs)
        me, now = obs["self"], obs["t"]
        pos = me["pos"][:2]
        waypoint = self.grid.waypoint(pos, goal)
        dx, dy = waypoint[0] - pos[0], waypoint[1] - pos[1]
        distance = math.hypot(dx, dy)
        move = [0.0, 0.0]
        boost = jump = False
        # A final zone can collapse onto an occupied tile. Cross the last
        # grid margin with the game's jump/jet if the walk ends outside it.
        current = self.grid.cell(pos)
        needs_zone = (not me["in_zone"] or
                      math.dist(pos, obs["zone"]["next_center"]) > obs["zone"]["next_radius"])
        zone_goal = goal == obs["zone"]["next_center"]
        climb = (zone_goal and needs_zone and math.dist(pos, goal) > stop_radius
                 and ((self.grid.cell(goal) != current and self.grid.cell(waypoint) == current)
                      or self.grid.snap[current] != current))
        if climb:
            dx, dy = goal[0] - pos[0], goal[1] - pos[1]
            distance = math.hypot(dx, dy)
        if distance > 0.6 and math.dist(pos, goal) > stop_radius:
            move = [dx / distance, dy / distance]
            if self.anchor is None:
                self.anchor, self.check_at = pos, now + 1.0
            elif now >= self.check_at:
                if math.dist(pos, self.anchor) < 1.5:
                    self.recover_until = now + 0.65
                    self.side = -self.side
                self.anchor, self.check_at = pos, now + 1.0
            recovering = now < self.recover_until
            if recovering and not climb:
                x, y = move
                move = [0.6 * x - self.side * 0.8 * y, 0.6 * y + self.side * 0.8 * x]
            jump = (recovering or climb) and me["grounded"]
            boost = ((recovering or climb) and not me["grounded"] or
                     not me["in_zone"] and me["grounded"]) and me["energy"] > 5
        else:
            self.anchor = None
            self.recover_until = 0
        action.update(move=move, boost=boost, jump=jump)
        mf.draw.clear()
        mf.draw.point([*goal, me["pos"][2]], "#40c0ff", 5)
        mf.draw.point([*waypoint, me["pos"][2]], "#f0b840", 3)
        mf.draw.label("next circle" if zone_goal else "supply drop")
        return action


if __name__ == "__main__":
    mf.run(Bot)
