from __future__ import annotations
import os
import sqlite3
import math
import random
import logging

from typing import Any, Dict, Optional, Union
from collections import namedtuple
from time import time as current_time
from copy import deepcopy
from networkx.readwrite import json_graph


import networkx as nx

from mesa import Model
from mesa.datacollection import DataCollector

from . import serialization, analysis, utils, time, network

from .agents import AgentView, BaseAgent, NetworkAgent, from_config as agents_from_config


Record = namedtuple('Record', 'dict_id t_step key value')


class BaseEnvironment(Model):
    """
    The environment is key in a simulation. It controls how agents interact,
    and what information is available to them.

    This is an opinionated version of `mesa.Model` class, which adds many
    convenience methods and abstractions.

    The environment parameters and the state of every agent can be accessed
    both by using the environment as a dictionary and with the environment's
    :meth:`soil.environment.Environment.get` method.
    """

    def __init__(self,
                 env_id='unnamed_env',
                 seed='default',
                 schedule=None,
                 dir_path=None,
                 interval=1,
                 agent_class=BaseAgent,
                 agents: [tuple[type, Dict[str, Any]]] = {},
                 agent_reporters: Optional[Any] = None,
                 model_reporters: Optional[Any] = None,
                 tables: Optional[Any] = None,
                 **env_params):

        super().__init__(seed=seed)
        self.current_id = -1

        self.id = env_id

        self.dir_path = dir_path or os.getcwd()

        if schedule is None:
            schedule = time.TimedActivation(self)
        self.schedule = schedule

        self.agent_class = agent_class

        self.init_agents(agents)

        self.env_params = env_params or {}

        self.interval = interval

        self.logger = utils.logger.getChild(self.id)

        self.datacollector = DataCollector(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters,
            tables=tables,
        )

    def __read_agent_tuple(self, tup):
        cls = self.agent_class
        args = tup
        if isinstance(tup, tuple):
            cls = tup[0]
            args = tup[1]
        return serialization.deserialize(cls)(unique_id=self.next_id(),
                                              model=self, **args)

    def init_agents(self, agents: [tuple[type, Dict[str, Any]]] = {}):
        agents = [self.__read_agent_tuple(tup) for tup in agents]
        self._agents = {'default': {agent.id: agent for agent in agents}}

    @property
    def agents(self):
        return AgentView(self._agents)

    def find_one(self, *args, **kwargs):
        return AgentView(self._agents).one(*args, **kwargs)
    
    def count_agents(self, *args, **kwargs):
        return sum(1 for i in self.agents(*args, **kwargs))

    @property
    def now(self):
        if self.schedule:
            return self.schedule.time
        raise Exception('The environment has not been scheduled, so it has no sense of time')


    # def init_agent(self, agent_id, agent_definitions, state=None):
    #     state = state or {}

    #     agent_class = None
    #     if 'agent_class' in self.states.get(agent_id, {}):
    #         agent_class = self.states[agent_id]['agent_class']
    #     elif 'agent_class' in self.default_state:
    #         agent_class = self.default_state['agent_class']

    #     if agent_class:
    #         agent_class = agents.deserialize_type(agent_class)
    #     elif agent_definitions:
    #         agent_class, state = agents._agent_from_definition(agent_definitions, unique_id=agent_id)
    #     else:
    #         serialization.logger.debug('Skipping agent {}'.format(agent_id))
    #         return
    #     return self.add_agent(agent_id, agent_class, state)


    def add_agent(self, agent_id, agent_class, state=None, graph='default'):
        defstate = deepcopy(self.default_state) or {}
        defstate.update(self.states.get(agent_id, {}))
        if state:
            defstate.update(state)
        a = None
        if agent_class:
            state = defstate
            a = agent_class(model=self,
                           unique_id=agent_id)

        for (k, v) in state.items():
            setattr(a, k, v)

        self.schedule.add(a)
        return a

    def log(self, message, *args, level=logging.INFO, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        message = message + " ".join(str(i) for i in args)
        message = " @{:>3}: {}".format(self.now, message)
        for k, v in kwargs:
            message += " {k}={v} ".format(k, v)
        extra = {}
        extra['now'] = self.now
        extra['unique_id'] = self.id
        return self.logger.log(level, message, extra=extra)

    def step(self):
        '''
        Advance one step in the simulation, and update the data collection and scheduler appropriately
        '''
        super().step()
        self.schedule.step()
        self.datacollector.collect(self)

    def __contains__(self, key):
        return key in self.env_params

    def get(self, key, default=None):
        '''
        Get the value of an environment attribute.
        Return `default` if the value is not set.
        '''
        return self.env_params.get(key, default)

    def __getitem__(self, key):
        return self.env_params.get(key)

    def __setitem__(self, key, value):
        return self.env_params.__setitem__(key, value)

    def _agent_to_tuples(self, agent, now=None):
        if now is None:
            now = self.now
        for k, v in agent.state.items():
            yield Record(dict_id=agent.id,
                          t_step=now,
                          key=k,
                          value=v)

    def state_to_tuples(self, agent_id=None, now=None):
        if now is None:
            now = self.now

        if agent_id:
            agent = self.agents[agent_id]
            yield from self._agent_to_tuples(agent, now)
            return

        for k, v in self.env_params.items():
            yield Record(dict_id='env',
                         t_step=now,
                         key=k,
                         value=v)
        for agent in self.agents:
            yield from self._agent_to_tuples(agent, now)


class AgentConfigEnvironment(BaseEnvironment):

    def __init__(self, *args,
                 agents: Dict[str, config.AgentConfig] = {},
                 **kwargs):
        return super().__init__(*args, agents=agents, **kwargs)

    def init_agents(self, agents: Union[Dict[str, config.AgentConfig], [tuple[type, Dict[str, Any]]]] = {}):
        if not isinstance(agents, dict):
            return BaseEnvironment.init_agents(self, agents)

        self._agents = agents_from_config(agents,
                                          env=self,
                                          random=self.random)
        for d in self._agents.values():
            for a in d.values():
                self.schedule.add(a)


class NetworkConfigEnvironment(BaseEnvironment):

    def __init__(self, *args, topologies: Dict[str, config.NetConfig] = {}, **kwargs):
        super().__init__(*args, **kwargs)
        self.topologies = {}
        self._node_ids = {}
        for (name, cfg) in topologies.items():
            self.set_topology(cfg=cfg, graph=name)

    @property
    def topology(self):
        return self.topologies['default']

    def set_topology(self, cfg=None, dir_path=None, graph='default'):
        topology = cfg
        if not isinstance(cfg, nx.Graph):
            topology = network.from_config(cfg, dir_path=dir_path or self.dir_path)

        self.topologies[graph] = topology

    def topology_for(self, agent_id):
        return self.topologies[self._node_ids[agent_id][0]]

    @property
    def network_agents(self):
        yield from self.agents(agent_class=NetworkAgent)

    def agent_to_node(self, agent_id, graph_name='default', node_id=None, shuffle=False):
        node_id = network.agent_to_node(G=self.topologies[graph_name], agent_id=agent_id,
                                        node_id=node_id, shuffle=shuffle,
                                        random=self.random)

        self._node_ids[agent_id] = (graph_name, node_id)


    def add_node(self, agent_class, state=None, graph='default'):
        agent_id = int(len(self.topologies[graph].nodes()))
        self.topologies[graph].add_node(agent_id)
        a = self.add_agent(agent_id, agent_class, state, graph=graph)
        a['visible'] = True
        return a

    def add_edge(self, agent1, agent2, start=None, graph='default', **attrs):
        if hasattr(agent1, 'id'):
            agent1 = agent1.id
        if hasattr(agent2, 'id'):
            agent2 = agent2.id
        start = start or self.now
        return self.topologies[graph].add_edge(agent1, agent2, **attrs)

    def add_agent(self, *args, state=None, graph='default', **kwargs):
        node = self.topologies[graph].nodes[agent_id]
        node_state = node.get('state', {})
        if node_state:
            node_state.update(state or {})
            state = node_state
        a = super().add_agent(*args, state=state, **kwargs)
        node['agent'] = a
        return a

    def node_id_for(self, agent_id):
        return self._node_ids[agent_id][1]

class Environment(AgentConfigEnvironment, NetworkConfigEnvironment):
    def __init__(self, *args, **kwargs):
        agents = kwargs.pop('agents', {})
        NetworkConfigEnvironment.__init__(self, *args, **kwargs)
        AgentConfigEnvironment.__init__(self, *args, agents=agents, **kwargs)
