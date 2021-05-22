import os
import csv as csvlib
import time
from io import BytesIO

import matplotlib.pyplot as plt
import networkx as nx


from .serialization import deserialize
from .utils import open_or_reuse, logger, timer


from . import utils


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
        content = '(binary data not shown)'
        try:
            content = self.getvalue().decode()
        except UnicodeDecodeError:
            pass
        logger.info('**Not** written to {} (dry run mode):\n\n{}\n\n'.format(self.__fname, content))
        super().close()


class Exporter:
    '''
    Interface for all exporters. It is not necessary, but it is useful
    if you don't plan to implement all the methods.
    '''

    def __init__(self, simulation, outdir=None, dry_run=None, copy_to=None):
        self.simulation = simulation
        outdir = outdir or os.path.join(os.getcwd(), 'soil_output')
        self.outdir = os.path.join(outdir,
                                   simulation.group or '',
                                   simulation.name)
        self.dry_run = dry_run
        self.copy_to = copy_to

    def start(self):
        '''Method to call when the simulation starts'''
        pass

    def end(self, stats):
        '''Method to call when the simulation ends'''
        pass

    def trial(self, env, stats):
        '''Method to call when a trial ends'''
        pass

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
            self.simulation.dump_yaml(outdir=self.outdir)
        else:
            logger.info('NOT dumping results')

    def trial(self, env, stats):
        if not self.dry_run:
            with timer('Dumping simulation {} trial {}'.format(self.simulation.name,
                                                               env.name)):
                with self.output('{}.sqlite'.format(env.name), mode='wb') as f:
                    env.dump_sqlite(f)

    def end(self, stats):
          with timer('Dumping simulation {}\'s stats'.format(self.simulation.name)):
              with self.output('{}.sqlite'.format(self.simulation.name), mode='wb') as f:
                  self.simulation.dump_sqlite(f)



class csv(Exporter):
    '''Export the state of each environment (and its agents) in a separate CSV file'''
    def trial(self, env, stats):
        with timer('[CSV] Dumping simulation {} trial {} @ dir {}'.format(self.simulation.name,
                                                                          env.name,
                                                                          self.outdir)):
            with self.output('{}.csv'.format(env.name)) as f:
                env.dump_csv(f)

            with self.output('{}.stats.csv'.format(env.name)) as f:
                statwriter = csvlib.writer(f, delimiter='\t', quotechar='"', quoting=csvlib.QUOTE_ALL)

                for stat in stats:
                    statwriter.writerow(stat)


class gexf(Exporter):
    def trial(self, env, stats):
        if self.dry_run:
            logger.info('Not dumping GEXF in dry_run mode')
            return

        with timer('[GEXF] Dumping simulation {} trial {}'.format(self.simulation.name,
                                                                  env.name)):
            with self.output('{}.gexf'.format(env.name), mode='wb') as f:
                env.dump_gexf(f)


class dummy(Exporter):

    def start(self):
        with self.output('dummy', 'w') as f:
            f.write('simulation started @ {}\n'.format(time.time()))

    def trial(self, env, stats):
        with self.output('dummy', 'w') as f:
            for i in env.history_to_tuples():
                f.write(','.join(map(str, i)))
                f.write('\n')

    def sim(self, stats):
        with self.output('dummy', 'a') as f:
            f.write('simulation ended @ {}\n'.format(time.time()))



class graphdrawing(Exporter):

    def trial(self, env, stats):
        # Outside effects
        f = plt.figure()
        nx.draw(env.G, node_size=10, width=0.2, pos=nx.spring_layout(env.G, scale=100), ax=f.add_subplot(111))
        with open('graph-{}.png'.format(env.name)) as f:
            f.savefig(f)

