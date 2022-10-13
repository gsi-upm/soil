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

from . import agents as agentmod, config, serialization, utils, time, network


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
                 id='unnamed_env',
                 seed='default',
                 schedule=None,
                 dir_path=None,
                 interval=1,
                 agent_class=None,
                 agents: [tuple[type, Dict[str, Any]]] = {},
                 agent_reporters: Optional[Any] = None,
                 model_reporters: Optional[Any] = None,
                 tables: Optional[Any] = None,
                 **env_params):

        super().__init__(seed=seed)
        self.current_id = -1

        self.id = id

        self.dir_path = dir_path or os.getcwd()

        if schedule is None:
            schedule = time.TimedActivation(self)
        self.schedule = schedule

        self.agent_class = agent_class or agentmod.BaseAgent

        self.init_agents(agents)

        self.env_params = env_params or {}

        self.interval = interval

        self.logger = utils.logger.getChild(self.id)

        self.datacollector = DataCollector(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters,
            tables=tables,
        )

    def _read_single_agent(self, agent):
        agent = dict(**agent)
        cls = agent.pop('agent_class', None) or self.agent_class
        unique_id = agent.pop('unique_id', None)
        if unique_id is None:
            unique_id = self.next_id()

        return serialization.deserialize(cls)(unique_id=unique_id,
                                              model=self, **agent)

    def init_agents(self, agents: Union[config.AgentConfig, [Dict[str, Any]]] = {}):
        if not agents:
            return

        lst = agents
        override = []
        if not isinstance(lst, list):
            if not isinstance(agents, config.AgentConfig):
                lst = config.AgentConfig(**agents)
            if lst.override:
                override = lst.override
            lst = agentmod.from_config(lst,
                                       topologies=getattr(self, 'topologies', None),
                                       random=self.random)

        #TODO: check override is working again. It cannot (easily) be part of agents.from_config anymore, 
        # because it needs attribute such as unique_id, which are only present after init
        new_agents = [self._read_single_agent(agent) for agent in lst]


        for a in new_agents:
            self.schedule.add(a)

        for rule in override:
            for agent in agentmod.filter_agents(self.schedule._agents, **rule.filter):
                for attr, value in rule.state.items():
                    setattr(agent, attr, value)


    @property
    def agents(self):
        return agentmod.AgentView(self.schedule._agents)

    def find_one(self, *args, **kwargs):
        return agentmod.AgentView(self.schedule._agents).one(*args, **kwargs)
    
    def count_agents(self, *args, **kwargs):
        return sum(1 for i in self.agents(*args, **kwargs))

    @property
    def now(self):
        if self.schedule:
            return self.schedule.time
        raise Exception('The environment has not been scheduled, so it has no sense of time')


    def add_agent(self, agent_id, agent_class, **kwargs):
        a = None
        if agent_class:
            a = agent_class(model=self,
                            unique_id=agent_id,
                            **kwargs)

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
        extra['id'] = self.id
        return self.logger.log(level, message, extra=extra)

    def step(self):
        '''
        Advance one step in the simulation, and update the data collection and scheduler appropriately
        '''
        super().step()
        self.logger.info(f'--- Step {self.now:^5} ---')
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


class NetworkEnvironment(BaseEnvironment):

    def __init__(self, *args, topology: nx.Graph = None, topologies: Dict[str, config.NetConfig] = {}, **kwargs):
        agents = kwargs.pop('agents', None)
        super().__init__(*args, agents=None, **kwargs)
        self._node_ids = {}
        assert not hasattr(self, 'topologies')
        if topology is not None:
            if topologies:
                raise ValueError('Please, provide either a single topology or a dictionary of them')
            topologies = {'default': topology}

        self.topologies = {}
        for (name, cfg) in topologies.items():
            self.set_topology(cfg=cfg, graph=name)

        self.init_agents(agents)


    def _read_single_agent(self, agent, unique_id=None):
        agent = dict(agent)

        if agent.get('topology', None) is not None:
            topology = agent.get('topology')
            if unique_id is None:
                unique_id = self.next_id()
            if topology:
                node_id = self.agent_to_node(unique_id, graph_name=topology, node_id=agent.get('node_id'))
                agent['node_id'] = node_id
                agent['topology'] = topology
            agent['unique_id'] = unique_id

        return super()._read_single_agent(agent)
        

    @property
    def topology(self):
        return self.topologies['default']

    def set_topology(self, cfg=None, dir_path=None, graph='default'):
        topology = cfg
        if not isinstance(cfg, nx.Graph):
            topology = network.from_config(cfg, dir_path=dir_path or self.dir_path)

        self.topologies[graph] = topology

    def topology_for(self, unique_id):
        return self.topologies[self._node_ids[unique_id][0]]

    @property
    def network_agents(self):
        yield from self.agents(agent_class=agentmod.NetworkAgent)

    def agent_to_node(self, unique_id, graph_name='default',
                      node_id=None, shuffle=False):
        node_id = network.agent_to_node(G=self.topologies[graph_name],
                                        agent_id=unique_id,
                                        node_id=node_id,
                                        shuffle=shuffle,
                                        random=self.random)

        self._node_ids[unique_id] = (graph_name, node_id)
        return node_id

    def add_node(self, agent_class, topology, **kwargs):
        unique_id = self.next_id()
        self.topologies[topology].add_node(unique_id)
        node_id = self.agent_to_node(unique_id=unique_id, node_id=unique_id, graph_name=topology)

        a = self.add_agent(unique_id=unique_id, agent_class=agent_class, node_id=node_id, topology=topology, **kwargs)
        a['visible'] = True
        return a

    def add_edge(self, agent1, agent2, start=None, graph='default', **attrs):
        agent1 = agent1.node_id
        agent2 = agent2.node_id
        return self.topologies[graph].add_edge(agent1, agent2, start=start)

    def add_agent(self, unique_id, state=None, graph='default', **kwargs):
        node = self.topologies[graph].nodes[unique_id]
        node_state = node.get('state', {})
        if node_state:
            node_state.update(state or {})
            state = node_state
        a = super().add_agent(unique_id, state=state, **kwargs)
        node['agent'] = a
        return a

    def node_id_for(self, agent_id):
        return self._node_ids[agent_id][1]


Environment = NetworkEnvironment
