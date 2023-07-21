import numpy as np
from collections import defaultdict
import math

# This is your team name
CREATOR = "chatgpt"

class PlayerAi:
    def __init__(self):
        self.team = CREATOR

        # Record the previous positions of all my vehicles
        self.previous_positions = {}
        # Record the number of tanks and ships I have at each base
        self.ntanks = {}
        self.nships = {}

        self.targets = defaultdict(lambda: None)

    def get_distance(self, obj1, obj2):
        return math.dist(obj1.position, obj2.position)

    def get_nearest_enemy_base(self, my_bases, enemy_bases):
        nearest_enemy_base = None
        min_distance = float("inf")
        for my_base in my_bases:
            for enemy_base in enemy_bases:
                distance = self.get_distance(my_base, enemy_base)
                if distance < min_distance:
                    nearest_enemy_base = enemy_base
                    min_distance = distance
        return nearest_enemy_base

    def attack_or_retreat(self, vehicle, target):
        distance_to_target = self.get_distance(vehicle, target)
        if distance_to_target <= 10:  # Attack when within 10 units of the target
            vehicle.attack(*target.position)
            vehicle.goto(*target.position)
        elif vehicle.health < 50:  # Retreat when health drops below 50
            vehicle.goto(vehicle.owner.x, vehicle.owner.y)
        else:
            vehicle.set_heading(np.random.random() * 360.0)

    def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
        myinfo = info[self.team]

        # Controlling my bases
        for base in myinfo["bases"]:
            if base.uid not in self.ntanks:
                self.ntanks[base.uid] = 0
            if base.uid not in self.nships:
                self.nships[base.uid] = 0

            if base.mines < 3 and base.crystal > base.cost("mine"):
                base.build_mine()
            elif base.crystal > base.cost("tank") and self.ntanks[base.uid] < 5:
                tank_uid = base.build_tank(heading=360 * np.random.random())
                self.ntanks[base.uid] += 1
            elif base.crystal > base.cost("ship") and self.nships[base.uid] < 3:
                ship_uid = base.build_ship(heading=360 * np.random.random())
                self.nships[base.uid] += 1
            elif base.crystal > base.cost("jet"):
                jet_uid = base.build_jet(heading=360 * np.random.random())

            if "bases" in info and len(info) > 1:
                enemy_bases = [b for name, team_info in info.items() if name != self.team for b in team_info["bases"]]
                target = self.get_nearest_enemy_base(myinfo["bases"], enemy_bases)
                self.targets[base.uid] = target


        vehicles = []

        if "tanks" in myinfo:
            vehicles += myinfo["tanks"]

        if "ships" in myinfo:
            vehicles += myinfo["ships"]

        if "jets" in myinfo:
            vehicles += myinfo["jets"]

        # Controlling my vehicles
        for vehicle in vehicles:
            if vehicle.uid in self.previous_positions and not vehicle.stopped:
                if all(vehicle.position == self.previous_positions[vehicle.uid]):
                    vehicle.set_heading(np.random.random() * 360.0)
                else:
                    target = self.targets[vehicle.owner.uid]
                    if target is not None:
                        self.attack_or_retreat(vehicle, target)

            self.previous_positions[vehicle.uid] = vehicle.position
