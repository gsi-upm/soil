import logging
from soil.agents import NetworkAgent, FSM, state, default_state, BaseAgent
from enum import Enum
from random import random, choice
from itertools import islice

logger = logging.getLogger(__name__)

class Genders(Enum):
    male = 'male'
    female = 'female'


class RabbitModel(NetworkAgent, FSM):

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
    max_females = 10

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
        logger.debug('{} impregnating: {}. {}'.format(self.id, whom.id, whom.state))

    @state
    def pregnant(self):
        self['age'] += 1
        if self['age'] > self.life_expectancy:
            return self.dead

        self['pregnancy'] += 1
        logger.debug('Pregnancy: {}'.format(self['pregnancy']))
        if self['pregnancy'] >= self.gestation:

            state = {}
            state['gender'] = choice(list(Genders)).value
            child = self.env.add_node(self.__class__, state)
            self.env.add_edge(self.id, child.id)
            self.env.add_edge(self['mate'], child.id)
            # self.add_edge()
            logger.info("A rabbit has been born: {}. Total: {}".format(child.id, len(self.global_topology.nodes)))
            self['offspring'] += 1
            self.env.get_agent(self['mate'])['offspring'] += 1
            del self['mate']
            self['pregnancy'] = -1
            return self.fertile

    @state
    def dead(self):
        logger.info('Agent {} is dying'.format(self.id))
        if 'pregnancy' in self and self['pregnancy'] > -1:
            logger.info('A mother has died carrying a baby!: {}!'.format(self.state))
        self.die()
        return


class RandomAccident(BaseAgent):

    def step(self):
        logger.debug('Killing some rabbits!')
        prob_death = self.env.get('prob_death', -1)
        for i in self.env.network_agents:
            r = random()
            if r < prob_death:
                logger.info('I killed a rabbit: {}'.format(i.id))
                i.set_state(i.dead)
