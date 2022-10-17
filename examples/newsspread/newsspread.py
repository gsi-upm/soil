from soil.agents import FSM, NetworkAgent, state, default_state, prob
import logging


class DumbViewer(FSM, NetworkAgent):
    """
    A viewer that gets infected via TV (if it has one) and tries to infect
    its neighbors once it's infected.
    """

    prob_neighbor_spread = 0.5
    prob_tv_spread = 0.1
    has_been_infected = False

    @default_state
    @state
    def neutral(self):
        if self["has_tv"]:
            if self.prob(self.model["prob_tv_spread"]):
                return self.infected
        if self.has_been_infected:
            return self.infected

    @state
    def infected(self):
        for neighbor in self.get_neighbors(state_id=self.neutral.id):
            if self.prob(self.model["prob_neighbor_spread"]):
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
        prob_infect = self.model["prob_neighbor_spread"] * infected / total
        self.debug("prob_infect", prob_infect)
        if self.prob(prob_infect):
            self.has_been_infected = True


class WiseViewer(HerdViewer):
    """
    A viewer that can change its mind.
    """

    defaults = {
        "prob_neighbor_spread": 0.5,
        "prob_neighbor_cure": 0.25,
        "prob_tv_spread": 0.1,
    }

    @state
    def cured(self):
        prob_cure = self.model["prob_neighbor_cure"]
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
        prob_cure = self.model["prob_neighbor_cure"] * (cured / infected)
        if self.prob(prob_cure):
            return self.cured
