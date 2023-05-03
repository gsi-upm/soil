from soil import BaseAgent, Environment, Simulation, PQueueActivation


class NoopAgent(BaseAgent):
    num_calls = 0

    def step(self):
        while True:
            self.num_calls += 1
            yield self.delay()


class NoopEnvironment(Environment):
    num_agents = 100
    schedule_class = PQueueActivation

    def init(self):
        self.add_agents(NoopAgent, k=self.num_agents)
        self.add_agent_reporter("num_calls")


if __name__ == "__main__":
    from _config import *

    run_sim(model=NoopEnvironment)
