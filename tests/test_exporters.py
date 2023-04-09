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
                self.add_agent(agent_class=agents.BaseAgent)
        

        num_trials = 5
        max_time = 2
        s = simulation.Simulation(num_trials=num_trials, max_time=max_time, name="exporter_sim", dry_run=True, model=SimpleEnv)

        for env in s.run_simulation(exporters=[Dummy], dry_run=True):
            assert len(env.agents) == 1

        assert Dummy.started
        assert Dummy.ended
        assert Dummy.called_start == 1
        assert Dummy.called_end == 1
        assert Dummy.called_trial == num_trials
        assert Dummy.trials == num_trials
        assert Dummy.total_time == max_time * num_trials

    def test_writing(self):
        """Try to write CSV, sqlite and YAML (without dry_run)"""
        n_trials = 5
        config = {
            "name": "exporter_sim",
            "model_params": {
                "network_generator": "complete_graph",
                "network_params": {"n": 4},
                "agent_class": "CounterModel",
            },
            "max_time": 2,
            "num_trials": n_trials,
            "dry_run": False,
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
            dry_run=False,
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
                db = sqlite3.connect(os.path.join(simdir, f"{s.name}.sqlite"))
                cur = db.cursor()
                agent_entries = cur.execute("SELECT * from agents").fetchall()
                env_entries = cur.execute("SELECT * from env").fetchall()
                assert len(agent_entries) > 0
                assert len(env_entries) > 0

                with open(os.path.join(simdir, "{}.env.csv".format(e.id))) as f:
                    result = f.read()
                    assert result
        finally:
            shutil.rmtree(tmpdir)
