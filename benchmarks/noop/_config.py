import os

NUM_AGENTS = int(os.environ.get('NUM_AGENTS', 100))
NUM_ITERS = int(os.environ.get('NUM_ITERS', 10))
MAX_STEPS = int(os.environ.get('MAX_STEPS', 1000))


def run_sim(model, **kwargs):
    from soil import Simulation
    opts = dict(model=model,
                dump=False,
                num_processes=1,
                parameters={'num_agents': NUM_AGENTS},
                seed="",
                max_steps=MAX_STEPS,
                iterations=NUM_ITERS)
    opts.update(kwargs)
    res = Simulation(**opts).run()

    total = sum(a.num_calls for e in res for a in e.schedule.agents)
    expected = NUM_AGENTS * NUM_ITERS * MAX_STEPS
    print(total)
    print(expected)

    assert total == expected
    return res
