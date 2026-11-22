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
        self.cube_radius = hello["config"].get("cubes", {}).get("pickup_radius", 3.5)
        self.goal = None
        self.plan_at = 0
        self.mode = "circle"
        self.sprinting = False
        self.seen_cubes = {}
        self.drop_wait = {}
        self.drop_retry = {}

    def available_cubes(self, obs):
        now = obs["t"]
        pos = obs["self"]["pos"]
        visible = {cube["id"]: cube for cube in obs.get("cubes", [])}
        for cube_id, (cube, last_seen) in list(self.seen_cubes.items()):
            if now - last_seen > 16 or (cube_id not in visible and
                                         math.dist(pos[:2], cube["pos"][:2]) <= 9):
                del self.seen_cubes[cube_id]
        self.seen_cubes.update((key, (item, now)) for key, item in visible.items())
        return [cube for cube, _ in self.seen_cubes.values()]

    def supply_goal(self, obs):
        me, zone = obs["self"], obs["zone"]
        pos, center, radius = me["pos"][:2], zone["next_center"], zone["next_radius"]
        options = []
        for drop in obs.get("drops", []):
            drop_id = drop["id"]
            if drop["holder"] not in (None, me["id"]) or self.drop_retry.get(drop_id, 0) > obs["t"]:
                self.drop_wait.pop(drop_id, None)
                continue
            point = drop["pos"][:2]
            if math.dist(point, center) > radius:
                continue
            distance = math.dist(pos, point)
            inside = distance < drop["radius"]
            progress = drop.get("progress", 0)
            if inside and drop["lands_in"] == 0 and "progress" in drop:
                previous, since = self.drop_wait.get(drop_id, (progress, obs["t"]))
                if progress != previous:
                    since = obs["t"]
                self.drop_wait[drop_id] = (progress, since)
                if obs["t"] - since > 3:
                    self.drop_retry[drop_id] = obs["t"] + 12
                    continue
            else:
                self.drop_wait.pop(drop_id, None)
            arrival = 1.25 * max(0, distance - drop["radius"]) / max(1, me["stats"]["walk_speed"])
            finish = max(arrival, drop["lands_in"]) + drop.get("capture_s", 4) - progress
            if finish <= 37:
                options.append((finish, drop["id"], point, drop["radius"]))
        if options:
            _, _, point, capture_radius = min(options)
            return point, capture_radius * 0.55

    def roam(self, obs, hops, others):
        me, zone = obs["self"], obs["zone"]
        x, y = me["pos"][:2]
        cx, cy = zone["next_center"]
        radius = zone["next_radius"]
        angle = math.atan2(y - cy, x - cx)
        if math.hypot(x - cx, y - cy) < self.grid.step:
            angle = me["id"] * math.tau / 16
        direction = 1 if me["id"] % 2 else -1
        tangent = (-math.sin(angle) * direction, math.cos(angle) * direction)
        preferred_radius = radius * 0.67
        best_value = -math.inf
        best = None
        for cell, depth in hops.items():
            px, py = self.grid.positions[cell]
            ring_distance = math.hypot(px - cx, py - cy)
            if depth < 2 or ring_distance > max(0, radius - min(6, radius * 0.15)):
                continue
            arc_progress = (px - x) * tangent[0] + (py - y) * tangent[1]
            crowd = sum(max(0, 100 - math.hypot(px - ox, py - oy)) for ox, oy in others)
            value = (0.75 * arc_progress - abs(ring_distance - preferred_radius)
                     - 1.5 * crowd - 0.16 * depth * self.grid.step)
            if value > best_value:
                best, best_value = (px, py), value
        return best

    def destination(self, obs):
        me, zone = obs["self"], obs["zone"]
        pos = me["pos"][:2]
        center = zone["next_center"]
        radius = zone["next_radius"]
        actors = [a["pos"][:2] for a in obs["mechs"] if a["kind"] == "mech"]
        nearest = min((math.dist(pos, point) for point in actors), default=math.inf)
        self.crate = None
        # Do not linger for loot while losing HP to the zone. A future circle
        # outside our current position may still leave a full minute to collect.
        walk = max(1, me["stats"]["walk_speed"])
        excess = max(0, math.dist(pos, center) - radius)
        slack = zone.get("shrink_end", obs["t"]) - obs["t"] - 1.5 * excess / walk
        if not me["in_zone"] or radius <= 12 or (excess > 0 and slack < 8):
            self.mode = "circle"
            return center, min(2.0, radius * 0.1)

        # Respect actual capture progress and the uninterrupted timer.
        supply = self.supply_goal(obs)
        if supply is not None:
            self.mode = "drop"
            return supply

        cubes = self.available_cubes(obs)
        if cubes or nearest > 50:
            options = []
            candidates = [(item, "cube") for item in cubes]
            if nearest > 50 and me["weapons"][1] is None:
                candidates += [(item, "pickup") for item in obs["pickups"] if item["kind"] != "gun"]
            if nearest > 100 and me["hp"] >= 0.8 * me.get("max_hp", me["hp"]):
                candidates += [(item, "crate") for item in obs.get("crates", [])]
            for item, kind in candidates:
                point = item["pos"][:2]
                distance = math.dist(pos, point)
                limit = (100 if nearest > 50 else 12) if kind == "cube" else 60
                if abs(item["pos"][2] - me["pos"][2]) > 4 or distance > limit:
                    continue
                if math.dist(point, center) > radius and (slack < 16 or
                        math.dist(point, zone.get("center", center)) + 8 > zone.get("radius", radius)):
                    continue
                value = {"cube": 0, "pickup": 5, "crate": 16}[kind] + distance
                if kind == "pickup" and item["kind"] == "lightning":
                    value -= 4
                options.append((value, item["id"], kind, point, item))
            if options:
                for _, _, kind, point, item in sorted(options):
                    cell = self.grid.cell(point)
                    start = self.grid.snap[self.grid.cell(pos)]
                    if math.dist(pos, point) > 12 and (
                            self.grid.snap[cell] != cell or self.grid.component[cell] != self.grid.component[start]):
                        continue
                    self.mode = kind
                    if kind == "crate":
                        self.crate = item
                    stop = {"cube": self.cube_radius * 0.55, "pickup": self.reach * 0.55, "crate": 8.0}[kind]
                    return point, stop

        if excess > 0:
            self.mode = "circle"
            return center, 2
        crowd = nearest < 65
        key = (tuple(center), radius, crowd)
        if (self.mode != "roam" or self.goal is None or key != self.roam_key
                or obs["t"] >= self.plan_at or math.dist(pos, self.goal) < 5):
            hops = self.grid.local_distances(pos, 12)
            self.goal = self.roam(obs, hops, actors)
            self.roam_key = key
            self.plan_at = obs["t"] + (1.6 if crowd else 3.5)
        self.mode = "roam"
        return (self.goal, 1.0) if self.goal else (center, 1.0)

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
        zone_goal = self.mode == "circle"
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
        moving = move != [0.0, 0.0]
        if me["grounded"] and moving and self.mode in ("roam", "circle"):
            energy = me["energy"] / max(1, me.get("max_energy", 100))
            self.sprinting = energy > (0.36 if self.sprinting else 0.82)
            boost = boost or self.sprinting
        action.update(move=move, boost=boost, jump=jump)

        if obs["offer"]:
            order = ("nanites", "plating", "armor", "servos", "jets", "reactor", "capacitor")
            choices = obs["offer"]["choices"]
            action["pick"] = min(range(len(choices)), key=lambda i:
                                 order.index(choices[i]["id"]) if choices[i]["id"] in order else len(order))
        if self.mode == "crate" and self.crate is not None:
            # A crate is a stationary game collectible. Opening it releases a
            # cube, which in turn can unlock a health or movement upgrade.
            bx, by, bz = self.crate["pos"]
            dx, dy = bx - pos[0], by - pos[1]
            action["aim"] = [math.atan2(dy, dx), math.atan2(bz + 1 - me["pos"][2] -
                             me["stats"].get("muzzle_height", 7), math.hypot(dx, dy))]
            action["fire"] = [True, False]
        elif not any(a["kind"] == "mech" for a in obs["mechs"]) and moving:
            action["aim"] = [math.atan2(move[1], move[0]), 0.0]
        if (self.mode == "roam" and me["hp"] < 0.65 * me.get("max_hp", me["hp"])
                and all(math.dist(pos, actor["pos"][:2]) > 50 for actor in obs["mechs"])):
            # Dealing any damage restarts the game's passive-healing clock.
            action["fire"] = [False, False]
        if action.get("take") is not None:
            if not any(p["id"] == action["take"] and abs(p["pos"][2] - me["pos"][2]) <= 4
                       for p in obs["pickups"]):
                action.pop("take")
        if self.mode == "pickup" and math.dist(pos, goal) <= self.reach:
            eligible = [p for p in obs["pickups"] if p["pos"][:2] == goal and
                        abs(p["pos"][2] - me["pos"][2]) <= 4 and p["kind"] != "gun"]
            if eligible:
                action["take"] = eligible[0]["id"]
        mf.draw.clear()
        mf.draw.point([*goal, me["pos"][2]], "#40c0ff", 5)
        mf.draw.point([*waypoint, me["pos"][2]], "#f0b840", 3)
        mf.draw.label(self.mode)
        return action


if __name__ == "__main__":
    mf.run(Bot)
