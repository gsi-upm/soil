import os
import time
from io import BytesIO

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from .serialization import deserialize
from .utils import open_or_reuse, logger, timer


from . import utils


def for_sim(simulation, names, *args, **kwargs):
    '''Return the set of exporters for a simulation, given the exporter names'''
    exporters = []
    for name in names:
        mod = deserialize(name, known_modules=['soil.exporters'])
        exporters.append(mod(simulation, *args, **kwargs))
    return exporters


class DryRunner(BytesIO):
    def __init__(self, fname, *args, copy_to=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__fname = fname
        self.__copy_to = copy_to

    def write(self, txt):
        if self.__copy_to:
            self.__copy_to.write('{}:::{}'.format(self.__fname, txt))
        try:
            super().write(txt)
        except TypeError:
            super().write(bytes(txt, 'utf-8'))

    def close(self):
        logger.info('**Not** written to {} (dry run mode):\n\n{}\n\n'.format(self.__fname,
                                                                       self.getvalue().decode()))
        super().close()


class Exporter:
    '''
    Interface for all exporters. It is not necessary, but it is useful
    if you don't plan to implement all the methods.
    '''

    def __init__(self, simulation, outdir=None, dry_run=None, copy_to=None):
        self.sim = simulation
        outdir = outdir or os.path.join(os.getcwd(), 'soil_output')
        self.outdir = os.path.join(outdir,
                                   simulation.group or '',
                                   simulation.name)
        self.dry_run = dry_run
        self.copy_to = copy_to

    def start(self):
        '''Method to call when the simulation starts'''

    def end(self):
        '''Method to call when the simulation ends'''

    def trial_end(self, env):
        '''Method to call when a trial ends'''

    def output(self, f, mode='w', **kwargs):
        if self.dry_run:
            f = DryRunner(f, copy_to=self.copy_to)
        else:
            try:
                if not os.path.isabs(f):
                    f = os.path.join(self.outdir, f)
            except TypeError:
                pass
        return open_or_reuse(f, mode=mode, **kwargs)


class default(Exporter):
    '''Default exporter. Writes sqlite results, as well as the simulation YAML'''

    def start(self):
        if not self.dry_run:
            logger.info('Dumping results to %s', self.outdir)
            self.sim.dump_yaml(outdir=self.outdir)
        else:
            logger.info('NOT dumping results')

    def trial_end(self, env):
        if not self.dry_run:
            with timer('Dumping simulation {} trial {}'.format(self.sim.name,
                                                               env.name)):
                with self.output('{}.sqlite'.format(env.name), mode='wb') as f:
                    env.dump_sqlite(f)


class csv(Exporter):
    '''Export the state of each environment (and its agents) in a separate CSV file'''
    def trial_end(self, env):
        with timer('[CSV] Dumping simulation {} trial {} @ dir {}'.format(self.sim.name,
                                                                          env.name,
                                                                          self.outdir)):
            with self.output('{}.csv'.format(env.name)) as f:
                env.dump_csv(f)


class gexf(Exporter):
    def trial_end(self, env):
        if self.dry_run:
            logger.info('Not dumping GEXF in dry_run mode')
            return

        with timer('[GEXF] Dumping simulation {} trial {}'.format(self.sim.name,
                                                                  env.name)):
            with self.output('{}.gexf'.format(env.name), mode='wb') as f:
                env.dump_gexf(f)


class dummy(Exporter):

    def start(self):
        with self.output('dummy', 'w') as f:
            f.write('simulation started @ {}\n'.format(time.time()))

    def trial_end(self, env):
        with self.output('dummy', 'w') as f:
            for i in env.history_to_tuples():
                f.write(','.join(map(str, i)))
                f.write('\n')

    def end(self):
        with self.output('dummy', 'a') as f:
            f.write('simulation ended @ {}\n'.format(time.time()))


class distribution(Exporter):
    '''
    Write the distribution of agent states at the end of each trial,
    the mean value, and its deviation.
    '''

    def start(self):
        self.means = []
        self.counts = []

    def trial_end(self, env):
        df = env[None, None, None].df()
        ix = df.index[-1]
        attrs = df.columns.levels[0]
        vc = {}
        stats = {}
        for a in attrs:
            t = df.loc[(ix, a)]
            try:
                self.means.append(('mean', a, t.mean()))
            except TypeError:
                for name, count in t.value_counts().iteritems():
                    self.counts.append(('count', a, name, count))

    def end(self):
        dfm = pd.DataFrame(self.means, columns=['metric', 'key', 'value'])
        dfc = pd.DataFrame(self.counts, columns=['metric', 'key', 'value', 'count'])
        dfm = dfm.groupby(by=['key']).agg(['mean', 'std', 'count', 'median', 'max', 'min'])
        dfc = dfc.groupby(by=['key', 'value']).agg(['mean', 'std', 'count', 'median', 'max', 'min'])
        with self.output('counts.csv') as f:
            dfc.to_csv(f)
        with self.output('metrics.csv') as f:
            dfm.to_csv(f)

class graphdrawing(Exporter):

    def trial_end(self, env):
        # Outside effects
        f = plt.figure()
        nx.draw(env.G, node_size=10, width=0.2, pos=nx.spring_layout(env.G, scale=100), ax=f.add_subplot(111))
        with open('graph-{}.png'.format(env.name)) as f:
            f.savefig(f)
