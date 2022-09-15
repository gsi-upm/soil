import logging
from collections import OrderedDict, defaultdict
from collections.abc import MutableMapping, Mapping, Set
from abc import ABCMeta
from copy import deepcopy
from functools import partial, wraps
from itertools import islice, chain
import json
import networkx as nx

from mesa import Agent as MesaAgent
from typing import Dict, List

from random import shuffle

from .. import serialization, utils, time, config



def as_node(agent):
    if isinstance(agent, BaseAgent):
        return agent.id
    return agent

IGNORED_FIELDS = ('model', 'logger')


class DeadAgent(Exception):
    pass

class BaseAgent(MesaAgent, MutableMapping):
    """
    A special type of Mesa Agent that:

    * Can be used as a dictionary to access its state.
    * Has logging built-in
    * Can be given default arguments through a defaults class attribute,
    which will be used on construction to initialize each agent's state

    Any attribute that is not preceded by an underscore (`_`) will also be added to its state.
    """

    defaults = {}

    def __init__(self,
                 unique_id,
                 model,
                 name=None,
                 interval=None,
                 **kwargs
    ):
        # Check for REQUIRED arguments
        # Initialize agent parameters
        if isinstance(unique_id, MesaAgent):
            raise Exception()
        assert isinstance(unique_id, int)
        super().__init__(unique_id=unique_id, model=model)
        self.name = str(name) if name else'{}[{}]'.format(type(self).__name__, self.unique_id)


        self._neighbors = None
        self.alive = True

        self.interval = interval or self.get('interval', 1)
        self.logger = logging.getLogger(self.model.id).getChild(self.name)

        if hasattr(self, 'level'):
            self.logger.setLevel(self.level)
        for (k, v) in self.defaults.items():
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, deepcopy(v))

        for (k, v) in kwargs.items():

            setattr(self, k, v)

        for (k, v) in getattr(self, 'defaults', {}).items():
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, v)

    # TODO: refactor to clean up mesa compatibility
    @property
    def id(self):
        return self.unique_id

    @property
    def env(self):
        return self.model

    @env.setter
    def env(self, model):
        self.model = model

    @property
    def state(self):
        '''
        Return the agent itself, which behaves as a dictionary.

        This method shouldn't be used, but is kept here for backwards compatibility.
        '''
        return self

    @state.setter
    def state(self, value):
        for k, v in value.items():
            self[k] = v

    @property
    def environment_params(self):
        return self.model.environment_params

    @environment_params.setter
    def environment_params(self, value):
        self.model.environment_params = value

    def __getitem__(self, key):
        return getattr(self, key)

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
        return (k for k in self.__dict__ if k[0] != '_')

    def items(self):
        return ((k, v) for (k, v) in self.__dict__.items() if k[0] != '_')

    def get(self, key, default=None):
        return self[key] if key in self else default

    @property
    def now(self):
        try:
            return self.model.now
        except AttributeError:
            # No environment
            return None

    def die(self, remove=False):
        self.info(f'agent {self.unique_id}  is dying')
        self.alive = False
        if remove:
            self.remove_node(self.id)
        return time.NEVER

    def step(self):
        if not self.alive:
            raise DeadAgent(self.unique_id)
        return super().step() or time.Delta(self.interval)

    def log(self, message, *args, level=logging.INFO, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        message = message + " ".join(str(i) for i in args)
        message = " @{:>3}: {}".format(self.now, message)
        for k, v in kwargs:
            message += " {k}={v} ".format(k, v)
        extra = {}
        extra['now'] = self.now
        extra['unique_id'] = self.unique_id
        extra['agent_name'] = self.name
        return self.logger.log(level, message, extra=extra)



    def debug(self, *args, **kwargs):
        return self.log(*args, level=logging.DEBUG, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(*args, level=logging.INFO, **kwargs)

# Alias
# Agent = BaseAgent

class NetworkAgent(BaseAgent):
    def __init__(self,
                 *args,
                 graph_name: str,
                 node_id: int = None,
                 **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.graph_name = graph_name
        self.topology = self.env.topologies[self.graph_name]
        self.node_id = node_id

    @property
    def G(self):
        return self.model.topologies[self._topology]

    def count_agents(self, **kwargs):
        return len(list(self.get_agents(**kwargs)))

    def count_neighboring_agents(self, state_id=None, **kwargs):
        return len(self.get_neighboring_agents(state_id=state_id, **kwargs))

    def get_neighboring_agents(self, state_id=None, **kwargs):
        return self.get_agents(limit_neighbors=True, state_id=state_id, **kwargs)

    def get_agents(self, *args, limit=None, **kwargs):
        it = self.iter_agents(*args, **kwargs)
        if limit is not None:
            it = islice(it, limit)
        return list(it)

    def iter_agents(self, agents=None, limit_neighbors=False, **kwargs):
        if limit_neighbors:
            agents = self.topology.neighbors(self.unique_id)

        return self.model.agents(ids=agents, **kwargs)

    def subgraph(self, center=True, **kwargs):
        include = [self] if center else []
        return self.topology.subgraph(n.unique_id for n in list(self.get_agents(**kwargs))+include)

    def remove_node(self, unique_id):
        self.topology.remove_node(unique_id)

    def add_edge(self, other, edge_attr_dict=None, *edge_attrs):
        # return super(NetworkAgent, self).add_edge(node1=self.id, node2=other, **kwargs)
        if self.unique_id not in self.topology.nodes(data=False):
            raise ValueError('{} not in list of existing agents in the network'.format(self.unique_id))
        if other.unique_id not in self.topology.nodes(data=False):
            raise ValueError('{} not in list of existing agents in the network'.format(other))

        self.topology.add_edge(self.unique_id, other.unique_id, edge_attr_dict=edge_attr_dict, *edge_attrs)

    def ego_search(self, steps=1, center=False, node=None, **kwargs):
        '''Get a list of nodes in the ego network of *node* of radius *steps*'''
        node = as_node(node if node is not None else self)
        G = self.subgraph(**kwargs)
        return nx.ego_graph(G, node, center=center, radius=steps).nodes()

    def degree(self, node, force=False):
        node = as_node(node)
        if force or (not hasattr(self.model, '_degree')) or getattr(self.model, '_last_step', 0) < self.now:
            self.model._degree = nx.degree_centrality(self.topology)
            self.model._last_step = self.now
        return self.model._degree[node]

    def betweenness(self, node, force=False):
        node = as_node(node)
        if force or (not hasattr(self.model, '_betweenness')) or getattr(self.model, '_last_step', 0) < self.now:
            self.model._betweenness = nx.betweenness_centrality(self.topology)
            self.model._last_step = self.now
        return self.model._betweenness[node]


def state(name=None):
    def decorator(func, name=None):
        '''
        A state function should return either a state id, or a tuple (state_id, when)
        The default value for state_id is the current state id.
        The default value for when is the interval defined in the environment.
        '''

        @wraps(func)
        def func_wrapper(self):
            next_state = func(self)
            when = None
            if next_state is None:
                return when
            try:
                next_state, when = next_state
            except (ValueError, TypeError):
                pass
            if next_state:
                self.set_state(next_state)
            return when

        func_wrapper.id = name or func.__name__
        func_wrapper.is_default = False
        return func_wrapper

    if callable(name):
        return decorator(name)
    else:
        return partial(decorator, name=name)


def default_state(func):
    func.is_default = True
    return func


class MetaFSM(ABCMeta):
    def __init__(cls, name, bases, nmspc):
        super(MetaFSM, cls).__init__(name, bases, nmspc)
        states = {}
        # Re-use states from inherited classes
        default_state = None
        for i in bases:
            if isinstance(i, MetaFSM):
                for state_id, state in i.states.items():
                    if state.is_default:
                        default_state = state
                    states[state_id] = state

        # Add new states
        for name, func in nmspc.items():
            if hasattr(func, 'id'):
                if func.is_default:
                    default_state = func
                states[func.id] = func
        cls.default_state = default_state
        cls.states = states


class FSM(BaseAgent, metaclass=MetaFSM):
    def __init__(self, *args, **kwargs):
        super(FSM, self).__init__(*args, **kwargs)
        if not hasattr(self, 'state_id'):
            if not self.default_state:
                raise ValueError('No default state specified for {}'.format(self.unique_id))
            self.state_id = self.default_state.id

        self.set_state(self.state_id)

    def step(self):
        self.debug(f'Agent {self.unique_id} @ state {self.state_id}')
        interval = super().step()
        if 'id' not in self.state:
            if self.default_state:
                self.set_state(self.default_state.id)
            else:
                raise Exception('{} has no valid state id or default state'.format(self))
        interval = self.states[self.state_id](self) or interval
        if not self.alive:
            return time.NEVER
        return interval

    def set_state(self, state):
        if hasattr(state, 'id'):
            state = state.id
        if state not in self.states:
            raise ValueError('{} is not a valid state'.format(state))
        self.state_id = state
        return state


def prob(prob=1):
    '''
    A true/False uniform distribution with a given probability.
    To be used like this:

    .. code-block:: python
          
          if prob(0.3):
              do_something()

    '''
    r = random.random()
    return r < prob


def calculate_distribution(network_agents=None,
                           agent_type=None):
    '''
    Calculate the threshold values (thresholds for a uniform distribution)
    of an agent distribution given the weights of each agent type.

    The input has this form: ::

            [
            {'agent_type': 'agent_type_1',
                'weight': 0.2,
                'state': {
                    'id': 0
                }
            },
            {'agent_type': 'agent_type_2',
                'weight': 0.8,
                'state': {
                    'id': 1
                }
            }
            ]

    In this example, 20% of the nodes will be marked as type
    'agent_type_1'.
    '''
    if network_agents:
        network_agents = [deepcopy(agent) for agent in network_agents if not hasattr(agent, 'id')]
    elif agent_type:
        network_agents = [{'agent_type': agent_type}]
    else:
        raise ValueError('Specify a distribution or a default agent type')

    # Fix missing weights and incompatible types
    for x in network_agents:
        x['weight'] = float(x.get('weight', 1))

    # Calculate the thresholds
    total = sum(x['weight'] for x in network_agents)
    acc = 0
    for v in network_agents:
        if 'ids' in v:
            continue
        upper = acc + (v['weight']/total)
        v['threshold'] = [acc, upper]
        acc = upper
    return network_agents


def serialize_type(agent_type, known_modules=[], **kwargs):
    if isinstance(agent_type, str):
        return agent_type
    known_modules += ['soil.agents']
    return serialization.serialize(agent_type, known_modules=known_modules, **kwargs)[1] # Get the name of the class


def serialize_definition(network_agents, known_modules=[]):
    '''
    When serializing an agent distribution, remove the thresholds, in order
    to avoid cluttering the YAML definition file.
    '''
    d = deepcopy(list(network_agents))
    for v in d:
        if 'threshold' in v:
            del v['threshold']
        v['agent_type'] = serialize_type(v['agent_type'],
                                         known_modules=known_modules)
    return d


def deserialize_type(agent_type, known_modules=[]):
    if not isinstance(agent_type, str):
        return agent_type
    known = known_modules + ['soil.agents', 'soil.agents.custom' ]
    agent_type = serialization.deserializer(agent_type, known_modules=known)
    return agent_type


def deserialize_definition(ind, **kwargs):
    d = deepcopy(ind)
    for v in d:
        v['agent_type'] = deserialize_type(v['agent_type'], **kwargs)
    return d


def _validate_states(states, topology):
    '''Validate states to avoid ignoring states during initialization'''
    states = states or []
    if isinstance(states, dict):
        for x in states:
            assert x in topology.nodes
    else:
        assert len(states) <= len(topology)
    return states


def _convert_agent_types(ind, to_string=False, **kwargs):
    '''Convenience method to allow specifying agents by class or class name.'''
    if to_string:
        return serialize_definition(ind, **kwargs)
    return deserialize_definition(ind, **kwargs)


def _agent_from_definition(definition, value=-1, unique_id=None):
    """Used in the initialization of agents given an agent distribution."""
    if value < 0:
        value = random.random()
    for d in sorted(definition, key=lambda x: x.get('threshold')):
        threshold = d.get('threshold', (-1, -1))
        # Check if the definition matches by id (first) or by threshold
        if (unique_id is not None and unique_id in d.get('ids', [])) or \
           (value >= threshold[0] and value < threshold[1]):
            state = {}
            if 'state' in d:
                state = deepcopy(d['state'])
            return d['agent_type'], state

    raise Exception('Definition for value {} not found in: {}'.format(value, definition))


def _definition_to_dict(definition, size=None, default_state=None):
    state = default_state or {}
    agents = {}
    remaining = {}
    if size:
        for ix in range(size):
            remaining[ix] = copy(state)
    else:
        remaining = defaultdict(lambda x: copy(state))

    distro = sorted([item for item in definition if 'weight' in item])

    id = 0

    def init_agent(item, id=ix):
        while id in agents:
            id += 1

        agent = remaining[id]
        agent['state'].update(copy(item.get('state', {})))
        agents[agent.unique_id] = agent
        del remaining[id]
        return agent

    for item in definition:
        if 'ids' in item:
            ids = item['ids']
            del item['ids']
            for id in ids:
                agent = init_agent(item, id)

    for item in definition:
        if 'number' in item:
            times = item['number']
            del item['number']
            for times in range(times):
                if size:
                    ix = random.choice(remaining.keys())
                    agent = init_agent(item, id)
                else:
                    agent = init_agent(item)
    if not size:
        return agents

    if len(remaining) < 0:
        raise Exception('Invalid definition. Too many agents to add')


    total_weight = float(sum(s['weight'] for s in distro))
    unit = size / total_weight

    for item in distro:
        times = unit * item['weight']
        del item['weight']
        for times in range(times):
            ix = random.choice(remaining.keys())
            agent = init_agent(item, id)
    return agents


class AgentView(Mapping, Set):
    """A lazy-loaded list of agents.
    """

    __slots__ = ("_agents",)


    def __init__(self, agents):
        self._agents = agents

    def __getstate__(self):
        return {"_agents": self._agents}

    def __setstate__(self, state):
        self._agents = state["_agents"]

    # Mapping methods
    def __len__(self):
        return sum(len(x) for x in self._agents.values())

    def __iter__(self):
        yield from iter(chain.from_iterable(g.values() for g in self._agents.values()))

    def __getitem__(self, agent_id):
        if isinstance(agent_id, slice):
            raise ValueError(f"Slicing is not supported")
        for group in self._agents.values():
            if agent_id in group:
                return group[agent_id]
        raise ValueError(f"Agent {agent_id} not found")

    def filter(self, *group_ids, **kwargs):
        yield from filter_groups(self._agents, group_ids=group_ids, **kwargs)

    def __call__(self, *args, **kwargs):
        return list(self.filter(*args, **kwargs))

    def __contains__(self, agent_id):
        return any(agent_id in g for g in self._agents)

    def __str__(self):
        return str(list(a.id for a in self))

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"


def filter_groups(groups, group_ids=None, **kwargs):
    assert isinstance(groups, dict)
    if group_ids:
        groups = list(groups[g] for g in group_ids if g in groups)
    else:
        groups = list(groups.values())
    
    agents = chain.from_iterable(filter_group(g, **kwargs) for g in groups)

    yield from agents


def filter_group(group, ids=None, state_id=None, agent_type=None, ignore=None, state=None, **kwargs):
    '''
    Filter agents given as a dict, by the criteria given as arguments (e.g., certain type or state id).
    '''
    assert isinstance(group, dict)

    if state_id is not None and not isinstance(state_id, (tuple, list)):
        state_id = tuple([state_id])

    if agent_type is not None:
        try:
            agent_type = tuple(agent_type)
        except TypeError:
            agent_type = tuple([agent_type])

    if ids:
        agents = (v[aid] for aid in ids if aid in group)
    else:
        agents = (a for a in group.values())

    f = agents
    if ignore:
        f = filter(lambda x: x not in ignore, f)

    if state_id is not None:
        f = filter(lambda agent: agent.get('state_id', None) in state_id, f)

    if agent_type is not None:
        f = filter(lambda agent: isinstance(agent, agent_type), f)

    state = state or dict()
    state.update(kwargs)

    for k, v in state.items():
        f = filter(lambda agent: agent.state.get(k, None) == v, f)

    yield from f


def from_config(cfg: Dict[str, config.AgentConfig], env):
    '''
    Agents are specified in groups.
    Each group can be specified in two ways, either through a fixed list in which each item has
    has the agent type, number of agents to create, and the other parameters, or through what we call
    an `agent distribution`, which is similar but instead of number of agents, it specifies the weight
    of each agent type.
    '''
    default = cfg.get('default', None)
    return {k: _group_from_config(c, default=default, env=env) for (k, c)  in cfg.items() if k is not 'default'}


def _group_from_config(cfg: config.AgentConfig, default: config.SingleAgentConfig, env):
    agents = {}
    if cfg.fixed is not None:
        agents = _from_fixed(cfg.fixed, topology=cfg.topology, default=default, env=env)
    if cfg.distribution:
        n = cfg.n or len(env.topologies[cfg.topology])
        target = n - len(agents)
        agents.update(_from_distro(cfg.distribution, target,
                                   topology=cfg.topology or default.topology,
                                   default=default,
                                   env=env))
        assert len(agents) == n
    if cfg.override:
        for attrs in cfg.override:
            if attrs.filter:
                filtered = list(filter_group(agents, **attrs.filter))
            else:
                filtered = list(agents)

            for agent in random.sample(filtered, attrs.n):
                agent.state.update(attrs.state)

    return agents


def _from_fixed(lst: List[config.FixedAgentConfig], topology: str, default: config.SingleAgentConfig, env):
    agents = {}

    for fixed in lst:
      agent_id = fixed.agent_id
      if agent_id is None:
          agent_id = env.next_id()

      cls = serialization.deserialize(fixed.agent_class or default.agent_class)
      state = fixed.state.copy()
      state.update(default.state)
      agent = cls(unique_id=agent_id,
                  model=env,
                  graph_name=fixed.topology or topology or default.topology,
                  **state)
      agents[agent.unique_id] = agent

    return agents


def _from_distro(distro: List[config.AgentDistro],
                 n: int,
                 topology: str,
                 default: config.SingleAgentConfig,
                 env):

    agents = {}

    if n is None:
        if any(lambda dist: dist.n is None, distro):
            raise ValueError('You must provide a total number of agents, or the number of each type')
        n = sum(dist.n for dist in distro)

    weights = list(dist.weight if dist.weight is not None else 1 for dist in distro)
    minw = min(weights)
    norm = list(weight / minw for weight in weights)
    total = sum(norm)
    chunk = n // total

    # random.choices would be enough to get a weighted distribution. But it can vary a lot for smaller k
    # So instead we calculate our own distribution to make sure the actual ratios are close to what we would expect

    # Calculate how many times each has to appear
    indices = list(chain.from_iterable([idx] * int(n*chunk) for (idx, n) in enumerate(norm)))

    # Complete with random agents following the original weight distribution
    if len(indices) < n:
        indices += random.choices(list(range(len(distro))), weights=[d.weight for d in distro], k=n-len(indices))

    # Deserialize classes for efficiency
    classes = list(serialization.deserialize(i.agent_class or default.agent_class) for i in distro)

    # Add them in random order
    random.shuffle(indices)


    for idx in indices:
        d = distro[idx]
        cls = classes[idx]
        agent_id = env.next_id()
        state = d.state.copy()
        state.update(default.state)
        agent = cls(unique_id=agent_id, model=env, graph_name=d.topology or topology or default.topology, **state)
        assert agent.name is not None
        assert agent.name != 'None'
        assert agent.name
        agents[agent.unique_id] = agent

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
    print('Could not load the Geo Agent, scipy is not installed', file=sys.stderr)
