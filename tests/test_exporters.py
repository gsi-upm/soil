import os
import io
import tempfile
import shutil
from time import time

from unittest import TestCase
from soil import exporters
from soil.utils import safe_open
from soil import simulation


class Dummy(exporters.Exporter):
    started = False
    trials = 0
    ended = False
    total_time = 0

    def start(self):
        self.__class__.started = True

    def trial_end(self, env):
        assert env
        self.__class__.trials += 1
        self.__class__.total_time += env.now

    def end(self):
        self.__class__.ended = True


class Exporters(TestCase):
    def test_basic(self):
        config = {
            'name': 'exporter_sim',
            'network_params': {},
            'agent_type': 'CounterModel',
            'max_time': 2,
            'num_trials': 5,
            'environment_params': {}
        }
        s = simulation.from_config(config)
        s.run_simulation(exporters=[Dummy], dry_run=True)
        assert Dummy.started
        assert Dummy.ended
        assert Dummy.trials == 5
        assert Dummy.total_time == 2*5

    def test_distribution(self):
        '''The distribution exporter should write the number of agents in each state'''
        config = {
            'name': 'exporter_sim',
            'network_params': {
                'generator': 'complete_graph',
                'n': 4
            },
            'agent_type': 'CounterModel',
            'max_time': 2,
            'num_trials': 5,
            'environment_params': {}
        }
        output = io.StringIO()
        s = simulation.from_config(config)
        s.run_simulation(exporters=[exporters.distribution], dry_run=True, exporter_params={'copy_to': output})
        result = output.getvalue()
        assert 'count' in result
        assert 'SEED,Noneexporter_sim_trial_3,1,,1,1,1,1' in result

    def test_writing(self):
        '''Try to write CSV, GEXF, sqlite and YAML (without dry_run)'''
        n_trials = 5
        config = {
            'name': 'exporter_sim',
            'network_params': {
                'generator': 'complete_graph',
                'n': 4
            },
            'agent_type': 'CounterModel',
            'max_time': 2,
            'num_trials': n_trials,
            'environment_params': {}
        }
        output = io.StringIO()
        s = simulation.from_config(config)
        tmpdir = tempfile.mkdtemp()
        envs = s.run_simulation(exporters=[
            exporters.default,
            exporters.csv,
            exporters.gexf,
            exporters.distribution,
        ],
                                outdir=tmpdir,
                                exporter_params={'copy_to': output})
        result = output.getvalue()

        simdir = os.path.join(tmpdir, s.group or '', s.name)
        with open(os.path.join(simdir, '{}.dumped.yml'.format(s.name))) as f:
            result = f.read()
            assert result

        try:
            for e in envs:
                with open(os.path.join(simdir, '{}.gexf'.format(e.name))) as f:
                    result = f.read()
                    assert result

                with open(os.path.join(simdir, '{}.csv'.format(e.name))) as f:
                    result = f.read()
                    assert result
        finally:
            shutil.rmtree(tmpdir)
