import os

NUM_AGENTS = int(os.environ.get('NUM_AGENTS', 100))
NUM_ITERS = int(os.environ.get('NUM_ITERS', 10))
MAX_STEPS = int(os.environ.get('MAX_STEPS', 1000))


def run_sim(model, **kwargs):
    from soil import Simulation
    opts = dict(model=model,
                dump=False,
                num_processes=1,
                parameters={'num_nodes': NUM_AGENTS,
                            "avg_node_degree": 3,
                            "initial_outbreak_size": 5,
                            "virus_spread_chance": 0.25,
                            "virus_check_frequency": 0.25,
                            "recovery_chance": 0.3,
                            "gain_resistance_chance": 0.1,
                            },
                max_steps=MAX_STEPS,
                iterations=NUM_ITERS)
    opts.update(kwargs)
    its = Simulation(**opts).run()

    assert all(it.schedule.steps == MAX_STEPS for it in its)
    ratios = list(it.resistant_susceptible_ratio() for it in its)
    print("Max - Avg - Min ratio:", max(ratios), sum(ratios)/len(ratios), min(ratios))
    assert all(sum([it.number_susceptible,
                    it.number_infected,
                    it.number_resistant]) == NUM_AGENTS for it in its)
    return its