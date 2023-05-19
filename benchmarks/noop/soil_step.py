from soil import Agent, Environment, Simulation


class NoopAgent(Agent):
    num_calls = 0

    def step(self):
        self.num_calls += 1

class NoopEnvironment(Environment):
    num_agents = 100

    def init(self):
        self.add_agents(NoopAgent, k=self.num_agents)
        self.add_agent_reporter("num_calls")


from _config import *

run_sim(model=NoopEnvironment)
