from mesa import batch_run, DataCollector, Agent, Model
from mesa.time import RandomActivation


class NoopAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_calls = 0

    def step(self):
        # import pdb;pdb.set_trace()
        self.num_calls += 1 


class NoopModel(Model):
    def __init__(self, N):
        super().__init__()
        self.schedule = RandomActivation(self)
        for i in range(N):
            self.schedule.add(NoopAgent(self.next_id(), self))
        self.datacollector = DataCollector(model_reporters={"num_agents": lambda m: m.schedule.get_agent_count(),
                                                            "time": lambda m: m.schedule.time},
                                           agent_reporters={"num_calls": "num_calls"})
        self.datacollector.collect(self)

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)


if __name__ == "__main__":
    from _config import *

    res = batch_run(model_cls=NoopModel,
                    max_steps=MAX_STEPS,
                    iterations=NUM_ITERS,
                    number_processes=1,
                    parameters={'N': NUM_AGENTS})
    total = sum(s["num_calls"] for s in res)
    total_agents = sum(s["num_agents"] for s in res)
    assert len(res) == NUM_AGENTS * NUM_ITERS
    assert total == NUM_AGENTS * NUM_ITERS * MAX_STEPS
    assert total_agents == NUM_AGENTS * NUM_AGENTS * NUM_ITERS

