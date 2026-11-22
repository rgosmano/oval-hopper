"""A movement-only Mech Royale controller using the game's rechargeable jet."""
import math

import mechfight as mf


class Bot:
    name = "Oval Hopper"

    def __init__(self, hello):
        self.climbing = False
        self.direction = 1 if hello.get("slot", 0) % 2 else -1

    def act(self, obs):
        me = obs["self"]
        x, y, _ = me["pos"]
        zone = obs["zone"]
        cx, cy = zone["next_center"]
        radius = zone["next_radius"]
        dx, dy = x - cx, y - cy
        distance = math.hypot(dx, dy)
        if distance < 0.01:
            angle = me["id"] * math.tau / 16
            ux, uy = math.cos(angle), math.sin(angle)
        else:
            ux, uy = dx / distance, dy / distance

        # Follow an orbit in the announced circle. Near the final point,
        # cancel horizontal drift using the simulator's reported velocity.
        vx, vy, _ = me["vel"]
        if radius <= 10:
            mx, my = -dx - 0.5 * vx, -dy - 0.5 * vy
            scale = max(4, math.hypot(mx, my))
        else:
            radial = max(-2.5, min(1, (0.70 * radius - distance) / max(10, 0.15 * radius)))
            mx = radial * ux - self.direction * uy
            my = radial * uy + self.direction * ux
            scale = math.hypot(mx, my)

        energy = me["energy"] / max(1, me["max_energy"])
        if me["grounded"]:
            self.climbing = energy >= 0.90
        elif self.climbing and energy <= 0.10:
            self.climbing = False
        action = dict(tick=obs["tick"], move=[mx / scale, my / scale],
                      jump=me["grounded"] and self.climbing,
                      boost=self.climbing and not me["grounded"])
        if obs.get("offer"):
            priority = ("reactor", "jets", "capacitor", "plating", "armor", "nanites", "servos")
            ids = [choice["id"] for choice in obs["offer"]["choices"]]
            action["pick"] = next((ids.index(item) for item in priority if item in ids), 0)
        return action


if __name__ == "__main__":
    mf.run(Bot)
