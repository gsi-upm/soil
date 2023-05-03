from . import MetaAgent, BaseAgent
from .. import time
from types import coroutine
from functools import partial, wraps
import inspect


class State:
    __slots__ = ("awaitable", "f", "generator", "name", "default")

    def __init__(self, f, name, default, generator, awaitable):
        self.f = f
        self.name = name
        self.generator = generator
        self.awaitable = awaitable
        self.default = default

    @coroutine
    def step(self, obj):
        if self.generator or self.awaitable:
            f = self.f
            next_state = yield from f(obj)
            return next_state

        else:
            return self.f(obj)

    @property
    def id(self):
        return self.name

    def __call__(self, *args, **kwargs):
        raise Exception("States should not be called directly")

class UnboundState(State):

    def bind(self, obj):
        bs = BoundState(self.f, self.name, self.default, self.generator, self.awaitable, obj=obj)
        setattr(obj, self.name, bs)
        return bs


class BoundState(State):
    __slots__ = ("obj", )

    def __init__(self, *args, obj):
        super().__init__(*args)
        self.obj = obj
    
    def delay(self, delta=0):
        return self, self.obj.delay(delta)
    
    def at(self, when):
        return self, self.obj.at(when)


def state(name=None, default=False):
    def decorator(func, name=None):
        """
        A state function should return either a state id, or a tuple (state_id, when)
        The default value for state_id is the current state id.
        """
        name = name or func.__name__
        generator = inspect.isgeneratorfunction(func)
        awaitable = inspect.iscoroutinefunction(func) or inspect.isasyncgen(func)
        return UnboundState(func, name, default, generator, awaitable)

    if callable(name):
        return decorator(name)
    else:
        return partial(decorator, name=name)


def default_state(func):
    func.default = True
    return func


class MetaFSM(MetaAgent):
    def __new__(mcls, name, bases, namespace):
        states = {}
        # Re-use states from inherited classes
        default_state = None
        for i in bases:
            if isinstance(i, MetaFSM):
                for state_id, state in i._states.items():
                    if state.default:
                        default_state = state
                    states[state_id] = state

        # Add new states
        for attr, func in namespace.items():
            if isinstance(func, State):
                if func.default:
                    default_state = func
                states[func.name] = func

        namespace.update(
            {
                "_state": default_state,
                "_states": states,
            }
        )

        cls = super(MetaFSM, mcls).__new__(
            mcls=mcls, name=name, bases=bases, namespace=namespace
        )
        for (k, v) in states.items():
            setattr(cls, k, v)
        return cls


class FSM(BaseAgent, metaclass=MetaFSM):
    def __init__(self, init=True, state_id=None, **kwargs):
        super().__init__(**kwargs, init=False)
        if state_id is not None:
            self._set_state(state_id)
        # If more than "dead" state is defined, but no default state
        if len(self._states) > 1 and not self._state:
            raise ValueError(
                f"No default state specified for {type(self)}({self.unique_id})"
            )
        for (k, v) in self._states.items():
            setattr(self, k, v.bind(self))

        if init:
            self.init()

    @classmethod
    def states(cls):
        return list(cls._states.keys())

    @property
    def state_id(self):
        return self._state.name
    
    def set_state(self, value):
        if self.now > 0:
            raise ValueError("Cannot change state after init")
        self._set_state(value)

    def step(self):
        self._check_alive()
        next_state = yield from self._state.step(self)

        try:
            next_state, when = next_state
        except (TypeError, ValueError) as ex:
            try:
                self._set_state(next_state)
                return None
            except ValueError:
                return next_state

        self._set_state(next_state)
        return when

    def _set_state(self, state):
        if state is None:
            return
        if isinstance(state, str):
            if state not in self._states:
                raise ValueError("{} is not a valid state".format(state))
            state = self._states[state]
        if not isinstance(state, State):
            raise ValueError("{} is not a valid state".format(state))
        self._state = state

    def die(self, *args, **kwargs):
        super().die(*args, **kwargs)
        return self.dead.at(time.INFINITY)

    @state
    def dead(self):
        return time.INFINITY