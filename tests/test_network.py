from unittest import TestCase

import io
import os
import networkx as nx

from os.path import join

from soil import network, environment

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, '..', 'examples')


class TestNetwork(TestCase):
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
        G = network.from_config(config['network_params'])
        assert G
        assert len(G) == 2
        with self.assertRaises(AttributeError):
            config = {
                'network_params': {
                    'path': join(ROOT, 'unknown.extension')
                }
            }
            G = network.from_config(config['network_params'])
            print(G)

    def test_generate_barabasi(self):
        """
        If no path is given, a generator and network parameters
        should be used to generate a network
        """
        cfg = {
            'params': {
                'generator': 'barabasi_albert_graph'
            }
        }
        with self.assertRaises(Exception):
            G = network.from_config(cfg)
        cfg['params']['n'] = 100
        cfg['params']['m'] = 10
        G = network.from_config(cfg)
        assert len(G) == 100

    def test_save_geometric(self):
        """
        There is a bug in networkx that prevents it from creating a GEXF file 
        from geometric models. We should work around it.
        """
        G = nx.random_geometric_graph(20, 0.1)
        env = environment.NetworkEnvironment(topology=G)
        f = io.BytesIO()
        env.dump_gexf(f)

    def test_custom_agent_neighbors(self):
        """Allow for search of neighbors with a certain state_id"""
        config = {
            'network_params': {
                'path': join(ROOT, 'test.gexf')
            },
            'network_agents': [{
                'agent_class': CustomAgent,
                'weight': 1

            }],
            'max_time': 10,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        env = s.run_simulation(dry_run=True)[0]
        assert env.agents[1].count_agents(state_id='normal') == 2
        assert env.agents[1].count_agents(state_id='normal', limit_neighbors=True) == 1
        assert env.agents[0].neighbors == 1

