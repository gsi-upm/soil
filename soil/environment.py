import os
import sqlite3
import csv
import math
import random
import yaml
import tempfile
import pandas as pd
from time import time as current_time
from copy import deepcopy
from networkx.readwrite import json_graph

import networkx as nx

from tsih import History, Record, Key, NoHistory

from mesa import Model

from . import serialization, agents, analysis, utils, time

# These properties will be copied when pickling/unpickling the environment
_CONFIG_PROPS = [ 'name',
                  'states',
                  'default_state',
                  'interval',
                 ]

class Environment(Model):
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
                 network_params=None,
                 seed=None,
                 topology=None,
                 schedule=None,
                 initial_time=0,
                 environment_params=None,
                 history=True,
                 dir_path=None,
                 **kwargs):


        super().__init__()

        self.schedule = schedule
        if schedule is None:
            self.schedule = time.TimedActivation()

        self.name = name or 'UnnamedEnvironment'
        seed = seed or current_time()
        random.seed(seed)
        if isinstance(states, list):
            states = dict(enumerate(states))
        self.states = deepcopy(states) if states else {}
        self.default_state = deepcopy(default_state) or {}

        if topology is None:
            network_params = network_params or {}
            topology = serialization.load_network(network_params,
                                                  dir_path=dir_path)
        if not topology:
            topology = nx.Graph()
        self.G = nx.Graph(topology) 


        self.environment_params = environment_params or {}
        self.environment_params.update(kwargs)

        self._env_agents = {}
        self.interval = interval
        if history:
            history = History
        else:
            history = NoHistory
        self._history = history(name=self.name,
                                backup=True)
        self['SEED'] = seed

        if network_agents:
            distro = agents.calculate_distribution(network_agents)
            self.network_agents = agents._convert_agent_types(distro)
        else:
            self.network_agents = []

        environment_agents = environment_agents or []
        if environment_agents:
            distro = agents.calculate_distribution(environment_agents)
            environment_agents = agents._convert_agent_types(distro)
        self.environment_agents = environment_agents

    @property
    def now(self):
        if self.schedule:
            return self.schedule.time
        raise Exception('The environment has not been scheduled, so it has no sense of time')

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
        self._environment_agents = environment_agents

        self._env_agents = agents._definition_to_dict(definition=environment_agents)

    @property
    def network_agents(self):
        for i in self.G.nodes():
            node = self.G.nodes[i]
            if 'agent' in node:
                yield node['agent']

    @network_agents.setter
    def network_agents(self, network_agents):
        self._network_agents = network_agents
        for ix in self.G.nodes():
            self.init_agent(ix, agent_definitions=network_agents)

    def init_agent(self, agent_id, agent_definitions):
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
        elif agent_definitions:
            agent_type, state = agents._agent_from_definition(agent_definitions, unique_id=agent_id)
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
            a = agent_type(model=self,
                           unique_id=agent_id)

        for (k, v) in getattr(a, 'defaults', {}).items():
            if not hasattr(a, k) or getattr(a, k) is None:
                setattr(a, k, v)

        for (k, v) in state.items():
            setattr(a, k, v)

        node['agent'] = a
        self.schedule.add(a)
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

    def step(self):
        super().step()
        self.datacollector.collect(self)
        self.schedule.step()

    def run(self, until, *args, **kwargs):
        self._save_state()

        while self.schedule.next_time <= until and not math.isinf(self.schedule.next_time):
            self.schedule.step(until=until)
            utils.logger.debug(f'Simulation step {self.schedule.time}/{until}. Next: {self.schedule.next_time}')
        self._history.flush_cache()

    def _save_state(self, now=None):
        serialization.logger.debug('Saving state @{}'.format(self.now))
        self._history.save_records(self.state_to_tuples(now=now))

    def __getitem__(self, key):
        if isinstance(key, tuple):
            self._history.flush_cache()
            return self._history[key]

        return self.environment_params[key]

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            k = Key(*key)
            self._history.save_record(*k,
                                      value=value)
            return
        self.environment_params[key] = value
        self._history.save_record(dict_id='env',
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
        return self.G.nodes[agent_id]['agent']

    def get_agents(self, nodes=None):
        if nodes is None:
            return self.agents
        return (self.G.nodes[i]['agent'] for i in nodes)

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
            if 'pos' in G.nodes[node]:
                G.nodes[node]['viz'] = {"position": {"x": G.nodes[node]['pos'][0], "y": G.nodes[node]['pos'][1], "z": 0.0}}
                del (G.nodes[node]['pos'])

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
            yield Record(dict_id='env',
                         t_step=now,
                         key=k,
                         value=v)
        for agent in self.agents:
            for k, v in agent.state.items():
                yield Record(dict_id=agent.id,
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
        state = {}
        for prop in _CONFIG_PROPS:
            state[prop] = self.__dict__[prop]
        state['G'] = json_graph.node_link_data(self.G)
        state['environment_agents'] = self._env_agents
        state['history'] = self._history
        state['schedule'] = self.schedule
        return state

    def __setstate__(self, state):
        for prop in _CONFIG_PROPS:
            self.__dict__[prop] = state[prop]
        self._env_agents = state['environment_agents']
        self.G = json_graph.node_link_graph(state['G'])
        self._history = state['history']
        # self._env = None
        self.schedule = state['schedule']
        self._queue = []


SoilEnvironment = Environment
