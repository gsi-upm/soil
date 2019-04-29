import os
import sqlite3
import time
import csv
import random
import simpy
import yaml
import tempfile
import pandas as pd
from copy import deepcopy
from collections import Counter
from networkx.readwrite import json_graph

import networkx as nx
import nxsim

from . import serialization, agents, analysis, history, utils

# These properties will be copied when pickling/unpickling the environment
_CONFIG_PROPS = [ 'name',
                 'states',
                 'default_state',
                 'interval',
                 ]

class Environment(nxsim.NetworkEnvironment):
    """
    The environment is key in a simulation. It contains the network topology,
    a reference to network and environment agents, as well as the environment
    params, which are used as shared state between agents.

    The environment parameters and the state of every agent can be accessed
    both by using the environment as a dictionary or with the environment's 
    :meth:`soil.environment.Environment.get` method.
    """

    def __init__(self, name=None,
                 network_agents=None,
                 environment_agents=None,
                 states=None,
                 default_state=None,
                 interval=1,
                 seed=None,
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
        self.interval = interval
        self._history = history.History(name=self.name,
                                        backup=True)
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
        self._network_agents = network_agents
        for ix in self.G.nodes():
            self.init_agent(ix, agent_distribution=network_agents)

    def init_agent(self, agent_id, agent_distribution):
        node = self.G.nodes[agent_id]
        init = False
        state = dict(node)

        agent_type = None
        if 'agent_type' in self.states.get(agent_id, {}):
            agent_type = self.states[agent_id]['agent_type']
        elif 'agent_type' in node:
            agent_type = node['agent_type']
        elif 'agent_type' in self.default_state:
            agent_type = self.default_state['agent_type']

        if agent_type:
            agent_type = agents.deserialize_type(agent_type)
        elif agent_distribution:
            agent_type, state = agents._agent_from_distribution(agent_distribution, agent_id=agent_id)
        else:
            serialization.logger.debug('Skipping node {}'.format(agent_id))
            return
        return self.set_agent(agent_id, agent_type, state)

    def set_agent(self, agent_id, agent_type, state=None):
        node = self.G.nodes[agent_id]
        defstate = deepcopy(self.default_state) or {}
        defstate.update(self.states.get(agent_id, {}))
        defstate.update(node.get('state', {}))
        if state:
            defstate.update(state)
        a = None
        if agent_type:
            state = defstate
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

    def add_edge(self, agent1, agent2, start=None, **attrs):
        if hasattr(agent1, 'id'):
            agent1 = agent1.id
        if hasattr(agent2, 'id'):
            agent2 = agent2.id
        start = start or self.now
        return self.G.add_edge(agent1, agent2, **attrs)

    def run(self, *args, **kwargs):
        self._save_state()
        self.log_stats()
        super().run(*args, **kwargs)
        self._history.flush_cache()
        self.log_stats()

    def _save_state(self, now=None):
        serialization.logger.debug('Saving state @{}'.format(self.now))
        self._history.save_records(self.state_to_tuples(now=now))

    def save_state(self):
        '''
        :DEPRECATED:
        Periodically save the state of the environment and the agents.
        '''
        self._save_state()
        while self.peek() != simpy.core.Infinity:
            delay = max(self.peek() - self.now, self.interval)
            serialization.logger.debug('Step: {}'.format(self.now))
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

    def get_agent(self, agent_id):
        return self.G.node[agent_id]['agent']

    def get_agents(self, nodes=None):
        if nodes is None:
            return list(self.agents)
        return [self.G.node[i]['agent'] for i in nodes]

    def dump_csv(self, f):
        with utils.open_or_reuse(f, 'w') as f:
            cr = csv.writer(f)
            cr.writerow(('agent_id', 't_step', 'key', 'value'))
            for i in self.history_to_tuples():
                cr.writerow(i)

    def dump_gexf(self, f):
        G = self.history_to_graph()
        # Workaround for geometric models
        # See soil/soil#4
        for node in G.nodes():
            if 'pos' in G.node[node]:
                G.node[node]['viz'] = {"position": {"x": G.node[node]['pos'][0], "y": G.node[node]['pos'][1], "z": 0.0}}
                del (G.node[node]['pos'])

        nx.write_gexf(G, f, version="1.2draft")

    def dump(self, *args, formats=None, **kwargs):
        if not formats:
            return
        functions = {
            'csv': self.dump_csv,
            'gexf': self.dump_gexf
        }
        for f in formats:
            if f in functions:
                functions[f](*args, **kwargs)
            else:
                raise ValueError('Unknown format: {}'.format(f))

    def dump_sqlite(self, f):
        return self._history.dump(f)

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

    def stats(self):
        stats = {}
        stats['network'] = {}
        stats['network']['n_nodes'] = self.G.number_of_nodes()
        stats['network']['n_edges'] = self.G.number_of_edges()
        c = Counter()
        c.update(a.__class__.__name__ for a in self.network_agents)
        stats['agents'] = {}
        stats['agents']['model_count'] = dict(c)
        c2 = Counter()
        c2.update(a['id'] for a in self.network_agents)
        stats['agents']['state_count'] = dict(c2)
        stats['params'] = self.environment_params
        return stats

    def log_stats(self):
        stats = self.stats()
        serialization.logger.info('Environment stats: \n{}'.format(yaml.dump(stats, default_flow_style=False)))
    
    def __getstate__(self):
        state = {}
        for prop in _CONFIG_PROPS:
            state[prop] = self.__dict__[prop]
        state['G'] = json_graph.node_link_data(self.G)
        state['environment_agents'] = self._env_agents
        state['history'] = self._history
        return state

    def __setstate__(self, state):
        for prop in _CONFIG_PROPS:
            self.__dict__[prop] = state[prop]
        self._env_agents = state['environment_agents']
        self.G = json_graph.node_link_graph(state['G'])
        self._history = state['history']


SoilEnvironment = Environment
