from unittest import TestCase
from unittest.case import SkipTest

import os
from os.path import join
from glob import glob


from soil import  simulation

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, "..", "examples")

FORCE_TESTS = os.environ.get("FORCE_TESTS", "")


class TestExamples(TestCase):
    """Empty class that will be populated with auto-discovery tests for every example"""
    pass


def get_test_for_sims(sims, path):
    root = os.getcwd()

    def wrapped(self):
        run = False
        for sim in sims:
            if sim.skip_test and not FORCE_TESTS:
                continue
            run = True

            if sim.max_steps is None:
                sim.max_steps = 100

            iterations = sim.max_steps * sim.iterations
            if iterations < 0 or iterations > 1000:
                sim.max_steps = 100
                sim.iterations = 1

            envs = sim.run(dump=False)
            assert envs
            for env in envs:
                assert env
                assert env.now > 0
                try:
                    n = sim.parameters["network_params"]["n"]
                    assert len(list(env.network_agents)) == n
                except KeyError:
                    pass
                assert env.schedule.steps > 0  # It has run
                assert env.schedule.steps <= sim.max_steps  # But not further than allowed
        if not run:
            raise SkipTest("Example ignored because all simulations are set up to be skipped.")

    return wrapped


def add_example_tests():
    sim_paths = {}
    for path in glob(join(EXAMPLES, '**', '*.yml')):
        if "soil_output" in path:
            continue
        if path not in sim_paths:
            sim_paths[path] = []
        for sim in simulation.iter_from_config(path):
            sim_paths[path].append(sim)
    for path in glob(join(EXAMPLES, '**', '*_sim.py')):
        if path not in sim_paths:
            sim_paths[path] = []
        for sim in simulation.iter_from_py(path):
            sim_paths[path].append(sim)

    for (path, sims) in sim_paths.items():
        test_case = get_test_for_sims(sims, path)
        fname = os.path.basename(path)
        test_case.__name__ = "test_example_file_%s" % fname
        test_case.__doc__ = "%s should be a valid configuration" % fname
        setattr(TestExamples, test_case.__name__, test_case)
        del test_case


add_example_tests()
