import random
from . import BaseAgent


class IndependentCascadeModel(BaseAgent):
    """
    Settings:
        innovation_prob

        imitation_prob
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.innovation_prob = environment.environment_params['innovation_prob']
        self.imitation_prob = environment.environment_params['imitation_prob']
        self.state['time_awareness'] = 0
        self.state['sentimentCorrelation'] = 0

    def step(self):
        self.behaviour()

    def behaviour(self):
        aware_neighbors_1_time_step = []
        # Outside effects
        if random.random() < self.innovation_prob:
            if self.state['id'] == 0:
                self.state['id'] = 1
                self.state['sentimentCorrelation'] = 1
                self.state['time_awareness'] = self.env.now  # To know when they have been infected
            else:
                pass

            return

        # Imitation effects
        if self.state['id'] == 0:
            aware_neighbors = self.get_neighboring_agents(state_id=1)
            for x in aware_neighbors:
                if x.state['time_awareness'] == (self.env.now-1):
                    aware_neighbors_1_time_step.append(x)
            num_neighbors_aware = len(aware_neighbors_1_time_step)
            if random.random() < (self.imitation_prob*num_neighbors_aware):
                self.state['id'] = 1
                self.state['sentimentCorrelation'] = 1
            else:
                pass

            return
