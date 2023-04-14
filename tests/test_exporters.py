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

from mesa import Agent as MesaAgent


class Dummy(exporters.Exporter):
    started = False
    trials = 0
    ended = False
    total_time = 0
    called_start = 0
    called_trial = 0
    called_end = 0

    def sim_start(self):
        self.__class__.called_start += 1
        self.__class__.started = True

    def trial_end(self, env):
        assert env
        self.__class__.trials += 1
        self.__class__.total_time += env.now
        self.__class__.called_trial += 1

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
        

        num_trials = 5
        max_time = 2
        s = simulation.Simulation(num_trials=num_trials, max_time=max_time, name="exporter_sim",
                                  dump=False, model=SimpleEnv)

        for env in s.run_simulation(exporters=[Dummy], dump=False):
            assert len(env.agents) == 1

        assert Dummy.started
        assert Dummy.ended
        assert Dummy.called_start == 1
        assert Dummy.called_end == 1
        assert Dummy.called_trial == num_trials
        assert Dummy.trials == num_trials
        assert Dummy.total_time == max_time * num_trials

    def test_writing(self):
        """Try to write CSV, sqlite and YAML (without no_dump)"""
        n_trials = 5
        n_nodes = 4
        max_time = 2
        config = {
            "name": "exporter_sim",
            "model_params": {
                "network_generator": "complete_graph",
                "network_params": {"n": n_nodes},
                "agent_class": "CounterModel",
            },
            "max_time": max_time,
            "num_trials": n_trials,
            "dump": True,
        }
        output = io.StringIO()
        s = simulation.from_config(config)
        tmpdir = tempfile.mkdtemp()
        envs = s.run_simulation(
            exporters=[
                exporters.default,
                exporters.csv,
            ],
            model_params={
                "agent_reporters": {"times": "times"},
                "model_reporters": {
                    "constant": lambda x: 1,
                },
            },
            dump=True,
            outdir=tmpdir,
            exporter_params={"copy_to": output},
        )
        result = output.getvalue()

        simdir = os.path.join(tmpdir, s.group or "", s.name)
        with open(os.path.join(simdir, "{}.dumped.yml".format(s.name))) as f:
            result = f.read()
            assert result

        try:
            for e in envs:
                dbpath = os.path.join(simdir, f"{s.name}.sqlite")
                db = sqlite3.connect(dbpath)
                cur = db.cursor()
                agent_entries = cur.execute("SELECT times FROM agents WHERE times > 0").fetchall()
                env_entries = cur.execute("SELECT constant from env WHERE constant == 1").fetchall()
                assert len(agent_entries) == n_nodes * n_trials * max_time
                assert len(env_entries) == n_trials * max_time

                with open(os.path.join(simdir, "{}.env.csv".format(e.id))) as f:
                    result = f.read()
                    assert result
        finally:
            shutil.rmtree(tmpdir)
