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

    def __init__(self, **kwargs):
        self._neighbors = None
        self.alive = True
        state = deepcopy(self.defaults)
        state.update(kwargs.pop('state', {}))
        kwargs['state'] = state
        super().__init__(**kwargs)
        if not hasattr(self, 'level'):
            self.level = logging.DEBUG
        self.logger = logging.getLogger('Agent-{}'.format(self.id))
        self.logger.setLevel(self.level)


    def __getitem__(self, key):
        if isinstance(key, tuple):
            k, t_step = key
            return self.env[self.id, t_step, k]
        return self.state.get(key, None)

    def __delitem__(self, key):
        del self.state[key]

    def __contains__(self, key):
        return key in self.state

    def __setitem__(self, key, value):
        self.state[key] = value

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
            if state_id and state_id != self.global_topology.node[agent]['agent'].state['id']:
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

    @wraps(func)
    def func_wrapper(self):
        when = None
        next_state = func(self)
        try:
            next_state, when = next_state
        except TypeError:
            pass
        if next_state:
            try:
                self.state['id'] = next_state.id
            except AttributeError:
                raise ValueError('State id %s is not valid.' % next_state)
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
            self.state['id'] = self.default_state.id

    def step(self):
        if 'id' in self.state:
            next_state = self.state['id']
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
        self.state['id'] = state


from .BassModel import *
from .BigMarketModel import *
from .IndependentCascadeModel import *
from .ModelM2 import *
from .SentimentCorrelationModel import *
from .SISaModel import *
from .CounterModel import *
from .DrawingAgent import *