from soil.agents import FSM, NetworkAgent, state, default_state
from soil.parameters import *
import logging

from soil.environment import Environment


class DumbViewer(FSM, NetworkAgent):
    """
    A viewer that gets infected via TV (if it has one) and tries to infect
    its neighbors once it's infected.
    """

    has_been_infected: bool = False
    has_tv: bool = False

    @default_state
    @state
    def neutral(self):
        if self.has_tv:
            if self.prob(self.get("prob_tv_spread")):
                return self.infected
        if self.has_been_infected:
            return self.infected

    @state
    def infected(self):
        for neighbor in self.get_neighbors(state_id=self.neutral.id):
            if self.prob(self.get("prob_neighbor_spread")):
                neighbor.infect()

    def infect(self):
        """
        This is not a state. It is a function that other agents can use to try to
        infect this agent. DumbViewer always gets infected, but other agents like
        HerdViewer might not become infected right away
        """
        self.has_been_infected = True


class HerdViewer(DumbViewer):
    """
    A viewer whose probability of infection depends on the state of its neighbors.
    """

    def infect(self):
        """Notice again that this is NOT a state. See DumbViewer.infect for reference"""
        infected = self.count_neighbors(state_id=self.infected.id)
        total = self.count_neighbors()
        prob_infect = self.get("prob_neighbor_spread") * infected / total
        self.debug("prob_infect", prob_infect)
        if self.prob(prob_infect):
            self.has_been_infected = True


class WiseViewer(HerdViewer):
    """
    A viewer that can change its mind.
    """

    @state
    def cured(self):
        prob_cure = self.get("prob_neighbor_cure")
        for neighbor in self.get_neighbors(state_id=self.infected.id):
            if self.prob(prob_cure):
                try:
                    neighbor.cure()
                except AttributeError:
                    self.debug("Viewer {} cannot be cured".format(neighbor.id))

    def cure(self):
        self.has_been_cured = True

    @state
    def infected(self):
        if self.has_been_cured:
            return self.cured
        cured = max(self.count_neighbors(self.cured.id), 1.0)
        infected = max(self.count_neighbors(self.infected.id), 1.0)
        prob_cure = self.get("prob_neighbor_cure") * (cured / infected)
        if self.prob(prob_cure):
            return self.cured


class NewsSpread(Environment):
    ratio_dumb: probability = 1,
    ratio_herd: probability = 0,
    ratio_wise: probability = 0,
    prob_tv_spread: probability = 0.1,
    prob_neighbor_spread: probability = 0.1,
    prob_neighbor_cure: probability = 0.05,

    def init(self):
        self.populate_network([DumbViewer, HerdViewer, WiseViewer],
                              [self.ratio_dumb, self.ratio_herd, self.ratio_wise])


from itertools import product
from soil import Simulation


# We want to investigate the effect of different agent distributions on the spread of news.
# To do that, we will run different simulations, with a varying ratio of DumbViewers, HerdViewers, and WiseViewers
# Because the effect of these agents might also depend on the network structure, we will run our simulations on two different networks:
# one with a small-world structure and one with a connected structure.

counter = 0
for [r1, r2] in product([0, 0.5, 1.0], repeat=2):
    for (generator, netparams) in {
        "barabasi_albert_graph": {"m": 5},
        "erdos_renyi_graph": {"p": 0.1},
    }.items():
        print(r1, r2, 1-r1-r2, generator)
        # Create new simulation
        netparams["n"] = 500
        Simulation(
            name='newspread_sim',
            model=NewsSpread,
            parameters=dict(
                ratio_dumb=r1,
                ratio_herd=r2,
                ratio_wise=1-r1-r2,
                network_generator=generator,
                network_params=netparams,
                prob_neighbor_spread=0,
            ),
            iterations=5,
            max_steps=300,
            dump=False,
        ).run()
        counter += 1
        # Run all the necessary instances
 
print(f"A total of {counter} simulations were run.")