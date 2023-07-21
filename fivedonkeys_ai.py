# SPDX-License-Identifier: BSD-3-Clause

from collections import defaultdict
from typing import Sequence, Union
import numpy as np

from supremacy.tools import distance_on_torus

# This is your team name
CREATOR = "5donkeys"

# def plot_line(x0, y0, x1, y1):
#   dx = x1 - x0
#   dy = y1 - y0
#   D = 2 * dy - dx
#   y = y0
#   for x in range(x0, x1):
#     yield (x, y)
#     if D > 0:
#       y = y + 1
#       D = D - 2*dx
#     D = D + 2*dy
#
#
# def raycast_until_land(origin: np.ndarray, heading: float, game_map: np.ndarray) -> np.ndarray:
#     map_width = game_map.shape[0]
#     map_height = game_map.shape[1]
#     plot_line(origin.x, origin.y, )
#
# def heading_away_from_land(position: np.ndarray, game_map: np.ndarray):
#     pass


def to_heading(vec: Union[np.ndarray, Sequence[float]]):
  vec = np.asarray(vec) / np.linalg.norm(vec)
  h = np.arccos(np.dot(vec, [1, 0])) * 180 / np.pi
  if vec[1] < 0:
    h = 360 - h
  return h


# This is the AI bot that will be instantiated for the competition
class PlayerAi:

  def __init__(self):
    self.team = CREATOR  # Mandatory attribute

    # Record the previous positions of all my vehicles
    self.previous_positions = {}
    # Record the number of tanks and ships I have at each base
    self.ntanks = {}
    self.nships = {}
    self.njets = {}
    self.ship_headings = {}

    # self.defense = set()
    # self.offense = set()

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

    base_positions = [[base.x, base.y] for base in myinfo["bases"]]

    # Iterate through all my bases (vehicles belong to bases)
    for base in myinfo["bases"]:
      # If this is a new base, initialize the tank, ship and jet counters
      if base.uid not in self.ntanks:
        self.ntanks[base.uid] = 0
      if base.uid not in self.nships:
        self.nships[base.uid] = 0
      if base.uid not in self.njets:
        self.njets[base.uid] = 0
      if base.uid not in self.ship_headings:
        self.ship_headings[base.uid] = to_heading(
            np.flip(np.add.reduce(base_positions)))
      # Firstly, each base should build a mine if it has less than 3 mines
      if base.mines < 3:
        if base.crystal > base.cost("mine"):
          base.build_mine()
      # Secondly, each base should build a tank if it has less than 5 tanks
      elif base.crystal > base.cost("tank") and self.ntanks[base.uid] < 5:
        # build_tank() returns the uid of the tank that was built
        tank_uid = base.build_tank(heading=self.ship_headings[base.uid])
        # Add 1 to the tank counter for this base
        self.ntanks[base.uid] += 1
      # Thirdly, each base should build a ship if it has less than 3 ships
      elif base.crystal > base.cost("ship") and self.nships[base.uid] < 4:
        # build_ship() returns the uid of the ship that was built
        self.ship_headings[base.uid] += 90
        self.ship_headings[base.uid] %= 360
        ship_uid = base.build_ship(heading=self.ship_headings[base.uid])
        # Add 1 to the ship counter for this base
        self.nships[base.uid] += 1
      # If everything else is satisfied, build a jet
      elif base.crystal > base.cost("jet"):
        # build_jet() returns the uid of the jet that was built
        jet_uid = base.build_jet(heading=self.ship_headings[base.uid])
        # Add 1 to the jet counter for this base
        self.njets[base.uid] += 1

        # We want to start by creating defensive jets
        # if self.njets[base.uid] <= 5:
        #     self.defense.add(jet_uid)
        # else:
        #     self.offense.add(jet_uid)

    enemy_bases = []
    enemy_tanks = []
    enemy_ships = []
    enemy_jets  = []

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

    target = None
    if len(enemy_entities) >= 1:
      target = [enemy_entities[0].x, enemy_entities[0].y]

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
    if "tanks" in myinfo:
      for tank in myinfo["tanks"]:
        if (tank.uid in self.previous_positions) and (not tank.stopped):
          # If the tank position is the same as the previous position,
          # set a random heading
          if all(tank.position == self.previous_positions[tank.uid]):
            tank.set_heading(np.random.random() * 360.0)
          # Else, if there is a target, go to the target
          elif target is not None:
            tank.goto(*target)
        # Store the previous position of this tank for the next time step
        self.previous_positions[tank.uid] = tank.position

    # Iterate through all my ships
    if "ships" in myinfo:
      for ship in myinfo["ships"]:
        if ship.uid in self.previous_positions:
          # If the ship position is the same as the previous position,
          # convert the ship to a base if it is far from the owning base,
          # set a random heading otherwise
          if all(ship.position == self.previous_positions[ship.uid]):
            if ship.get_distance(ship.owner.x, ship.owner.y, False) > 20:
              ship.convert_to_base()
            else:
              self.ship_headings[ship.owner.uid] = 360 * np.random.random()
              ship.set_heading(self.ship_headings[ship.owner.uid])
        # else:
        #     ship.set_vector(np.flip(np.add.reduce(base_positions)))
        # Store the previous position of this ship for the next time step
        self.previous_positions[ship.uid] = ship.position

    # Iterate through all my jets
    if "jets" in myinfo:
      for jet in myinfo["jets"]:
        home_position = [jet.owner.x, jet.owner.y]
        home_distance = jet.get_distance(*home_position, False)

        closest_distance = None
        closest_target = None
        if len(enemy_vehicles) > 0:
          for enemy in enemy_vehicles:
            enemy_jet_distance = jet.get_distance(*enemy.position, False)
            enemy_home_distance = distance_on_torus(*home_position, *enemy.position)

            if (closest_distance is None) or min(enemy_jet_distance, enemy_home_distance) < closest_distance or enemy_jet_distance < enemy_home_distance:
              closest_distance = min(enemy_jet_distance, enemy_home_distance)
              closest_target = [enemy.x, enemy.y]

        if home_distance > 400:
          jet.set_vector(home_position)
        elif closest_target is not None:
          jet.goto(*closest_target)
        elif target is not None:
          jet.goto(*target)

        # Store the previous position of this jet for the next time step
        self.previous_positions[jet.uid] = jet.position
