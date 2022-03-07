import logging
from collections import OrderedDict, defaultdict
from copy import deepcopy
from functools import partial, wraps
from itertools import islice
import json
import networkx as nx

from .. import serialization, utils, time

from tsih import Key

from mesa import Agent


def as_node(agent):
    if isinstance(agent, BaseAgent):
        return agent.id
    return agent

IGNORED_FIELDS = ('model', 'logger')


class DeadAgent(Exception):
    pass

class BaseAgent(Agent):
    """
    A special Agent that keeps track of its state history.
    """

    defaults = {}

    def __init__(self,
                 unique_id,
                 model,
                 name=None,
                 interval=None):
        # Check for REQUIRED arguments
        # Initialize agent parameters
        if isinstance(unique_id, Agent):
            raise Exception()
        self._saved = set()
        super().__init__(unique_id=unique_id, model=model)
        self.name = name or '{}[{}]'.format(type(self).__name__, self.unique_id)

        self._neighbors = None
        self.alive = True

        self.interval = interval or self.get('interval', 1)
        self.logger = logging.getLogger(self.model.name).getChild(self.name)

        if hasattr(self, 'level'):
            self.logger.setLevel(self.level)


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
        Changes made to `agent.state` will be reflected in the history.

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

    def __setattr__(self, key, value):
        if not key.startswith('_') and key not in IGNORED_FIELDS:
            try:
                k = Key(t_step=self.now,
                        dict_id=self.unique_id,
                        key=key)
                self._saved.add(key)
                self.model[k] = value
            except AttributeError:
                pass
        super().__setattr__(key, value)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key, t_step = key
            k = Key(key=key, t_step=t_step, dict_id=self.unique_id)
            return self.model[k]
        return getattr(self, key)

    def __delitem__(self, key):
        return delattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def items(self):
        return ((k, getattr(self, k)) for k in self._saved)

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


class NetworkAgent(BaseAgent):

    @property
    def topology(self):
        return self.model.G

    @property
    def G(self):
        return self.model.G

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

        agents = self.model.get_agents(agents)
        return select(agents, **kwargs)

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


class MetaFSM(type):
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


class FSM(NetworkAgent, metaclass=MetaFSM):
    def __init__(self, *args, **kwargs):
        super(FSM, self).__init__(*args, **kwargs)
        if not hasattr(self, 'state_id'):
            if not self.default_state:
                raise ValueError('No default state specified for {}'.format(self.unique_id))
            self.state_id = self.default_state.id

        self.set_state(self.state_id)

    def step(self):
        self.debug(f'Agent {self.unique_id} @ state {self.state_id}')
        try:
            interval = super().step()
        except DeadAgent:
            return time.When('inf')
        if 'id' not in self.state:
            # if 'id' in self.state:
            #     self.set_state(self.state['id'])
            if self.default_state:
                self.set_state(self.default_state.id)
            else:
                raise Exception('{} has no valid state id or default state'.format(self))
        return self.states[self.state_id](self) or interval

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

    ix = 0
    def init_agent(item, id=ix):
        while id in agents:
            id += 1

        agent = remaining[id]
        agent['state'].update(copy(item.get('state', {})))
        agents[id] = agent
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


def select(agents, state_id=None, agent_type=None, ignore=None, iterator=False, **kwargs):

    if state_id is not None and not isinstance(state_id, (tuple, list)):
        state_id = tuple([state_id])
    if agent_type is not None:
        try:
            agent_type = tuple(agent_type)
        except TypeError:
            agent_type = tuple([agent_type])

    f = agents

    if ignore:
        f = filter(lambda x: x not in ignore, f)

    if state_id is not None:
        f = filter(lambda agent: agent.get('state_id', None) in state_id, f)

    if agent_type is not None:
        f = filter(lambda agent: isinstance(agent, agent_type), f)
    for k, v in kwargs.items():
        f = filter(lambda agent: agent.state.get(k, None) == v, f)

    if iterator:
        return f
    return f


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
