# SPDX-License-Identifier: BSD-3-Clause

from collections import defaultdict
from enum import Enum, auto
import math
import numpy as np

# This is your team name
CREATOR = "tank"


def heading_away_from_land(game_map: np.ndarray, x: int, y: int) -> np.ndarray:
  offset = 5
  surrounding = game_map[y - offset:y + offset + 1, x - offset:x + offset + 1]
  samples = []

  for sx, sy in np.ndindex(surrounding.shape):
    if sx == offset and sy == offset:
      continue
    if surrounding[sx, sy] != 1:
      samples.append(np.nan_to_num(np.arctan2(y - sy, x - sx)))

  return np.nan_to_num(np.mean(samples)) * 180 / np.pi


class BaseTactic(Enum):
  TANK = auto()
  JET  = auto()

# This is the AI bot that will be instantiated for the competition
class PlayerAi:

  def __init__(self):
    self.team = CREATOR  # Mandatory attribute

    # Record the previous positions of all my vehicles
    self.previous_positions = {}
    self.historic_positions = set()
    self.base_ntanks = defaultdict(lambda: 0)
    self.base_nships = defaultdict(lambda: 0)
    self.base_tactic = defaultdict(lambda: BaseTactic.TANK)

  def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
    """
        This is the main function that will be called by the game engine.

        Parameters
        ----------
        t : float
            The current time in seconds.
        dt : float
            The time step in seconds.
        info : dict
            A dictionary containing all the information about the game.
            The structure is as follows:
            {
                "team_name_1": {
                    "bases": [base_1, base_2, ...],
                    "tanks": [tank_1, tank_2, ...],
                    "ships": [ship_1, ship_2, ...],
                    "jets": [jet_1, jet_2, ...],
                },
                "team_name_2": {
                    ...
                },
                ...
            }
        game_map : np.ndarray
            A 2D numpy array containing the game map.
            1 means land, 0 means water, -1 means no info.
        """

    # Get information about my team
    myinfo = info[self.team]

    enemy_bases = []
    enemy_tanks = []
    enemy_ships = []
    enemy_jets = []

    if len(info) > 1:
      for name in info:
        if name == self.team:
          continue

        if "bases" in info[name]:
          enemy_bases += info[name]["bases"]
        if "tanks" in info[name]:
          enemy_tanks += info[name]["tanks"]
        if "ships" in info[name]:
          enemy_ships += info[name]["ships"]
        if "jets" in info[name]:
          enemy_jets += info[name]["jets"]

    enemy_vehicles = enemy_tanks + enemy_ships + enemy_jets
    enemy_entities = enemy_bases + enemy_vehicles

    base_grouped_tanks = defaultdict(list)
    if "tanks" in myinfo:
      for tank in myinfo["tanks"]:
        base_grouped_tanks[tank.owner.uid].append(tank)

    base_grouped_ships = defaultdict(list)
    if "ships" in myinfo:
      for ship in myinfo["ships"]:
        base_grouped_ships[ship.owner.uid].append(ship)

    base_grouped_jets = defaultdict(list)
    if "jets" in myinfo:
      for jet in myinfo["jets"]:
        base_grouped_jets[jet.owner.uid].append(jet)

    base_positions = [(base.x, base.y) for base in myinfo["bases"]]
    self.historic_positions.update(base_positions)

    for base in myinfo["bases"]:
      base_tanks = base_grouped_tanks[base.uid]
      base_ships = base_grouped_ships[base.uid]
      base_jets = base_grouped_jets[base.uid]
      base_tactic = self.base_tactic[base.uid]
      heading_away = heading_away_from_land(game_map, base.x, base.y)
      base_ntanks = self.base_ntanks[base.uid]
      base_nships = self.base_nships[base.uid]


      # First we need to prioritize building our 3 mines, that way we have
      # ample production for all of our conquests.
      if base.mines < 3:
        if base.crystal > base.cost("mine"):
          base.build_mine()
      elif base.crystal > base.cost("tank") and base_ntanks < 6:
        base.build_tank(np.flip(heading_away))
        self.base_ntanks[base.uid] += 1
      # Time to divide like a bacteria! Send out the ships!
      elif base_nships < 4:
        if base.crystal > base.cost("ship"):
          # We need to check that there is not a friendly base in the direct
          # vicinity (a margin of 10 degrees in this case) of the heading we
          # initially chose. If there is we want to shift our heading, here
          # by 20 degrees.
          for bx, by in base_positions:
            margin = 10
            heading_towards_base = math.atan2(base.y - by, base.x - bx)
  
            if heading_towards_base - margin <= heading_away or heading_towards_base + margin >= heading_away:
              heading_away = (heading_away + 20) % 360
  
          base.build_ship(heading_away)
          self.base_nships[base.uid] += 1
      elif base.crystal > base.cost("tank") and base_tactic == BaseTactic.TANK:
        base.build_tank(np.flip(heading_away))
        self.base_ntanks[base.uid] += 1
      # If everything else is satisfied, build a jet.
      elif base.crystal > base.cost("jet") and base_tactic == BaseTactic.JET:
        base.build_jet(np.flip(heading_away))

      for jet in base_jets:
        if len(enemy_bases) >= 1:
          jet.goto(enemy_bases[0].x, enemy_bases[0].y)
        # else:
        #   jet.goto(jet.owner.x, jet.owner.y)

      for tank in base_tanks:
        if (tank.uid in self.previous_positions) and (not tank.stopped):
          # If the tank position is the same as the previous position,
          # set a random heading
          if all(tank.position == self.previous_positions[tank.uid]):
            tank.set_heading(np.random.random() * 360.0)
          elif len(enemy_bases) > 0:
            closest_base_to_tank = min(
                enemy_bases, key=lambda enemy: tank.get_distance(enemy.x, enemy.y, False))
            tank.goto(closest_base_to_tank.x, closest_base_to_tank.y)
          elif len(enemy_tanks) > 0:
            closest_tank_to_tank = min(
                enemy_tanks, key=lambda enemy: tank.get_distance(enemy.x, enemy.y, False))
            tank.goto(closest_tank_to_tank.x, closest_tank_to_tank.y)
          elif len(enemy_tanks) > 0:
            closest_tank_to_tank = min(
                enemy_tanks, key=lambda enemy: tank.get_distance(enemy.x, enemy.y, False))
            tank.goto(closest_tank_to_tank.x, closest_tank_to_tank.y)

        # Store the previous position of this tank for the next time step
        self.previous_positions[tank.uid] = tank.position

      for ship in base_ships:
        if ship.uid in self.previous_positions:
          # If the ship position is the same as the previous position,
          # convert the ship to a base if it is far from the owning base,
          # set a random heading otherwise
          if all(ship.position == self.previous_positions[ship.uid]):
            min_base_ship_distance = 10
            base_ship_distances = [((x, y), ship.get_distance(x, y, False))
                                   for x, y in base_positions]
            closest_base = min(
                base_ship_distances,
                key=lambda base_ship_distance: base_ship_distance[1])
            closest_base_position = closest_base[0]
            closest_base_distance = closest_base[1]

            if closest_base_distance > min_base_ship_distance:
              # Try to convert the ship into a base
              base_uid = ship.convert_to_base()

              # We failed and most likely got stuck, lets move a tiny bit
              if base_uid is None:
                ship.set_heading((ship.heading + 10) % 360)
              else:
                self.base_tactic[base_uid] = BaseTactic.TANK if np.random.random() < 0.8 else BaseTactic.JET
              # Switch BaseTactic every other base
              # elif base_tactic == BaseTactic.TANK:
              #   self.base_tactic[base_uid] = BaseTactic.JET
              # elif base_tactic == BaseTactic.JET:
              #   self.base_tactic[base_uid] = BaseTactic.TANK

            else:
              ship.set_heading(np.random.random() * 360.0)
              # next_heading = heading_away_from_land(game_map, *closest_base_position)
              # Lets move in the next best direction
              # ship.set_heading(heading_away_from_land(game_map, *closest_base_position))

        # Store the previous position of this ship for the next time step
        self.previous_positions[ship.uid] = ship.position

    # Controlling my bases =================================================

    # Description of information available on bases:
    #
    # This is read-only information that all the bases (enemy and your own) have.
    # We define base = info[team_name_1]["bases"][0]. Then:
    #
    # base.x (float): the x position of the base
    # base.y (float): the y position of the base
    # base.position (np.ndarray): the (x, y) position as a numpy array
    # base.team (str): the name of the team the base belongs to, e.g. ‘John’
    # base.number (int): the player number
    # base.mines (int): the number of mines inside the base
    # base.crystal (int): the amount of crystal the base has in stock
    #     (crystal is per base, not shared globally)
    # base.uid (str): unique id for the base
    #
    # Description of base methods:
    #
    # If the base is your own, the object will also have the following methods:
    #
    # base.cost("mine"): get the cost of an object.
    #     Possible types are: "mine", "tank", "ship", "jet"
    # base.build_mine(): build a mine
    # base.build_tank(): build a tank
    # base.build_ship(): build a ship
    # base.build_jet(): build a jet

    # Iterate through all my bases (vehicles belong to bases)
    # for base in myinfo["bases"]:
    #   # If this is a new base, initialize the tank & ship counters
    #   if base.uid not in self.ntanks:
    #     self.ntanks[base.uid] = 0
    #   if base.uid not in self.nships:
    #     self.nships[base.uid] = 0
    #   # Firstly, each base should build a mine if it has less than 3 mines
    #   if base.mines < 3:
    #     if base.crystal > base.cost("mine"):
    #       base.build_mine()
    #   # Secondly, each base should build a tank if it has less than 5 tanks
    #   elif base.crystal > base.cost("tank") and self.ntanks[base.uid] < 5:
    #     # build_tank() returns the uid of the tank that was built
    #     tank_uid = base.build_tank(heading=360 * np.random.random())
    #     # Add 1 to the tank counter for this base
    #     self.ntanks[base.uid] += 1
    #   # Thirdly, each base should build a ship if it has less than 3 ships
    #   elif base.crystal > base.cost("ship") and self.nships[base.uid] < 3:
    #     # build_ship() returns the uid of the ship that was built
    #     ship_uid = base.build_ship(heading=360 * np.random.random())
    #     # Add 1 to the ship counter for this base
    #     self.nships[base.uid] += 1
    #   # If everything else is satisfied, build a jet
    #   elif base.crystal > base.cost("jet"):
    #     # build_jet() returns the uid of the jet that was built
    #     jet_uid = base.build_jet(heading=360 * np.random.random())

    # Try to find an enemy target
    target = None
    # If there are multiple teams in the info, find the first team that is not mine
    if len(info) > 1:
      for name in info:
        if name != self.team:
          # Target only bases
          if "bases" in info[name]:
            # Simply target the first base
            t = info[name]["bases"][0]
            target = [t.x, t.y]

    # Controlling my vehicles ==============================================

    # Description of information available on vehicles
    # (same info for tanks, ships, and jets):
    #
    # This is read-only information that all the vehicles (enemy and your own) have.
    # We define tank = info[team_name_1]["tanks"][0]. Then:
    #
    # tank.x (float): the x position of the tank
    # tank.y (float): the y position of the tank
    # tank.team (str): the name of the team the tank belongs to, e.g. ‘John’
    # tank.number (int): the player number
    # tank.speed (int): vehicle speed
    # tank.health (int): current health
    # tank.attack (int): vehicle attack force (how much damage it deals to enemy
    #     vehicles and bases)
    # tank.stopped (bool): True if the vehicle has been told to stop
    # tank.heading (float): the heading angle (in degrees) of the direction in
    #     which the vehicle will advance (0 = east, 90 = north, 180 = west,
    #     270 = south)
    # tank.vector (np.ndarray): the heading of the vehicle as a vector
    #     (basically equal to (cos(heading), sin(heading))
    # tank.position (np.ndarray): the (x, y) position as a numpy array
    # tank.uid (str): unique id for the tank
    #
    # Description of vehicle methods:
    #
    # If the vehicle is your own, the object will also have the following methods:
    #
    # tank.get_position(): returns current np.array([x, y])
    # tank.get_heading(): returns current heading in degrees
    # tank.set_heading(angle): set the heading angle (in degrees)
    # tank.get_vector(): returns np.array([cos(heading), sin(heading)])
    # tank.set_vector(np.array([vx, vy])): set the heading vector
    # tank.goto(x, y): go towards the (x, y) position
    # tank.stop(): halts the vehicle
    # tank.start(): starts the vehicle if it has stopped
    # tank.get_distance(x, y): get the distance between the current vehicle
    #     position and the given point (x, y) on the map
    # ship.convert_to_base(): convert the ship to a new base (only for ships).
    #     This only succeeds if there is land close to the ship.
    #
    # Note that by default, the goto() and get_distance() methods will use the
    # shortest path on the map (i.e. they may go through the map boundaries).

    # Iterate through all my tanks
    # if "tanks" in myinfo:
    #   for tank in myinfo["tanks"]:
    #     if (tank.uid in self.previous_positions) and (not tank.stopped):
    #       # If the tank position is the same as the previous position,
    #       # set a random heading
    #       if all(tank.position == self.previous_positions[tank.uid]):
    #         tank.set_heading(np.random.random() * 360.0)
    #       # Else, if there is a target, go to the target
    #       elif target is not None:
    #         tank.goto(*target)
    #     # Store the previous position of this tank for the next time step
    #     self.previous_positions[tank.uid] = tank.position

    # Iterate through all my ships
"""     if "ships" in myinfo:
      for ship in myinfo["ships"]:
        if ship.uid in self.previous_positions:
          # If the ship position is the same as the previous position,
          # convert the ship to a base if it is far from the owning base,
          # set a random heading otherwise
          if all(ship.position == self.previous_positions[ship.uid]):
            min_base_ship_distance = 20
            base_ship_distances = [((x, y), ship.get_distance(x, y, False))
                                   for x, y in base_positions]
            closest_base = min(
                base_ship_distances,
                key=lambda base_ship_distance: base_ship_distance[1])
            closest_base_position = closest_base[0]
            closest_base_distance = closest_base[1]

            if closest_base_distance > min_base_ship_distance:
              # Try to convert the ship into a base
              base_uid = ship.convert_to_base()

              # We failed and most likely got stuck, lets move a tiny bit
              if base_uid is None:
                ship.set_heading((ship.heading + 10) % 360)
            else:
              ship.set_heading(np.random.random() * 360.0)
              # next_heading = heading_away_from_land(game_map, *closest_base_position)
              # Lets move in the next best direction
              # ship.set_heading(heading_away_from_land(game_map, *closest_base_position))

        # Store the previous position of this ship for the next time step
        self.previous_positions[ship.uid] = ship.position """

    # Iterate through all my jets
    # if "jets" in myinfo:
    #   for jet in myinfo["jets"]:
    #     # Jets simply go to the target if there is one, they never get stuck
    #     if target is not None:
    #       jet.goto(*target)
