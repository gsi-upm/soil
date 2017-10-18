import random
from . import BaseAgent


class BassModel(BaseAgent):
    """
    Settings:
        innovation_prob
        imitation_prob
    """

    def __init__(self, environment, agent_id, state):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        env_params = environment.environment_params
        self.state['sentimentCorrelation'] = 0

    def step(self):
        self.behaviour()

    def behaviour(self):
        # Outside effects
        if random.random() < self.state_params['innovation_prob']:
            if self.state['id'] == 0:
                self.state['id'] = 1
                self.state['sentimentCorrelation'] = 1
            else:
                pass

            return

        # Imitation effects
        if self.state['id'] == 0:
            aware_neighbors = self.get_neighboring_agents(state_id=1)
            num_neighbors_aware = len(aware_neighbors)
            if random.random() < (self.state_params['imitation_prob']*num_neighbors_aware):
                self.state['id'] = 1
                self.state['sentimentCorrelation'] = 1

            else:
                pass
