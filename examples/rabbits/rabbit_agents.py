from soil.agents import FSM, state, default_state, BaseAgent, NetworkAgent
from enum import Enum
from random import random, choice
from itertools import islice
import logging
import math


class Genders(Enum):
    male = 'male'
    female = 'female'


class RabbitModel(FSM):

    level = logging.INFO

    defaults = {
        'age': 0,
        'gender': Genders.male.value,
        'mating_prob': 0.001,
        'offspring': 0,
    }

    sexual_maturity = 4*30
    life_expectancy = 365 * 3
    gestation = 33
    pregnancy = -1
    max_females = 5

    @default_state
    @state
    def newborn(self):
        self['age'] += 1

        if self['age'] >= self.sexual_maturity:
            return self.fertile

    @state
    def fertile(self):
        self['age'] += 1
        if self['age'] > self.life_expectancy:
            return self.dead

        if self['gender'] == Genders.female.value:
            return

        # Males try to mate
        females = self.get_agents(state_id=self.fertile.id, gender=Genders.female.value, limit_neighbors=False)
        for f in islice(females, self.max_females):
            r = random()
            if r < self['mating_prob']:
                self.impregnate(f)
                break # Take a break

    def impregnate(self, whom):
        if self['gender'] == Genders.female.value:
            raise NotImplementedError('Females cannot impregnate')
        whom['pregnancy'] = 0
        whom['mate'] = self.id
        whom.set_state(whom.pregnant)
        self.debug('{} impregnating: {}. {}'.format(self.id, whom.id, whom.state))

    @state
    def pregnant(self):
        self['age'] += 1
        if self['age'] > self.life_expectancy:
            return self.dead

        self['pregnancy'] += 1
        self.debug('Pregnancy: {}'.format(self['pregnancy']))
        if self['pregnancy'] >= self.gestation:
            number_of_babies = int(8+4*random())
            self.info('Having {} babies'.format(number_of_babies))
            for i in range(number_of_babies):
                state = {}
                state['gender'] = choice(list(Genders)).value
                child = self.env.add_node(self.__class__, state)
                self.env.add_edge(self.id, child.id)
                self.env.add_edge(self['mate'], child.id)
                # self.add_edge()
                self.debug('A BABY IS COMING TO LIFE')
                self.env['rabbits_alive'] = self.env.get('rabbits_alive', self.topology.number_of_nodes())+1
                self.debug('Rabbits alive: {}'.format(self.env['rabbits_alive']))
                self['offspring'] += 1
                self.env.get_agent(self['mate'])['offspring'] += 1
            del self['mate']
            self['pregnancy'] = -1
            return self.fertile

    @state
    def dead(self):
        self.info('Agent {} is dying'.format(self.id))
        if 'pregnancy' in self and self['pregnancy'] > -1:
            self.info('A mother has died carrying a baby!!')
        self.die()
        return


class RandomAccident(NetworkAgent):

    level = logging.DEBUG

    def step(self):
        rabbits_total = self.topology.number_of_nodes()
        if 'rabbits_alive' not in self.env:
            self.env['rabbits_alive'] = 0
        rabbits_alive = self.env.get('rabbits_alive', rabbits_total)
        prob_death = self.env.get('prob_death', 1e-100)*math.floor(math.log10(max(1, rabbits_alive)))
        self.debug('Killing some rabbits with prob={}!'.format(prob_death))
        for i in self.env.network_agents:
            if i.state['id'] == i.dead.id:
                continue
            r = random()
            if r < prob_death:
                self.debug('I killed a rabbit: {}'.format(i.id))
                rabbits_alive = self.env['rabbits_alive'] = rabbits_alive -1
                self.log('Rabbits alive: {}'.format(self.env['rabbits_alive']))
                i.set_state(i.dead)
        self.log('Rabbits alive: {}/{}'.format(rabbits_alive, rabbits_total))
        if self.count_agents(state_id=RabbitModel.dead.id) == self.topology.number_of_nodes():
            self.die()
