# Verbatim copy from mesa
# https://github.com/projectmesa/mesa/blob/976ddfc8a1e5feaaf8007a7abaa9abc7093881a0/examples/virus_on_network/virus_on_network/model.py
import math
from enum import Enum
import networkx as nx

from soil import *


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
            a.set_state(VirusAgent.infected)
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
        return self.count_agents(state_id=VirusAgent.infected.id)

    @report
    @property
    def number_susceptible(self):
        return self.count_agents(state_id=VirusAgent.susceptible.id)

    @report
    @property
    def number_resistant(self):
        return self.count_agents(state_id=VirusAgent.resistant.id)


class VirusAgent(Agent):
    virus_spread_chance = None # Inherit from model
    virus_check_frequency = None # Inherit from model
    recovery_chance = None # Inherit from model
    gain_resistance_chance = None # Inherit from model
    just_been_infected = False

    @state(default=True)
    def susceptible(self):
        if self.just_been_infected:
            self.just_been_infected = False
            return self.infected

    @state
    def infected(self):
        susceptible_neighbors = self.get_neighbors(state_id=self.susceptible.id)
        for a in susceptible_neighbors:
            if self.prob(self.virus_spread_chance):
                a.just_been_infected = True
        if self.prob(self.virus_check_frequency):
            if self.prob(self.recovery_chance):
                if self.prob(self.gain_resistance_chance):
                    return self.resistant
                else:
                    return self.susceptible
            else:
                return self.infected

    @state
    def resistant(self):
        return self.at(INFINITY)


if __name__ == "__main__":
    from _config import run_sim
    run_sim(model=VirusOnNetwork)