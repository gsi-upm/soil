from __future__ import annotations

import os
import sys
import logging
from datetime import datetime

from typing import Any, Callable, Dict, Optional, Union, List, Type
from types import coroutine

import networkx as nx


from mesa import Model
from time import time as current_time

from . import agents as agentmod, datacollection, utils, time, network, events


# TODO: maybe add metaclass to read attributes of a model

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

    collector_class = datacollection.SoilCollector
    schedule_class = time.TimedActivation
    start_time = 0
    time_format = "%Y-%m-%d %H:%M:%S"

    def __new__(cls,
                *args: Any,
                seed="default",
                dir_path=None,
                collector_class: type = None,
                agent_reporters: Optional[Any] = None,
                model_reporters: Optional[Any] = None,
                tables: Optional[Any] = None,
                **kwargs: Any) -> Any:
        """Create a new model with a default seed value"""
        seed = seed or str(current_time())
        self = super().__new__(cls, *args, seed=seed, **kwargs)
        self.dir_path = dir_path or os.getcwd()
        collector_class = collector_class or cls.collector_class
        self.datacollector = collector_class(
            model_reporters=model_reporters,
            agent_reporters=agent_reporters,
            tables=tables,
        )
        for k in dir(cls):
            v = getattr(cls, k)
            if isinstance(v, property):
                v = v.fget
            if getattr(v, "add_to_report", False):
                self.add_model_reporter(k, k)

        return self

    def __init__(
        self,
        *,
        id="unnamed_env",
        seed="default",
        dir_path=None,
        schedule=None,
        schedule_class=None,
        logger = None,
        agents: Optional[Dict] = None,
        collector_class: type = datacollection.SoilCollector,
        agent_reporters: Optional[Any] = None,
        model_reporters: Optional[Any] = None,
        start_time=None,
        time_format=None,
        tables: Optional[Any] = None,
        init: bool = True,
        **env_params,
    ):

        super().__init__()


        self.current_id = -1

        self.id = id

        if logger:
            self.logger = logger
        else:
            self.logger = utils.logger.getChild(self.id)
        if start_time is not None:
            self.start_time = start_time
        if time_format is not None:
            self.time_format = time_format

        if isinstance(self.start_time, str):
            self.start_time = datetime.strptime(self.start_time, self.time_format)
        if isinstance(self.start_time, datetime):
            self.start_time = self.start_time.timestamp()

        self.schedule = schedule
        if schedule is None:
            if schedule_class is None:
                schedule_class = self.schedule_class
            self.schedule = schedule_class(self, time=self.start_time)

        for (k, v) in env_params.items():
            self[k] = v

        if agents:
            self.add_agents(**agents)
        if init:
            self.init()
            self.datacollector.collect(self)

    def init(self):
        pass

    @property
    def agents(self):
        return agentmod.AgentView(self.schedule._agents, getattr(self.schedule, "agents_by_type", None))

    def agent(self, *args, **kwargs):
        return agentmod.AgentView(self.schedule._agents, self.schedule.agents_by_type).one(*args, **kwargs)

    def count_agents(self, *args, **kwargs):
        return sum(1 for i in self.agents(*args, **kwargs))

    def agent_df(self, steps=False):
        df = self.datacollector.get_agent_vars_dataframe()
        df.index.rename(["step", "agent_id"], inplace=True)
        if steps:
            return df
        df = df.reset_index()
        model_df = self.datacollector.get_model_vars_dataframe()
        df['time'] = df.apply(lambda row: model_df.loc[row.step].time, axis=1)
        return df.groupby(["time", "agent_id"]).last()

    def model_df(self, steps=False):
        df = self.datacollector.get_model_vars_dataframe()
        if steps:
            return df
        df.index.rename("step", inplace=True)
        return df.reset_index().set_index("time")

    @property
    def now(self):
        if self.schedule is not None:
            return self.schedule.time
        raise Exception(
            "The environment has not been scheduled, so it has no sense of time"
        )
    def init_agents(self):
        pass

    def add_agent(self, agent_class, unique_id=None, **agent):
        if unique_id is None:
            unique_id = self.next_id()

        agent["unique_id"] = unique_id

        agent = dict(**agent)
        unique_id = agent.pop("unique_id", None)
        if unique_id is None:
            unique_id = self.next_id()

        a = agent_class(unique_id=unique_id, model=self, **agent)

        self.schedule.add(a)
        return a

    def remove_agent(self, agent):
        agent.alive = False
        self.schedule.remove(agent)

    def add_agents(self, agent_classes: List[type], k, weights: Optional[List[float]] = None, **kwargs):
        if isinstance(agent_classes, type):
            agent_classes = [agent_classes]
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
        self.schedule.step()
        self.datacollector.collect(self)
        if self.now == time.INFINITY:
            self.running = False

        if self.logger.isEnabledFor(logging.DEBUG):
            msg = "Model data:\n"
            max_width = max(len(k) for k in self.datacollector.model_vars.keys())
            for (k, v) in self.datacollector.model_vars.items():
                # msg += f"\t{k:<{max_width}}"
                msg += f"\t{k:<{max_width}}: {v[-1]}\n"
            self.logger.debug(f"--- Steps: {self.schedule.steps:^5} - Time: {self.now:^5} --- " + msg)

    def add_model_reporter(self, name, func=None):
        if not func:
            func = name
        self.datacollector._new_model_reporter(name, func)

    def add_agent_reporter(self, name, reporter=None, agent_class=None, *, agent_type=None):
        if agent_type:
            print("agent_type is deprecated, use agent_class instead", file=sys.stderr)
        agent_class = agent_type or agent_class
        if not reporter and not agent_class:
            reporter = name
        if agent_class:
            if reporter:
                _orig = reporter
            else:
                _orig = lambda a: getattr(a, name)
            reporter = lambda a: (_orig(a) if isinstance(a, agent_class) else None)
        self.datacollector._new_agent_reporter(name, reporter)

    @classmethod
    def run(cls, *,
            name=None,
            iterations=1,
            num_processes=1, **kwargs):
        from .simulation import Simulation
        return Simulation(name=name or cls.__name__,
                          model=cls, iterations=iterations,
                          num_processes=num_processes, **kwargs).run()

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

    def __init__(self,
                 *args,
                 topology: Optional[Union[nx.Graph, str]] = None,
                 agent_class: Optional[Type[agentmod.Agent]] = None,
                 network_generator: Optional[Callable] = None,
                 network_params: Optional[Dict] = {},
                 init=True,
                 **kwargs):
        self.topology = topology
        self.network_generator = network_generator
        self.network_params = network_params
        if topology or network_params or network_generator:
            self.create_network(topology, generator=network_generator, **network_params)
        else:
            self.G = nx.Graph()
        super().__init__(*args, **kwargs, init=False)

        self.agent_class = agent_class
        if self.agent_class:
            self.populate_network(self.agent_class)
        self._check_agent_nodes()
        if init:
            self.init()
            self.datacollector.collect(self)

    def add_agent(self, agent_class, *args, node_id=None, topology=None, **kwargs):
        if node_id is None and topology is None:
            return super().add_agent(agent_class, *args, **kwargs)
        try:
            a = super().add_agent(agent_class, *args, node_id=node_id, **kwargs)
        except TypeError:
            self.logger.warning(f"Agent constructor for {agent_class} does not have a node_id attribute. Might be a bug.")
            a = super().add_agent(agent_class, *args, **kwargs)
        self.G.nodes[node_id]["agent"] = a
        return a

    def remove_agent(self, agent, remove_node=True):
        super().remove_agent(agent)
        if remove_node and hasattr(agent, "remove_node"):
            agent.remove_node()

    def add_agents(self, *args, k=None, **kwargs):
        if not k and not self.G:
            raise ValueError("Cannot add agents to an empty network")
        super().add_agents(*args, k=k or len(self.G), **kwargs)

    def create_network(self, topology=None, generator=None, path=None, **network_params):
        if topology is not None:
            topology = network.from_topology(topology, dir_path=self.dir_path)
        elif path is not None:
            topology = network.from_topology(path, dir_path=self.dir_path)
        elif generator is not None:
            params = dict(generator=generator,
                                           dir_path=self.dir_path,
                                           seed=self.random,
                                           **network_params)
            try:
                topology = network.from_params(**params)
            except TypeError:
                del params["seed"]
                topology = network.from_params(**params)
        else:
            raise ValueError("topology must be a networkx.Graph or a string, or network_generator must be provided")
        self.G = topology

    def init_agents(self, *args, **kwargs):
        """Initialize the agents from a"""
        super().init_agents(*args, **kwargs)

    @property
    def network_agents(self):
        """Return agents still alive and assigned to a node in the network."""
        for (id, data) in self.G.nodes(data=True):
            if "agent" in data:
                agent = data["agent"]
                if getattr(agent, "alive", True):
                    yield agent

    def add_node(self, agent_class, unique_id=None, node_id=None, find_unassigned=False, **kwargs):
        if unique_id is None:
            unique_id = self.next_id()
        if node_id is None:
            if find_unassigned:
                node_id = network.find_unassigned(
                    G=self.G, shuffle=True, random=self.random
                )
            if node_id is None:
                node_id = f"Node_for_agent_{unique_id}"
            assert node_id not in self.G.nodes

        if node_id not in self.G.nodes:
            self.G.add_node(node_id)

        assert "agent" not in self.G.nodes[node_id]

        a = self.add_agent(
            unique_id=unique_id,
            agent_class=agent_class,
            topology=self.G,
            node_id=node_id,
            **kwargs,
        )
        a["visible"] = True
        return a

    def _check_agent_nodes(self):
        """
        Detect nodes that have agents assigned to them.
        """
        for (id, data) in self.G.nodes(data=True):
            if "agent_id" in data:
                agent = self.agents(data["agent_id"])
                self.G.nodes[id]["agent"] = agent
                assert not getattr(agent, "node_id", None) or agent.node_id == id
                agent.node_id = id
        for agent in self.agents():
            if hasattr(agent, "node_id"):
                node_id = agent["node_id"]
                if node_id not in self.G.nodes:
                    raise ValueError(f"Agent {agent} is assigned to node {agent.node_id} which is not in the network")
                node = self.G.nodes[node_id]
                if node.get("agent") is not None and node["agent"] != agent:
                    raise ValueError(f"Node {node_id} already has a different agent assigned to it")
                self.G.nodes[node_id]["agent"] = agent

    def add_agents(self, agent_classes: List[type], k=None, weights: Optional[List[float]] = None, **kwargs):
        if k is None:
            k = len(self.G)
            if not k:
                raise ValueError("Cannot add agents to an empty network")
        super().add_agents(agent_classes, k=k, weights=weights, **kwargs)

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
        toadd = []
        for (cls, (node_id, node)) in zip(classes, self.G.nodes(data=True)):
            if "agent" in node:
                continue
            node["agent"] = None # Reserve
            toadd.append(dict(node_id=node_id, topology=self.G,  agent_class=cls, **agent_params))
        for d in toadd:
            a = self.add_agent(**d)
            self.G.nodes[d["node_id"]]["agent"] = a
        assert all("agent" in node for (_, node) in self.G.nodes(data=True))
        assert len(list(self.network_agents))


class EventedEnvironment(BaseEnvironment):

    def __init__(self, *args, **kwargs):
        self._inbox = dict()
        super().__init__(*args, **kwargs)
        self._can_reschedule = hasattr(self.schedule, "add_callback") and hasattr(self.schedule, "remove_callback")
        self._can_reschedule = True
        self._callbacks = {}

    def register(self, agent):
        self._inbox[agent.unique_id] = []

    def inbox_for(self, agent):
        try:
            return self._inbox[agent.unique_id]
        except KeyError:
            raise ValueError(f"Trying to access inbox for unregistered agent: {agent} (class: {type(agent)}). "
                            "Make sure your agent is of type EventedAgent and it is registered with the environment.")

    @coroutine
    def _polling_callback(self, agent, expiration, delay):
        # this wakes the agent up at every step. It is better to wait until timeout (or inf)
        # and if a message is received before that, reschedule the agent
        # (That is implemented in the `received` method)
        inbox = self.inbox_for(agent)
        while self.now < expiration:
            if inbox:
                return self.process_messages(inbox)
            yield time.Delay(delay)
        raise events.TimedOut("No message received")

    @coroutine
    def received(self, agent, expiration=None, timeout=None, delay=1):
        if not expiration:
            if timeout:
                expiration = self.now + timeout
            else:
                expiration = float("inf")
        inbox = self.inbox_for(agent)
        if inbox:
            return self.process_messages(inbox)

        if self._can_reschedule:
            checked = False
            def cb():
                nonlocal checked
                if checked:
                    return time.INFINITY
                checked = True
                self.schedule.add_callback(self.now, agent.step)
            self.schedule.add_callback(expiration, cb)
            self._callbacks[agent.unique_id] = cb
            yield time.INFINITY
        res = yield from self._polling_callback(agent, expiration, delay)
        return res


    def tell(self, msg, recipient, sender=None, expiration=None, timeout=None, **kwargs):
        if expiration is None:
            expiration = float("inf") if timeout is None else self.now + timeout
        self._add_to_inbox(recipient.unique_id,
            events.Tell(timestamp=self.now,
                        payload=msg,
                        sender=sender,
                        expiration=expiration,
                        **kwargs))

    def broadcast(self, msg, sender, ttl=None, expiration=None, agent_class=None):
        expiration = expiration if ttl is None else self.now + ttl
        # This only works for Soil environments. Mesa agents do not have an `agents` method
        sender_id = sender.unique_id
        for (agent_id, inbox) in self._inbox.items():
            if agent_id == sender_id:
                continue
            if agent_class and not isinstance(self.agents(unique_id=agent_id), agent_class):
                continue
            self.logger.debug(f"Telling {agent_id}: {msg} ttl={ttl}")
            self._add_to_inbox(agent_id,
                events.Tell(
                    payload=msg,
                    sender=sender,
                    expiration=expiration,
                )
            )
    def _add_to_inbox(self, inbox_id, msg):
        self._inbox[inbox_id].append(msg)
        if inbox_id in self._callbacks:
            cb = self._callbacks.pop(inbox_id)
            cb()

    @coroutine
    def ask(self, msg, recipient, sender=None, expiration=None, timeout=None, delay=1):
        ask = events.Ask(timestamp=self.now, payload=msg, sender=sender)
        self._add_to_inbox(recipient.unique_id, ask)
        expiration = float("inf") if timeout is None else self.now + timeout
        while self.now < expiration:
            if ask.reply:
                return ask.reply
            yield time.Delay(delay)
        raise events.TimedOut("No reply received")

    def process_messages(self, inbox):
        valid = list()
        for msg in inbox:
            if msg.expired(self.now):
                continue
            valid.append(msg)
        inbox.clear()
        return valid


class Environment(EventedEnvironment, NetworkEnvironment):
    pass
