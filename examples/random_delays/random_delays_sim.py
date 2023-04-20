"""
Example of setting a 
Example of a fully programmatic simulation, without definition files.
"""
from soil import Simulation, agents, Environment
from soil.time import Delta


class MyAgent(agents.FSM):
    """
    An agent that first does a ping
    """

    defaults = {"pong_counts": 2}

    @agents.default_state
    @agents.state
    def ping(self):
        self.info("Ping")
        return self.pong, Delta(self.random.expovariate(1 / 16))

    @agents.state
    def pong(self):
        self.info("Pong")
        self.pong_counts -= 1
        self.info(str(self.pong_counts))
        if self.pong_counts < 1:
            return self.die()
        return None, Delta(self.random.expovariate(1 / 16))


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
