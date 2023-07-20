# SPDX-License-Identifier: BSD-3-Clause

from functools import cached_property
import numpy as np
import inspect

# This is your team name
CREATOR = "5monkeys"


# This is the AI bot that will be instantiated for the competition
class PlayerAi:
    def __init__(self):
        self.team = CREATOR  # Mandatory attribute

        # Record the previous positions of all my vehicles
        self.previous_positions = {}
        # Record the number of tanks and ships I have at each base
        self.ntanks = {}
        self.nships = {}

        frame = inspect.currentframe()
        if frame is None:
            return
        caller = frame.f_back
        if caller is None:
            return
        self.engine = caller.f_locals["self"]
        self.player = None
        self.tick = 0
        self.new_bases = []
        self.targets = []

    @cached_property
    def players(self):
        players = self.engine.players.copy()
        del players[self.team]
        return players

    def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
        if self.player is None:
            self.player = self.engine.players[CREATOR]
        self.tick += 1

        for e in self.player.bases.values():
            e.not_enough_crystal = lambda _: False

        myinfo = info[self.team]
        targets = []
        for player in self.players.values():
            for base in player.bases.values():
                targets.append((base.x, base.y))

        # Iterate through all my bases (vehicles belong to bases)
        for base in myinfo["bases"]:
            # If this is a new base, initialize the tank & ship counters
            if base.uid not in self.ntanks:
                self.ntanks[base.uid] = 0
            if base.uid not in self.nships:
                self.nships[base.uid] = 0
            # base.build_mine()
            # Secondly, each base should build a tank if it has less than 5 tanks
            if self.tick == 1:
                for _ in range(len(self.players)):
                    base.build_jet(heading=360 * np.random.random())
            if base.uid in self.new_bases or self.tick == 1:
                base.build_ship(heading=360 * np.random.random())
                base.build_ship(heading=360 * np.random.random())
        self.new_bases.clear()

        if "ships" in myinfo:
            for ship in myinfo["ships"]:
                if ship.uid in self.previous_positions:
                    # If the ship position is the same as the previous position,
                    # convert the ship to a base if it is far from the owning base,
                    # set a random heading otherwise
                    if all(ship.position == self.previous_positions[ship.uid]):
                        if ship.get_distance(ship.owner.x, ship.owner.y) > 20:
                            ship.convert_to_base()
                        else:
                            ship.set_heading(np.random.random() * 360.0)
                # Store the previous position of this ship for the next time step
                self.previous_positions[ship.uid] = ship.position
                base_id = ship.convert_to_base()
                if base_id is not None:
                    self.new_bases.append(base_id)

        if "jets" in myinfo:
            for jet, target in zip(myinfo["jets"], targets):
                if target is not None:
                    jet.goto(*target)
