from unittest import TestCase
import os
from os.path import join

from soil import utils, simulation

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')


class TestExamples(TestCase):
    pass


def make_example_test(path, config):
    def wrapped(self):
        root = os.getcwd()
        os.chdir(os.path.dirname(path))
        s = simulation.from_config(config)
        envs = s.run_simulation(dry_run=True)
        assert envs
        for env in envs:
            assert env
            try:
                n = config['network_params']['n']
                assert len(list(env.network_agents)) == n
                assert env.now > 2  # It has run
                assert env.now <= config['max_time']  # But not further than allowed
            except KeyError:
                pass
        os.chdir(root)
    return wrapped


def add_example_tests():
    for config, path in utils.load_config(join(EXAMPLES, '**', '*.yml')):
        p = make_example_test(path=path, config=config)
        fname = os.path.basename(path)
        p.__name__ = 'test_example_file_%s' % fname
        p.__doc__ = '%s should be a valid configuration' % fname
        setattr(TestExamples, p.__name__, p)
        del p


add_example_tests()
