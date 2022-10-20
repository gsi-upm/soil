from . import MetaAgent, BaseAgent

from functools import partial, wraps
import inspect


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
                        if self._last_except:
                            n = self._coroutine.throw(self._last_except)
                        else:
                            n = self._coroutine.send(self._last_return)
                        if n:
                            return None, n
                        return n
                    except StopIteration as ex:
                        self._coroutine = None
                        next_state = ex.value
                        if next_state is not None:
                            self._set_state(next_state)
                        return next_state
                    finally:
                        self._last_return = None
                        self._last_except = None

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
    def __init__(self, **kwargs):
        super(FSM, self).__init__(**kwargs)
        if not hasattr(self, "state_id"):
            if not self._default_state:
                raise ValueError(
                    "No default state specified for {}".format(self.unique_id)
                )
            self.state_id = self._default_state.id

        self._coroutine = None
        self._set_state(self.state_id)

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
            self._set_state(next_state)

        return when or default_interval

    def _set_state(self, state, when=None):
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
