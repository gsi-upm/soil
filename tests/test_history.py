from unittest import TestCase

import os
import io
import yaml
import copy
import pickle
import networkx as nx
from functools import partial

from os.path import join
from soil import (simulation, Environment, agents, serialization,
                  utils)
from soil.time import Delta
from tsih import NoHistory, History


ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')


class CustomAgent(agents.FSM):
    @agents.default_state
    @agents.state
    def normal(self):
        self.neighbors = self.count_agents(state_id='normal',
                                           limit_neighbors=True)
    @agents.state
    def unreachable(self):
        return

class TestHistory(TestCase):

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
                'state': {'state_id': 0}

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

    def test_row_conversion(self):
        env = Environment(history=True)
        env['test'] = 'test_value'

        res = list(env.history_to_tuples())
        assert len(res) == len(env.environment_params)

        env.schedule.time = 1
        env['test'] = 'second_value'
        res = list(env.history_to_tuples())

        assert env['env', 0, 'test' ] == 'test_value'
        assert env['env', 1, 'test' ] == 'second_value'

    def test_nohistory(self):
        '''
        Make sure that no history(/sqlite) is used by default
        '''
        env = Environment(topology=nx.Graph(), network_agents=[])
        assert isinstance(env._history, NoHistory)

    def test_save_graph_history(self):
        '''
        The history_to_graph method should return a valid networkx graph.

        The state of the agent should be encoded as intervals in the nx graph.
        '''
        G = nx.cycle_graph(5)
        distribution = agents.calculate_distribution(None, agents.BaseAgent)
        env = Environment(topology=G, network_agents=distribution, history=True)
        env[0, 0, 'testvalue'] = 'start'
        env[0, 10, 'testvalue'] = 'finish'
        nG = env.history_to_graph()
        values = nG.nodes[0]['attr_testvalue']
        assert ('start', 0, 10) in values
        assert ('finish', 10, None) in values

    def test_save_graph_nohistory(self):
        '''
        The history_to_graph method should return a valid networkx graph.

        When NoHistory is used, only the last known value is known
        '''
        G = nx.cycle_graph(5)
        distribution = agents.calculate_distribution(None, agents.BaseAgent)
        env = Environment(topology=G, network_agents=distribution, history=False)
        env.get_agent(0)['testvalue'] = 'start'
        env.schedule.time = 10
        env.get_agent(0)['testvalue'] = 'finish'
        nG = env.history_to_graph()
        values = nG.nodes[0]['attr_testvalue']
        assert ('start', 0, None) not in values
        assert ('finish', 10, None) in values

    def test_pickle_agent_environment(self):
        env = Environment(name='Test', history=True)
        a = agents.BaseAgent(model=env, unique_id=25)

        a['key'] = 'test'

        pickled = pickle.dumps(a)
        recovered = pickle.loads(pickled)

        assert recovered.env.name == 'Test'
        assert list(recovered.env._history.to_tuples())
        assert recovered['key', 0] == 'test'
        assert recovered['key'] == 'test'
