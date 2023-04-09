from unittest import TestCase
import os
from os.path import join
from glob import glob

from soil import  simulation, config, do_not_run

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, "..", "examples")

FORCE_TESTS = os.environ.get("FORCE_TESTS", "")


class TestExamples(TestCase):
    """Empty class that will be populated with auto-discovery tests for every example"""
    pass


def get_test_for_sim(sim, path):
    root = os.getcwd()
    iterations = sim.max_steps * sim.num_trials
    if iterations < 0 or iterations > 1000:
        sim.max_steps = 100
        sim.num_trials = 1

    def wrapped(self):
        envs = sim.run_simulation(dry_run=True)
        assert envs
        for env in envs:
            assert env
            try:
                n = sim.model_params["network_params"]["n"]
                assert len(list(env.network_agents)) == n
            except KeyError:
                pass
            assert env.schedule.steps > 0  # It has run
            assert env.schedule.steps <= sim.max_steps  # But not further than allowed

    return wrapped


def add_example_tests():
    sim_paths = []
    for path in glob(join(EXAMPLES, '**', '*.yml')):
        if "soil_output" in path:
            continue
        for sim in simulation.iter_from_config(path):
            sim_paths.append((sim, path))
    for path in glob(join(EXAMPLES, '**', '*_sim.py')):
        for sim in simulation.iter_from_py(path):
            sim_paths.append((sim, path))

    for (sim, path) in sim_paths:
        if sim.skip_test and not FORCE_TESTS:
            continue
        test_case = get_test_for_sim(sim, path)
        fname = os.path.basename(path)
        test_case.__name__ = "test_example_file_%s" % fname
        test_case.__doc__ = "%s should be a valid configuration" % fname
        setattr(TestExamples, test_case.__name__, test_case)
        del test_case


add_example_tests()
