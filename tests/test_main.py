from unittest import TestCase

import os
import pickle
import networkx as nx
from functools import partial

from os.path import join
from soil import simulation, Environment, agents, serialization, from_file, time
from mesa import Agent as MesaAgent

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
            "parameters": {
                "topology": join(ROOT, "test.gexf"),
                "agent_class": MesaAgent,
            },
            "max_time": 1
        }
        s = simulation.from_config(config)
        s.run(dump=False)

    def test_network_agent(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            "name": "CounterAgent",
            "iterations": 1,
            "max_time": 2,
            "parameters": {
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
            env = s.run(dump=False)[0]
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

        ser, name = serialization.serialize(
            agents.BaseAgent,
            known_modules=[
                "soil",
            ],
        )
        assert name == "BaseAgent"

        ser, name = serialization.serialize(CustomAgent)
        assert name == "test_main.CustomAgent"
        pickle.dumps(ser)

    def test_serialize_builtin_types(self):

        for i in [1, None, True, False, {}, [], list(), dict()]:
            ser, name = serialization.serialize(i)
            assert type(ser) == str
            des = serialization.deserialize(name, ser)
            assert i == des

    def test_serialize_agent_class(self):
        """A class from soil.agents should be serialized without the module part"""
        ser = serialization.serialize(CustomAgent, known_modules=["soil.agents"])[1]
        assert ser == "test_main.CustomAgent"
        ser = serialization.serialize(agents.BaseAgent, known_modules=["soil.agents"])[1]
        assert ser == "BaseAgent"
        pickle.dumps(ser)

    def test_until(self):
        n_runs = 0

        class CheckRun(agents.BaseAgent):
            def step(self):
                nonlocal n_runs
                n_runs += 1

        n_trials = 50
        max_time = 2
        s = simulation.Simulation(
            parameters=dict(agents=dict(agent_classes=[CheckRun], k=1)),
            iterations=n_trials,
            max_time=max_time,
        )
        runs = list(s.run(dump=False))
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
                return self.pong.delay(2)

            @agents.state
            def pong(self):
                return self.ping

        a = ToggleAgent(unique_id=1, model=Environment())
        when = float(a.step())
        assert when == 2
        when = a.step()
        assert when == None

    def test_load_sim(self):
        """Make sure at least one of the examples can be loaded"""
        sims = from_file(os.path.join(EXAMPLES, "newsspread", "newsspread_sim.py"))
        assert len(sims) == 3*3*2
        for sim in sims:
            assert sim
            assert sim.name == "newspread_sim"
            assert sim.iterations == 5
            assert sim.max_steps == 300
            assert not sim.dump
            assert sim.parameters
            assert "ratio_dumb" in sim.parameters
            assert "ratio_herd" in sim.parameters
            assert "ratio_wise" in sim.parameters
            assert "network_generator" in sim.parameters
            assert "network_params" in sim.parameters
            assert "prob_neighbor_spread" in sim.parameters

    def test_config_matrix(self):
        """It should be possible to specify a matrix of parameters"""
        a = [1, 2]
        b = [3, 4]
        sim = simulation.Simulation(matrix=dict(a=a, b=b))
        configs = sim._collect_params()
        assert len(configs) == len(a) * len(b)
        for i in a:
            for j in b:
                assert {"a": i, "b": j} in configs

    def test_agent_reporters(self):
        """An environment should be able to set its own reporters"""
        class Noop2(agents.Noop):
            pass

        e = Environment()
        e.add_agent(agents.Noop)
        e.add_agent(Noop2)
        e.add_agent_reporter("now")
        e.add_agent_reporter("base", lambda a: "base", agent_class=agents.Noop)
        e.add_agent_reporter("subclass", lambda a:"subclass", agent_class=Noop2)
        e.step()

        # Step 0 is not present because we added the reporters
        # after initialization.
        df = e.agent_df()
        assert "now" in df.columns
        assert "base" in df.columns
        assert "subclass" in df.columns
        assert df["now"][(1,0)] == 1
        assert df["now"][(1,1)] == 1
        assert df["base"][(1,0)] == "base"
        assert df["base"][(1,1)] == "base"
        assert df["subclass"][(1,0)] is None
        assert df["subclass"][(1,1)] == "subclass"

    def test_remove_agent(self):
        """An agent that is scheduled should be removed from the schedule"""
        model = Environment()
        model.add_agent(agents.Noop)
        model.step()
        model.remove_agent(model.agents[0])
        assert not model.agents
        when = model.step()
        assert when == None
        assert not model.running

    def test_remove_agent(self):
        """An agent that is scheduled should be removed from the schedule"""

        allagents = []
        class Removed(agents.BaseAgent):
            def step(self):
                nonlocal allagents
                assert self.alive
                assert self in self.model.agents
                for agent in allagents:
                    self.model.remove_agent(agent)

        model = Environment()
        a1 = model.add_agent(Removed)
        a2 = model.add_agent(Removed)
        allagents = [a1, a2]
        model.step()
        assert not model.agents

    def test_agent_df(self):
        '''The agent dataframe should have the right columns'''

        class PeterPan(agents.BaseAgent):
            steps = 0

            def step(self):
                self.steps += 1
                return self.delay(0)

        class AgentDF(Environment):
            def init(self):
                self.add_agent(PeterPan)
                self.add_agent_reporter("steps")

        e = AgentDF()
        df = e.agent_df()
        assert df["steps"][(0,0)] == 0
        e.step()
        df = e.agent_df()
        assert len(df) == 1
        assert df["steps"][(0,0)] == 1
        e.step()
        df = e.agent_df()
        assert len(df) == 1
        assert df["steps"][(0,0)] == 2