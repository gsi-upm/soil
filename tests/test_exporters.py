import os
import io
import tempfile
import shutil
import sqlite3

from unittest import TestCase
from soil import exporters
from soil import environment
from soil import simulation
from soil import agents
from soil import decorators

from mesa import Agent as MesaAgent


class Dummy(exporters.Exporter):
    started = False
    iterations = 0
    ended = False
    total_time = 0
    called_start = 0
    called_iteration = 0
    called_end = 0

    def sim_start(self):
        self.__class__.called_start += 1
        self.__class__.started = True

    def iteration_end(self, env, *args, **kwargs):
        assert env
        self.__class__.iterations += 1
        self.__class__.total_time += env.now
        self.__class__.called_iteration += 1

    def sim_end(self):
        self.__class__.ended = True
        self.__class__.called_end += 1


class Exporters(TestCase):
    def test_basic(self):
        # We need to add at least one agent to make sure the scheduler
        # ticks every step
        class SimpleEnv(environment.Environment):
            def init(self):
                self.add_agent(agent_class=MesaAgent)

        iterations = 5
        max_time = 2
        s = simulation.Simulation(iterations=iterations,
                                  max_time=max_time, name="exporter_sim",
                                  exporters=[Dummy], dump=False, model=SimpleEnv)

        for env in s.run():
            assert len(env.agents) == 1

        assert Dummy.started
        assert Dummy.ended
        assert Dummy.called_start == 1
        assert Dummy.called_end == 1
        assert Dummy.called_iteration == iterations
        assert Dummy.iterations == iterations
        assert Dummy.total_time == max_time * iterations

    def test_writing(self):
        """Try to write CSV, sqlite and YAML (without no_dump)"""
        n_iterations = 5
        n_nodes = 4
        max_time = 2
        output = io.StringIO()
        tmpdir = tempfile.mkdtemp()

        class ConstantEnv(environment.Environment):
            @decorators.report
            @property
            def constant(self):
                return 1

        s = simulation.Simulation(
            model=ConstantEnv,
            name="exporter_sim",
            exporters=[
                exporters.YAML,
                exporters.SQLite,
                exporters.csv,
            ],
            exporter_params={"copy_to": output},
            parameters=dict(
                network_generator="complete_graph",
                network_params={"n": n_nodes},
                agent_class=agents.CounterModel,
                agent_reporters={"times": "times"},
            ),
            max_time=max_time,
            outdir=tmpdir,
            iterations=n_iterations,
            dump=True,
        )
        envs = s.run()
        result = output.getvalue()

        simdir = os.path.join(tmpdir, s.group or "", s.name)
        with open(os.path.join(simdir, "{}.dumped.yml".format(s.id))) as f:
            result = f.read()
            assert result

        try:
            dbpath = os.path.join(simdir, f"{s.name}.sqlite")
            db = sqlite3.connect(dbpath)
            cur = db.cursor()
            agent_entries = cur.execute("SELECT times FROM agents WHERE times > 0").fetchall()
            env_entries = cur.execute("SELECT constant from env WHERE constant == 1").fetchall()
            assert len(agent_entries) == n_nodes * n_iterations * max_time
            assert len(env_entries) == n_iterations * (max_time + 1) # +1 for the initial state

            for e in envs:
                with open(os.path.join(simdir, "{}.env.csv".format(e.id))) as f:
                    result = f.read()
                    assert result

        finally:
            shutil.rmtree(tmpdir)
