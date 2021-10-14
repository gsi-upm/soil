import random
from . import FSM, state, default_state


class BassModel(FSM):
    """
    Settings:
        innovation_prob
        imitation_prob
    """
    sentimentCorrelation = 0

    def step(self):
        self.behaviour()

    @default_state
    @state
    def innovation(self):
        if random.random() < self.innovation_prob:
            self.sentimentCorrelation = 1
            return self.aware
        else:
            aware_neighbors = self.get_neighboring_agents(state_id=self.aware.id)
            num_neighbors_aware = len(aware_neighbors)
            if random.random() < (self['imitation_prob']*num_neighbors_aware):
                self.sentimentCorrelation = 1
                return self.aware

    @state
    def aware(self):
        self.die()
