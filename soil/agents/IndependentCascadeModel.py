from . import Agent, state, default_state


class IndependentCascadeModel(Agent):
    """
    Settings:
        innovation_prob

        imitation_prob
    """

    time_awareness = 0
    sentimentCorrelation = 0

    # Outside effects
    @default_state
    @state
    def outside(self):
        if self.prob(self.model.innovation_prob):
            self.sentimentCorrelation = 1
            self.time_awareness = self.model.now # To know when they have been infected
            return self.imitate

    @state
    def imitate(self):
        aware_neighbors = self.get_neighbors(state_id=1, time_awareness=self.now-1)

        if self.prob(self.model.imitation_prob * len(aware_neighbors)):
            self.sentimentCorrelation = 1
            return self.outside