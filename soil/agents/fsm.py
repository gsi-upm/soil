from . import MetaAgent, BaseAgent
from .. import time
from types import coroutine
from functools import partial, wraps
import inspect


class State:
    __slots__ = ("awaitable", "f", "attribute", "generator", "name", "default")

    def __init__(self, f, name, default, generator, awaitable):
        self.f = f
        self.name = name
        self.attribute = "_{}".format(name)
        self.generator = generator
        self.awaitable = awaitable
        self.default = default

    @property
    def id(self):
        return self.name
    
    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        try:
            return getattr(obj, self.attribute)
        except AttributeError:
            b = self.bind(obj)
            setattr(obj, self.attribute, b)
            return b

    def bind(self, obj):
        bs = BoundState(self.f, self.name, self.default, self.generator, self.awaitable, obj=obj)
        setattr(obj, self.name, bs)
        return bs

    def __call__(self, *args, **kwargs):
        raise Exception("States should not be called directly")


class BoundState(State):
    __slots__ = ("obj", )

    def __init__(self, *args, obj):
        super().__init__(*args)
        self.obj = obj

    @coroutine
    def __call__(self):
        if self.generator or self.awaitable:
            f = self.f
            next_state = yield from f(self.obj)
            return next_state

        else:
            return self.f(self.obj)


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
        return State(func, name, default, generator, awaitable)

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
        bound_states = {}
        for (k, v) in list(self._states.items()):
            if isinstance(v, State):
                v = v.bind(self)
            bound_states[k] = v
            setattr(self, k, v)

        self._states = bound_states

        if state_id is not None:
            self._set_state(state_id)
        else:
            self._set_state(self._state)
        # If more than "dead" state is defined, but no default state
        if len(self._states) > 1 and not self._state:
            raise ValueError(
                f"No default state specified for {type(self)}({self.unique_id})"
            )

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

    @coroutine
    def step(self):
        if self._state is None:
            if len(self._states) == 1:
                raise Exception("Agent class has no valid states: {}. Make sure to define states or define a custom step function".format(self.__class__.__name__))
            else:
                raise Exception("Invalid state (None) for agent {}".format(self))

        next_state = yield from self._state()

        try:
            next_state, when = next_state
            self._set_state(next_state)
            return when
        except (TypeError, ValueError) as ex:
            try:
                self._set_state(next_state)
                return None
            except ValueError:
                return next_state

    def _set_state(self, state):
        if state is None:
            return
        if isinstance(state, str):
            if state not in self._states:
                raise ValueError("{} is not a valid state".format(state))
            state = self._states[state]
        if isinstance(state, State):
            state = state.bind(self)
        elif not isinstance(state, BoundState):
            raise ValueError("{} is not a valid state".format(state))
        self._state = state

    def die(self, *args, **kwargs):
        super().die(*args, **kwargs)
        return self.dead.at(time.INFINITY)

    @state
    def dead(self):
        return time.INFINITY
