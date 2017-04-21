import random
import numpy as np
from models.BaseBehaviour import *


class SISaModel(BaseBehaviour):
    """
    Settings:
        neutral_discontent_spon_prob
        
        neutral_discontent_infected_prob
        
        neutral_content_spong_prob
        
        neutral_content_infected_prob
        
        discontent_neutral
        
        discontent_content
        
        variance_d_c
        
        content_discontent
        
        variance_c_d
        
        content_neutral
        
        standard_variance
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.neutral_discontent_spon_prob = np.random.normal(environment.neutral_discontent_spon_prob,
                                                             environment.standard_variance)
        self.neutral_discontent_infected_prob = np.random.normal(environment.neutral_discontent_infected_prob,
                                                                 environment.standard_variance)
        self.neutral_content_spon_prob = np.random.normal(environment.neutral_content_spon_prob,
                                                          environment.standard_variance)
        self.neutral_content_infected_prob = np.random.normal(environment.neutral_content_infected_prob,
                                                              environment.standard_variance)

        self.discontent_neutral = np.random.normal(environment.discontent_neutral, environment.standard_variance)
        self.discontent_content = np.random.normal(environment.discontent_content, environment.variance_d_c)

        self.content_discontent = np.random.normal(environment.content_discontent, environment.variance_c_d)
        self.content_neutral = np.random.normal(environment.content_neutral, environment.standard_variance)

    def step(self, now):
        if self.state['id'] == 0:
            self.neutral_behaviour()
        if self.state['id'] == 1:
            self.discontent_behaviour()
        if self.state['id'] == 2:
            self.content_behaviour()

        self.attrs['status'] = self.state['id']
        super().step(now)

    def neutral_behaviour(self):
        # Spontaneous effects
        if random.random() < self.neutral_discontent_spon_prob:
            self.state['id'] = 1
        if random.random() < self.neutral_content_spon_prob:
            self.state['id'] = 2

        # Infected
        discontent_neighbors = self.get_neighboring_agents(state_id=1)
        if random.random() < len(discontent_neighbors) * self.neutral_discontent_infected_prob:
            self.state['id'] = 1
        content_neighbors = self.get_neighboring_agents(state_id=2)
        if random.random() < len(content_neighbors) * self.neutral_content_infected_prob:
            self.state['id'] = 2

    def discontent_behaviour(self):
        # Healing
        if random.random() < self.discontent_neutral:
            self.state['id'] = 0

        # Superinfected
        content_neighbors = self.get_neighboring_agents(state_id=2)
        if random.random() < len(content_neighbors) * self.discontent_content:
            self.state['id'] = 2

    def content_behaviour(self):
        # Healing
        if random.random() < self.content_neutral:
            self.state['id'] = 0

        # Superinfected
        discontent_neighbors = self.get_neighboring_agents(state_id=1)
        if random.random() < len(discontent_neighbors) * self.content_discontent:
            self.state['id'] = 1
