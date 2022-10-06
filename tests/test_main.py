from unittest import TestCase

import os
import pickle
import networkx as nx
from functools import partial

from os.path import join
from soil import (simulation, Environment, agents, network, serialization,
                  utils, config)
from soil.time import Delta

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')


class CustomAgent(agents.FSM, agents.NetworkAgent):
    @agents.default_state
    @agents.state
    def normal(self):
        self.neighbors = self.count_agents(state_id='normal',
                                           limit_neighbors=True)
    @agents.state
    def unreachable(self):
        return

class TestMain(TestCase):

    def test_empty_simulation(self):
        """A simulation with a base behaviour should do nothing"""
        config = {
            'model_params': {
              'network_params': {
                  'path': join(ROOT, 'test.gexf')
              },
              'agent_class': 'BaseAgent',
            }
        }
        s = simulation.from_config(config)
        s.run_simulation(dry_run=True)


    def test_network_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            'name': 'CounterAgent',
            'num_trials': 1,
            'max_time': 2,
            'model_params': {
                'network_params': {
                    'generator': nx.complete_graph,
                    'n': 2,
                },
                'agent_class': 'CounterModel',
                'states': {
                    0: {'times': 10},
                    1: {'times': 20},
                },
            }
        }
        s = simulation.from_config(config)

    def test_counter_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            'version': '2',
            'name': 'CounterAgent',
            'dry_run': True,
            'num_trials': 1,
            'max_time': 2,
            'model_params': {
                'topologies': {
                    'default': {
                        'path': join(ROOT, 'test.gexf')
                    }
                },
                'agents': {
                    'default': {
                        'agent_class': 'CounterModel',
                    },
                    'counters': {
                        'topology': 'default',
                        'fixed': [{'state': {'times': 10}}, {'state': {'times': 20}}],
                    }
                }
            }
        }
        s = simulation.from_config(config)
        env = s.get_env()
        assert isinstance(env.agents[0], agents.CounterModel)
        assert env.agents[0].topology == env.topologies['default']
        assert env.agents[0]['times'] == 10
        assert env.agents[0]['times'] == 10
        env.step()
        assert env.agents[0]['times'] == 11
        assert env.agents[1]['times'] == 21

    def test_init_and_count_agents(self):
        """Agents should be properly initialized and counting should filter them properly"""
        #TODO: separate this test into two or more test cases
        config = {
            'max_time': 10,
            'model_params': {
                'agents': [(CustomAgent, {'weight': 1}),
                           (CustomAgent, {'weight': 3}),
                ],
                'topologies': {
                    'default': {
                        'path': join(ROOT, 'test.gexf')
                    }
                },
            },
        }
        s = simulation.from_config(config)
        env = s.run_simulation(dry_run=True)[0]
        assert env.agents[0].weight == 1
        assert env.count_agents() == 2
        assert env.count_agents(weight=1) == 1
        assert env.count_agents(weight=3) == 1
        assert env.count_agents(agent_class=CustomAgent) == 2


    def test_torvalds_example(self):
        """A complete example from a documentation should work."""
        config = serialization.load_file(join(EXAMPLES, 'torvalds.yml'))[0]
        config['model_params']['network_params']['path'] = join(EXAMPLES,
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

    def test_serialize_class(self):
        ser, name = serialization.serialize(agents.BaseAgent, known_modules=[])
        assert name == 'soil.agents.BaseAgent'
        assert ser == agents.BaseAgent

        ser, name = serialization.serialize(agents.BaseAgent, known_modules=['soil', ])
        assert name == 'BaseAgent'
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

    def test_serialize_agent_class(self):
        '''A class from soil.agents should be serialized without the module part'''
        ser = agents.serialize_type(CustomAgent)
        assert ser == 'test_main.CustomAgent'
        ser = agents.serialize_type(agents.BaseAgent)
        assert ser == 'BaseAgent'
        pickle.dumps(ser)
    
    def test_deserialize_agent_distribution(self):
        agent_distro = [
            {
                'agent_class': 'CounterModel',
                'weight': 1
            },
            {
                'agent_class': 'test_main.CustomAgent',
                'weight': 2
            },
        ]
        converted = agents.deserialize_definition(agent_distro)
        assert converted[0]['agent_class'] == agents.CounterModel
        assert converted[1]['agent_class'] == CustomAgent
        pickle.dumps(converted)

    def test_serialize_agent_distribution(self):
        agent_distro = [
            {
                'agent_class': agents.CounterModel,
                'weight': 1
            },
            {
                'agent_class': CustomAgent,
                'weight': 2
            },
        ]
        converted = agents.serialize_definition(agent_distro)
        assert converted[0]['agent_class'] == 'CounterModel'
        assert converted[1]['agent_class'] == 'test_main.CustomAgent'
        pickle.dumps(converted)

    def test_subgraph(self):
        '''An agent should be able to subgraph the global topology'''
        G = nx.Graph()
        G.add_node(3)
        G.add_edge(1, 2)
        distro = agents.calculate_distribution(agent_class=agents.NetworkAgent)
        distro[0]['topology'] = 'default'
        aconfig = config.AgentConfig(distribution=distro, topology='default')
        env = Environment(name='Test', topologies={'default': G}, agents={'network': aconfig})
        lst = list(env.network_agents)

        a2 = env.find_one(node_id=2)
        a3 = env.find_one(node_id=3)
        assert len(a2.subgraph(limit_neighbors=True)) == 2
        assert len(a3.subgraph(limit_neighbors=True)) == 1
        assert len(a3.subgraph(limit_neighbors=True, center=False)) == 0
        assert len(a3.subgraph(agent_class=agents.NetworkAgent)) == 3

    def test_templates(self):
        '''Loading a template should result in several configs'''
        configs = serialization.load_file(join(EXAMPLES, 'template.yml'))
        assert len(configs) > 0

    def test_until(self):
        config = {
            'name': 'until_sim',
            'model_params': {
                'network_params': {},
                'agent_class': 'CounterModel',
            },
            'max_time': 2,
            'num_trials': 50,
        }
        s = simulation.from_config(config)
        runs = list(s.run_simulation(dry_run=True))
        over = list(x.now for x in runs if x.now>2)
        assert len(runs) == config['num_trials']
        assert len(over) == 0

    def test_fsm(self):
        '''Basic state change'''
        class ToggleAgent(agents.FSM):
            @agents.default_state
            @agents.state
            def ping(self):
                return self.pong

            @agents.state
            def pong(self):
                return self.ping

        a = ToggleAgent(unique_id=1, model=Environment())
        assert a.state_id == a.ping.id
        a.step()
        assert a.state_id == a.pong.id
        a.step()
        assert a.state_id == a.ping.id

    def test_fsm_when(self):
        '''Basic state change'''
        class ToggleAgent(agents.FSM):
            @agents.default_state
            @agents.state
            def ping(self):
                return self.pong, 2

            @agents.state
            def pong(self):
                return self.ping

        a = ToggleAgent(unique_id=1, model=Environment())
        when = a.step()
        assert when == 2
        when = a.step()
        assert when == Delta(a.interval)
