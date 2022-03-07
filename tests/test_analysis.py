from unittest import TestCase

import os
import pandas as pd
import yaml
from functools import partial

from os.path import join
from soil import simulation, analysis, agents


ROOT = os.path.abspath(os.path.dirname(__file__))


class Ping(agents.FSM):

    defaults = {
        'count': 0,
    }

    @agents.default_state
    @agents.state
    def even(self):
        self.debug(f'Even {self["count"]}')
        self['count'] += 1
        return self.odd

    @agents.state
    def odd(self):
        self.debug(f'Odd {self["count"]}')
        self['count'] += 1
        return self.even


class TestAnalysis(TestCase):

    # Code to generate a simple sqlite history
    def setUp(self):
        """
        The initial states should be applied to the agent and the
        agent should be able to update its state."""
        config = {
            'name': 'analysis',
            'seed': 'seed',
            'network_params': {
                'generator': 'complete_graph',
                'n': 2
            },
            'agent_type': Ping,
            'states': [{'interval': 1}, {'interval': 2}],
            'max_time': 30,
            'num_trials': 1,
            'environment_params': {
            }
        }
        s = simulation.from_config(config)
        self.env = s.run_simulation(dry_run=True)[0]

    def test_saved(self):
        env = self.env
        assert env.get_agent(0)['count', 0] == 1
        assert env.get_agent(0)['count', 29] == 30
        assert env.get_agent(1)['count', 0] == 1
        assert env.get_agent(1)['count', 29] == 15
        assert env['env', 29, None]['SEED'] == env['env', 29, 'SEED']

    def test_count(self):
        env = self.env
        df = analysis.read_sql(env._history.db_path)
        res = analysis.get_count(df, 'SEED', 'state_id')
        assert res['SEED'][self.env['SEED']].iloc[0] == 1
        assert res['SEED'][self.env['SEED']].iloc[-1] == 1
        assert res['state_id']['odd'].iloc[0] == 2
        assert res['state_id']['even'].iloc[0] == 0
        assert res['state_id']['odd'].iloc[-1] == 1
        assert res['state_id']['even'].iloc[-1] == 1

    def test_value(self):
        env = self.env
        df = analysis.read_sql(env._history.db_path)
        res_sum = analysis.get_value(df, 'count')

        assert res_sum['count'].iloc[0] == 2

        import numpy as np
        res_mean = analysis.get_value(df, 'count', aggfunc=np.mean)
        assert res_mean['count'].iloc[15] == (16+8)/2

        res_total = analysis.get_majority(df)
        res_total['SEED'].iloc[0] == self.env['SEED']
