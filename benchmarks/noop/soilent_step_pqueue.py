from soil import BaseAgent, Environment, Simulation
from soil.time import SoilentPQueueActivation


class NoopAgent(BaseAgent):
    num_calls = 0

    def step(self):
        self.num_calls += 1

class NoopEnvironment(Environment):
    num_agents = 100
    schedule_class = SoilentPQueueActivation

    def init(self):
        self.add_agents(NoopAgent, k=self.num_agents)
        self.add_agent_reporter("num_calls")


if __name__ == "__main__":
    from _config import *
    res = run_sim(model=NoopEnvironment)
    for r in res:
        assert isinstance(r.schedule, SoilentPqueueActivation)
