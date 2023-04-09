from __future__ import annotations

import os
import sqlite3
import math
import logging
import inspect

from typing import Any, Callable, Dict, Optional, Union, List, Type
from collections import namedtuple
from time import time as current_time
from copy import deepcopy


import networkx as nx

from mesa import Model, Agent

from . import agents as agentmod, datacollection, serialization, utils, time, network, events


# TODO: add metaclass to read attributes of a model
# TODO: read "report" attributes from the model

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

    def __new__(cls, *args: Any, seed="default", dir_path=None, **kwargs: Any) -> Any:
        """Create a new model with a default seed value"""
        self = super().__new__(cls, *args, seed=seed, **kwargs)
        self.dir_path = dir_path or os.getcwd()
        return self

    def __init__(
        self,
        *,
        id="unnamed_env",
        seed="default",
        dir_path=None,
        schedule_class=time.TimedActivation,
        interval=1,
        agents: Optional[Dict] = None,
        collector_class: type = datacollection.SoilCollector,
        agent_reporters: Optional[Any] = None,
        model_reporters: Optional[Any] = None,
        tables: Optional[Any] = None,
        init: bool = True,
        **env_params,
    ):

        super().__init__()

        self.current_id = -1

        self.id = id


        if schedule_class is None:
            schedule_class = time.TimedActivation
        else:
            schedule_class = serialization.deserialize(schedule_class)
        self.schedule = schedule_class(self)

        self.interval = interval

        self.logger = utils.logger.getChild(self.id)

        collector_class = serialization.deserialize(collector_class)
        self.datacollector = collector_class(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters,
            tables=tables,
        )
        for (k, v) in env_params.items():
            self[k] = v

        if agents:
            self.add_agents(**agents)
        if init:
            self.init()

    def init(self):
        pass

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

    def add_agent(self, agent_class, unique_id=None, **agent):
        if unique_id is None:
            unique_id = self.next_id()

        agent["unique_id"] = unique_id

        agent = dict(**agent)
        unique_id = agent.pop("unique_id", None)
        if unique_id is None:
            unique_id = self.next_id()

        a = serialization.deserialize(agent_class)(unique_id=unique_id, model=self, **agent)

        self.schedule.add(a)
        return a

    def add_agents(self, agent_classes: List[type], k, weights: Optional[List[float]] = None, **kwargs):
        if weights is None:
            weights = [1] * len(agent_classes)

        for cls in self.random.choices(agent_classes, weights=weights, k=k):
            self.add_agent(agent_class=cls, **kwargs)

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
        # self.logger.info(
        #     "--- Step: {:^5} - Time: {now:^5} ---", steps=self.schedule.steps, now=self.now
        # )
        self.schedule.step()
        self.datacollector.collect(self)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"key {key}  not found in environment")

    def __delitem__(self, key):
        return delattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        return str(dict(self))

    def __len__(self):
        return sum(1 for n in self.keys())

    def __iter__(self):
        return iter(self.agents())

    def get(self, key, default=None):
        return self[key] if key in self else default

    def keys(self):
        return (k for k in self.__dict__ if k[0] != "_")

class NetworkEnvironment(BaseEnvironment):
    """
    The NetworkEnvironment is an environment that includes one or more networkx.Graph intances
    and methods to associate agents to nodes and vice versa.
    """

    def __init__(
        self, *args,
        topology: Optional[Union[nx.Graph, str]] = None,
        agent_class: Optional[Type[agentmod.Agent]] = None,
        network_generator: Optional[Callable] = None,
        network_params: Optional[Dict] = None, **kwargs
    ):
        self.topology = topology
        self.network_generator = network_generator
        self.network_params = network_params
        if topology or network_params or network_generator:
            self.create_network(topology, network_params=network_params, network_generator=network_generator)
        else:
            self.G = nx.Graph()
        super().__init__(*args, **kwargs, init=False)

        self.agent_class = agent_class
        if agent_class:
            self.agent_class = serialization.deserialize(agent_class)
        self.init()
        if self.agent_class:
            self.populate_network(self.agent_class)


    def add_agents(self, *args, k=None, **kwargs):
        if not k and not self.G:
            raise ValueError("Cannot add agents to an empty network")
        super().add_agents(*args, k=k or len(self.G), **kwargs)

    def create_network(self, topology=None, network_generator=None, path=None, network_params=None):
        if topology is not None:
            topology = network.from_topology(topology, dir_path=self.dir_path)
        elif path is not None:
            topology = network.from_topology(path, dir_path=self.dir_path)
        elif network_generator is not None:
            topology = network.from_params(network_generator, dir_path=self.dir_path, **network_params)
        else:
            raise ValueError("topology must be a networkx.Graph or a string, or network_generator must be provided")
        self.G = topology

    def init_agents(self, *args, **kwargs):
        """Initialize the agents from a"""
        super().init_agents(*args, **kwargs)
        for agent in self.schedule._agents.values():
            self._assign_node(agent)

    def _assign_node(self, agent):
        """
        Make sure the node for a given agent has the proper attributes.
        """
        if hasattr(agent, "node_id"):
            self.G.nodes[agent.node_id]["agent"] = agent

    @property
    def network_agents(self):
        for a in self.schedule._agents.values():
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

    def add_agent(self, agent_class, *args, **kwargs):
        if issubclass(agent_class, agentmod.NetworkAgent) and "node_id" not in kwargs:
            return self.add_node(agent_class, *args, **kwargs)
        a = super().add_agent(agent_class, *args, **kwargs)
        if hasattr(a, "node_id"):
            assigned = self.G.nodes[a.node_id].get("agent")
            if not assigned:
                self.G.nodes[a.node_id]["agent"] = a
            elif assigned != a:
                raise ValueError(f"Node {a.node_id} already has an agent assigned: {assigned}")
        return a

    def agent_for_node_id(self, node_id):
        return self.G.nodes[node_id].get("agent")

    def populate_network(self, agent_class: List[Model], weights: List[float] = None, **agent_params):
        if isinstance(agent_class, type):
            agent_class = [agent_class]
        else:
            agent_class = list(agent_class)
        if not weights:
            weights = [1] * len(agent_class)
        assert len(self.G)
        classes = self.random.choices(agent_class, weights, k=len(self.G))
        for (cls, (node_id, node)) in zip(classes, self.G.nodes(data=True)):
            if "agent" in node:
                continue
            a = self.add_agent(node_id=node_id, topology=self.G,  agent_class=cls, **agent_params)
            node["agent"] = a
        assert all("agent" in node for (_, node) in self.G.nodes(data=True))
        assert len(list(self.network_agents))


class EventedEnvironment(BaseEnvironment):
    def broadcast(self, msg, sender=None, expiration=None, ttl=None, **kwargs):
        for agent in self.agents(**kwargs):
            if agent == sender:
                continue
            self.logger.info(f"Telling {repr(agent)}: {msg} ttl={ttl}")
            try:
                inbox = agent._inbox
            except AttributeError:
                self.logger.info(
                    f"Agent {agent.unique_id} cannot receive events because it does not have an inbox"
                )
                continue
            # Allow for AttributeError exceptions in this part of the code
            inbox.append(
                events.Tell(
                    payload=msg,
                    sender=sender,
                    expiration=expiration if ttl is None else self.now + ttl,
                )
            )


class Environment(NetworkEnvironment, EventedEnvironment):
    """Default environment class, has both network and event capabilities"""
