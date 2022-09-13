from __future__ import annotations
import os
import sqlite3
import math
import random
import logging

from typing import Dict
from collections import namedtuple
from time import time as current_time
from copy import deepcopy
from networkx.readwrite import json_graph


import networkx as nx

from mesa import Model

from . import serialization, agents, analysis, utils, time, config, network


Record = namedtuple('Record', 'dict_id t_step key value')


class Environment(Model):
    """
    The environment is key in a simulation. It contains the network topology,
    a reference to network and environment agents, as well as the environment
    params, which are used as shared state between agents.

    The environment parameters and the state of every agent can be accessed
    both by using the environment as a dictionary or with the environment's
    :meth:`soil.environment.Environment.get` method.
    """

    def __init__(self,
                 env_id='unnamed_env',
                 seed='default',
                 schedule=None,
                 dir_path=None,
                 interval=1,
                 agents: Dict[str, config.AgentConfig] = {},
                 topologies: Dict[str, config.NetConfig] = {},
                 **env_params):

        super().__init__()
        self.current_id = -1

        self.seed = '{}_{}'.format(seed, env_id)
        self.id = env_id

        self.dir_path = dir_path or os.getcwd()

        if schedule is None:
            schedule = time.TimedActivation()
        self.schedule = schedule

        seed = seed or current_time()

        random.seed(seed)


        self.topologies = {}
        for (name, cfg) in topologies.items():
            self.set_topology(cfg=cfg,
                              graph=name)
        self.agents = agents or {}

        self.env_params = env_params or {}

        self.interval = interval
        self['SEED'] = seed

        self.logger = utils.logger.getChild(self.id)

    @property
    def topology(self):
        return self.topologies['default']

    @property
    def network_agents(self):
        yield from self.agents(agent_type=agents.NetworkAgent, iterator=True)


    @staticmethod
    def from_config(conf: config.Config, trial_id, **kwargs) -> Environment:
        '''Create an environment for a trial of the simulation'''
        conf = conf
        if kwargs:
            conf = config.Config(**conf.dict(exclude_defaults=True), **kwargs)
        seed = '{}_{}'.format(conf.general.seed, trial_id)
        id = '{}_trial_{}'.format(conf.general.id, trial_id).replace('.', '-')
        opts = conf.environment.params.copy()
        opts.update(conf)
        opts.update(kwargs)
        env = serialization.deserialize(conf.environment.environment_class)(env_id=id, seed=seed, **opts)
        return env

    @property
    def now(self):
        if self.schedule:
            return self.schedule.time
        raise Exception('The environment has not been scheduled, so it has no sense of time')


    def set_topology(self, cfg=None, dir_path=None, graph='default'):
        self.topologies[graph] = network.from_config(cfg, dir_path=dir_path)

    @property
    def agents(self):
        return agents.AgentView(self._agents)

    @agents.setter
    def agents(self, agents_def: Dict[str, config.AgentConfig]):
        self._agents = agents.from_config(agents_def, env=self)
        for d in self._agents.values():
            for a in d.values():
                self.schedule.add(a)


    # @property
    # def network_agents(self):
    #     for i in self.G.nodes():
    #         node = self.G.nodes[i]
    #         if 'agent' in node:
    #             yield node['agent']

    def init_agent(self, agent_id, agent_definitions, graph='default'):
        node = self.topologies[graph].nodes[agent_id]
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

    def set_agent(self, agent_id, agent_type, state=None, graph='default'):
        node = self.topologies[graph].nodes[agent_id]
        defstate = deepcopy(self.default_state) or {}
        defstate.update(self.states.get(agent_id, {}))
        defstate.update(node.get('state', {}))
        if state:
            defstate.update(state)
        a = None
        if agent_type:
            state = defstate
            a = agent_type(model=self,
                           unique_id=agent_id
            )

        for (k, v) in state.items():
            setattr(a, k, v)

        node['agent'] = a
        self.schedule.add(a)
        return a

    def add_node(self, agent_type, state=None, graph='default'):
        agent_id = int(len(self.topologies[graph].nodes()))
        self.topologies[graph].add_node(agent_id)
        a = self.set_agent(agent_id, agent_type, state, graph=graph)
        a['visible'] = True
        return a

    def add_edge(self, agent1, agent2, start=None, graph='default', **attrs):
        if hasattr(agent1, 'id'):
            agent1 = agent1.id
        if hasattr(agent2, 'id'):
            agent2 = agent2.id
        start = start or self.now
        return self.topologies[graph].add_edge(agent1, agent2, **attrs)

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

    def run(self, until, *args, **kwargs):
        until = until or float('inf')

        while self.schedule.next_time < until:
            self.step()
            utils.logger.debug(f'Simulation step {self.schedule.time}/{until}. Next: {self.schedule.next_time}')
        self.schedule.time = until

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



SoilEnvironment = Environment
