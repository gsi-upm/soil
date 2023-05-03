from unittest import TestCase, skip
import os
import yaml
import copy
from os.path import join

from soil import simulation, serialization, config, network, agents, utils

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, "..", "examples")

FORCE_TESTS = os.environ.get("FORCE_TESTS", "")


def isequal(a, b):
    if isinstance(a, dict):
        for (k, v) in a.items():
            if v:
                isequal(a[k], b[k])
            else:
                assert not b.get(k, None)
        return
    assert a == b


# @skip("new versions of soil do not rely on configuration files")
class TestConfig(TestCase):

    def test_torvalds_config(self):
        sim = simulation.from_config(os.path.join(ROOT, "test_config.yml"))
        MAX_STEPS = 10
        assert sim.max_steps == MAX_STEPS
        envs = sim.run()
        assert len(envs) == 1
        env = envs[0]
        assert env.count_agents() == 3
        assert env.now == MAX_STEPS 


def make_example_test(path, cfg):
    def wrapped(self):
        root = os.getcwd()
        print(path)
        s = simulation.from_config(cfg)
        iterations = s.max_time * s.iterations
        if iterations > 1000:
            s.max_time = 100
            s.iterations = 1
        if cfg.skip_test and not FORCE_TESTS:
            self.skipTest('Example ignored.')
        envs = s.run_simulation(dump=False)
        assert envs
        for env in envs:
            assert env
            try:
                n = cfg.parameters['topology']['params']['n']
                assert len(list(env.network_agents)) == n
                assert env.now > 0  # It has run
                assert env.now <= cfg.max_time  # But not further than allowed
            except KeyError:
                pass

    return wrapped


def add_example_tests():
    for config, path in serialization.load_files(
        join(EXAMPLES, "*", "*.yml"),
        join(EXAMPLES, "*.yml"),
    ):
        p = make_example_test(path=path, cfg=config)
        fname = os.path.basename(path)
        p.__name__ = "test_example_file_%s" % fname
        p.__doc__ = "%s should be a valid configuration" % fname
        setattr(TestConfig, p.__name__, p)
        del p


add_example_tests()
