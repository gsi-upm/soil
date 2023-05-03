from mesa import batch_run, DataCollector, Agent, Model
from mesa.time import RandomActivation
from soil import Simulation
from _config import *


class NoopAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_calls = 0

    def step(self):
        # import pdb;pdb.set_trace()
        self.num_calls += 1 


class NoopModel(Model):
    def __init__(self, num_agents, *args, **kwargs):
        super().__init__()
        self.schedule = RandomActivation(self)
        for i in range(num_agents):
            self.schedule.add(NoopAgent(self.next_id(), self))
        self.datacollector = DataCollector(model_reporters={"num_agents": lambda m: m.schedule.get_agent_count(),
                                                            "time": lambda m: m.schedule.time},
                                           agent_reporters={"num_calls": "num_calls"})
        self.datacollector.collect(self)

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)


def run():
    run_sim(model=NoopModel)


if __name__ == "__main__":
    run()
