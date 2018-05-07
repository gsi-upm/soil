import os
import sqlite3
import time
import csv
import random
import simpy
import tempfile
import pandas as pd
from copy import deepcopy
from networkx.readwrite import json_graph

import networkx as nx
import nxsim

from . import utils, agents, analysis, history


class SoilEnvironment(nxsim.NetworkEnvironment):
    """
    The environment is key in a simulation. It contains the network topology,
    a reference to network and environment agents, as well as the environment
    params, which are used as shared state between agents.

    The environment parameters and the state of every agent can be accessed
    both by using the environment as a dictionary or with the environment's 
    :meth:`soil.environment.SoilEnvironment.get` method.
    """

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
        self.dir_path = dir_path or tempfile.mkdtemp('soil-env')
        self.get_path()
        self._history = history.History(name=self.name if not dry_run else None,
                                        dir_path=self.dir_path)
        # Add environment agents first, so their events get
        # executed before network agents
        self.environment_agents = environment_agents or []
        self.network_agents = network_agents or []
        self['SEED'] = seed or time.time()
        random.seed(self['SEED'])

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
            agent, state = agents._agent_from_distribution(network_agents)
            self.set_agent(ix, agent_type=agent, state=state)

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
        self._save_state()
        super().run(*args, **kwargs)
        self._history.flush_cache()

    def _save_state(self, now=None):
        # for agent in self.agents:
        #     agent.save_state()
        utils.logger.debug('Saving state @{}'.format(self.now))
        self._history.save_records(self.state_to_tuples(now=now))

    def save_state(self):
        '''
        :DEPRECATED:
        Periodically save the state of the environment and the agents.
        '''
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
            self._history.flush_cache()
            return self._history[key]

        return self.environment_params[key]

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            k = history.Key(*key)
            self._history.save_record(*k,
                                      value=value)
            return
        self.environment_params[key] = value
        self._history.save_record(agent_id='env',
                                  t_step=self.now,
                                  key=key,
                                  value=value)

    def __contains__(self, key):
        return key in self.environment_params

    def get(self, key, default=None):
        '''
        Get the value of an environment attribute in a
        given point in the simulation (history).
        If key is an attribute name, this method returns
        the current value.
        To get values at other times, use a
        :meth: `soil.history.Key` tuple.
        '''
        return self[key] if key in self else default

    def get_path(self, dir_path=None):
        dir_path = dir_path or self.dir_path
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except FileExistsError:
                pass
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
            yield history.Record(agent_id='env',
                                 t_step=now,
                                 key=k,
                                 value=v)
        for agent in self.agents:
            for k, v in agent.state.items():
                yield history.Record(agent_id=agent.id,
                                     t_step=now,
                                     key=k,
                                     value=v)

    def history_to_tuples(self):
        return self._history.to_tuples()

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
            for t_step, attribute, value in sorted(list(history)):
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

    def __getstate__(self):
        state = self.__dict__.copy()
        state['G'] = json_graph.node_link_data(self.G)
        state['network_agents'] = agents._serialize_distribution(self.network_agents)
        state['environment_agents'] = agents._convert_agent_types(self.environment_agents,
                                                                 to_string=True)
        del state['_queue']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.G = json_graph.node_link_graph(state['G'])
        self.network_agents = self.calculate_distribution(self._convert_agent_types(self.network_agents))
        self.environment_agents = self._convert_agent_types(self.environment_agents)
        return state
