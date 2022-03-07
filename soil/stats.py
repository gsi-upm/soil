import pandas as pd

from collections import Counter

class Stats:
    '''
    Interface for all stats. It is not necessary, but it is useful
    if you don't plan to implement all the methods.
    '''

    def __init__(self, simulation):
        self.simulation = simulation

    def start(self):
        '''Method to call when the simulation starts'''
        pass

    def end(self):
        '''Method to call when the simulation ends'''
        return {}

    def trial(self, env):
        '''Method to call when a trial ends'''
        return {}


class distribution(Stats):
    '''
    Calculate the distribution of agent states at the end of each trial,
    the mean value, and its deviation.
    '''

    def start(self):
        self.means = []
        self.counts = []

    def trial(self, env):
        df = env[None, None, None].df()
        df = df.drop('SEED', axis=1)
        ix = df.index[-1]
        attrs = df.columns.get_level_values(0)
        vc = {}
        stats = {
            'mean': {},
            'count': {},
        }
        for a in attrs:
            t = df.loc[(ix, a)]
            try:
                stats['mean'][a] = t.mean()
                self.means.append(('mean', a, t.mean()))
            except TypeError:
                pass

            for name, count in t.value_counts().iteritems():
                if a not in stats['count']:
                    stats['count'][a] = {}
                stats['count'][a][name] = count
                self.counts.append(('count', a, name, count))

        return stats

    def end(self):
        dfm = pd.DataFrame(self.means, columns=['metric', 'key', 'value'])
        dfc = pd.DataFrame(self.counts, columns=['metric', 'key', 'value', 'count'])

        count = {}
        mean = {}

        if self.means:
            res = dfm.groupby(by=['key']).agg(['mean', 'std', 'count', 'median', 'max', 'min'])
            mean = res['value'].to_dict()
        if self.counts:
            res = dfc.groupby(by=['key', 'value']).agg(['mean', 'std', 'count', 'median', 'max', 'min'])
            for k,v in res['count'].to_dict().items():
                if k not in count:
                    count[k] = {}
                for tup, times in v.items():
                    subkey, subcount = tup
                    if subkey not in count[k]:
                        count[k][subkey] = {}
                    count[k][subkey][subcount] = times


        return {'count': count, 'mean': mean}


class defaultStats(Stats):

    def trial(self, env):
        c = Counter()
        c.update(a.__class__.__name__ for a in env.network_agents)

        c2 = Counter()
        c2.update(a['id'] for a in env.network_agents)

        return {
            'network ': {
                'n_nodes': env.G.number_of_nodes(),
                'n_edges': env.G.number_of_edges(),
            },
            'agents': {
                'model_count': dict(c),
                'state_count': dict(c2),
            }
        }
