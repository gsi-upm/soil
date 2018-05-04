from . import BaseAgent


class CounterModel(BaseAgent):
    """
    Dummy behaviour. It counts the number of nodes in the network and neighbors
    in each step and adds it to its state.
    """

    def step(self):
        # Outside effects
        total = len(list(self.get_all_agents()))
        neighbors = len(list(self.get_neighboring_agents()))
        self['times'] = self.get('times', 0) + 1
        self['neighbors'] = neighbors
        self['total'] = total


class AggregatedCounter(BaseAgent):
    """
    Dummy behaviour. It counts the number of nodes in the network and neighbors
    in each step and adds it to its state.
    """

    def step(self):
        # Outside effects
        total = len(list(self.get_all_agents()))
        neighbors = len(list(self.get_neighboring_agents()))
        self['times'] = self.get('times', 0) + 1
        self['neighbors'] = self.get('neighbors', 0) + neighbors
        self['total'] = total = self.get('total', 0) + total
        self.debug('Running for step: {}. Total: {}'.format(self.now, total))
