"""
Example of a fully programmatic simulation, without definition files.
"""
from soil import Simulation, agents, Environment


class MyAgent(agents.FSM):
    """
    An agent that first does a ping
    """

    max_pongs = 2

    @agents.default_state
    @agents.state
    def ping(self):
        self.info("Ping")
        return self.pong.delay(self.random.expovariate(1 / 16))

    @agents.state
    def pong(self):
        self.info("Pong")
        self.max_pongs -= 1
        self.info(str(self.max_pongs), "pongs remaining")
        if self.max_pongs < 1:
            return self.die()
        return self.delay(self.random.expovariate(1 / 16))


class RandomEnv(Environment):

    def init(self):
        self.add_agent(agent_class=MyAgent)


s = Simulation(
    name="Programmatic",
    model=RandomEnv,
    iterations=1,
    max_time=100,
    dump=False,
)


envs = s.run()
