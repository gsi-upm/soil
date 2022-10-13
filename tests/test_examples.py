from unittest import TestCase
import os
from os.path import join

from soil import serialization, simulation, config

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')

FORCE_TESTS = os.environ.get('FORCE_TESTS', '')


class TestExamples(TestCase):
    pass


def make_example_test(path, cfg):
    def wrapped(self):
        root = os.getcwd()
        for s in simulation.iter_from_config(cfg):
            iterations = s.max_steps * s.num_trials
            if iterations < 0 or iterations > 1000:
                s.max_steps = 100
                s.num_trials = 1
            assert isinstance(cfg, config.Config)
            if getattr(cfg, 'skip_test', False) and not FORCE_TESTS:
                self.skipTest('Example ignored.')
            envs = s.run_simulation(dry_run=True)
            assert envs
            for env in envs:
                assert env
                try:
                    n = cfg.model_params['network_params']['n']
                    assert len(list(env.network_agents)) == n
                except KeyError:
                    pass
                assert env.schedule.steps > 0  # It has run
                assert env.schedule.steps <= s.max_steps  # But not further than allowed
    return wrapped


def add_example_tests():
    for cfg, path in serialization.load_files(
            join(EXAMPLES, '*', '*.yml'),
            join(EXAMPLES, '*.yml'),
    ):
        p = make_example_test(path=path, cfg=config.Config.from_raw(cfg))
        fname = os.path.basename(path)
        p.__name__ = 'test_example_file_%s' % fname
        p.__doc__ = '%s should be a valid configuration' % fname
        setattr(TestExamples, p.__name__, p)
        del p


add_example_tests()
