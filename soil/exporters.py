import os
from time import time as current_time
from io import BytesIO
from sqlalchemy import create_engine


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

    def sim_start(self):
        '''Method to call when the simulation starts'''
        pass

    def sim_end(self):
        '''Method to call when the simulation ends'''
        pass

    def trial_start(self, env):
        '''Method to call when a trial start'''
        pass

    def trial_end(self, env):
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

    # def sim_start(self):
    #     if not self.dry_run:
    #         logger.info('Dumping results to %s', self.outdir)
    #         self.simulation.dump_yaml(outdir=self.outdir)
    #     else:
    #         logger.info('NOT dumping results')

    # def trial_start(self, env, stats):
    #     if not self.dry_run:
    #         with timer('Dumping simulation {} trial {}'.format(self.simulation.name,
    #                                                            env.name)):
    #             engine = create_engine('sqlite:///{}.sqlite'.format(env.name), echo=False)

    #             dc = env.datacollector
    #             tables = {'env': dc.get_model_vars_dataframe(),
    #                       'agents': dc.get_agent_vars_dataframe(),
    #                       'agents': dc.get_agent_vars_dataframe()}
    #             for table in dc.tables:
    #                 tables[table] = dc.get_table_dataframe(table)
    #             for (t, df) in tables.items():
    #                 df.to_sql(t, con=engine)

    # def sim_end(self, stats):
    #       with timer('Dumping simulation {}\'s stats'.format(self.simulation.name)):
    #           engine = create_engine('sqlite:///{}.sqlite'.format(self.simulation.name), echo=False)
    #           with self.output('{}.sqlite'.format(self.simulation.name), mode='wb') as f:
    #               self.simulation.dump_sqlite(f)


def get_dc_dfs(dc):
    dfs = {'env': dc.get_model_vars_dataframe(),
        'agents': dc.get_agent_vars_dataframe }
    for table_name in dc.tables:
        dfs[table_name] = dc.get_table_dataframe(table_name)
    yield from dfs.items() 


class csv(Exporter):

    '''Export the state of each environment (and its agents) in a separate CSV file'''
    def trial_end(self, env):
        with timer('[CSV] Dumping simulation {} trial {} @ dir {}'.format(self.simulation.name,
                                                                          env.id,
                                                                          self.outdir)):
            for (df_name, df) in get_dc_dfs(env.datacollector):
                with self.output('{}.stats.{}.csv'.format(env.id, df_name)) as f:
                    df.to_csv(f)


class gexf(Exporter):
    def trial_end(self, env):
        if self.dry_run:
            logger.info('Not dumping GEXF in dry_run mode')
            return

        with timer('[GEXF] Dumping simulation {} trial {}'.format(self.simulation.name,
                                                                  env.id)):
            with self.output('{}.gexf'.format(env.id), mode='wb') as f:
                self.dump_gexf(env, f)

    def dump_gexf(self, env, f):
        G = env.history_to_graph()
        # Workaround for geometric models
        # See soil/soil#4
        for node in G.nodes():
            if 'pos' in G.nodes[node]:
                G.nodes[node]['viz'] = {"position": {"x": G.nodes[node]['pos'][0], "y": G.nodes[node]['pos'][1], "z": 0.0}}
                del (G.nodes[node]['pos'])

        nx.write_gexf(G, f, version="1.2draft")

class dummy(Exporter):

    def sim_start(self):
        with self.output('dummy', 'w') as f:
            f.write('simulation started @ {}\n'.format(current_time()))

    def trial_start(self, env):
        with self.output('dummy', 'w') as f:
            f.write('trial started@ {}\n'.format(current_time()))

    def trial_end(self, env):
        with self.output('dummy', 'w') as f:
            f.write('trial ended@ {}\n'.format(current_time()))

    def sim_end(self):
        with self.output('dummy', 'a') as f:
            f.write('simulation ended @ {}\n'.format(current_time()))

class graphdrawing(Exporter):

    def trial_end(self, env):
        # Outside effects
        f = plt.figure()
        nx.draw(env.G, node_size=10, width=0.2, pos=nx.spring_layout(env.G, scale=100), ax=f.add_subplot(111))
        with open('graph-{}.png'.format(env.id)) as f:
            f.savefig(f)

'''
Convert an environment into a NetworkX graph
'''
def env_to_graph(env, history=None):
    G = nx.Graph(env.G)

    for agent in env.network_agents:

        attributes = {'agent': str(agent.__class__)}
        lastattributes = {}
        spells = []
        lastvisible = False
        laststep = None
        if not history:
            history = sorted(list(env.state_to_tuples()))
        for _, t_step, attribute, value in history:
            if attribute == 'visible':
                nowvisible = value
                if nowvisible and not lastvisible:
                    laststep = t_step
                if not nowvisible and lastvisible:
                    spells.append((laststep, t_step))

                lastvisible = nowvisible
                continue
            key = 'attr_' + attribute
            if key not in attributes:
                attributes[key] = list()
            if key not in lastattributes:
                lastattributes[key] = (value, t_step)
            elif lastattributes[key][0] != value:
                last_value, laststep = lastattributes[key]
                commit_value = (last_value, laststep, t_step)
                if key not in attributes:
                    attributes[key] = list()
                attributes[key].append(commit_value)
                lastattributes[key] = (value, t_step)
        for k, v in lastattributes.items():
            attributes[k].append((v[0], v[1], None))
        if lastvisible:
            spells.append((laststep, None))
        if spells:
            G.add_node(agent.id, spells=spells, **attributes)
        else:
            G.add_node(agent.id, **attributes)

    return G
