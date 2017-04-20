import settings
import random
import numpy as np
from ..BaseBehaviour import *
from .. import init_states

settings.init()


class ControlModelM2(BaseBehaviour):
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

    # Init infected
    init_states[random.randint(0, settings.number_of_nodes-1)] = {'id':1}
    init_states[random.randint(0, settings.number_of_nodes-1)] = {'id':1}

    # Init beacons
    init_states[random.randint(0, settings.number_of_nodes-1)] = {'id': 4}
    init_states[random.randint(0, settings.number_of_nodes-1)] = {'id': 4}

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.prob_neutral_making_denier = np.random.normal(settings.prob_neutral_making_denier, settings.standard_variance)

        self.prob_infect = np.random.normal(settings.prob_infect, settings.standard_variance)

        self.prob_cured_healing_infected = np.random.normal(settings.prob_cured_healing_infected, settings.standard_variance)
        self.prob_cured_vaccinate_neutral = np.random.normal(settings.prob_cured_vaccinate_neutral, settings.standard_variance)

        self.prob_vaccinated_healing_infected = np.random.normal(settings.prob_vaccinated_healing_infected, settings.standard_variance)
        self.prob_vaccinated_vaccinate_neutral = np.random.normal(settings.prob_vaccinated_vaccinate_neutral, settings.standard_variance)
        self.prob_generate_anti_rumor = np.random.normal(settings.prob_generate_anti_rumor, settings.standard_variance)

    def step(self, now):

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

        self.attrs['status'] = self.state['id']
        super().step(now)

    def neutral_behaviour(self):

        # Infected
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors)>0:
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

    def beacon_off_behaviour(self):
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors) > 0:
            self.state['id'] == 5  # Beacon on

    def beacon_on_behaviour(self):

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
