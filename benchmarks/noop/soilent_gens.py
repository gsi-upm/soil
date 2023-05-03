from soil import Agent, Environment, Simulation
from soilent import Scheduler


class NoopAgent(Agent):
    num_calls = 0

    def step(self):
        while True:
            self.num_calls += 1
            # yield self.delay(1)
            yield self.delay()

class NoopEnvironment(Environment):
    num_agents = 100
    schedule_class = Scheduler

    def init(self):
        self.add_agents(NoopAgent, k=self.num_agents)
        self.add_agent_reporter("num_calls")


if __name__ == "__main__":
    from _config import *

    res = run_sim(model=NoopEnvironment)
    for r in res:
        assert isinstance(r.schedule, Scheduler)
