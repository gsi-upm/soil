from unittest import TestCase

import os
import yaml
from functools import partial

from os.path import join
from soil import simulation, environment, agents, utils


ROOT = os.path.abspath(os.path.dirname(__file__))

EXAMPLES = join(ROOT, '..', 'examples')


class TestMain(TestCase):

    def test_load_graph(self):
        """
        Load a graph from file if the extension is known.
        Raise an exception otherwise.
        """
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            }
        }
        G = utils.load_network(config['network_params'])
        assert G
        assert len(G) == 2
        with self.assertRaises(AttributeError):
            config = {
                'network_params': {
                    'path': join(ROOT, 'unknown.extension')
                }
            }
            G = utils.load_network(config['network_params'])
            print(G)

    def test_generate_barabasi(self):
        """
        If no path is given, a generator and network parameters
        should be used to generate a network
        """
        config = {
            'network_params': {
                'generator': 'barabasi_albert_graph'
            }
        }
        with self.assertRaises(TypeError):
            G = utils.load_network(config['network_params'])
        config['network_params']['n'] = 100
        config['network_params']['m'] = 10
        G = utils.load_network(config['network_params'])
        assert len(G) == 100

    def test_empty_simulation(self):
        """A simulation with a base behaviour should do nothing"""
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'agent_type': 'NetworkAgent',
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        s.run_simulation()

    def test_counter_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'agent_type': 'CounterModel',
            'states': [{'neighbors': 10}, {'total': 12}],
            'max_time': 2,
            'num_trials': 1,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        env = s.run_simulation()[0]
        assert env.get_agent(0)['neighbors', 0] == 10
        assert env.get_agent(0)['neighbors', 1] == 1
        assert env.get_agent(1)['total', 0] == 12
        assert env.get_agent(1)['neighbors', 1] == 1

    def test_counter_agent_history(self):
        """
        The evolution of the state should be recorded in the logging agent
        """
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'network_agents': [{
                'agent_type': 'AggregatedCounter',
                'weight': 1,
                'state': {'id': 0}

            }],
            'max_time': 10,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        env = s.run_simulation()[0]
        for agent in env.network_agents:
            last = 0
            assert len(agent[None, None]) == 11
            for step, total in agent['total', None].items():
                if step > 0:
                    assert total == last + 2
                    last = total

    def test_custom_agent(self):
        """Allow for search of neighbors with a certain state_id"""
        class CustomAgent(agents.NetworkAgent):
            def step(self):
                self.state['neighbors'] = self.count_agents(state_id=0,
                                                            limit_neighbors=True)
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'network_agents': [{
                'agent_type': CustomAgent,
                'weight': 1,
                'state': {'id': 0}

            }],
            'max_time': 10,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        env = s.run_simulation()[0]
        assert env.get_agent(0).state['neighbors'] == 1

    def test_torvalds_example(self):
        """A complete example from a documentation should work."""
        config = utils.load_file(join(EXAMPLES, 'torvalds.yml'))[0]
        config['network_params']['path'] = join(EXAMPLES,
                                                config['network_params']['path'])
        s = simulation.from_config(config)
        env = s.run_simulation()[0]
        for a in env.network_agents:
            skill_level = a.state['skill_level']
            if a.id == 'Torvalds':
                assert skill_level == 'God'
                assert a.state['total'] == 3
                assert a.state['neighbors'] == 2
            elif a.id == 'balkian':
                assert skill_level == 'developer'
                assert a.state['total'] == 3
                assert a.state['neighbors'] == 1
            else:
                assert skill_level == 'beginner'
                assert a.state['total'] == 3
                assert a.state['neighbors'] == 1

    def test_yaml(self):
        """
        The YAML version of a newly created simulation
        should be equivalent to the configuration file used
        """
        with utils.timer('loading'):
            config = utils.load_file(join(EXAMPLES, 'complete.yml'))[0]
            s = simulation.from_config(config)
        with utils.timer('serializing'):
            serial = s.to_yaml()
        with utils.timer('recovering'):
            recovered = yaml.load(serial)
        with utils.timer('deleting'):
            del recovered['topology']
            del recovered['load_module']
        assert config == recovered

    def test_configuration_changes(self):
        """
        The configuration should not change after running
         the simulation.
        """
        config = utils.load_file('examples/complete.yml')[0]
        s = simulation.from_config(config)
        for i in range(5):
            s.run_simulation()
            nconfig = s.to_dict()
            del nconfig['topology']
            del nconfig['load_module']
            assert config == nconfig

    def test_examples(self):
        """
        Make sure all examples in the examples folder are correct
        """
        pass

    def test_row_conversion(self):
        sim = simulation.SoilSimulation()
        env = environment.SoilEnvironment(simulation=sim)
        env['test'] = 'test_value'
        env._save_state(now=0)

        res = list(env.history_to_tuples())
        assert len(res) == len(env.environment_params)
        assert ('env', 0, 'test', 'test_value') in res

        env['test'] = 'second_value'
        env._save_state(now=1)
        res = list(env.history_to_tuples())

        assert env['env', 0, 'test' ] == 'test_value'
        assert env['env', 1, 'test' ] == 'second_value'




def make_example_test(path, config):
    def wrapped(self):
        root = os.getcwd()
        os.chdir(os.path.dirname(path))
        s = simulation.from_config(config)
        envs = s.run_simulation()
        for env in envs:
            try:
                n = config['network_params']['n']
                assert len(env.get_agents()) == n
            except KeyError:
                pass
        os.chdir(root)
    return wrapped


def add_example_tests():
    for config, path in utils.load_config(join(EXAMPLES, '*.yml')):
        p = make_example_test(path=path, config=config)
        fname = os.path.basename(path)
        p.__name__ = 'test_example_file_%s' % fname
        p.__doc__ = '%s should be a valid configuration' % fname
        setattr(TestMain, p.__name__, p)
        del p


add_example_tests()
