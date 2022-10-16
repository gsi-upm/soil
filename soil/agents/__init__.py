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

from typing import Any

from mesa import Agent as MesaAgent
from typing import Dict, List

from .. import serialization, utils, time, config


def as_node(agent):
    if isinstance(agent, BaseAgent):
        return agent.id
    return agent


IGNORED_FIELDS = ("model", "logger")


class DeadAgent(Exception):
    pass


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
            if (
                isinstance(func, types.FunctionType)
                or isinstance(func, property)
                or isinstance(func, classmethod)
                or attr[0] == "_"
            ):
                new_nmspc[attr] = func
            elif attr == "defaults":
                defaults.update(func)
            else:
                defaults[attr] = copy(func)

        return super().__new__(mcls=mcls, name=name, bases=bases, namespace=new_nmspc)


class BaseAgent(MesaAgent, MutableMapping, metaclass=MetaAgent):
    """
    A special type of Mesa Agent that:

    * Can be used as a dictionary to access its state.
    * Has logging built-in
    * Can be given default arguments through a defaults class attribute,
    which will be used on construction to initialize each agent's state

    Any attribute that is not preceded by an underscore (`_`) will also be added to its state.
    """

    def __init__(self, unique_id, model, name=None, interval=None, **kwargs):
        # Check for REQUIRED arguments
        # Initialize agent parameters
        if isinstance(unique_id, MesaAgent):
            raise Exception()
        assert isinstance(unique_id, int)
        super().__init__(unique_id=unique_id, model=model)

        self.name = (
            str(name) if name else "{}[{}]".format(type(self).__name__, self.unique_id)
        )

        self.alive = True

        self.interval = interval or self.get("interval", 1)
        logger = utils.logger.getChild(getattr(self.model, "id", self.model)).getChild(
            self.name
        )
        self.logger = logging.LoggerAdapter(logger, {"agent_name": self.name})

        if hasattr(self, "level"):
            self.logger.setLevel(self.level)

        for (k, v) in self._defaults.items():
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, deepcopy(v))

        for (k, v) in kwargs.items():

            setattr(self, k, v)

    def __hash__(self):
        return hash(self.unique_id)

    def prob(self, probability):
        return prob(probability, self.model.random)

    # TODO: refactor to clean up mesa compatibility
    @property
    def id(self):
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
        return self[key] if key in self else default

    @property
    def now(self):
        try:
            return self.model.now
        except AttributeError:
            # No environment
            return None

    def die(self):
        self.info(f"agent dying")
        self.alive = False
        return time.NEVER

    def step(self):
        if not self.alive:
            raise DeadAgent(self.unique_id)
        return super().step() or time.Delta(self.interval)

    def log(self, message, *args, level=logging.INFO, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        message = message + " ".join(str(i) for i in args)
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


class NetworkAgent(BaseAgent):
    def __init__(self, *args, topology, node_id, **kwargs):
        super().__init__(*args, **kwargs)

        assert topology is not None
        assert node_id is not None
        self.G = topology
        assert self.G
        self.node_id = node_id

    def count_neighboring_agents(self, state_id=None, **kwargs):
        return len(self.get_neighboring_agents(state_id=state_id, **kwargs))

    def get_neighboring_agents(self, **kwargs):
        return list(self.iter_agents(limit_neighbors=True, **kwargs))

    def add_edge(self, other):
        self.topology.add_edge(self.node_id, other.node_id)

    @property
    def node(self):
        return self.topology.nodes[self.node_id]

    def iter_agents(self, unique_id=None, *, limit_neighbors=False, **kwargs):
        unique_ids = None
        if isinstance(unique_id, list):
            unique_ids = set(unique_id)
        elif unique_id is not None:
            unique_ids = set(
                [
                    unique_id,
                ]
            )

        if limit_neighbors:
            neighbor_ids = set()
            for node_id in self.G.neighbors(self.node_id):
                if self.G.nodes[node_id].get("agent") is not None:
                    neighbor_ids.add(node_id)
            if unique_ids:
                unique_ids = unique_ids & neighbor_ids
            else:
                unique_ids = neighbor_ids
            if not unique_ids:
                return
            unique_ids = list(unique_ids)
        yield from super().iter_agents(unique_id=unique_ids, **kwargs)

    def subgraph(self, center=True, **kwargs):
        include = [self] if center else []
        G = self.G.subgraph(
            n.node_id for n in list(self.get_agents(**kwargs) + include)
        )
        return G

    def remove_node(self):
        self.G.remove_node(self.node_id)

    def add_edge(self, other, edge_attr_dict=None, *edge_attrs):
        if self.node_id not in self.G.nodes(data=False):
            raise ValueError(
                "{} not in list of existing agents in the network".format(
                    self.unique_id
                )
            )
        if other.node_id not in self.G.nodes(data=False):
            raise ValueError(
                "{} not in list of existing agents in the network".format(other)
            )

        self.G.add_edge(
            self.node_id, other.node_id, edge_attr_dict=edge_attr_dict, *edge_attrs
        )

    def die(self, remove=True):
        if remove:
            self.remove_node()
        return super().die()


def state(name=None):
    def decorator(func, name=None):
        """
        A state function should return either a state id, or a tuple (state_id, when)
        The default value for state_id is the current state id.
        The default value for when is the interval defined in the environment.
        """
        if inspect.isgeneratorfunction(func):
            orig_func = func

            @wraps(func)
            def func(self):
                while True:
                    if not self._coroutine:
                        self._coroutine = orig_func(self)
                    try:
                        n = next(self._coroutine)
                        if n:
                            return None, n
                        return
                    except StopIteration as ex:
                        self._coroutine = None
                        next_state = ex.value
                        if next_state is not None:
                            self.set_state(next_state)
                        return next_state

        func.id = name or func.__name__
        func.is_default = False
        return func

    if callable(name):
        return decorator(name)
    else:
        return partial(decorator, name=name)


def default_state(func):
    func.is_default = True
    return func


class MetaFSM(MetaAgent):
    def __new__(mcls, name, bases, namespace):
        states = {}
        # Re-use states from inherited classes
        default_state = None
        for i in bases:
            if isinstance(i, MetaFSM):
                for state_id, state in i._states.items():
                    if state.is_default:
                        default_state = state
                    states[state_id] = state

        # Add new states
        for attr, func in namespace.items():
            if hasattr(func, "id"):
                if func.is_default:
                    default_state = func
                states[func.id] = func

        namespace.update(
            {
                "_default_state": default_state,
                "_states": states,
            }
        )

        return super(MetaFSM, mcls).__new__(
            mcls=mcls, name=name, bases=bases, namespace=namespace
        )


class FSM(BaseAgent, metaclass=MetaFSM):
    def __init__(self, *args, **kwargs):
        super(FSM, self).__init__(*args, **kwargs)
        if not hasattr(self, "state_id"):
            if not self._default_state:
                raise ValueError(
                    "No default state specified for {}".format(self.unique_id)
                )
            self.state_id = self._default_state.id

        self._coroutine = None
        self.set_state(self.state_id)

    def step(self):
        self.debug(f"Agent {self.unique_id} @ state {self.state_id}")
        default_interval = super().step()

        next_state = self._states[self.state_id](self)

        when = None
        try:
            next_state, *when = next_state
            if not when:
                when = None
            elif len(when) == 1:
                when = when[0]
            else:
                raise ValueError(
                    "Too many values returned. Only state (and time) allowed"
                )
        except TypeError:
            pass

        if next_state is not None:
            self.set_state(next_state)

        return when or default_interval

    def set_state(self, state, when=None):
        if hasattr(state, "id"):
            state = state.id
        if state not in self._states:
            raise ValueError("{} is not a valid state".format(state))
        self.state_id = state
        if when is not None:
            self.model.schedule.add(self, when=when)
        return state

    def die(self):
        return self.dead, super().die()

    @state
    def dead(self):
        return self.die()


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


def serialize_type(agent_class, known_modules=[], **kwargs):
    if isinstance(agent_class, str):
        return agent_class
    known_modules += ["soil.agents"]
    return serialization.serialize(agent_class, known_modules=known_modules, **kwargs)[
        1
    ]  # Get the name of the class


def serialize_definition(network_agents, known_modules=[]):
    """
    When serializing an agent distribution, remove the thresholds, in order
    to avoid cluttering the YAML definition file.
    """
    d = deepcopy(list(network_agents))
    for v in d:
        if "threshold" in v:
            del v["threshold"]
        v["agent_class"] = serialize_type(v["agent_class"], known_modules=known_modules)
    return d


def deserialize_type(agent_class, known_modules=[]):
    if not isinstance(agent_class, str):
        return agent_class
    known = known_modules + ["soil.agents", "soil.agents.custom"]
    agent_class = serialization.deserializer(agent_class, known_modules=known)
    return agent_class


def deserialize_definition(ind, **kwargs):
    d = deepcopy(ind)
    for v in d:
        v["agent_class"] = deserialize_type(v["agent_class"], **kwargs)
    return d


def _validate_states(states, topology):
    """Validate states to avoid ignoring states during initialization"""
    states = states or []
    if isinstance(states, dict):
        for x in states:
            assert x in topology.nodes
    else:
        assert len(states) <= len(topology)
    return states


def _convert_agent_classs(ind, to_string=False, **kwargs):
    """Convenience method to allow specifying agents by class or class name."""
    if to_string:
        return serialize_definition(ind, **kwargs)
    return deserialize_definition(ind, **kwargs)


# def _agent_from_definition(definition, random, value=-1, unique_id=None):
#     """Used in the initialization of agents given an agent distribution."""
#     if value < 0:
#         value = random.random()
#     for d in sorted(definition, key=lambda x: x.get('threshold')):
#         threshold = d.get('threshold', (-1, -1))
#         # Check if the definition matches by id (first) or by threshold
#         if (unique_id is not None and unique_id in d.get('ids', [])) or \
#            (value >= threshold[0] and value < threshold[1]):
#             state = {}
#             if 'state' in d:
#                 state = deepcopy(d['state'])
#             return d['agent_class'], state

#     raise Exception('Definition for value {} not found in: {}'.format(value, definition))


# def _definition_to_dict(definition, random, size=None, default_state=None):
#     state = default_state or {}
#     agents = {}
#     remaining = {}
#     if size:
#         for ix in range(size):
#             remaining[ix] = copy(state)
#     else:
#         remaining = defaultdict(lambda x: copy(state))

#     distro = sorted([item for item in definition if 'weight' in item])

#     id = 0

#     def init_agent(item, id=ix):
#         while id in agents:
#             id += 1

#         agent = remaining[id]
#         agent['state'].update(copy(item.get('state', {})))
#         agents[agent.unique_id] = agent
#         del remaining[id]
#         return agent

#     for item in definition:
#         if 'ids' in item:
#             ids = item['ids']
#             del item['ids']
#             for id in ids:
#                 agent = init_agent(item, id)

#     for item in definition:
#         if 'number' in item:
#             times = item['number']
#             del item['number']
#             for times in range(times):
#                 if size:
#                     ix = random.choice(remaining.keys())
#                     agent = init_agent(item, id)
#                 else:
#                     agent = init_agent(item)
#     if not size:
#         return agents

#     if len(remaining) < 0:
#         raise Exception('Invalid definition. Too many agents to add')


#     total_weight = float(sum(s['weight'] for s in distro))
#     unit = size / total_weight

#     for item in distro:
#         times = unit * item['weight']
#         del item['weight']
#         for times in range(times):
#             ix = random.choice(remaining.keys())
#             agent = init_agent(item, id)
#     return agents


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
    agents,
    *id_args,
    unique_id=None,
    state_id=None,
    agent_class=None,
    ignore=None,
    state=None,
    limit=None,
    **kwargs,
):
    """
    Filter agents given as a dict, by the criteria given as arguments (e.g., certain type or state id).
    """
    assert isinstance(agents, dict)

    ids = []

    if unique_id is not None:
        if isinstance(unique_id, list):
            ids += unique_id
        else:
            ids.append(unique_id)

    if id_args:
        ids += id_args

    if ids:
        f = (agents[aid] for aid in ids if aid in agents)
    else:
        f = (a for a in agents.values())

    if state_id is not None and not isinstance(state_id, (tuple, list)):
        state_id = tuple([state_id])

    if agent_class is not None:
        agent_class = deserialize_type(agent_class)
        try:
            agent_class = tuple(agent_class)
        except TypeError:
            agent_class = tuple([agent_class])

    if ignore:
        f = filter(lambda x: x not in ignore, f)

    if state_id is not None:
        f = filter(lambda agent: agent.get("state_id", None) in state_id, f)

    if agent_class is not None:
        f = filter(lambda agent: isinstance(agent, agent_class), f)

    state = state or dict()
    state.update(kwargs)

    for k, v in state.items():
        f = filter(lambda agent: getattr(agent, k, None) == v, f)

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
    return _agents_from_config(cfg, topology=topology, random=random)


def _agents_from_config(
    cfg: config.AgentConfig, topology: nx.Graph, random
) -> List[Dict[str, Any]]:
    if cfg and not isinstance(cfg, config.AgentConfig):
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
    topology: str,
    default: config.SingleAgentConfig,
    random,
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


from .BassModel import *
from .BigMarketModel import *
from .IndependentCascadeModel import *
from .ModelM2 import *
from .SentimentCorrelationModel import *
from .SISaModel import *
from .CounterModel import *

try:
    import scipy
    from .Geo import Geo
except ImportError:
    import sys

    print("Could not load the Geo Agent, scipy is not installed", file=sys.stderr)
