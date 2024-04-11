from __future__ import annotations

import logging
from collections import OrderedDict, defaultdict
from collections.abc import MutableMapping, Mapping, Set
from abc import ABCMeta
from copy import deepcopy, copy
from functools import partial, wraps
from itertools import islice, chain
import inspect
import types
import textwrap
import networkx as nx
import warnings
import sys

from typing import Any

from mesa import Agent as MesaAgent, Model
from typing import Dict, List

from .. import serialization, network, utils, time, config


IGNORED_FIELDS = ("model", "logger")


def decorate_generator_step(func, name):
    @wraps(func)
    def decorated(self):
        while True:
            if self._coroutine is None:
                self._coroutine = func(self)
            try:
                if self._last_except:
                    val = self._coroutine.throw(self._last_except)
                else:
                    val = self._coroutine.send(self._last_return)
            except StopIteration as ex:
                self._coroutine = None
                val = ex.value
            finally:
                self._last_return = None
                self._last_except = None
            return float(val) if val is not None else val
    return decorated


def decorate_normal_func(func, name):
    @wraps(func)
    def decorated(self):
        val = func(self)
        return float(val) if val is not None else val
    return decorated


class MetaAgent(ABCMeta):
    def __new__(mcls, name, bases, namespace):
        defaults = {}

        # Re-use defaults from inherited classes
        for i in bases:
            if isinstance(i, MetaAgent):
                defaults.update(i._defaults)

        new_nmspc = {
            "_defaults": defaults,
        }

        for attr, func in namespace.items():
            if attr == "step":
                if inspect.isgeneratorfunction(func) or inspect.iscoroutinefunction(func):
                    func = decorate_generator_step(func, attr)
                    new_nmspc.update({
                        "_last_return": None,
                        "_last_except": None,
                        "_coroutine": None,
                    })
                elif inspect.isasyncgenfunction(func):
                    raise ValueError("Illegal step function: {}. It probably mixes both async/await and yield".format(func))
                elif inspect.isfunction(func):
                    func = decorate_normal_func(func, attr)
                else:
                    raise ValueError("Illegal step function: {}".format(func))
                new_nmspc[attr] = func
            elif (
                isinstance(func, types.FunctionType)
                or isinstance(func, property)
                or isinstance(func, classmethod)
                or attr[0] == "_"
            ):
                new_nmspc[attr] = func
            elif attr == "defaults":
                defaults.update(func)
            elif inspect.isfunction(func):
                new_nmspc[attr] = func
            else:
                defaults[attr] = copy(func)


        # Add attributes for their use in the decorated functions
        return super().__new__(mcls, name, bases, new_nmspc)


class BaseAgent(MesaAgent, MutableMapping, metaclass=MetaAgent):
    """
    A special type of Mesa Agent that:

    * Can be used as a dictionary to access its state.
    * Has logging built-in
    * Can be given default arguments through a defaults class attribute,
    which will be used on construction to initialize each agent's state

    Any attribute that is not preceded by an underscore (`_`) will also be added to its state.
    """

    def __init__(self, unique_id, model, name=None, init=True, **kwargs):
        assert isinstance(unique_id, int)
        super().__init__(unique_id=unique_id, model=model)

        self.name = (
            str(name) if name else "{}[{}]".format(type(self).__name__, self.unique_id)
        )

        self.alive = True

        logger = model.logger.getChild(self.name)
        self.logger = logging.LoggerAdapter(logger, {"agent_name": self.name})

        if hasattr(self, "level"):
            self.logger.setLevel(self.level)

        for k in self._defaults:
            v = getattr(model, k, None)
            if v is not None:
                setattr(self, k, v)

        for (k, v) in self._defaults.items():
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, deepcopy(v))

        for (k, v) in kwargs.items():
            setattr(self, k, v)

        if init:
            self.init()

    def init(self):
        pass

    def __hash__(self):
        return hash(self.unique_id)

    def prob(self, probability):
        return prob(probability, self.model.random)

    @classmethod
    def w(cls, **kwargs):
        return custom(cls, **kwargs)

    # TODO: refactor to clean up mesa compatibility
    @property
    def id(self):
        msg = "This attribute is deprecated. Use `unique_id` instead"
        warnings.warn(msg, DeprecationWarning)
        print(msg, file=sys.stderr)
        return self.unique_id

    @classmethod
    def from_dict(cls, model, attrs, warn_extra=True):
        ignored = {}
        args = {}
        for k, v in attrs.items():
            if k in inspect.signature(cls).parameters:
                args[k] = v
            else:
                ignored[k] = v
        if ignored and warn_extra:
            utils.logger.info(
                f"Ignoring the following arguments for agent class { agent_class.__name__ }: { ignored }"
            )
        return cls(model=model, **args)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"key {key}  not found in agent")

    def __delitem__(self, key):
        return delattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __len__(self):
        return sum(1 for n in self.keys())

    def __iter__(self):
        return self.items()

    def keys(self):
        return (k for k in self.__dict__ if k[0] != "_" and k not in IGNORED_FIELDS)

    def items(self, keys=None, skip=None):
        keys = keys if keys is not None else self.keys()
        it = ((k, self.get(k, None)) for k in keys)
        if skip:
            return filter(lambda x: x[0] not in skip, it)
        return it

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            try:
                return getattr(self.model, key)
            except AttributeError:
                return default

    @property
    def now(self):
        try:
            return self.model.now
        except AttributeError:
            # No environment
            return None

    def die(self, msg=None):
        if msg:
            self.debug("Agent dying:", msg)
        else:
            self.debug(f"agent dying")
        self.alive = False
        try:
            self.model.schedule.remove(self)
        except KeyError:
            pass
        return time.Delay(time.INFINITY)

    def step(self):
        raise NotImplementedError("Agent must implement step method")

    def _check_alive(self):
        if not self.alive:
            raise time.DeadAgent(self.unique_id)

    def log(self, *message, level=logging.INFO, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        message = " ".join(str(i) for i in message)
        message = "[@{:>4}]\t{:>10}: {}".format(self.now, repr(self), message)
        for k, v in kwargs:
            message += " {k}={v} ".format(k, v)
        extra = {}
        extra["now"] = self.now
        extra["unique_id"] = self.unique_id
        extra["agent_name"] = self.name
        return self.logger.log(level, message, extra=extra)

    def debug(self, *args, **kwargs):
        return self.log(*args, level=logging.DEBUG, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(*args, level=logging.INFO, **kwargs)

    def count_agents(self, **kwargs):
        return len(list(self.get_agents(**kwargs)))

    def get_agents(self, *args, **kwargs):
        it = self.iter_agents(*args, **kwargs)
        return list(it)

    def iter_agents(self, *args, **kwargs):
        yield from filter_agents(self.model.schedule._agents, *args, **kwargs)

    def __str__(self):
        return self.to_str()

    def to_str(self, keys=None, skip=None, pretty=False):
        content = dict(self.items(keys=keys))
        if pretty and content:
            d = content
            content = "\n"
            for k, v in d.items():
                content += f"- {k}: {v}\n"
            content = textwrap.indent(content, "    ")
        return f"{repr(self)}{content}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.unique_id})"
    
    def at(self, at):
        return time.Delay(float(at) - self.now)
    
    def delay(self, delay=1):
        return time.Delay(delay)


def prob(prob, random):
    """
    A true/False uniform distribution with a given probability.
    To be used like this:

    .. code-block:: python

          if prob(0.3):
              do_something()

    """
    r = random.random()
    return r < prob


def calculate_distribution(network_agents=None, agent_class=None):
    """
    Calculate the threshold values (thresholds for a uniform distribution)
    of an agent distribution given the weights of each agent type.

    The input has this form: ::

            [
            {'agent_class': 'agent_class_1',
                'weight': 0.2,
                'state': {
                    'id': 0
                }
            },
            {'agent_class': 'agent_class_2',
                'weight': 0.8,
                'state': {
                    'id': 1
                }
            }
            ]

    In this example, 20% of the nodes will be marked as type
    'agent_class_1'.
    """
    if network_agents:
        network_agents = [
            deepcopy(agent) for agent in network_agents if not hasattr(agent, "id")
        ]
    elif agent_class:
        network_agents = [{"agent_class": agent_class}]
    else:
        raise ValueError("Specify a distribution or a default agent type")

    # Fix missing weights and incompatible types
    for x in network_agents:
        x["weight"] = float(x.get("weight", 1))

    # Calculate the thresholds
    total = sum(x["weight"] for x in network_agents)
    acc = 0
    for v in network_agents:
        if "ids" in v:
            continue
        upper = acc + (v["weight"] / total)
        v["threshold"] = [acc, upper]
        acc = upper
    return network_agents


def _serialize_type(agent_class, known_modules=[], **kwargs):
    if isinstance(agent_class, str):
        return agent_class
    known_modules += ["soil.agents"]
    return serialization.serialize(agent_class, known_modules=known_modules, **kwargs)[
        1
    ]  # Get the name of the class


def _deserialize_type(agent_class, known_modules=[]):
    if not isinstance(agent_class, str):
        return agent_class
    known = known_modules + ["soil.agents", "soil.agents.custom"]
    agent_class = serialization.deserializer(agent_class, known_modules=known)
    return agent_class


class AgentView(Mapping, Set):
    """A lazy-loaded list of agents."""

    __slots__ = ("_agents",)

    def __init__(self, agents):
        self._agents = agents

    def __getstate__(self):
        return {"_agents": self._agents}

    def __setstate__(self, state):
        self._agents = state["_agents"]

    # Mapping methods
    def __len__(self):
        return len(self._agents)

    def __iter__(self):
        yield from self._agents.values()

    def __getitem__(self, agent_id):
        if isinstance(agent_id, slice):
            raise ValueError(f"Slicing is not supported")
        if agent_id in self._agents:
            return self._agents[agent_id]
        raise ValueError(f"Agent {agent_id} not found")

    def filter(self, *args, **kwargs):
        yield from filter_agents(self._agents, *args, **kwargs)

    def one(self, *args, **kwargs):
        return next(filter_agents(self._agents, *args, **kwargs))

    def __call__(self, *args, **kwargs):
        return list(self.filter(*args, **kwargs))

    def __contains__(self, agent_id):
        return agent_id in self._agents

    def __str__(self):
        return str(list(unique_id for unique_id in self.keys()))

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"


def filter_agents(
    agents: dict,
    *id_args,
    unique_id=None,
    state_id=None,
    agent_class=None,
    state=None,
    limit=None,
    **kwargs,
):
    """
    Filter agents given as a dict, by the criteria given as arguments (e.g., certain type or state id).
    """

    ids = []

    if unique_id is not None:
        if isinstance(unique_id, list):
            ids += unique_id
        else:
            ids.append(unique_id)

    if id_args:
        ids += id_args

    if ids:
        f = (agent for agent in agents if agent.unique_id in ids)
    else:
        f = agents

    if state_id is not None and not isinstance(state_id, (tuple, list)):
        state_id = tuple([state_id])

    if agent_class is not None:
        agent_class = _deserialize_type(agent_class)
        try:
            agent_class = tuple(agent_class)
        except TypeError:
            agent_class = tuple([agent_class])

    if state_id is not None:
        f = filter(lambda agent: agent.get("state_id", None) in state_id, f)

    if agent_class is not None:
        f = filter(lambda agent: isinstance(agent, agent_class), f)

    state = state or dict()
    state.update(kwargs)

    for k, vs in state.items():
        if not isinstance(vs, list):
            vs = [vs]
        f = filter(lambda agent: any(getattr(agent, k, None) == v for v in vs), f)

    if limit is not None:
        f = islice(f, limit)

    yield from f


def from_config(
    cfg: config.AgentConfig, random, topology: nx.Graph = None
) -> List[Dict[str, Any]]:
    """
    This function turns an agentconfig into a list of individual "agent specifications", which are just a dictionary
    with the parameters that the environment will use to construct each agent.

    This function does NOT return a list of agents, mostly because some attributes to the agent are not known at the
    time of calling this function, such as `unique_id`.
    """
    default = cfg or config.AgentConfig()
    if not isinstance(cfg, config.AgentConfig):
        cfg = config.AgentConfig(**cfg)

    agents = []

    assigned_total = 0
    assigned_network = 0

    if cfg.fixed is not None:
        agents, assigned_total, assigned_network = _from_fixed(
            cfg.fixed, topology=cfg.topology, default=cfg
        )

    n = cfg.n

    if cfg.distribution:
        topo_size = len(topology) if topology else 0

        networked = []
        total = []

        for d in cfg.distribution:
            if d.strategy == config.Strategy.topology:
                topo = d.topology if ("topology" in d.__fields_set__) else cfg.topology
                if not topo:
                    raise ValueError(
                        'The "topology" strategy only works if the topology parameter is set to True'
                    )
                if not topo_size:
                    raise ValueError(
                        f"Topology does not have enough free nodes to assign one to the agent"
                    )

                networked.append(d)

            if d.strategy == config.Strategy.total:
                if not cfg.n:
                    raise ValueError(
                        'Cannot use the "total" strategy without providing the total number of agents'
                    )
                total.append(d)

        if networked:
            new_agents = _from_distro(
                networked,
                n=topo_size - assigned_network,
                topology=topo,
                default=cfg,
                random=random,
            )
            assigned_total += len(new_agents)
            assigned_network += len(new_agents)
            agents += new_agents

        if total:
            remaining = n - assigned_total
            agents += _from_distro(total, n=remaining, default=cfg, random=random)

        if assigned_network < topo_size:
            utils.logger.warn(
                f"The total number of agents does not match the total number of nodes in "
                "every topology. This may be due to a definition error: assigned: "
                f"{ assigned } total size: { topo_size }"
            )

    return agents


def _from_fixed(
    lst: List[config.FixedAgentConfig],
    topology: bool,
    default: config.SingleAgentConfig,
) -> List[Dict[str, Any]]:
    agents = []

    counts_total = 0
    counts_network = 0

    for fixed in lst:
        agent = {}
        if default:
            agent = default.state.copy()
        agent.update(fixed.state)
        cls = serialization.deserialize(
            fixed.agent_class or (default and default.agent_class)
        )
        agent["agent_class"] = cls
        topo = (
            fixed.topology
            if ("topology" in fixed.__fields_set__)
            else topology or default.topology
        )

        if topo:
            agent["topology"] = True
            counts_network += 1
        if not fixed.hidden:
            counts_total += 1
        agents.append(agent)

    return agents, counts_total, counts_network


def _from_distro(
    distro: List[config.AgentDistro],
    n: int,
    default: config.SingleAgentConfig,
    random,
    topology: str = None
) -> List[Dict[str, Any]]:

    agents = []

    if n is None:
        if any(lambda dist: dist.n is None, distro):
            raise ValueError(
                "You must provide a total number of agents, or the number of each type"
            )
        n = sum(dist.n for dist in distro)

    weights = list(dist.weight if dist.weight is not None else 1 for dist in distro)
    minw = min(weights)
    norm = list(weight / minw for weight in weights)
    total = sum(norm)
    chunk = n // total

    # random.choices would be enough to get a weighted distribution. But it can vary a lot for smaller k
    # So instead we calculate our own distribution to make sure the actual ratios are close to what we would expect

    # Calculate how many times each has to appear
    indices = list(
        chain.from_iterable([idx] * int(n * chunk) for (idx, n) in enumerate(norm))
    )

    # Complete with random agents following the original weight distribution
    if len(indices) < n:
        indices += random.choices(
            list(range(len(distro))),
            weights=[d.weight for d in distro],
            k=n - len(indices),
        )

    # Deserialize classes for efficiency
    classes = list(
        serialization.deserialize(i.agent_class or default.agent_class) for i in distro
    )

    # Add them in random order
    random.shuffle(indices)

    for idx in indices:
        d = distro[idx]
        agent = d.state.copy()
        cls = classes[idx]
        agent["agent_class"] = cls
        if default:
            agent.update(default.state)
        topology = (
            d.topology
            if ("topology" in d.__fields_set__)
            else topology or default.topology
        )
        if topology:
            agent["topology"] = topology
        agents.append(agent)

    return agents


from .network_agents import *
from .fsm import *
from .evented import *
from typing import Optional


class Agent(NetworkAgent, FSM, EventedAgent):
    """Default agent class, has both network and event capabilities"""


from ..environment import NetworkEnvironment


from .BassModel import *
from .IndependentCascadeModel import *
from .SISaModel import *
from .CounterModel import *


def custom(cls, **kwargs):
    """Create a new class from a template class and keyword arguments"""
    return type(cls.__name__, (cls,), kwargs)
