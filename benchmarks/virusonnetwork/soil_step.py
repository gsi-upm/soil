# Verbatim copy from mesa
# https://github.com/projectmesa/mesa/blob/976ddfc8a1e5feaaf8007a7abaa9abc7093881a0/examples/virus_on_network/virus_on_network/model.py
import math
from enum import Enum
import networkx as nx

from soil import *


class State(Enum):
    SUSCEPTIBLE = 0
    INFECTED = 1
    RESISTANT = 2


class VirusOnNetwork(Environment):
    """A virus model with some number of agents"""
    num_nodes = 10
    avg_node_degree = 3
    initial_outbreak_size = 1
    virus_spread_chance = 0.4
    virus_check_frequency = 0.4
    recovery_chance = 0
    gain_resistance_chance = 0

    def init(self):
        prob = self.avg_node_degree / self.num_nodes
        # Use internal seed with the networkx generator
        self.create_network(generator=nx.erdos_renyi_graph, n=self.num_nodes, p=prob)

        self.initial_outbreak_size = min(self.initial_outbreak_size, self.num_nodes)
        self.populate_network(VirusAgent)

        # Infect some nodes
        infected_nodes = self.random.sample(list(self.G), self.initial_outbreak_size)
        for a in self.get_agents(node_id=infected_nodes):
            a.status = State.INFECTED
        assert self.number_infected == self.initial_outbreak_size

    @report
    def resistant_susceptible_ratio(self):
        try:
            return self.number_resistant / self.number_susceptible
        except ZeroDivisionError:
            return math.inf

    @report
    @property
    def number_infected(self):
        return self.count_agents(status=State.INFECTED)

    @report
    @property
    def number_susceptible(self):
        return self.count_agents(status=State.SUSCEPTIBLE)

    @report
    @property
    def number_resistant(self):
        return self.count_agents(status=State.RESISTANT)



class VirusAgent(Agent):
    status = State.SUSCEPTIBLE
    virus_spread_chance = None # Inherit from model
    virus_check_frequency = None # Inherit from model
    recovery_chance = None # Inherit from model
    gain_resistance_chance = None # Inherit from model

    def try_to_infect_neighbors(self):
        susceptible_neighbors = self.get_neighbors(status=State.SUSCEPTIBLE)
        for a in susceptible_neighbors:
            if self.prob(self.virus_spread_chance):
                a.status = State.INFECTED

    def try_gain_resistance(self):
        if self.prob(self.gain_resistance_chance):
            self.status = State.RESISTANT
            return self.at(INFINITY)

    def try_remove_infection(self):
        # Try to remove
        if self.prob(self.recovery_chance):
            # Success
            self.status = State.SUSCEPTIBLE
            return self.try_gain_resistance()

    def try_check_situation(self):
        if self.prob(self.virus_check_frequency):
            # Checking...
            if self.status is State.INFECTED:
                return self.try_remove_infection()

    def step(self):
        if self.status is State.INFECTED:
            self.try_to_infect_neighbors()
        return self.try_check_situation()



if __name__ == "__main__":
    from _config import run_sim
    run_sim(model=VirusOnNetwork)