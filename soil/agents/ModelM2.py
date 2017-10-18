import random
import numpy as np
from . import BaseAgent


class SpreadModelM2(BaseAgent):
    """
    Settings:
        prob_neutral_making_denier

        prob_infect

        prob_cured_healing_infected

        prob_cured_vaccinate_neutral

        prob_vaccinated_healing_infected

        prob_vaccinated_vaccinate_neutral

        prob_generate_anti_rumor
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.prob_neutral_making_denier = np.random.normal(environment.environment_params['prob_neutral_making_denier'],
                                                           environment.environment_params['standard_variance'])

        self.prob_infect = np.random.normal(environment.environment_params['prob_infect'],
                                            environment.environment_params['standard_variance'])

        self.prob_cured_healing_infected = np.random.normal(environment.environment_params['prob_cured_healing_infected'],
                                                            environment.environment_params['standard_variance'])
        self.prob_cured_vaccinate_neutral = np.random.normal(environment.environment_params['prob_cured_vaccinate_neutral'],
                                                             environment.environment_params['standard_variance'])

        self.prob_vaccinated_healing_infected = np.random.normal(environment.environment_params['prob_vaccinated_healing_infected'],
                                                                 environment.environment_params['standard_variance'])
        self.prob_vaccinated_vaccinate_neutral = np.random.normal(environment.environment_params['prob_vaccinated_vaccinate_neutral'],
                                                                  environment.environment_params['standard_variance'])
        self.prob_generate_anti_rumor = np.random.normal(environment.environment_params['prob_generate_anti_rumor'],
                                                         environment.environment_params['standard_variance'])

    def step(self):

        if self.state['id'] == 0:  # Neutral
            self.neutral_behaviour()
        elif self.state['id'] == 1:  # Infected
            self.infected_behaviour()
        elif self.state['id'] == 2:  # Cured
            self.cured_behaviour()
        elif self.state['id'] == 3:  # Vaccinated
            self.vaccinated_behaviour()

    def neutral_behaviour(self):

        # Infected
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors) > 0:
            if random.random() < self.prob_neutral_making_denier:
                self.state['id'] = 3   # Vaccinated making denier

    def infected_behaviour(self):

        # Neutral
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_infect:
                neighbor.state['id'] = 1  # Infected

    def cured_behaviour(self):

        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured

    def vaccinated_behaviour(self):

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured

        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Generate anti-rumor
        infected_neighbors_2 = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors_2:
            if random.random() < self.prob_generate_anti_rumor:
                neighbor.state['id'] = 2  # Cured


class ControlModelM2(BaseAgent):
    """
    Settings:
        prob_neutral_making_denier

        prob_infect
        
        prob_cured_healing_infected
        
        prob_cured_vaccinate_neutral
        
        prob_vaccinated_healing_infected
        
        prob_vaccinated_vaccinate_neutral
        
        prob_generate_anti_rumor
    """


    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.prob_neutral_making_denier = np.random.normal(environment.environment_params['prob_neutral_making_denier'],
                                                           environment.environment_params['standard_variance'])

        self.prob_infect = np.random.normal(environment.environment_params['prob_infect'],
                                            environment.environment_params['standard_variance'])

        self.prob_cured_healing_infected = np.random.normal(environment.environment_params['prob_cured_healing_infected'],
                                                            environment.environment_params['standard_variance'])
        self.prob_cured_vaccinate_neutral = np.random.normal(environment.environment_params['prob_cured_vaccinate_neutral'],
                                                             environment.environment_params['standard_variance'])

        self.prob_vaccinated_healing_infected = np.random.normal(environment.environment_params['prob_vaccinated_healing_infected'],
                                                                 environment.environment_params['standard_variance'])
        self.prob_vaccinated_vaccinate_neutral = np.random.normal(environment.environment_params['prob_vaccinated_vaccinate_neutral'],
                                                                  environment.environment_params['standard_variance'])
        self.prob_generate_anti_rumor = np.random.normal(environment.environment_params['prob_generate_anti_rumor'],
                                                         environment.environment_params['standard_variance'])

    def step(self):

        if self.state['id'] == 0:  # Neutral
            self.neutral_behaviour()
        elif self.state['id'] == 1:  # Infected
            self.infected_behaviour()
        elif self.state['id'] == 2:  # Cured
            self.cured_behaviour()
        elif self.state['id'] == 3:  # Vaccinated
            self.vaccinated_behaviour()
        elif self.state['id'] == 4:  # Beacon-off
            self.beacon_off_behaviour()
        elif self.state['id'] == 5:  # Beacon-on
            self.beacon_on_behaviour()

    def neutral_behaviour(self):
        self.state['visible'] = False

        # Infected
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors) > 0:
            if random.random() < self.prob_neutral_making_denier:
                self.state['id'] = 3   # Vaccinated making denier

    def infected_behaviour(self):

        # Neutral
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_infect:
                neighbor.state['id'] = 1  # Infected
        self.state['visible'] = False

    def cured_behaviour(self):

        self.state['visible'] = True
        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured

    def vaccinated_behaviour(self):
        self.state['visible'] = True

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured

        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Generate anti-rumor
        infected_neighbors_2 = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors_2:
            if random.random() < self.prob_generate_anti_rumor:
                neighbor.state['id'] = 2  # Cured

    def beacon_off_behaviour(self):
        self.state['visible'] = False
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors) > 0:
            self.state['id'] == 5  # Beacon on

    def beacon_on_behaviour(self):
        self.state['visible'] = False
        # Cure (M2 feature added)
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_generate_anti_rumor:
                neighbor.state['id'] = 2  # Cured
            neutral_neighbors_infected = neighbor.get_neighboring_agents(state_id=0)
            for neighbor in neutral_neighbors_infected:
                if random.random() < self.prob_generate_anti_rumor:
                    neighbor.state['id'] = 3  # Vaccinated
            infected_neighbors_infected = neighbor.get_neighboring_agents(state_id=1)
            for neighbor in infected_neighbors_infected:
                if random.random() < self.prob_generate_anti_rumor:
                    neighbor.state['id'] = 2  # Cured

        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated
