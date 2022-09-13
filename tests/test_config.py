from unittest import TestCase
import os
from os.path import join

from soil import simulation, serialization, config, network

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')

FORCE_TESTS = os.environ.get('FORCE_TESTS', '')


class TestConfig(TestCase):

    def test_conversion(self):
        new = serialization.load_file(join(ROOT, "complete_converted.yml"))[0]
        old = serialization.load_file(join(ROOT, "old_complete.yml"))[0]
        converted_defaults = config.convert_old(old, strict=False)
        converted = converted_defaults.dict(skip_defaults=True)
        def isequal(old, new):
            if isinstance(old, dict):
                for (k, v) in old.items():
                    isequal(old[k], new[k])
                return
            assert old == new

        isequal(new, converted)

    def test_topology_config(self):
        netconfig = config.NetConfig(**{
            'path': join(ROOT, 'test.gexf')
        })
        net = network.from_config(netconfig, dir_path=ROOT)
        assert len(net.nodes) == 2
        assert len(net.edges) == 1

    def test_env_from_config(self):
        """
        Simple configuration that tests that the graph is loaded, and that
        network agents are initialized properly.
        """
        config = {
            'name': 'CounterAgent',
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'agent_type': 'CounterModel',
            # 'states': [{'times': 10}, {'times': 20}],
            'max_time': 2,
            'dry_run': True,
            'num_trials': 1,
            'environment_params': {
            }
        }
        s = simulation.from_old_config(config)
        env = s.get_env()
        assert len(env.topologies['default'].nodes) == 2
        assert len(env.topologies['default'].edges) == 1
        assert len(env.agents) == 2
        assert env.agents[0].topology == env.topologies['default']


def make_example_test(path, cfg):
    def wrapped(self):
        root = os.getcwd()
        print(path)
        s = simulation.from_config(cfg)
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
