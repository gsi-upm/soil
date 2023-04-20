from soil import FSM, state, default_state, BaseAgent, NetworkAgent, Environment, Simulation
from soil.time import Delta
from enum import Enum
from collections import Counter
import logging
import math

from rabbits_basic_sim import RabbitEnv


class RabbitsImprovedEnv(RabbitEnv):
    def init(self):
        """Initialize the environment with the new versions of the agents"""
        a1 = self.add_node(Male)
        a2 = self.add_node(Female)
        a1.add_edge(a2)
        self.add_agent(RandomAccident)


class Rabbit(FSM, NetworkAgent):

    sexual_maturity = 30
    life_expectancy = 300
    birth = None

    @property
    def age(self):
        if self.birth is None:
            return None
        return self.now - self.birth

    @default_state
    @state
    def newborn(self):
        self.info("I am a newborn.")
        self.birth = self.now
        self.offspring = 0
        return self.youngling, Delta(self.sexual_maturity - self.age)

    @state
    def youngling(self):
        if self.age >= self.sexual_maturity:
            self.info(f"I am fertile! My age is {self.age}")
            return self.fertile

    @state
    def fertile(self):
        raise Exception("Each subclass should define its fertile state")

    @state
    def dead(self):
        self.die()


class Male(Rabbit):
    max_females = 5
    mating_prob = 0.001

    @state
    def fertile(self):
        if self.age > self.life_expectancy:
            return self.dead

        # Males try to mate
        for f in self.model.agents(
            agent_class=Female, state_id=Female.fertile.id, limit=self.max_females
        ):
            self.debug("FOUND A FEMALE: ", repr(f), self.mating_prob)
            if self.prob(self["mating_prob"]):
                f.impregnate(self)
                break  # Do not try to impregnate other females


class Female(Rabbit):
    gestation = 10
    conception = None

    @state
    def fertile(self):
        # Just wait for a Male
        if self.age > self.life_expectancy:
            return self.dead
        if self.conception is not None:
            return self.pregnant

    @property
    def pregnancy(self):
        if self.conception is None:
            return None
        return self.now - self.conception

    def impregnate(self, male):
        self.info(f"impregnated by {repr(male)}")
        self.mate = male
        self.conception = self.now
        self.number_of_babies = int(8 + 4 * self.random.random())

    @state
    def pregnant(self):
        self.debug("I am pregnant")

        if self.age > self.life_expectancy:
            self.info("Dying before giving birth")
            return self.die()

        if self.pregnancy >= self.gestation:
            self.info("Having {} babies".format(self.number_of_babies))
            for i in range(self.number_of_babies):
                state = {}
                agent_class = self.random.choice([Male, Female])
                child = self.model.add_node(agent_class=agent_class, **state)
                child.add_edge(self)
                if self.mate:
                    child.add_edge(self.mate)
                    self.mate.offspring += 1
                else:
                    self.debug("The father has passed away")

                self.offspring += 1
            self.mate = None
            return self.fertile

    def die(self):
        if self.pregnancy is not None:
            self.info("A mother has died carrying a baby!!")
        return super().die()


class RandomAccident(BaseAgent):
    def step(self):
        rabbits_alive = self.model.G.number_of_nodes()

        if not rabbits_alive:
            return self.die()

        prob_death = self.model.get("prob_death", 1e-100) * math.floor(
            math.log10(max(1, rabbits_alive))
        )
        self.debug("Killing some rabbits with prob={}!".format(prob_death))
        for i in self.iter_agents(agent_class=Rabbit):
            if i.state_id == i.dead.id:
                continue
            if self.prob(prob_death):
                self.info("I killed a rabbit: {}".format(i.id))
                rabbits_alive -= 1
                i.die()
        self.debug("Rabbits alive: {}".format(rabbits_alive))


sim = Simulation(model=RabbitsImprovedEnv, max_time=100, seed="MySeed", iterations=1)

if __name__ == "__main__":
    sim.run()
