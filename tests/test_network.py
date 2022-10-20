from unittest import TestCase

import io
import os
import networkx as nx

from os.path import join

from soil import config, network, environment, agents, simulation
from test_main import CustomAgent

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, "..", "examples")


class TestNetwork(TestCase):
    def test_load_graph(self):
        """
        Load a graph from file if the extension is known.
        Raise an exception otherwise.
        """
        config = {"network_params": {"path": join(ROOT, "test.gexf")}}
        G = network.from_config(config["network_params"])
        assert G
        assert len(G) == 2
        with self.assertRaises(AttributeError):
            config = {"network_params": {"path": join(ROOT, "unknown.extension")}}
            G = network.from_config(config["network_params"])
            print(G)

    def test_generate_barabasi(self):
        """
        If no path is given, a generator and network parameters
        should be used to generate a network
        """
        cfg = {"params": {"generator": "barabasi_albert_graph"}}
        with self.assertRaises(Exception):
            G = network.from_config(cfg)
        cfg["params"]["n"] = 100
        cfg["params"]["m"] = 10
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
        assert env.G
        network.dump_gexf(env.G, f)

    def test_networkenvironment_creation(self):
        """Networkenvironment should accept netconfig as parameters"""
        model_params = {
            "topology": {"path": join(ROOT, "test.gexf")},
            "agents": {
                "topology": True,
                "distribution": [
                    {
                        "agent_class": CustomAgent,
                    }
                ],
            },
        }
        env = environment.Environment(**model_params)
        assert env.G
        env.step()
        assert len(env.G) == 2
        assert len(env.agents) == 2
        assert env.agents[1].count_agents(state_id="normal") == 2
        assert env.agents[1].count_agents(state_id="normal", limit_neighbors=True) == 1
        assert env.agents[0].count_neighbors() == 1

    def test_custom_agent_neighbors(self):
        """Allow for search of neighbors with a certain state_id"""
        config = {
            "model_params": {
                "topology": {"path": join(ROOT, "test.gexf")},
                "agents": {
                    "topology": True,
                    "distribution": [{"weight": 1, "agent_class": CustomAgent}],
                },
            },
            "max_time": 10,
        }
        s = simulation.from_config(config)
        env = s.run_simulation(dry_run=True)[0]
        assert env.agents[1].count_agents(state_id="normal") == 2
        assert env.agents[1].count_agents(state_id="normal", limit_neighbors=True) == 1
        assert env.agents[0].count_neighbors() == 1

    def test_subgraph(self):
        """An agent should be able to subgraph the global topology"""
        G = nx.Graph()
        G.add_node(3)
        G.add_edge(1, 2)
        distro = agents.calculate_distribution(agent_class=agents.NetworkAgent)
        aconfig = config.AgentConfig(distribution=distro, topology=True)
        env = environment.Environment(name="Test", topology=G, agents=aconfig)
        lst = list(env.network_agents)

        a2 = env.find_one(node_id=2)
        a3 = env.find_one(node_id=3)
        assert len(a2.subgraph(limit_neighbors=True)) == 2
        assert len(a3.subgraph(limit_neighbors=True)) == 1
        assert len(a3.subgraph(limit_neighbors=True, center=False)) == 0
        assert len(a3.subgraph(agent_class=agents.NetworkAgent)) == 3
