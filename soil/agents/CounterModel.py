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
        self.state['times'] = self.state.get('times', 0) + 1
        self.state['neighbors'] = neighbors
        self.state['total'] = total


class AggregatedCounter(BaseAgent):
    """
    Dummy behaviour. It counts the number of nodes in the network and neighbors
    in each step and adds it to its state.
    """

    def step(self):
        # Outside effects
        total = len(list(self.get_all_agents()))
        neighbors = len(list(self.get_neighboring_agents()))
        self.state['times'] = self.state.get('times', 0) + 1
        self.state['neighbors'] = self.state.get('neighbors', 0) + neighbors
        self.state['total'] = total = self.state.get('total', 0) + total
        self.debug('Running for step: {}. Total: {}'.format(self.now, total))
