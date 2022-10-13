from soil.agents import FSM, state, default_state, BaseAgent, NetworkAgent
from soil.time import Delta, When, NEVER
from enum import Enum
import logging
import math


class RabbitModel(FSM, NetworkAgent):

    mating_prob = 0.005
    offspring = 0
    birth = None

    sexual_maturity = 3
    life_expectancy = 30

    @default_state
    @state
    def newborn(self):
        self.birth = self.now
        self.info(f'I am a newborn.')
        self.model['rabbits_alive'] = self.model.get('rabbits_alive', 0) + 1

        # Here we can skip the `youngling` state by using a coroutine/generator. 
        while self.age < self.sexual_maturity:
            interval = self.sexual_maturity - self.age
            yield Delta(interval)

        self.info(f'I am fertile! My age is {self.age}')
        return self.fertile

    @property
    def age(self):
        return self.now - self.birth

    @state
    def fertile(self):
        raise Exception("Each subclass should define its fertile state")

    def step(self):
        super().step()
        if self.prob(self.age / self.life_expectancy):
            return self.die()


class Male(RabbitModel):

    max_females = 5

    @state
    def fertile(self):
        # Males try to mate
        for f in self.model.agents(agent_class=Female,
                                   state_id=Female.fertile.id,
                                   limit=self.max_females):
            self.debug('Found a female:', repr(f))
            if self.prob(self['mating_prob']):
                f.impregnate(self)
                break  # Take a break, don't try to impregnate the rest

            
class Female(RabbitModel):
    due_date = None
    age_of_pregnancy = None
    gestation = 10
    mate = None

    @state
    def fertile(self):
        return self.fertile, NEVER

    @state
    def pregnant(self):
        self.info('I am pregnant')
        if self.age > self.life_expectancy:
            return self.dead

        self.due_date = self.now + self.gestation

        number_of_babies = int(8+4*self.random.random())

        while self.now < self.due_date:
            yield When(self.due_date)

        self.info('Having {} babies'.format(number_of_babies))
        for i in range(number_of_babies):
            agent_class = self.random.choice([Male, Female])
            child = self.model.add_node(agent_class=agent_class,
                                        topology=self.topology)
            self.model.add_edge(self, child)
            self.model.add_edge(self.mate, child)
            self.offspring += 1
            self.model.agents[self.mate].offspring += 1
        self.mate = None
        self.due_date = None
        return self.fertile

    @state
    def dead(self):
        super().dead()
        if self.due_date is not None:
            self.info('A mother has died carrying a baby!!')

    def impregnate(self, male):
        self.info(f'{repr(male)} impregnating female {repr(self)}')
        self.mate = male
        self.set_state(self.pregnant, when=self.now)


class RandomAccident(BaseAgent):

    level = logging.INFO

    def step(self):
        rabbits_total = self.model.topology.number_of_nodes()
        if 'rabbits_alive' not in self.model:
            self.model['rabbits_alive'] = 0
        rabbits_alive = self.model.get('rabbits_alive', rabbits_total)
        prob_death = self.model.get('prob_death', 1e-100)*math.floor(math.log10(max(1, rabbits_alive)))
        self.debug('Killing some rabbits with prob={}!'.format(prob_death))
        for i in self.model.network_agents:
            if i.state.id == i.dead.id:
                continue
            if self.prob(prob_death):
                self.info('I killed a rabbit: {}'.format(i.id))
                rabbits_alive = self.model['rabbits_alive'] = rabbits_alive -1
                i.set_state(i.dead)
        self.debug('Rabbits alive: {}/{}'.format(rabbits_alive, rabbits_total))
        if self.model.count_agents(state_id=RabbitModel.dead.id) == self.model.topology.number_of_nodes():
            self.die()
