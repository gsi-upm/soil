from unittest import TestCase

from soil import simulation, stats
from soil.utils import unflatten_dict

class Stats(TestCase):

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
        s = simulation.from_config(config)
        for env in s.run_simulation(stats=[stats.distribution]):
            pass
            # stats_res = unflatten_dict(dict(env._history['stats', -1, None]))
        allstats = s.get_stats()
        for stat in allstats:
            assert 'count' in stat
            assert 'mean' in stat
            if 'trial_id' in stat:
                assert stat['mean']['neighbors'] == 3
                assert stat['count']['total']['4'] == 4
            else:
                assert stat['count']['count']['neighbors']['3'] == 20
                assert stat['mean']['min']['neighbors'] == stat['mean']['max']['neighbors']
