import nxsim
from collections import OrderedDict
from copy import deepcopy
import json

from functools import wraps


class BaseAgent(nxsim.BaseAgent):
    """
    A special simpy BaseAgent that keeps track of its state history.
    """

    def __init__(self, *args, **kwargs):
        self._history = OrderedDict()
        self._neighbors = None
        super().__init__(*args, **kwargs)
        self._history[None] = deepcopy(self.state)

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
            self._history[self.env.now] = deepcopy(self.state)
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
