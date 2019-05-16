# networkStatus = {}  # Dict that will contain the status of every agent in the network
# sentimentCorrelationNodeArray = []
# for x in range(0, settings.network_params["number_of_nodes"]):
#     sentimentCorrelationNodeArray.append({'id': x})
# Initialize agent states. Let's assume everyone is normal.
    

import nxsim
import logging
from collections import OrderedDict
from copy import deepcopy
from functools import partial
from scipy.spatial import cKDTree as KDTree
import json

from functools import wraps

from .. import serialization, history


def as_node(agent):
    if isinstance(agent, BaseAgent):
        return agent.id
    return agent


class BaseAgent(nxsim.BaseAgent):
    """
    A special simpy BaseAgent that keeps track of its state history.
    """

    defaults = {}

    def __init__(self, environment, agent_id, state=None,
                 name=None, interval=None, **state_params):
        # Check for REQUIRED arguments
        assert environment is not None, TypeError('__init__ missing 1 required keyword argument: \'environment\'. '
                                                  'Cannot be NoneType.')
        # Initialize agent parameters
        self.id = agent_id
        self.name = name or '{}[{}]'.format(type(self).__name__, self.id)
        self.state_params = state_params

        # Register agent to environment
        self.env = environment

        self._neighbors = None
        self.alive = True
        real_state = deepcopy(self.defaults)
        real_state.update(state or {})
        self.state = real_state
        self.interval = interval

        if not hasattr(self, 'level'):
            self.level = logging.DEBUG
        self.logger = logging.getLogger(self.env.name)
        self.logger.setLevel(self.level)

        # initialize every time an instance of the agent is created
        self.action = self.env.process(self.run())

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
        self._state = {}
        for k, v in value.items():
            self[k] = v

    @property
    def global_topology(self):
        return self.env.G
    
    @property
    def environment_params(self):
        return self.env.environment_params
    
    @environment_params.setter
    def environment_params(self, value):
        self.env.environment_params = value

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key, t_step = key
            k = history.Key(key=key, t_step=t_step, agent_id=self.id)
            return self.env[k]
        return self._state.get(key, None)

    def __delitem__(self, key):
        self._state[key] = None

    def __contains__(self, key):
        return key in self._state

    def __setitem__(self, key, value):
        self._state[key] = value
        k = history.Key(t_step=self.now,
                        agent_id=self.id,
                        key=key)
        self.env[k] = value

    def items(self):
        return self._state.items()

    def get(self, key, default=None):
        return self[key] if key in self else default

    @property
    def now(self):
        try:
            return self.env.now
        except AttributeError:
            # No environment
            return None

    def run(self):
        if self.interval is not None:
            interval = self.interval
        elif 'interval' in self:
            interval = self['interval']
        else:
            interval = self.env.interval
        while self.alive:
            res = self.step()
            yield res or self.env.timeout(interval)

    def die(self, remove=False):
        self.alive = False
        if remove:
            super().die()

    def step(self):
        pass

    def count_agents(self, **kwargs):
        return len(list(self.get_agents(**kwargs)))

    def count_neighboring_agents(self, state_id=None, **kwargs):
        return len(super().get_neighboring_agents(state_id=state_id, **kwargs))

    def get_neighboring_agents(self, state_id=None, **kwargs):
        return self.get_agents(limit_neighbors=True, state_id=state_id, **kwargs)

    def get_agents(self, agents=None, limit_neighbors=False, **kwargs):
        if limit_neighbors:
            agents = super().get_agents(limit_neighbors=limit_neighbors)
        else:
            agents = self.env.get_agents(agents)
        return select(agents, **kwargs)

    def log(self, message, *args, level=logging.INFO, **kwargs):
        message = message + " ".join(str(i) for i in args)
        message = "\t{:10}@{:>5}:\t{}".format(self.name, self.now, message)
        for k, v in kwargs:
            message += " {k}={v} ".format(k, v)
        extra = {}
        extra['now'] = self.now
        extra['id'] = self.id
        return self.logger.log(level, message, extra=extra)

    def debug(self, *args, **kwargs):
        return self.log(*args, level=logging.DEBUG, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(*args, level=logging.INFO, **kwargs)

    def __getstate__(self):
        '''
        Serializing an agent will lose all its running information (you cannot
        serialize an iterator), but it keeps the state and link to the environment,
        so it can be used for inspection and dumping to a file
        '''
        state = {}
        state['id'] = self.id
        state['environment'] = self.env
        state['_state'] = self._state
        return state

    def __setstate__(self, state):
        '''
        Get back a serialized agent and try to re-compose it
        '''
        self.id = state['id']
        self._state = state['_state']
        self.env = state['environment']

    def add_edge(self, node1, node2, **attrs):
        node1 = as_node(node1)
        node2 = as_node(node2)

        for n in [node1, node2]:
            if n not in self.global_topology.nodes(data=False):
                raise ValueError('"{}" not in the graph'.format(n))
        return self.global_topology.add_edge(node1, node2, **attrs)

    def subgraph(self, center=True, **kwargs):
        include = [self] if center else []
        return self.global_topology.subgraph(n.id for n in self.get_agents(**kwargs)+include)


class NetworkAgent(BaseAgent):

    def add_edge(self, other, **kwargs):
        return super(NetworkAgent, self).add_edge(node1=self.id, node2=other, **kwargs)

    def ego_search(self, steps=1, center=False, node=None, **kwargs):
        '''Get a list of nodes in the ego network of *node* of radius *steps*'''
        node = as_node(node if node is not None else self)
        G = self.subgraph(**kwargs)
        return nx.ego_graph(G, node, center=center, radius=steps).nodes()

    def degree(self, node, force=False):
        node = as_node(node)
        if force or (not hasattr(self.env, '_degree')) or getattr(self.env, '_last_step', 0) < self.now:
            self.env._degree = nx.degree_centrality(self.global_topology)
            self.env._last_step = self.now
        return self.env._degree[node]

    def betweenness(self, node, force=False):
        node = as_node(node)
        if force or (not hasattr(self.env, '_betweenness')) or getattr(self.env, '_last_step', 0) < self.now:
            self.env._betweenness = nx.betweenness_centrality(self.global_topology)
            self.env._last_step = self.now
        return self.env._betweenness[node]


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


class FSM(BaseAgent, metaclass=MetaFSM):
    def __init__(self, *args, **kwargs):
        super(FSM, self).__init__(*args, **kwargs)
        if 'id' not in self.state:
            if not self.default_state:
                raise ValueError('No default state specified for {}'.format(self.id))
            self['id'] = self.default_state.id

    def step(self):
        if 'id' in self.state:
            next_state = self['id']
        elif self.default_state:
            next_state = self.default_state.id
        else:
            raise Exception('{} has no valid state id or default state'.format(self))
        if next_state not in self.states:
            raise Exception('{} is not a valid id for {}'.format(next_state, self))
        return self.states[next_state](self)

    def set_state(self, state):
        if hasattr(state, 'id'):
            state = state.id
        if state not in self.states:
            raise ValueError('{} is not a valid state'.format(state))
        self['id'] = state
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


STATIC_THRESHOLD = (-1, -1)


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
        network_agents = deepcopy(network_agents)
    elif agent_type:
        network_agents = [{'agent_type': agent_type}]
    else:
        raise ValueError('Specify a distribution or a default agent type')

    # Calculate the thresholds
    total = sum(x.get('weight', 1) for x in network_agents)
    acc = 0
    for v in network_agents:
        if 'ids' in v:
            v['threshold'] = STATIC_THRESHOLD
            continue
        upper = acc + (v.get('weight', 1)/total)
        v['threshold'] = [acc, upper]
        acc = upper
    return network_agents


def serialize_type(agent_type, known_modules=[], **kwargs):
    if isinstance(agent_type, str):
        return agent_type
    known_modules += ['soil.agents']
    return serialization.serialize(agent_type, known_modules=known_modules, **kwargs)[1] # Get the name of the class


def serialize_distribution(network_agents, known_modules=[]):
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


def deserialize_distribution(ind, **kwargs):
    d = deepcopy(ind)
    for v in d:
        v['agent_type'] = deserialize_type(v['agent_type'], **kwargs)
    return d


def _validate_states(states, topology):
    '''Validate states to avoid ignoring states during initialization'''
    states = states or []
    if isinstance(states, dict):
        for x in states:
            assert x in topology.node
    else:
        assert len(states) <= len(topology)
    return states


def _convert_agent_types(ind, to_string=False, **kwargs):
    '''Convenience method to allow specifying agents by class or class name.'''
    if to_string:
        return serialize_distribution(ind, **kwargs)
    return deserialize_distribution(ind, **kwargs)


def _agent_from_distribution(distribution, value=-1, agent_id=None):
    """Used in the initialization of agents given an agent distribution."""
    if value < 0:
        value = random.random()
    for d in sorted(distribution, key=lambda x: x['threshold']):
        threshold = d['threshold']
        # Check if the definition matches by id (first) or by threshold
        if not ((agent_id is not None and threshold == STATIC_THRESHOLD and agent_id in d['ids']) or \
                (value >= threshold[0] and value < threshold[1])):
            continue
        state = {}
        if 'state' in d:
            state = deepcopy(d['state'])
        return d['agent_type'], state

    raise Exception('Distribution for value {} not found in: {}'.format(value, distribution))


class Geo(NetworkAgent):
    '''In this type of network, nodes have a "pos" attribute.'''

    def geo_search(self, radius, node=None, center=False, **kwargs):
        '''Get a list of nodes whose coordinates are closer than *radius* to *node*.'''
        node = as_node(node if node is not None else self)

        G = self.subgraph(**kwargs)

        pos = nx.get_node_attributes(G, 'pos')
        if not pos:
            return []
        nodes, coords = list(zip(*pos.items()))
        kdtree = KDTree(coords)  # Cannot provide generator.
        indices = kdtree.query_ball_point(pos[node], radius)
        return [nodes[i] for i in indices if center or (nodes[i] != node)]


def select(agents, state_id=None, agent_type=None, ignore=None, iterator=False, **kwargs):

    if state_id is not None and not isinstance(state_id, (tuple, list)):
        state_id = tuple([state_id])
    if agent_type is not None:
        try:
            agent_type = tuple(agent_type)
        except TypeError:
            agent_type = tuple([agent_type])

    def matches_all(agent):
        if state_id is not None:
            if agent.state.get('id', None) not in state_id:
                return False
        if agent_type is not None:
            if not isinstance(agent, agent_type):
                return False
        state = agent.state
        for k, v in kwargs.items():
            if state.get(k, None) != v:
                return False
        return True

    f = filter(matches_all, agents)
    if ignore:
        f = filter(lambda x: x not in ignore, f)
    if iterator:
        return f
    return list(f)


from .BassModel import *
from .BigMarketModel import *
from .IndependentCascadeModel import *
from .ModelM2 import *
from .SentimentCorrelationModel import *
from .SISaModel import *
from .CounterModel import *
