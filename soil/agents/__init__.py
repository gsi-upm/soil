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
import json

from functools import wraps

from .. import utils, history

agent_types = {}


class MetaAgent(type):
    def __init__(cls, name, bases, nmspc):
        super(MetaAgent, cls).__init__(name, bases, nmspc)
        agent_types[name] = cls


class BaseAgent(nxsim.BaseAgent, metaclass=MetaAgent):
    """
    A special simpy BaseAgent that keeps track of its state history.
    """

    defaults = {}

    def __init__(self, environment=None, agent_id=None, state=None,
                 name='network_process', interval=None, **state_params):
        # Check for REQUIRED arguments
        assert environment is not None, TypeError('__init__ missing 1 required keyword argument: \'environment\'. '
                                                  'Cannot be NoneType.')
        # Initialize agent parameters
        self.id = agent_id
        self.name = name
        self.state_params = state_params

        # Global parameters
        self.global_topology = environment.G
        self.environment_params = environment.environment_params

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
        self.logger = logging.getLogger('{}-Agent-{}'.format(self.env.name,
                                                             self.id))
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

    def to_json(self):
        return json.dumps(self.state)

    def count_agents(self, state_id=None, limit_neighbors=False):
        if limit_neighbors:
            agents = self.global_topology.neighbors(self.id)
        else:
            agents = self.global_topology.nodes()
        count = 0
        for agent in agents:
            if state_id and state_id != self.global_topology.node[agent]['agent']['id']:
                continue
            count += 1
        return count

    def count_neighboring_agents(self, state_id=None):
        return len(super().get_agents(state_id, limit_neighbors=True))

    def get_agents(self, state_id=None, limit_neighbors=False, iterator=False, **kwargs):
        if limit_neighbors:
            agents = super().get_agents(state_id, limit_neighbors)
        else:
            agents = filter(lambda x: state_id is None or x.state.get('id', None) == state_id,
                            self.env.agents)

        def matches_all(agent):
            state = agent.state
            for k, v in kwargs.items():
                if state.get(k, None) != v:
                    return False
            return True

        f = filter(matches_all, agents)
        if iterator:
            return f
        return list(f)

    def log(self, message, *args, level=logging.INFO, **kwargs):
        message = message + " ".join(str(i) for i in args)
        message = "\t@{:>5}:\t{}".format(self.now, message)
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


def state(func):
    '''
    A state function should return either a state id, or a tuple (state_id, when)
    The default value for state_id is the current state id.
    The default value for when is the interval defined in the nevironment.
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

    func_wrapper.id = func.__name__
    func_wrapper.is_default = False
    return func_wrapper


def default_state(func):
    func.is_default = True
    return func


class MetaFSM(MetaAgent):
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
        self.states[next_state](self)

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
        return []

    # Calculate the thresholds
    total = sum(x.get('weight', 1) for x in network_agents)
    acc = 0
    for v in network_agents:
        upper = acc + (v.get('weight', 1)/total)
        v['threshold'] = [acc, upper]
        acc = upper
    return network_agents


def _serialize_distribution(network_agents):
    d = _convert_agent_types(network_agents,
                             to_string=True)
    '''
    When serializing an agent distribution, remove the thresholds, in order
    to avoid cluttering the YAML definition file.
    '''
    for v in d:
        if 'threshold' in v:
            del v['threshold']
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


def _convert_agent_types(ind, to_string=False):
    '''Convenience method to allow specifying agents by class or class name.'''
    d = deepcopy(ind)
    for v in d:
        agent_type = v['agent_type']
        if to_string and not isinstance(agent_type, str):
            v['agent_type'] = str(agent_type.__name__)
        elif not to_string and isinstance(agent_type, str):
            v['agent_type'] = agent_types[agent_type]
    return d


def _agent_from_distribution(distribution, value=-1):
    """Used in the initialization of agents given an agent distribution."""
    if value < 0:
        value = random.random()
    for d in distribution:
        threshold = d['threshold']
        if value >= threshold[0] and value < threshold[1]:
            state = {}
            if 'state' in d:
                state = deepcopy(d['state'])
            return d['agent_type'], state

    raise Exception('Distribution for value {} not found in: {}'.format(value, distribution))


from .BassModel import *
from .BigMarketModel import *
from .IndependentCascadeModel import *
from .ModelM2 import *
from .SentimentCorrelationModel import *
from .SISaModel import *
from .CounterModel import *
from .DrawingAgent import *
