from unittest import TestCase

import os
import pickle
import networkx as nx
from functools import partial

from os.path import join
from soil import simulation, Environment, agents, network, serialization, utils, config
from soil.time import Delta

ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES = join(ROOT, "..", "examples")


class CustomAgent(agents.FSM, agents.NetworkAgent):
    @agents.default_state
    @agents.state
    def normal(self):
        self.neighbors = self.count_agents(state_id="normal", limit_neighbors=True)

    @agents.state
    def unreachable(self):
        return


class TestMain(TestCase):
    def test_empty_simulation(self):
        """A simulation with a base behaviour should do nothing"""
        config = {
            "model_params": {
                "topology": join(ROOT, "test.gexf"),
                "agent_class": "NetworkAgent",
            }
        }
        s = simulation.from_config(config)
        s.run_simulation(dry_run=True)

    def test_network_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            "name": "CounterAgent",
            "num_trials": 1,
            "max_time": 2,
            "model_params": {
                "network_params": {
                    "generator": nx.complete_graph,
                    "n": 2,
                },
                "agent_class": "CounterModel",
                "states": {
                    0: {"times": 10},
                    1: {"times": 20},
                },
            },
        }
        s = simulation.from_config(config)

    def test_counter_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        env = Environment()
        env.add_agent(agents.Ticker, times=10)
        env.add_agent(agents.Ticker, times=20)

        assert isinstance(env.agents[0], agents.Ticker)
        assert env.agents[0]["times"] == 10
        assert env.agents[1]["times"] == 20
        env.step()
        assert env.agents[0]["times"] == 11
        assert env.agents[1]["times"] == 21

    def test_init_and_count_agents(self):
        """Agents should be properly initialized and counting should filter them properly"""
        # TODO: separate this test into two or more test cases
        env = Environment(topology=join(ROOT, "test.gexf"))
        env.populate_network([CustomAgent.w(weight=1), CustomAgent.w(weight=3)])
        assert env.agents[0].weight == 1
        assert env.count_agents() == 2
        assert env.count_agents(weight=1) == 1
        assert env.count_agents(weight=3) == 1
        assert env.count_agents(agent_class=CustomAgent) == 2

    def test_torvalds_example(self):
        """A complete example from a documentation should work."""
        owd = os.getcwd()
        pyfile = join(EXAMPLES, "torvalds_sim.py")
        try:
            os.chdir(os.path.dirname(pyfile))
            s = simulation.from_py(pyfile)
            env = s.run_simulation(dry_run=True)[0]
            for a in env.network_agents:
                skill_level = a["skill_level"]
                if a.node_id == "Torvalds":
                    assert skill_level == "God"
                    assert a["total"] == 3
                    assert a["neighbors"] == 2
                elif a.node_id == "balkian":
                    assert skill_level == "developer"
                    assert a["total"] == 3
                    assert a["neighbors"] == 1
                else:
                    assert skill_level == "beginner"
                    assert a["total"] == 3
                    assert a["neighbors"] == 1
        finally:
            os.chdir(owd)

    def test_serialize_class(self):
        ser, name = serialization.serialize(agents.BaseAgent, known_modules=[])
        assert name == "soil.agents.BaseAgent"
        assert ser == agents.BaseAgent

        ser, name = serialization.serialize(
            agents.BaseAgent,
            known_modules=[
                "soil",
            ],
        )
        assert name == "BaseAgent"
        assert ser == agents.BaseAgent

        ser, name = serialization.serialize(CustomAgent)
        assert name == "test_main.CustomAgent"
        assert ser == CustomAgent
        pickle.dumps(ser)

    def test_serialize_builtin_types(self):

        for i in [1, None, True, False, {}, [], list(), dict()]:
            ser, name = serialization.serialize(i)
            assert type(ser) == str
            des = serialization.deserialize(name, ser)
            assert i == des

    def test_serialize_agent_class(self):
        """A class from soil.agents should be serialized without the module part"""
        ser = agents._serialize_type(CustomAgent)
        assert ser == "test_main.CustomAgent"
        ser = agents._serialize_type(agents.BaseAgent)
        assert ser == "BaseAgent"
        pickle.dumps(ser)

    def test_until(self):
        n_runs = 0

        class CheckRun(agents.BaseAgent):
            def step(self):
                nonlocal n_runs
                n_runs += 1
                return super().step()

        n_trials = 50
        max_time = 2
        s = simulation.Simulation(
            model_params=dict(agents=dict(agent_classes=[CheckRun], k=1)),
            num_trials=n_trials,
            max_time=max_time,
        )
        runs = list(s.run_simulation(dry_run=True))
        over = list(x.now for x in runs if x.now > 2)
        assert len(runs) == n_trials
        assert len(over) == 0

    def test_fsm(self):
        """Basic state change"""

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
        """Basic state change"""

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
