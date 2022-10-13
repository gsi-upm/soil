from soil.agents import FSM, state, default_state, BaseAgent, NetworkAgent
from soil.time import Delta
from enum import Enum
from collections import Counter
import logging
import math


class RabbitModel(FSM, NetworkAgent):

    sexual_maturity = 30
    life_expectancy = 300

    @default_state
    @state
    def newborn(self):
        self.info('I am a newborn.')
        self.age = 0
        self.offspring = 0
        return self.youngling

    @state
    def youngling(self):
        self.age += 1
        if self.age >= self.sexual_maturity:
            self.info(f'I am fertile! My age is {self.age}')
            return self.fertile

    @state
    def fertile(self):
        raise Exception("Each subclass should define its fertile state")

    @state
    def dead(self):
        self.die()


class Male(RabbitModel):
    max_females = 5
    mating_prob = 0.001

    @state
    def fertile(self):
        self.age += 1

        if self.age > self.life_expectancy:
            return self.dead

        # Males try to mate
        for f in self.model.agents(agent_class=Female,
                                   state_id=Female.fertile.id,
                                   limit=self.max_females):
            self.debug('FOUND A FEMALE: ', repr(f), self.mating_prob)
            if self.prob(self['mating_prob']):
                f.impregnate(self)
                break  # Take a break


class Female(RabbitModel):
    gestation = 100

    @state
    def fertile(self):
        # Just wait for a Male
        self.age += 1
        if self.age > self.life_expectancy:
            return self.dead

    def impregnate(self, male):
        self.info(f'{repr(male)} impregnating female {repr(self)}')
        self.mate = male
        self.pregnancy = -1
        self.set_state(self.pregnant, when=self.now)
        self.number_of_babies = int(8+4*self.random.random())
        self.debug('I am pregnant')

    @state
    def pregnant(self):
        self.age += 1
        self.pregnancy += 1

        if self.prob(self.age / self.life_expectancy):
            return self.die()

        if self.pregnancy >= self.gestation:
            self.info('Having {} babies'.format(self.number_of_babies))
            for i in range(self.number_of_babies):
                state = {}
                agent_class = self.random.choice([Male, Female])
                child = self.model.add_node(agent_class=agent_class,
                                            topology=self.topology,
                                            **state)
                child.add_edge(self)
                try:
                    child.add_edge(self.mate)
                    self.model.agents[self.mate].offspring += 1
                except ValueError:
                    self.debug('The father has passed away')

                self.offspring += 1
            self.mate = None
            return self.fertile

    @state
    def dead(self):
        super().dead()
        if 'pregnancy' in self and self['pregnancy'] > -1:
            self.info('A mother has died carrying a baby!!')


class RandomAccident(BaseAgent):

    level = logging.INFO

    def step(self):
        rabbits_alive = self.model.topology.number_of_nodes()

        if not rabbits_alive:
            return self.die()

        prob_death = self.model.get('prob_death', 1e-100)*math.floor(math.log10(max(1, rabbits_alive)))
        self.debug('Killing some rabbits with prob={}!'.format(prob_death))
        for i in self.iter_agents(agent_class=RabbitModel):
            if i.state.id == i.dead.id:
                continue
            if self.prob(prob_death):
                self.info('I killed a rabbit: {}'.format(i.id))
                rabbits_alive -= 1
                i.set_state(i.dead)
        self.debug('Rabbits alive: {}'.format(rabbits_alive))
