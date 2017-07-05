import random
import numpy as np
from ..BaseBehaviour import *
import settings
import networkx as nx



POPULATION = 0
LEADERS = 1
HAVEN = 2
TRAININGENV = 3

NON_RADICAL = 0
NEUTRAL = 1
RADICAL = 2

POPNON =0
POPNE=1
POPRAD=2

HAVNON=3
HAVNE=4
HAVRAD=5

LEADER=6

TRAINING = 7


class TerroristModel(BaseBehaviour):
    num_agents = 0

    def __init__(self, environment=None, agent_id=0, state=()):

        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.population = settings.network_params["number_of_nodes"] * settings.environment_params['initial_population']
        self.havens = settings.network_params["number_of_nodes"] * settings.environment_params['initial_havens']
        self.training_enviroments = settings.network_params["number_of_nodes"] * settings.environment_params['initial_training_enviroments']

        self.initial_radicalism = settings.environment_params['initial_radicalism']
        self.information_spread_intensity = settings.environment_params['information_spread_intensity']
        self.influence = settings.environment_params['influence']
        self.relative_inequality = settings.environment_params['relative_inequality']
        self.additional_influence = settings.environment_params['additional_influence']

        if TerroristModel.num_agents < self.population:
            self.state['type'] = POPULATION
            TerroristModel.num_agents = TerroristModel.num_agents + 1
            random1 = random.random()
            if random1 < 0.7:
                self.state['id'] = NON_RADICAL
                self.state['fstatus'] = POPNON
            elif random1 >= 0.7 and random1 < 0.9:
                self.state['id'] = NEUTRAL
                self.state['fstatus'] = POPNE
            elif random1 >= 0.9:
                self.state['id'] = RADICAL
                self.state['fstatus'] = POPRAD

        elif TerroristModel.num_agents < self.havens + self.population:
            self.state['type'] = HAVEN
            TerroristModel.num_agents = TerroristModel.num_agents + 1
            random2 = random.random()
            random1 = random2 + self.initial_radicalism
            if random1 < 1.2:
                self.state['id'] = NON_RADICAL
                self.state['fstatus'] = HAVNON
            elif random1 >= 1.2 and random1 < 1.6:
                self.state['id'] = NEUTRAL
                self.state['fstatus'] = HAVNE
            elif random1 >= 1.6:
                self.state['id'] = RADICAL
                self.state['fstatus'] = HAVRAD

        elif TerroristModel.num_agents < self.training_enviroments + self.havens + self.population:
            self.state['type'] = TRAININGENV
            self.state['fstatus'] = TRAINING
            TerroristModel.num_agents = TerroristModel.num_agents + 1

    def step(self, now):
        if self.state['type'] == POPULATION:
            self.population_and_leader_conduct()
        if self.state['type'] == LEADERS:
            self.population_and_leader_conduct()
        if self.state['type'] == HAVEN:
            self.haven_conduct()
        if self.state['type'] == TRAININGENV:
            self.training_enviroment_conduct()

        self.attrs['status'] = self.state['id']
        self.attrs['type'] = self.state['type']
        self.attrs['radicalism'] = self.state['rad']
        self.attrs['fstatus'] = self.state['fstatus']
        super().step(now)

    def population_and_leader_conduct(self):
        if self.state['id'] == NON_RADICAL:
            if self.state['rad'] == 0.000:
                self.state['rad'] = self.set_radicalism()
            self.non_radical_behaviour()
        if self.state['id'] == NEUTRAL:
            if self.state['rad'] == 0.000:
                self.state['rad'] = self.set_radicalism()
            while self.state['id'] == RADICAL:
                self.radical_behaviour()
                break
            self.neutral_behaviour()
        if self.state['id'] == RADICAL:
            if self.state['rad'] == 0.000:
                self.state['rad'] = self.set_radicalism()
            self.radical_behaviour()

    def haven_conduct(self):
        non_radical_neighbors = self.get_neighboring_agents(state_id=NON_RADICAL)
        neutral_neighbors = self.get_neighboring_agents(state_id=NEUTRAL)
        radical_neighbors = self.get_neighboring_agents(state_id=RADICAL)

        neighbors_of_non_radical = len(neutral_neighbors) + len(radical_neighbors)
        neighbors_of_neutral = len(non_radical_neighbors) + len(radical_neighbors)
        neighbors_of_radical = len(non_radical_neighbors) + len(neutral_neighbors)
        threshold = 8
        if (len(non_radical_neighbors) > neighbors_of_non_radical) and len(non_radical_neighbors) >= threshold:
            self.state['id'] = NON_RADICAL
        elif (len(neutral_neighbors) > neighbors_of_neutral) and len(neutral_neighbors) >= threshold:
            self.state['id'] = NEUTRAL
        elif (len(radical_neighbors) > neighbors_of_radical) and len(radical_neighbors) >= threshold:
            self.state['id'] = RADICAL

        if self.state['id'] == NEUTRAL:
            for neighbor in non_radical_neighbors:
                neighbor.state['rad'] = neighbor.state['rad'] + (self.influence + self.additional_influence) * self.information_spread_intensity
                if neighbor.state['rad'] >= 0.3 and neighbor.state['rad'] <= 0.59:
                    neighbor.state['id'] = NEUTRAL
                    if neighbor.state['type'] == POPULATION:
                        neighbor.state['fstatus'] = POPNE
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVNE
                elif neighbor.state['rad'] > 0.59:
                    neighbor.state['rad'] = 0.59
                    neighbor.state['id'] = NEUTRAL
                    if neighbor.state['type'] == POPULATION:
                        neighbor.state['fstatus'] = POPNE
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVNE

        if self.state['id'] == RADICAL:

            for neighbor in non_radical_neighbors:
                neighbor.state['rad'] = neighbor.state['rad'] + (self.influence + self.additional_influence) * self.information_spread_intensity
                if neighbor.state['rad'] >= 0.3 and neighbor.state['rad'] <= 0.59:
                    neighbor.state['id'] = NEUTRAL
                    if neighbor.state['type'] == POPULATION:
                        neighbor.state['fstatus'] = POPNE
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVNE
                elif neighbor.state['rad'] > 0.59:
                    neighbor.state['rad'] = 0.59
                    neighbor.state['id'] = NEUTRAL
                    if neighbor.state['type'] == POPULATION:
                        neighbor.state['fstatus'] = POPNE
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVNE

            for neighbor in neutral_neighbors:
                neighbor.state['rad'] = neighbor.state['rad'] + (self.influence + self.additional_influence) * self.information_spread_intensity
                if neighbor.state['rad'] >= 0.6:
                    neighbor.state['id'] = RADICAL
                    if neighbor.state['type'] != HAVEN and neighbor.state['type']!=TRAININGENV:
                        if neighbor.state['rad'] >= 0.62:
                            if create_leader(neighbor):
                                neighbor.state['type'] = LEADERS
                                neighbor.state['fstatus'] = LEADER
                            # elif neighbor.state['type'] == LEADERS:
                            #     neighbor.state['type'] = POPULATION
                            #     neighbor.state['fstatus'] = POPRAD
                            elif neighbor.state['type'] == POPULATION:
                                neighbor.state['fstatus'] = POPRAD
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVRAD

    def training_enviroment_conduct(self):
        self.state['id'] = RADICAL
        self.state['rad'] = 1
        neighbors = self.get_neighboring_agents()
        for neighbor in neighbors:
            if neighbor.state['id'] == NON_RADICAL:
                neighbor.state['rad'] = neighbor.state['rad'] + (self.influence + self.additional_influence) * self.information_spread_intensity
                if neighbor.state['rad'] >= 0.3 and self.state['rad'] <= 0.59:
                    neighbor.state['id'] = NEUTRAL
                    if neighbor.state['type'] == POPULATION:
                        neighbor.state['fstatus'] = POPNE
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVNE
                elif neighbor.state['rad'] > 0.59:
                    neighbor.state['rad'] = 0.59
                    neighbor.state['id'] = NEUTRAL
                    if neighbor.state['type'] == POPULATION:
                        neighbor.state['fstatus'] = POPNE
                    elif neighbor.state['type'] == HAVEN:
                        neighbor.state['fstatus'] = HAVNE


            neighbor.state['rad'] = neighbor.state['rad'] + (neighbor.influence + neighbor.additional_influence) * neighbor.information_spread_intensity
            if neighbor.state['rad'] >= 0.3 and neighbor.state['rad'] <= 0.59:
                neighbor.state['id'] = NEUTRAL
                if neighbor.state['type'] == POPULATION:
                    neighbor.state['fstatus'] = POPNE
                elif neighbor.state['type'] == HAVEN:
                    neighbor.state['fstatus'] = HAVNE
            elif neighbor.state['rad'] >= 0.6:
                neighbor.state['id'] = RADICAL
                if neighbor.state['type'] != HAVEN and neighbor.state['type'] != TRAININGENV:
                    if neighbor.state['rad'] >= 0.62:
                        if create_leader(neighbor):
                            neighbor.state['type'] = LEADERS
                            neighbor.state['fstatus'] = LEADER
                        # elif neighbor.state['type'] == LEADERS:
                        #     neighbor.state['type'] = POPULATION
                        #     neighbor.state['fstatus'] = POPRAD
                        elif neighbor.state['type'] == POPULATION:
                            neighbor.state['fstatus'] = POPRAD
                elif neighbor.state['type'] == HAVEN:
                    neighbor.state['fstatus'] = HAVRAD

    def non_radical_behaviour(self):
        neighbors = self.get_neighboring_agents()

        for neighbor in neighbors:
            if neighbor.state['type'] == POPULATION:
                if neighbor.state['id'] == NEUTRAL or neighbor.state['id'] == RADICAL:
                    self.state['rad'] = self.state['rad'] + self.influence * self.information_spread_intensity
                    if self.state['rad'] >= 0.3 and self.state['rad'] <= 0.59:
                        self.state['id'] = NEUTRAL

                        if self.state['type']==POPULATION:
                            self.state['fstatus'] = POPNE
                        elif self.state['type'] == HAVEN:
                            self.state['fstatus'] = HAVNE
                    elif self.state['rad'] > 0.59:
                        self.state['rad'] = 0.59
                        self.state['id'] = NEUTRAL
                        if self.state['type']==POPULATION:
                            self.state['fstatus'] = POPNE
                        elif self.state['type'] == HAVEN:
                            self.state['fstatus'] = HAVNE

            elif neighbor.state['type'] == LEADERS:

                if neighbor.state['id'] == NEUTRAL or neighbor.state['id'] == RADICAL:
                    self.state['rad'] = self.state['rad'] + (self.influence + self.additional_influence) * self.information_spread_intensity
                    if self.state['rad'] >= 0.3 and self.state['rad'] <= 0.59:
                        self.state['id'] = NEUTRAL
                        if self.state['type']==POPULATION:
                            self.state['fstatus'] = POPNE
                        elif self.state['type'] == HAVEN:
                            self.state['fstatus'] = HAVNE
                    elif self.state['rad'] > 0.59:
                        self.state['rad'] = 0.59
                        self.state['id'] = NEUTRAL
                        if self.state['type']==POPULATION:
                            self.state['fstatus'] = POPNE
                        elif self.state['type'] == HAVEN:
                            self.state['fstatus'] = HAVNE


    def neutral_behaviour(self):
        neighbors = self.get_neighboring_agents()
        for neighbor in neighbors:
            if neighbor.state['type'] == POPULATION:
                if neighbor.state['id'] == RADICAL:
                    self.state['rad'] = self.state['rad'] + self.influence * self.information_spread_intensity
                    if self.state['rad'] >= 0.6:
                        self.state['id'] = RADICAL
                        if self.state['type'] != HAVEN:
                            if self.state['rad'] >= 0.62:
                                if create_leader(self):
                                    self.state['type'] = LEADERS

                                    self.state['fstatus'] = LEADER
                                # elif self.state['type'] == LEADERS:
                                #     self.state['type'] = POPULATION
                                #     self.state['fstatus'] = POPRAD
                                elif neighbor.state['type'] == POPULATION:
                                    self.state['fstatus'] = POPRAD
                        elif self.state['type'] == HAVEN:
                            self.state['fstatus'] = HAVRAD


            elif neighbor.state['type'] == LEADERS:
                if neighbor.state['id'] == RADICAL:
                    self.state['rad'] = self.state['rad'] + (self.influence + self.additional_influence) * self.information_spread_intensity
                    if self.state['rad'] >= 0.6:
                        self.state['id'] = RADICAL
                        if self.state['type'] != HAVEN:
                            if self.state['rad'] >= 0.62:
                                if create_leader(self):
                                    self.state['type'] = LEADERS
                                    self.state['fstatus'] = LEADER
                                # elif self.state['type'] == LEADERS:
                                #     self.state['type'] = POPULATION
                                #     self.state['fstatus'] = POPRAD
                                elif neighbor.state['type'] == POPULATION:
                                    self.state['fstatus'] = POPRAD
                        elif self.state['type'] == HAVEN:
                            self.state['fstatus'] = HAVRAD





    def radical_behaviour(self):
        neighbors = self.get_neighboring_agents(state_id=RADICAL)

        for neighbor in neighbors:
            if self.state['rad']< neighbor.state['rad'] and self.state['type']== LEADERS and neighbor.state['type']==LEADERS:
                self.state['type'] = POPULATION
                self.state['fstatus'] = POPRAD


    def set_radicalism(self):
        if self.state['id'] == NON_RADICAL:
            radicalism = random.uniform(0.0, 0.29) * self.relative_inequality
            return radicalism
        elif self.state['id'] == NEUTRAL:
            radicalism = 0.3 + random.uniform(0.3, 0.59) * self.relative_inequality
            if radicalism >= 0.6:
                self.state['id'] = RADICAL
            return radicalism
        elif self.state['id'] == RADICAL:
            radicalism = 0.6 + random.uniform(0.6, 1.0) * self.relative_inequality
            return radicalism

def get_partition(agent):
    return settings.partition_param[agent.id]

def get_centrality(agent):
    return settings.centrality_param[agent.id]
def get_centrality_given_id(id):
    return settings.centrality_param[id]

def get_leader(partition):
    if not bool(settings.leaders) or partition not in settings.leaders.keys():
        return None
    return settings.leaders[partition]

def set_leader(partition, agent):
    settings.leaders[partition] = agent.id

def create_leader(agent):
    my_partition = get_partition(agent)
    old_leader = get_leader(my_partition)

    if old_leader == None:
        set_leader(my_partition, agent)
        return True
    else:
        my_centrality = get_centrality(agent)
        old_leader_centrality = get_centrality_given_id(old_leader)
        if my_centrality > old_leader_centrality:
            set_leader(my_partition, agent)
            return True
        return False



