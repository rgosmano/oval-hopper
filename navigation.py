"""Ground navigation for the mechfight tile map. All geometry is read at hello."""

import json
import math
import sys
from array import array
from collections import deque
from pathlib import Path


class GroundGrid:
    step = 5.0

    @classmethod
    def load(cls, directory, stats):
        folder = Path(directory) / "v2"
        world = json.loads((folder / "world.json").read_bytes())
        terrain = world["terrain"]
        heights = array("h")
        heights.frombytes((folder / terrain["file"]).read_bytes())
        if sys.byteorder != "little":
            heights.byteswap()

        def height(x, y):
            fx = min(terrain["nx"] - 1, max(0, (x - terrain["minX"]) / terrain["step"]))
            fy = min(terrain["ny"] - 1, max(0, (y - terrain["minY"]) / terrain["step"]))
            col, row = int(fx), int(fy)
            right = min(col + 1, terrain["nx"] - 1)
            above = min(row + 1, terrain["ny"] - 1) * terrain["nx"]
            row *= terrain["nx"]
            tx, ty = fx - col, fy - int(fy)
            return terrain["scale"] * (
                (1 - ty) * ((1 - tx) * heights[row + col] + tx * heights[row + right])
                + ty * ((1 - tx) * heights[above + col] + tx * heights[above + right])
            )

        return cls(world["bounds"], world["prisms"], height, stats)

    def __init__(self, bounds, prisms, height, stats):
        radius = stats["radius"]
        self.x0 = bounds["minX"] + radius
        self.y0 = bounds["minY"] + radius
        self.width = 1 + int((bounds["maxX"] - radius - self.x0) / self.step)
        self.rows = 1 + int((bounds["maxY"] - radius - self.y0) / self.step)
        count = self.width * self.rows
        self.positions = [(self.x0 + (i % self.width) * self.step,
                           self.y0 + (i // self.width) * self.step) for i in range(count)]
        levels = [height(x, y) for x, y in self.positions]
        self.ground_heights = levels
        blocked = bytearray(count)
        # The extra half cell keeps a grid edge from stepping across a thin wall.
        margin = radius + self.step / 2
        for prism in prisms:
            rings = [prism["ring"], *prism.get("holes", [])]
            edges = []
            for ring in rings:
                points = list(zip(ring[::2], ring[1::2]))
                edges.extend(zip(points, points[1:] + points[:1]))
            ymin, ymax = min(a[1] for a, _ in edges), max(a[1] for a, _ in edges)
            for row in range(max(0, math.ceil((ymin - margin - self.y0) / self.step)),
                             min(self.rows, 1 + math.floor((ymax + margin - self.y0) / self.step))):
                y = self.y0 + row * self.step
                crossings, spans = [], []
                for (ax, ay), (bx, by) in edges:
                    if min(ay, by) > y + margin or max(ay, by) < y - margin:
                        continue
                    if ay == by:
                        spans.append((min(ax, bx) - margin, max(ax, bx) + margin))
                        continue
                    slope = (bx - ax) / (by - ay)
                    if (ay > y) != (by > y):
                        crossings.append(ax + (y - ay) * slope)
                    lo = max(min(ay, by), y - margin)
                    hi = min(max(ay, by), y + margin)
                    x1, x2 = ax + (lo - ay) * slope, ax + (hi - ay) * slope
                    spans.append((min(x1, x2) - margin, max(x1, x2) + margin))
                crossings.sort()
                spans.extend(zip(crossings[::2], crossings[1::2]))
                for left, right in spans:
                    first = max(0, math.ceil((left - self.x0) / self.step))
                    last = min(self.width - 1, math.floor((right - self.x0) / self.step))
                    for i in range(row * self.width + first, row * self.width + last + 1):
                        if (levels[i] + stats["step_up"] < prism["top"]
                                and levels[i] + stats["height"] > prism["base"]):
                            blocked[i] = 1

        self.links = [[] for _ in range(count)]
        limit = self.step * math.tan(math.radians(stats["max_slope_deg"]))
        for i in range(count):
            if blocked[i]:
                continue
            for j in (i - 1 if i % self.width else -1, i - self.width):
                if j >= 0 and not blocked[j] and abs(levels[i] - levels[j]) <= limit:
                    self.links[i].append(j)
                    self.links[j].append(i)

        # Map roof spawns and obstructed destinations to a nearby walkable cell.
        self.snap = [i if not blocked[i] else -1 for i in range(count)]
        queue = deque(i for i in self.snap if i >= 0)
        if not queue:
            raise ValueError("Arena has no walkable grid cells")
        while queue:
            i = queue.popleft()
            for j in (i - 1 if i % self.width else -1,
                      i + 1 if (i + 1) % self.width else -1, i - self.width, i + self.width):
                if 0 <= j < count and self.snap[j] < 0:
                    self.snap[j] = self.snap[i]
                    queue.append(j)

        self.component = [-1] * count
        self.members = []
        for start in range(count):
            if blocked[start] or self.component[start] >= 0:
                continue
            group = len(self.members)
            cells = [start]
            self.component[start] = group
            for i in cells:
                for j in self.links[i]:
                    if self.component[j] < 0:
                        self.component[j] = group
                        cells.append(j)
            self.members.append(cells)
        self.route_key = None

    def cell(self, point):
        col = min(self.width - 1, max(0, round((point[0] - self.x0) / self.step)))
        row = min(self.rows - 1, max(0, round((point[1] - self.y0) / self.step)))
        return col + row * self.width

    def local_distances(self, pos, steps):
        """Walk distances in a small neighborhood, respecting walls and bridges."""
        start = self.snap[self.cell(pos)]
        hops = {start: 0}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            depth = hops[cell]
            if depth >= steps:
                continue
            for neighbor in self.links[cell]:
                if neighbor not in hops:
                    hops[neighbor] = depth + 1
                    queue.append(neighbor)
        return hops

    def waypoint(self, pos, goal):
        raw = self.cell(pos)
        start = self.snap[raw]
        if raw != start:
            return self.positions[start]
        target = self.cell(goal)
        group = self.component[start]
        key = (target, group)
        if self.route_key != key:
            end = self.snap[target]
            if self.component[end] != group:
                end = min(self.members[group], key=lambda i: math.dist(self.positions[i], goal))
            self.forward = [-1] * len(self.links)
            self.forward[end] = end
            queue = deque([end])
            while queue:
                i = queue.popleft()
                for j in self.links[i]:
                    if self.forward[j] < 0:
                        self.forward[j] = i
                        queue.append(j)
            self.route_key = key
        next_cell = self.forward[start]
        if start == target:
            return goal
        return self.positions[next_cell]
