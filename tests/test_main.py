from unittest import TestCase

import os
import io
import yaml
import pickle
import networkx as nx
from functools import partial

from os.path import join
from soil import (simulation, Environment, agents, serialization,
                  history, utils)


ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')


class CustomAgent(agents.FSM):
    @agents.default_state
    @agents.state
    def normal(self):
        self.state['neighbors'] = self.count_agents(state_id='normal',
                                                    limit_neighbors=True)
    @agents.state
    def unreachable(self):
        return

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
        G = serialization.load_network(config['network_params'])
        assert G
        assert len(G) == 2
        with self.assertRaises(AttributeError):
            config = {
                'network_params': {
                    'path': join(ROOT, 'unknown.extension')
                }
            }
            G = serialization.load_network(config['network_params'])
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
            G = serialization.load_network(config['network_params'])
        config['network_params']['n'] = 100
        config['network_params']['m'] = 10
        G = serialization.load_network(config['network_params'])
        assert len(G) == 100

    def test_empty_simulation(self):
        """A simulation with a base behaviour should do nothing"""
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'agent_type': 'BaseAgent',
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        s.run_simulation(dry_run=True)

    def test_counter_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            'name': 'CounterAgent',
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'agent_type': 'CounterModel',
            'states': [{'times': 10}, {'times': 20}],
            'max_time': 2,
            'num_trials': 1,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        env = s.run_simulation(dry_run=True)[0]
        assert env.get_agent(0)['times', 0] == 11
        assert env.get_agent(0)['times', 1] == 12
        assert env.get_agent(1)['times', 0] == 21
        assert env.get_agent(1)['times', 1] == 22

    def test_counter_agent_history(self):
        """
        The evolution of the state should be recorded in the logging agent
        """
        config = {
            'name': 'CounterAgent',
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
        env = s.run_simulation(dry_run=True)[0]
        for agent in env.network_agents:
            last = 0
            assert len(agent[None, None]) == 11
            for step, total in sorted(agent['total', None]):
                assert total == last + 2
                last = total

    def test_custom_agent(self):
        """Allow for search of neighbors with a certain state_id"""
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'network_agents': [{
                'agent_type': CustomAgent,
                'weight': 1

            }],
            'max_time': 10,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        env = s.run_simulation(dry_run=True)[0]
        assert env.get_agent(0).state['neighbors'] == 1
        assert env.get_agent(0).state['neighbors'] == 1
        assert env.get_agent(1).count_agents(state_id='normal') == 2
        assert env.get_agent(1).count_agents(state_id='normal', limit_neighbors=True) == 1

    def test_torvalds_example(self):
        """A complete example from a documentation should work."""
        config = serialization.load_file(join(EXAMPLES, 'torvalds.yml'))[0]
        config['network_params']['path'] = join(EXAMPLES,
                                                config['network_params']['path'])
        s = simulation.from_config(config)
        env = s.run_simulation(dry_run=True)[0]
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
            config = serialization.load_file(join(EXAMPLES, 'complete.yml'))[0]
            s = simulation.from_config(config)
        with utils.timer('serializing'):
            serial = s.to_yaml()
        with utils.timer('recovering'):
            recovered = yaml.load(serial, Loader=yaml.SafeLoader)
        with utils.timer('deleting'):
            del recovered['topology']
        assert config == recovered

    def test_configuration_changes(self):
        """
        The configuration should not change after running
         the simulation.
        """
        config = serialization.load_file(join(EXAMPLES, 'complete.yml'))[0]
        s = simulation.from_config(config)

        s.run_simulation(dry_run=True)
        nconfig = s.to_dict()
        del nconfig['topology']
        assert config == nconfig

    def test_row_conversion(self):
        env = Environment()
        env['test'] = 'test_value'

        res = list(env.history_to_tuples())
        assert len(res) == len(env.environment_params)

        env.schedule.time = 1
        env['test'] = 'second_value'
        res = list(env.history_to_tuples())

        assert env['env', 0, 'test' ] == 'test_value'
        assert env['env', 1, 'test' ] == 'second_value'

    def test_save_geometric(self):
        """
        There is a bug in networkx that prevents it from creating a GEXF file 
        from geometric models. We should work around it.
        """
        G = nx.random_geometric_graph(20, 0.1)
        env = Environment(topology=G)
        f = io.BytesIO()
        env.dump_gexf(f)

    def test_save_graph(self):
        '''
        The history_to_graph method should return a valid networkx graph.

        The state of the agent should be encoded as intervals in the nx graph.
        '''
        G = nx.cycle_graph(5)
        distribution = agents.calculate_distribution(None, agents.BaseAgent)
        env = Environment(topology=G, network_agents=distribution)
        env[0, 0, 'testvalue'] = 'start'
        env[0, 10, 'testvalue'] = 'finish'
        nG = env.history_to_graph()
        values = nG.nodes[0]['attr_testvalue']
        assert ('start', 0, 10) in values
        assert ('finish', 10, None) in values

    def test_serialize_class(self):
        ser, name = serialization.serialize(agents.BaseAgent)
        assert name == 'soil.agents.BaseAgent'
        assert ser == agents.BaseAgent

        ser, name = serialization.serialize(CustomAgent)
        assert name == 'test_main.CustomAgent'
        assert ser == CustomAgent
        pickle.dumps(ser)

    def test_serialize_builtin_types(self):

        for i in [1, None, True, False, {}, [], list(), dict()]:
            ser, name = serialization.serialize(i)
            assert type(ser) == str
            des = serialization.deserialize(name, ser)
            assert i == des

    def test_serialize_agent_type(self):
        '''A class from soil.agents should be serialized without the module part'''
        ser = agents.serialize_type(CustomAgent)
        assert ser == 'test_main.CustomAgent'
        ser = agents.serialize_type(agents.BaseAgent)
        assert ser == 'BaseAgent'
        pickle.dumps(ser)
    
    def test_deserialize_agent_distribution(self):
        agent_distro = [
            {
                'agent_type': 'CounterModel',
                'weight': 1
            },
            {
                'agent_type': 'test_main.CustomAgent',
                'weight': 2
            },
        ]
        converted = agents.deserialize_definition(agent_distro)
        assert converted[0]['agent_type'] == agents.CounterModel
        assert converted[1]['agent_type'] == CustomAgent
        pickle.dumps(converted)

    def test_serialize_agent_distribution(self):
        agent_distro = [
            {
                'agent_type': agents.CounterModel,
                'weight': 1
            },
            {
                'agent_type': CustomAgent,
                'weight': 2
            },
        ]
        converted = agents.serialize_definition(agent_distro)
        assert converted[0]['agent_type'] == 'CounterModel'
        assert converted[1]['agent_type'] == 'test_main.CustomAgent'
        pickle.dumps(converted)

    def test_pickle_agent_environment(self):
        env = Environment(name='Test')
        a = agents.BaseAgent(model=env, unique_id=25)

        a['key'] = 'test'

        pickled = pickle.dumps(a)
        recovered = pickle.loads(pickled)

        assert recovered.env.name == 'Test'
        assert list(recovered.env._history.to_tuples())
        assert recovered['key', 0] == 'test'
        assert recovered['key'] == 'test'

    def test_history(self):
        '''Test storing in and retrieving from history (sqlite)'''
        h = history.History()
        h.save_record(agent_id=0, t_step=0, key="test", value="hello")
        assert h[0, 0, "test"] == "hello"

    def test_subgraph(self):
        '''An agent should be able to subgraph the global topology'''
        G = nx.Graph()
        G.add_node(3)
        G.add_edge(1, 2)
        distro = agents.calculate_distribution(agent_type=agents.NetworkAgent)
        env = Environment(name='Test', topology=G, network_agents=distro)
        lst = list(env.network_agents)

        a2 = env.get_agent(2)
        a3 = env.get_agent(3)
        assert len(a2.subgraph(limit_neighbors=True)) == 2
        assert len(a3.subgraph(limit_neighbors=True)) == 1
        assert len(a3.subgraph(limit_neighbors=True, center=False)) == 0
        assert len(a3.subgraph(agent_type=agents.NetworkAgent)) == 3

    def test_templates(self):
        '''Loading a template should result in several configs'''
        configs = serialization.load_file(join(EXAMPLES, 'template.yml'))
        assert len(configs) > 0

    def test_until(self):
        config = {
            'name': 'until_sim',
            'network_params': {},
            'agent_type': 'CounterModel',
            'max_time': 2,
            'num_trials': 100,
            'environment_params': {}
        }
        s = simulation.from_config(config)
        runs = list(s.run_simulation(dry_run=True))
        over = list(x.now for x in runs if x.now>2)
        assert len(over) == 0
