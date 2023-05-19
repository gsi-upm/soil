from soil import FSM, state, default_state, BaseAgent, NetworkAgent, Environment, report, parameters as params
import math


class RabbitEnv(Environment):
    prob_death: params.probability = 1e-3

    def init(self):
        a1 = self.add_node(Male)
        a2 = self.add_node(Female)
        a1.add_edge(a2)
        self.add_agent(RandomAccident)

    @report
    @property
    def num_rabbits(self):
        return self.count_agents(agent_class=Rabbit)

    @report
    @property
    def num_males(self):
        return self.count_agents(agent_class=Male)

    @report
    @property
    def num_females(self):
        return self.count_agents(agent_class=Female)


class Rabbit(NetworkAgent, FSM):

    sexual_maturity = 30
    life_expectancy = 300

    @default_state
    @state
    def newborn(self):
        self.debug("I am a newborn.")
        self.age = 0
        self.offspring = 0
        return self.youngling

    @state
    def youngling(self):
        self.age += 1
        if self.age >= self.sexual_maturity:
            self.debug(f"I am fertile! My age is {self.age}")
            return self.fertile

    @state
    def fertile(self):
        raise Exception("Each subclass should define its fertile state")

    @state
    def dead(self):
        self.die()


class Male(Rabbit):
    max_females = 5
    mating_prob = 0.005

    @state
    def fertile(self):
        self.age += 1

        if self.age > self.life_expectancy:
            return self.dead

        # Males try to mate
        for f in self.model.agents.filter(
            agent_class=Female, state_id=Female.fertile.id).limit(self.max_females):
            self.debug("FOUND A FEMALE: ", repr(f), self.mating_prob)
            if self.prob(self["mating_prob"]):
                f.impregnate(self)
                break  # Take a break


class Female(Rabbit):
    gestation = 10
    pregnancy = -1

    @state
    def fertile(self):
        # Just wait for a Male
        self.age += 1
        if self.age > self.life_expectancy:
            return self.dead
        if self.pregnancy >= 0:
            return self.pregnant

    def impregnate(self, male):
        self.debug(f"impregnated by {repr(male)}")
        self.mate = male
        self.pregnancy = 0
        self.number_of_babies = int(8 + 4 * self.random.random())

    @state
    def pregnant(self):
        self.debug("I am pregnant")
        self.age += 1

        if self.age >= self.life_expectancy:
            return self.die()

        if self.pregnancy < self.gestation:
            self.pregnancy += 1
            return

        self.debug("Having {} babies".format(self.number_of_babies))
        for i in range(self.number_of_babies):
            state = {}
            agent_class = self.random.choice([Male, Female])
            child = self.model.add_node(agent_class=agent_class, **state)
            child.add_edge(self)
            try:
                child.add_edge(self.mate)
                self.model.agents[self.mate].offspring += 1
            except ValueError:
                self.debug("The father has passed away")

            self.offspring += 1
        self.mate = None
        self.pregnancy = -1
        return self.fertile

    def die(self):
        if "pregnancy" in self and self["pregnancy"] > -1:
            self.debug("A mother has died carrying a baby!!")
        return super().die()


class RandomAccident(BaseAgent):
    prob_death = None
    def step(self):
        alive = self.get_agents(agent_class=Rabbit, alive=True)

        if not alive:
            return self.die("No more rabbits to kill")

        num_alive = len(alive)
        prob_death = min(1, self.prob_death * num_alive/10)
        self.debug("Killing some rabbits with prob={}!".format(prob_death))

        for i in alive:
            if i.state_id == i.dead.id:
                continue
            if self.prob(prob_death):
                self.debug("I killed a rabbit: {}".format(i.unique_id))
                num_alive -= 1
                self.model.remove_agent(i)
                i.alive = False
                i.killed = True
        self.debug("Rabbits alive: {}".format(num_alive))


RabbitEnv.run(max_time=1000, seed="MySeed", iterations=1)