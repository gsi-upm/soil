import random
import numpy as np
from . import FSM, state


class SISaModel(FSM):
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

        self.neutral_discontent_spon_prob = np.random.normal(environment.environment_params['neutral_discontent_spon_prob'],
                                                             environment.environment_params['standard_variance'])
        self.neutral_discontent_infected_prob = np.random.normal(environment.environment_params['neutral_discontent_infected_prob'],
                                                                 environment.environment_params['standard_variance'])
        self.neutral_content_spon_prob = np.random.normal(environment.environment_params['neutral_content_spon_prob'],
                                                          environment.environment_params['standard_variance'])
        self.neutral_content_infected_prob = np.random.normal(environment.environment_params['neutral_content_infected_prob'],
                                                              environment.environment_params['standard_variance'])

        self.discontent_neutral = np.random.normal(environment.environment_params['discontent_neutral'],
                                                   environment.environment_params['standard_variance'])
        self.discontent_content = np.random.normal(environment.environment_params['discontent_content'],
                                                   environment.environment_params['variance_d_c'])

        self.content_discontent = np.random.normal(environment.environment_params['content_discontent'],
                                                   environment.environment_params['variance_c_d'])
        self.content_neutral = np.random.normal(environment.environment_params['content_neutral'],
                                                environment.environment_params['standard_variance'])

    @state
    def neutral(self):
        # Spontaneous effects
        if random.random() < self.neutral_discontent_spon_prob:
            return self.discontent
        if random.random() < self.neutral_content_spon_prob:
            return self.content

        # Infected
        discontent_neighbors = self.count_neighboring_agents(state_id=self.discontent)
        if random.random() < discontent_neighbors * self.neutral_discontent_infected_prob:
            return self.discontent
        content_neighbors = self.count_neighboring_agents(state_id=self.content.id)
        if random.random() < content_neighbors * self.neutral_content_infected_prob:
            return self.content
        return self.neutral

    @state
    def discontent(self):
        # Healing
        if random.random() < self.discontent_neutral:
            return self.neutral

        # Superinfected
        content_neighbors = self.count_neighboring_agents(state_id=self.content.id)
        if random.random() < content_neighbors * self.discontent_content:
            return self.content
        return self.discontent

    @state
    def content(self):
        # Healing
        if random.random() < self.content_neutral:
            return self.neutral

        # Superinfected
        discontent_neighbors = self.count_neighboring_agents(state_id=self.discontent.id)
        if random.random() < discontent_neighbors * self.content_discontent:
            self.discontent
        return self.content
