import os
import sqlite3
import time
import csv
import random
import simpy
import tempfile
from copy import deepcopy
from networkx.readwrite import json_graph

import networkx as nx
import nxsim

from . import utils, agents


class SoilEnvironment(nxsim.NetworkEnvironment):

    def __init__(self, name=None,
                 network_agents=None,
                 environment_agents=None,
                 states=None,
                 default_state=None,
                 interval=1,
                 seed=None,
                 dry_run=False,
                 dir_path=None,
                 topology=None,
                 *args, **kwargs):
        self.name = name or 'UnnamedEnvironment'
        if isinstance(states, list):
            states = dict(enumerate(states))
        self.states = deepcopy(states) if states else {}
        self.default_state = deepcopy(default_state) or {}
        if not topology:
            topology = nx.Graph()
        super().__init__(*args, topology=topology, **kwargs)
        self._env_agents = {}
        self.dry_run = dry_run
        self.interval = interval
        # Add environment agents first, so their events get
        # executed before network agents
        self['SEED'] = seed or time.time()
        random.seed(self['SEED'])
        self.process(self.save_state())
        self.environment_agents = environment_agents or []
        self.network_agents = network_agents or []
        self.dir_path = dir_path or tempfile.mkdtemp('soil-env')
        if self.dry_run:
            self._db_path = ":memory:"
        else:
            self._db_path = os.path.join(self.get_path(), '{}.db.sqlite'.format(self.name))
        self.create_db(self._db_path)

    def create_db(self, db_path=None):
        db_path = db_path or self._db_path
        if os.path.exists(db_path):
            newname = db_path.replace('db.sqlite', 'backup{}.sqlite'.format(time.time()))
            os.rename(db_path, newname)
        self._db = sqlite3.connect(db_path)
        with self._db:
            self._db.execute('''CREATE TABLE IF NOT EXISTS history (agent_id text, t_step int, key text, value text, value_type text)''')

    @property
    def agents(self):
        yield from self.environment_agents
        yield from self.network_agents

    @property
    def environment_agents(self):
        for ref in self._env_agents.values():
            yield ref

    @environment_agents.setter
    def environment_agents(self, environment_agents):
        # Set up environmental agent
        self._env_agents = {}
        for item in environment_agents:
            kwargs = deepcopy(item)
            atype = kwargs.pop('agent_type')
            kwargs['agent_id'] = kwargs.get('agent_id', atype.__name__)
            kwargs['state'] = kwargs.get('state', {})
            a = atype(environment=self, **kwargs)
            self._env_agents[a.id] = a

    @property
    def network_agents(self):
        for i in self.G.nodes():
            node = self.G.node[i]
            if 'agent' in node:
                yield node['agent']

    @network_agents.setter
    def network_agents(self, network_agents):
        if not network_agents:
            return
        for ix in self.G.nodes():
            i = ix
            node = self.G.node[i]
            agent, state = agents._agent_from_distribution(network_agents)
            self.set_agent(i, agent_type=agent, state=state)

    def set_agent(self, agent_id, agent_type, state=None):
        node = self.G.nodes[agent_id]
        defstate = deepcopy(self.default_state)
        defstate.update(self.states.get(agent_id, {}))
        if state:
            defstate.update(state)
        state = defstate
        state.update(node.get('state', {}))
        a = agent_type(environment=self,
                       agent_id=agent_id,
                       state=state)
        node['agent'] = a
        return a

    def add_node(self, agent_type, state=None):
        agent_id = int(len(self.G.nodes()))
        self.G.add_node(agent_id)
        a = self.set_agent(agent_id, agent_type, state)
        a['visible'] = True
        return a

    def add_edge(self, agent1, agent2, attrs=None):
        return self.G.add_edge(agent1, agent2)

    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)

    def _save_state(self, now=None):
        # for agent in self.agents:
        #     agent.save_state()
        utils.logger.debug('Saving state @{}'.format(self.now))
        with self._db:
            self._db.executemany("insert into history(agent_id, t_step, key, value, value_type) values (?, ?, ?, ?, ?)", self.state_to_tuples(now=now))

    def save_state(self):
        self._save_state()
        while self.peek() != simpy.core.Infinity:
            delay = max(self.peek() - self.now, self.interval)
            utils.logger.debug('Step: {}'.format(self.now))
            ev = self.event()
            ev._ok = True
            # Schedule the event with minimum priority so
            # that it executes before all agents
            self.schedule(ev, -999, delay)
            yield ev
            self._save_state()

    def __getitem__(self, key):
        if isinstance(key, tuple):
            values = [("agent_id", key[0]),
                      ("t_step", key[1]),
                      ("key", key[2]),
                      ("value", None),
                      ("value_type", None)]
            fields = list(k for k, v in values if v is None)
            conditions = " and ".join("{}='{}'".format(k, v) for k, v in values if v is not None)

            query = """SELECT {fields} from history""".format(fields=",".join(fields))
            if conditions:
                query = """{query} where {conditions}""".format(query=query,
                                                                conditions=conditions)
            with self._db:
                rows = self._db.execute(query).fetchall()

            utils.logger.debug(rows)
            results = self.rows_to_dict(rows)
            return results

        return self.environment_params[key]

    def rows_to_dict(self, rows):
        if len(rows) < 1:
            return None

        level = len(rows[0])-2

        if level == 0:
            if len(rows) != 1:
                raise ValueError('Cannot convert {} to dictionaries'.format(rows))
            value, value_type = rows[0]
            return utils.convert(value, value_type)

        results = {}
        for row in rows:
            item = results
            for i in range(level-1):
                key = row[i]
                if key not in item:
                    item[key] = {}
                item = item[key]
            key, value, value_type = row[level-1:]
            item[key] = utils.convert(value, value_type)
        return results

    def __setitem__(self, key, value):
        self.environment_params[key] = value

    def __contains__(self, key):
        return key in self.environment_params

    def get(self, key, default=None):
        return self[key] if key in self else default

    def get_path(self, dir_path=None):
        dir_path = dir_path or self.dir_path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return dir_path

    def get_agent(self, agent_id):
        return self.G.node[agent_id]['agent']

    def get_agents(self):
        return list(self.agents)

    def dump_csv(self, dir_path=None):
        csv_name = os.path.join(self.get_path(dir_path),
                                '{}.environment.csv'.format(self.name))

        with open(csv_name, 'w') as f:
            cr = csv.writer(f)
            cr.writerow(('agent_id', 't_step', 'key', 'value', 'value_type'))
            for i in self.history_to_tuples():
                cr.writerow(i)

    def dump_gexf(self, dir_path=None):
        G = self.history_to_graph()
        graph_path = os.path.join(self.get_path(dir_path),
                                  self.name+".gexf")
        # Workaround for geometric models
        # See soil/soil#4
        for node in G.nodes():
            if 'pos' in G.node[node]:
                G.node[node]['viz'] = {"position": {"x": G.node[node]['pos'][0], "y": G.node[node]['pos'][1], "z": 0.0}}
                del (G.node[node]['pos'])

        nx.write_gexf(G, graph_path, version="1.2draft")

    def dump(self, dir_path=None, formats=None):
        if not formats:
            return
        functions = {
            'csv': self.dump_csv,
            'gexf': self.dump_gexf
        }
        for f in formats:
            if f in functions:
                functions[f](dir_path)
            else:
                raise ValueError('Unknown format: {}'.format(f))

    def state_to_tuples(self, now=None):
        if now is None:
            now = self.now
        for k, v in self.environment_params.items():
            v, v_t = utils.repr(v)
            yield 'env', now, k, v, v_t
        for agent in self.agents:
            for k, v in agent.state.items():
                v, v_t = utils.repr(v)
                yield agent.id, now, k, v, v_t

    def history_to_tuples(self):
        with self._db:
            res = self._db.execute("select agent_id, t_step, key, value, value_type from history ").fetchall()
        yield from res

    def history_to_graph(self):
        G = nx.Graph(self.G)

        for agent in self.network_agents:

            attributes = {'agent': str(agent.__class__)}
            lastattributes = {}
            spells = []
            lastvisible = False
            laststep = None
            history = self[agent.id, None, None]
            if not history:
                continue
            for t_step, state in reversed(sorted(list(history.items()))):
                for attribute, value in state.items():
                    if attribute == 'visible':
                        nowvisible = state[attribute]
                        if nowvisible and not lastvisible:
                            laststep = t_step
                        if not nowvisible and lastvisible:
                            spells.append((laststep, t_step))

                        lastvisible = nowvisible
                    else:
                        key = 'attr_' + attribute
                        if key not in attributes:
                            attributes[key] = list()
                        if key not in lastattributes:
                            lastattributes[key] = (state[attribute], t_step)
                        elif lastattributes[key][0] != value:
                            last_value, laststep = lastattributes[key]
                            value = (last_value, t_step, laststep)
                            if key not in attributes:
                                attributes[key] = list()
                            attributes[key].append(value)
                            lastattributes[key] = (state[attribute], t_step)
            for k, v in lastattributes.items():
                attributes[k].append((v[0], 0, v[1]))
            if lastvisible:
                spells.append((laststep, None))
            if spells:
                G.add_node(agent.id, spells=spells, **attributes)
            else:
                G.add_node(agent.id, **attributes)

        return G

    def __getstate__(self):
        state = self.__dict__.copy()
        state['G'] = json_graph.node_link_data(self.G)
        state['network_agents'] = agents.serialize_distribution(self.network_agents)
        state['environment_agents'] = agents._convert_agent_types(self.environment_agents,
                                                                 to_string=True)
        del state['_queue']
        import inspect
        for k, v in state.items():
            if inspect.isgeneratorfunction(v):
                print(k, v, type(v))
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.G = json_graph.node_link_graph(state['G'])
        self.network_agents = self.calculate_distribution(self._convert_agent_types(self.network_agents))
        self.environment_agents = self._convert_agent_types(self.environment_agents)
        return state
