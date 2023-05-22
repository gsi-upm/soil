from __future__ import annotations

import logging
from collections.abc import MutableMapping
from copy import deepcopy
import inspect
import textwrap
import warnings
import sys

from mesa import Agent as MesaAgent

from .. import utils, time

from .meta import MetaAgent


IGNORED_FIELDS = ("model", "logger")


class BaseAgent(MesaAgent, MutableMapping, metaclass=MetaAgent):
    """
    A special type of Mesa Agent that:

    * Can be used as a dictionary to access its state.
    * Has logging built-in
    * Can be given default arguments through a defaults class attribute,
    which will be used on construction to initialize each agent's state

    Any attribute that is not preceded by an underscore (`_`) will also be added to its state.
    """

    def __init__(self, unique_id=None, model=None, name=None, init=True, **kwargs):
        # Ideally, model should be the first argument, but Mesa's Agent class has unique_id first
        assert not (model is None), "Must provide a model"
        if unique_id is None:
            unique_id = model.next_id()
        super().__init__(unique_id=unique_id, model=model)

        self.name = (
            str(name) if name else "{}[{}]".format(type(self).__name__, self.unique_id)
        )

        self.alive = True

        logger = utils.logger.getChild(getattr(self.model, "id", self.model)).getChild(
            self.name
        )
        self.logger = logging.LoggerAdapter(logger, {"agent_name": self.name})

        if hasattr(self, "level"):
            self.logger.setLevel(self.level)

        for k in self._defaults:
            v = getattr(model, k, None)
            if v is not None:
                setattr(self, k, v)

        for (k, v) in self._defaults.items():
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, deepcopy(v))

        for (k, v) in kwargs.items():
            setattr(self, k, v)

        if init:
            self.init()

    def init(self):
        pass

    def __hash__(self):
        return hash(self.unique_id)

    def prob(self, probability):
        return utils.prob(probability, self.model.random)

    @classmethod
    def w(cls, **kwargs):
        return utils.custom(cls, **kwargs)

    # TODO: refactor to clean up mesa compatibility
    @property
    def id(self):
        msg = "This attribute is deprecated. Use `unique_id` instead"
        warnings.warn(msg, DeprecationWarning)
        print(msg, file=sys.stderr)
        return self.unique_id

    @property
    def env(self):
        msg = "This attribute is deprecated. Use `model` instead"
        warnings.warn(msg, DeprecationWarning)
        print(msg, file=sys.stderr)
        return self.model

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"key {key}  not found in agent")

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
        return (k for k in self.__dict__ if k[0] != "_" and k not in IGNORED_FIELDS)

    def items(self, keys=None, skip=None):
        keys = keys if keys is not None else self.keys()
        it = ((k, self.get(k, None)) for k in keys)
        if skip:
            return filter(lambda x: x[0] not in skip, it)
        return it

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            try:
                return getattr(self.model, key)
            except AttributeError:
                return default

    @property
    def now(self):
        try:
            return self.model.now
        except AttributeError:
            # No environment
            return None

    def die(self, msg=None):
        if msg:
            self.info("Agent dying:", msg)
        else:
            self.debug(f"agent dying")
        self.alive = False
        return time.Delay(time.INFINITY)

    def step(self):
        raise NotImplementedError("Agent must implement step method")

    def _check_alive(self):
        if not self.alive:
            raise time.DeadAgent(self.unique_id)

    def log(self, *message, level=logging.INFO, **kwargs):
        if not self.logger.isEnabledFor(level):
            return
        message = " ".join(str(i) for i in message)
        message = "[@{:>4}]\t{:>10}: {}".format(self.now, repr(self), message)
        for k, v in kwargs:
            message += " {k}={v} ".format(k, v)
        extra = {}
        extra["now"] = self.now
        extra["unique_id"] = self.unique_id
        extra["agent_name"] = self.name
        return self.logger.log(level, message, extra=extra)

    def debug(self, *args, **kwargs):
        return self.log(*args, level=logging.DEBUG, **kwargs)

    def info(self, *args, **kwargs):
        return self.log(*args, level=logging.INFO, **kwargs)

    def count_agents(self, **kwargs):
        return len(list(self.get_agents(**kwargs)))

    def get_agents(self, *args, **kwargs):
        it = self.iter_agents(*args, **kwargs)
        return list(it)

    def iter_agents(self, *args, **kwargs):
        yield from filter_agents(self.model.schedule._agents, *args, **kwargs)

    def __str__(self):
        return self.to_str()

    def to_str(self, keys=None, skip=None, pretty=False):
        content = dict(self.items(keys=keys))
        if pretty and content:
            d = content
            content = "\n"
            for k, v in d.items():
                content += f"- {k}: {v}\n"
            content = textwrap.indent(content, "    ")
        return f"{repr(self)}{content}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.unique_id})"

    def at(self, at):
        return time.Delay(float(at) - self.now)

    def delay(self, delay=1):
        return time.Delay(delay)


from .network_agents import *
from .fsm import *
from .evented import *
from .view import *


class Noop(EventedAgent, BaseAgent):
    def step(self):
        return


class Agent(FSM, EventedAgent, NetworkAgent):
    """Default agent class, has network, FSM and event capabilities"""


# Additional types of agents
from .BassModel import *
from .IndependentCascadeModel import *
from .SISaModel import *
from .CounterModel import *
