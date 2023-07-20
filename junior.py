# SPDX-License-Identifier: BSD-3-Clause

from os import CLD_CONTINUED
from typing import Any, Iterable
import numpy as np
from dataclasses import dataclass, field
from supremacy.base import Base
from supremacy.vehicles import Jet, Tank, Ship

# This is your team name
# CREATOR = "5monkeys"
CREATOR = "junior"

class DeadError(RuntimeError): ...

@dataclass
class Team:
    teams: list["Team"]
    base_id: str
    info: dict
    mines: int = 1
    tank_ids: list[str] = field(default_factory=list)
    ship_ids: list[str] = field(default_factory=list)
    jet_ids: list[str] = field(default_factory=list)
    money: int = 0

    last_positions: dict[str, np.ndarray] = field(default_factory=dict)

    @property
    def base(self) -> Base:
        for base in self.me["bases"]:
            if base.uid == self.base_id:
                return base
        raise DeadError("we seem to be dead :(")

    @property
    def me(self) -> dict:
        return self.info[CREATOR]

    @property
    def bases(self) -> list[Base]:
        return self.me["bases"] if "bases" in self.me else []

    @property
    def tanks(self) -> Iterable[Tank]:
        all_tanks = self.me["tanks"] if "tanks" in self.me else []
        return (tank for tank in all_tanks if tank.uid in self.tank_ids)

    @property
    def ships(self) -> Iterable[Ship]:
        all_ships = self.me["ships"] if "ships" in self.me else []
        return (ship for ship in all_ships if ship.uid in self.ship_ids)

    @property
    def jets(self) -> Iterable[Jet]:
        all_jets = self.me["jets"] if "jets" in self.me else []
        return (jet for jet in all_jets if jet.uid in self.jet_ids)

    def remove_dead_entities(self):
        all_tanks = (tank.uid for tank in (self.me["tanks"] if "tanks" in self.me else []))
        self.tank_ids = [tank_id for tank_id in self.tank_ids if tank_id in all_tanks]

        all_ships = (ship.uid for ship in (self.me["ships"] if "ships" in self.me else []))
        self.ship_ids = [ship_id for ship_id in self.ship_ids if ship_id in all_ships]

        all_jets = (jet.uid for jet in (self.me["jets"] if "jets" in self.me else []))
        self.jet_ids = [jet_id for jet_id in self.jet_ids if jet_id in all_jets]

    @property
    def enemy_teams(self) -> Iterable[dict]:
        info = self.info.copy()
        del info[CREATOR]
        return info.values()

    def run(self):
        self.remove_dead_entities()
        if self.mines != 2:
            if self.base.build_mine():
                self.mines += 1
        if len(list(self.tanks)) != 5:
            if (tank := self.base.build_tank(heading=180*np.random.random())):
                self.tank_ids.append(tank)
        if len(list(self.ships)) != 2:
            if (ship := self.base.build_ship(heading=180*np.random.random())):
                self.ship_ids.append(ship)
        if len(list(self.jets)) != 2:
            if (jet := self.base.build_jet(heading=180*np.random.random())):
                self.jet_ids.append(jet)

        targets = []
        for enemy_team in self.enemy_teams:
            if "planes" in enemy_team:
                t = enemy_team["planes"][0]
                targets.append([t.x, t.y])
            if "bases" in enemy_team:
                t = enemy_team["bases"][0]
                targets.append([t.x, t.y])
            elif "ships" in enemy_team:
                t = enemy_team["ships"][0]
                targets.append([t.x, t.y])
            elif "tanks" in enemy_team:
                t = enemy_team["tanks"][0]
                targets.append([t.x, t.y])
        targets *= 10

        for tank in self.tanks:
            if (tank.uid in self.last_positions) and (not tank.stopped):
                if all(tank.position == self.last_positions[tank.uid]):
                    tank.set_heading(np.random.random() * 360.0)
                if targets:
                    target = targets.pop()
                    tank.goto(*target)
            self.last_positions[tank.uid] = tank.position

        for ship in self.ships:
            if ship.uid in self.last_positions:
                if all(ship.position == self.last_positions[ship.uid]):
                    if ship.get_distance(ship.owner.x, ship.owner.y) > 80:
                        if (base := ship.convert_to_base()):
                            self.ship_ids.remove(ship.uid)
                            self.teams.append(Team(
                                teams=self.teams,
                                base_id=base,
                                info=self.info
                            ))
                    else:
                        ship.set_heading(np.random.random() * 360.0)
            self.last_positions[ship.uid] = ship.position

        for jet in self.jets:
            if targets:
                target = targets.pop()
                jet.goto(*target)


# This is the AI bot that will be instantiated for the competition
class PlayerAi:
    team: str
    tick: int
    teams: list[Team]

    def __init__(self):
        self.team = CREATOR  # Mandatory attribute

        # Record the previous positions of all my vehicles
        self.previous_positions = {}
        # Record the number of tanks and ships I have at each base
        self.ntanks = {}
        self.nships = {}
        self.tick = 0
        self.teams = []

    def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
        self.tick += 1
        if self.tick == 1:
            self.teams.append(Team(
                teams=self.teams,
                base_id=info[self.team]["bases"][0].uid,
                info=info
            ))
        for team in self.teams:
            team.info = info
            try:
                team.run()
            except DeadError:
                pass
