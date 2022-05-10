from unittest import TestCase
import os
from os.path import join

from soil import serialization, config

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')

FORCE_TESTS = os.environ.get('FORCE_TESTS', '')


class TestConfig(TestCase):

    def test_conversion(self):
        new = serialization.load_file(join(EXAMPLES, "complete.yml"))[0]
        old = serialization.load_file(join(ROOT, "old_complete.yml"))[0]
        converted = config.convert_old(old).dict(skip_defaults=True)
        for (k, v) in new.items():
            assert v == converted[k]


def make_example_test(path, cfg):
    def wrapped(self):
        root = os.getcwd()
        s = config.Config(**cfg)
        import pdb;pdb.set_trace()
        # for s in simulation.all_from_config(path):
        #     iterations = s.config.max_time * s.config.num_trials
        #     if iterations > 1000:
        #         s.config.max_time = 100
        #         s.config.num_trials = 1
        #     if config.get('skip_test', False) and not FORCE_TESTS:
        #         self.skipTest('Example ignored.')
        #     envs = s.run_simulation(dry_run=True)
        #     assert envs
        #     for env in envs:
        #         assert env
        #         try:
        #             n = config['network_params']['n']
        #             assert len(list(env.network_agents)) == n
        #             assert env.now > 0  # It has run
        #             assert env.now <= config['max_time']  # But not further than allowed
        #         except KeyError:
        #             pass
    return wrapped


def add_example_tests():
    for config, path in serialization.load_files(
            join(EXAMPLES, '*', '*.yml'),
            join(EXAMPLES, '*.yml'),
    ):
        p = make_example_test(path=path, cfg=config)
        fname = os.path.basename(path)
        p.__name__ = 'test_example_file_%s' % fname
        p.__doc__ = '%s should be a valid configuration' % fname
        setattr(TestConfig, p.__name__, p)
        del p


add_example_tests()
