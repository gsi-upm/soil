from __future__ import annotations

import os
import sqlite3
import math
import logging
import inspect

from typing import Any, Dict, Optional, Union
from collections import namedtuple
from time import time as current_time
from copy import deepcopy
from networkx.readwrite import json_graph


import networkx as nx

from mesa import Model
from mesa.datacollection import DataCollector

from . import agents as agentmod, config, serialization, utils, time, network, events


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

    def __init__(
        self,
        id="unnamed_env",
        seed="default",
        schedule=None,
        dir_path=None,
        interval=1,
        agent_class=None,
        agents: [tuple[type, Dict[str, Any]]] = {},
        agent_reporters: Optional[Any] = None,
        model_reporters: Optional[Any] = None,
        tables: Optional[Any] = None,
        **env_params,
    ):

        super().__init__(seed=seed)
        self.env_params = env_params or {}

        self.current_id = -1

        self.id = id

        self.dir_path = dir_path or os.getcwd()

        if schedule is None:
            schedule = time.TimedActivation(self)
        self.schedule = schedule

        self.agent_class = agent_class or agentmod.BaseAgent

        self.interval = interval
        self.init_agents(agents)

        self.logger = utils.logger.getChild(self.id)

        self.datacollector = DataCollector(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters,
            tables=tables,
        )

    def _agent_from_dict(self, agent):
        """
        Translate an agent dictionary into an agent
        """
        agent = dict(**agent)
        cls = agent.pop("agent_class", None) or self.agent_class
        unique_id = agent.pop("unique_id", None)
        if unique_id is None:
            unique_id = self.next_id()

        return serialization.deserialize(cls)(unique_id=unique_id, model=self, **agent)

    def init_agents(self, agents: Union[config.AgentConfig, [Dict[str, Any]]] = {}):
        """
        Initialize the agents in the model from either a `soil.config.AgentConfig` or a list of
        dictionaries that each describes an agent.

        If given a list of dictionaries, an agent will be created for each dictionary. The agent
        class can be specified through the `agent_class` key. The rest of the items will be used
        as parameters to the agent.
        """
        if not agents:
            return

        lst = agents
        override = []
        if not isinstance(lst, list):
            if not isinstance(agents, config.AgentConfig):
                lst = config.AgentConfig(**agents)
            if lst.override:
                override = lst.override
            lst = self._agent_dict_from_config(lst)

        # TODO: check override is working again. It cannot (easily) be part of agents.from_config anymore,
        # because it needs attribute such as unique_id, which are only present after init
        new_agents = [self._agent_from_dict(agent) for agent in lst]

        for a in new_agents:
            self.schedule.add(a)

        for rule in override:
            for agent in agentmod.filter_agents(self.schedule._agents, **rule.filter):
                for attr, value in rule.state.items():
                    setattr(agent, attr, value)

    def _agent_dict_from_config(self, cfg):
        return agentmod.from_config(cfg, random=self.random)

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
        raise Exception(
            "The environment has not been scheduled, so it has no sense of time"
        )

    def add_agent(self, unique_id=None, **kwargs):
        if unique_id is None:
            unique_id = self.next_id()

        kwargs["unique_id"] = unique_id
        a = self._agent_from_dict(kwargs)

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
        extra["now"] = self.now
        extra["id"] = self.id
        return self.logger.log(level, message, extra=extra)

    def step(self):
        """
        Advance one step in the simulation, and update the data collection and scheduler appropriately
        """
        super().step()
        self.logger.info(
            f"--- Step: {self.schedule.steps:^5} - Time: {self.now:^5} ---"
        )
        self.schedule.step()
        self.datacollector.collect(self)

    def __contains__(self, key):
        return key in self.env_params

    def get(self, key, default=None):
        """
        Get the value of an environment attribute.
        Return `default` if the value is not set.
        """
        return self.env_params.get(key, default)

    def __getitem__(self, key):
        return self.env_params.get(key)

    def __setitem__(self, key, value):
        return self.env_params.__setitem__(key, value)

    def __str__(self):
        return str(self.env_params)


class NetworkEnvironment(BaseEnvironment):
    """
    The NetworkEnvironment is an environment that includes one or more networkx.Graph intances
    and methods to associate agents to nodes and vice versa.
    """

    def __init__(
        self, *args, topology: Union[config.NetConfig, nx.Graph] = None, **kwargs
    ):
        agents = kwargs.pop("agents", None)
        super().__init__(*args, agents=None, **kwargs)

        self._set_topology(topology)

        self.init_agents(agents)

    def init_agents(self, *args, **kwargs):
        """Initialize the agents from a"""
        super().init_agents(*args, **kwargs)
        for agent in self.schedule._agents.values():
            if hasattr(agent, "node_id"):
                self._init_node(agent)

    def _init_node(self, agent):
        """
        Make sure the node for a given agent has the proper attributes.
        """
        self.G.nodes[agent.node_id]["agent"] = agent

    def _agent_dict_from_config(self, cfg):
        return agentmod.from_config(cfg, topology=self.G, random=self.random)

    def _agent_from_dict(self, agent, unique_id=None):
        agent = dict(agent)

        if not agent.get("topology", False):
            return super()._agent_from_dict(agent)

        if unique_id is None:
            unique_id = self.next_id()
        node_id = agent.get("node_id", None)
        if node_id is None:
            node_id = network.find_unassigned(self.G, random=self.random)
        self.G.nodes[node_id]["agent"] = None
        agent["node_id"] = node_id
        agent["unique_id"] = unique_id
        agent["topology"] = self.G
        node_attrs = self.G.nodes[node_id]
        node_attrs.update(agent)
        agent = node_attrs

        a = super()._agent_from_dict(agent)
        self._init_node(a)

        return a

    def _set_topology(self, cfg=None, dir_path=None):
        if cfg is None:
            cfg = nx.Graph()
        elif not isinstance(cfg, nx.Graph):
            cfg = network.from_config(cfg, dir_path=dir_path or self.dir_path)

        self.G = cfg

    @property
    def network_agents(self):
        for a in self.schedule._agents:
            if isinstance(a, agentmod.NetworkAgent):
                yield a

    def add_node(self, agent_class, unique_id=None, node_id=None, **kwargs):
        if unique_id is None:
            unique_id = self.next_id()
        if node_id is None:
            node_id = network.find_unassigned(
                G=self.G, shuffle=True, random=self.random
            )
            if node_id is None:
                node_id = f"node_for_{unique_id}"

        if node_id not in self.G.nodes:
            self.G.add_node(node_id)

        assert "agent" not in self.G.nodes[node_id]
        self.G.nodes[node_id]["agent"] = None  # Reserve

        a = self.add_agent(
            unique_id=unique_id,
            agent_class=agent_class,
            topology=self.G,
            node_id=node_id,
            **kwargs,
        )
        a["visible"] = True
        return a

    def add_agent(self, *args, **kwargs):
        a = super().add_agent(*args, **kwargs)
        if "node_id" in a:
            assert self.G.nodes[a.node_id]["agent"] == a
        return a

    def agent_for_node_id(self, node_id):
        return self.G.nodes[node_id].get("agent")

    def populate_network(self, agent_class, weights=None, **agent_params):
        if not hasattr(agent_class, "len"):
            agent_class = [agent_class]
            weights = None
        for (node_id, node) in self.G.nodes(data=True):
            if "agent" in node:
                continue
            a_class = self.random.choices(agent_class, weights)[0]
            self.add_agent(node_id=node_id, agent_class=a_class, **agent_params)


Environment = NetworkEnvironment


class EventedEnvironment(Environment):
    def broadcast(self, msg,  sender, expiration=None, ttl=None, **kwargs):
        for agent in self.agents(**kwargs):
            self.logger.info(f'Telling {repr(agent)}: {msg} ttl={ttl}')
            try:
                agent._inbox.append(events.Tell(payload=msg, sender=sender, expiration=expiration if ttl is None else self.now+ttl))
            except AttributeError:
                self.info(f'Agent {agent.unique_id} cannot receive events')

