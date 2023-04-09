from . import BaseAgent, NetworkAgent


class Ticker(BaseAgent):
    times = 0

    def step(self):
        self.times += 1

class CounterModel(NetworkAgent):
    """
    Dummy behaviour. It counts the number of nodes in the network and neighbors
    in each step and adds it to its state.
    """

    times = 0
    neighbors = 0
    total = 0

    def step(self):
        # Outside effects
        total = len(list(self.model.schedule._agents))
        neighbors = len(list(self.get_neighbors()))
        self["times"] = self.get("times", 0) + 1
        self["neighbors"] = neighbors
        self["total"] = total


class AggregatedCounter(NetworkAgent):
    """
    Dummy behaviour. It counts the number of nodes in the network and neighbors
    in each step and adds it to its state.
    """

    times = 0
    neighbors = 0
    total = 0

    def step(self):
        # Outside effects
        self["times"] += 1
        neighbors = len(list(self.get_neighbors()))
        self["neighbors"] += neighbors
        total = len(list(self.model.schedule.agents))
        self["total"] += total
        self.debug("Running for step: {}. Total: {}".format(self.now, total))
