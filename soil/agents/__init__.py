# networkStatus = {}  # Dict that will contain the status of every agent in the network
# sentimentCorrelationNodeArray = []
# for x in range(0, settings.network_params["number_of_nodes"]):
#     sentimentCorrelationNodeArray.append({'id': x})
# Initialize agent states. Let's assume everyone is normal.
    

import nxsim
from collections import OrderedDict
from copy import deepcopy
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

    def __init__(self, *args, **kwargs):
        self._history = OrderedDict()
        self._neighbors = None
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            k, t_step = key
            if k is not None:
                if t_step is not None:
                    return self._history[t_step][k]
                else:
                    return {tt: tv.get(k, None) for tt, tv in self._history.items()}
            else:
                return self._history[t_step]
        return self.state[key]

    def __setitem__(self, key, value):
        self.state[key] = value

    def save_state(self):
        self._history[self.now] = deepcopy(self.state)

    @property
    def now(self):
        try:
            return self.env.now
        except AttributeError:
            # No environment
            return None

    def run(self):
        while True:
            res = self.step()
            yield res or self.env.timeout(self.env.interval)

    def step(self):
        pass

    def to_json(self):
        return json.dumps(self._history)


class NetworkAgent(BaseAgent, nxsim.BaseNetworkAgent):

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
        return self.count_agents(state_id, limit_neighbors=True)


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
                raise NotImplemented('State id %s is not valid.' % next_state)
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


from .BassModel import *
from .BigMarketModel import *
from .IndependentCascadeModel import *
from .ModelM2 import *
from .SentimentCorrelationModel import *
from .SISaModel import *
from .CounterModel import *
from .DrawingAgent import *
