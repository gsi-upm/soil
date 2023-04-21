from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop, heapreplace
import math

from inspect import getsource
from numbers import Number
from textwrap import dedent

from .utils import logger
from mesa import Agent as MesaAgent


INFINITY = float("inf")


class DeadAgent(Exception):
    pass


class When:
    def __init__(self, time):
        if isinstance(time, When):
            return time
        self._time = time

    def abs(self, time):
        return self._time

    def schedule_next(self, time, delta, first=False):
        return (self._time, None)


NEVER = When(INFINITY)


class Delta(When):
    def __init__(self, delta):
        self._delta = delta

    def abs(self, time):
        return self._time + self._delta

    def __eq__(self, other):
        if isinstance(other, Delta):
            return self._delta == other._delta
        return False

    def schedule_next(self, time, delta, first=False):
        return (time + self._delta, None)

    def __repr__(self):
        return str(f"Delta({self._delta})")


class BaseCond:
    def __init__(self, msg=None, delta=None, eager=False):
        self._msg = msg
        self._delta = delta
        self.eager = eager

    def schedule_next(self, time, delta, first=False):
        if first and self.eager:
            return (time, self)
        if self._delta:
            delta = self._delta
        return (time + delta, self)

    def return_value(self, agent):
        return None

    def __repr__(self):
        return self._msg or self.__class__.__name__


class Cond(BaseCond):
    def __init__(self, func, *args, **kwargs):
        self._func = func
        super().__init__(*args, **kwargs)

    def ready(self, agent, time):
        return self._func(agent)

    def __repr__(self):
        if self._msg:
            return self._msg
        return str(f'Cond("{dedent(getsource(self._func)).strip()}")')


class TimedActivation(BaseScheduler):
    """A scheduler which activates each agent when the agent requests.
    In each activation, each agent will update its 'next_time'.
    """

    def __init__(self, *args, shuffle=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._next = {}
        self._queue = []
        self._shuffle = shuffle
        # self.step_interval = getattr(self.model, "interval", 1)
        self.step_interval = self.model.interval
        self.logger = getattr(self.model, "logger", logger).getChild(f"time_{ self.model }")
        self.next_time = self.time

    def add(self, agent: MesaAgent, when=None):
        if when is None:
            when = self.time
        elif isinstance(when, When):
            when = when.abs()

        self._schedule(agent, None, when)
        super().add(agent)

    def _schedule(self, agent, condition=None, when=None, replace=False):
        if condition:
            if not when:
                when, condition = condition.schedule_next(
                    when or self.time, self.step_interval
                )
        else:
            if when is None:
                when = self.time + self.step_interval
            condition = None
        if self._shuffle:
            key = (when, self.model.random.random(), condition)
        else:
            key = (when, agent.unique_id, condition)
        self._next[agent.unique_id] = key
        if replace:
            heapreplace(self._queue, (key, agent))
        else:
            heappush(self._queue, (key, agent))

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """

        self.logger.debug(f"Simulation step {self.time}")
        if not self.model.running or self.time == INFINITY:
            return

        self.logger.debug(f"Queue length: %s", len(self._queue))

        while self._queue:
            ((when, _id, cond), agent) = self._queue[0]
            if when > self.time:
                break

            if cond:
                if not cond.ready(agent, self.time):
                    self._schedule(agent, cond, replace=True)
                    continue
                try:
                    agent._last_return = cond.return_value(agent)
                except Exception as ex:
                    agent._last_except = ex
            else:
                agent._last_return = None
                agent._last_except = None

            self.logger.debug("Stepping agent %s", agent)
            self._next.pop(agent.unique_id, None)

            try:
                returned = agent.step()
            except DeadAgent:
                agent.alive = False
                heappop(self._queue)
                continue

            # Check status for MESA agents
            if not getattr(agent, "alive", True):
                heappop(self._queue)
                continue

            if returned:
                next_check = returned.schedule_next(
                    self.time, self.step_interval, first=True
                )
                self._schedule(agent, when=next_check[0], condition=next_check[1], replace=True)
            else:
                next_check = (self.time + self.step_interval, None)

                self._schedule(agent, replace=True)

        self.steps += 1

        if not self._queue:
            self.model.running = False
            self.time = INFINITY
            return

        next_time = self._queue[0][0][0]

        if next_time < self.time:
            raise Exception(
                f"An agent has been scheduled for a time in the past, there is probably an error ({when} < {self.time})"
            )
        self.logger.debug("Updating time step: %s -> %s ", self.time, next_time)

        self.time = next_time


class ShuffledTimedActivation(TimedActivation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=True, **kwargs)


class OrderedTimedActivation(TimedActivation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=False, **kwargs)
