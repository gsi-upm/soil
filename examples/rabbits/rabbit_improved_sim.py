from soil import Evented, FSM, state, default_state, BaseAgent, NetworkAgent, Environment, parameters, report, TimedOut
import math


class RabbitsImprovedEnv(Environment):
    prob_death: parameters.probability = 1e-3

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


class Rabbit(Evented, FSM, NetworkAgent):

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
        self.debug("I am a newborn.")
        self.birth = self.now
        self.offspring = 0
        return self.youngling

    @state
    async def youngling(self):
        self.debug("I am a youngling.")
        await self.delay(self.sexual_maturity - self.age)
        assert self.age >= self.sexual_maturity
        self.debug(f"I am fertile! My age is {self.age}")
        return self.fertile

    @state
    def fertile(self):
        raise Exception("Each subclass should define its fertile state")


class Male(Rabbit):
    max_females = 5
    mating_prob = 0.005

    @state
    def fertile(self):
        if self.age > self.life_expectancy:
            return self.die()

        # Males try to mate
        for f in self.model.agents(
            agent_class=Female, state_id=Female.fertile.id, limit=self.max_females
        ):
            self.debug(f"FOUND A FEMALE: {repr(f)}. Mating with prob {self.mating_prob}")
            if self.prob(self["mating_prob"]):
                f.tell(self.unique_id, sender=self, timeout=1)
                break  # Do not try to impregnate other females


class Female(Rabbit):
    gestation = 10
    conception = None

    @state
    async def fertile(self):
        # Just wait for a Male
        try:
            timeout = self.life_expectancy - self.age
            while timeout > 0:
                mates = await self.received(timeout=timeout)
                # assert self.age <= self.life_expectancy
                for mate in mates:
                    try:
                        male = self.model.agents[mate.payload]
                    except ValueError:
                        continue
                    self.debug(f"impregnated by {repr(male)}")
                    self.mate = male
                    self.number_of_babies = int(8 + 4 * self.random.random())
                    self.conception = self.now
                    return self.pregnant
        except TimedOut:
            pass
        return self.die()

    @state
    async def pregnant(self):
        self.debug("I am pregnant")
        # assert self.mate is not None

        when = min(self.gestation, self.life_expectancy - self.age)
        if when < 0:
            return self.die()
        await self.delay(when)

        if self.age > self.life_expectancy:
            self.debug("Dying before giving birth")
            return self.die()

        # assert self.now - self.conception >= self.gestation
        if not self.alive:
            return self.die()

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
        self.conception = None
        return self.fertile

    def die(self):
        if self.conception is not None:
            self.debug("A mother has died carrying a baby!!")
        return super().die()


class RandomAccident(BaseAgent):
    # Default value, but the value from the environment takes precedence
    prob_death = 1e-3

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
        self.debug("Rabbits alive: {}".format(num_alive))


RabbitsImprovedEnv.run(max_time=1000, seed="MySeed", iterations=1)
