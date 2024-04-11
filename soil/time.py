from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop, heapreplace
from collections import deque
import math
import logging

from inspect import getsource
from numbers import Number
from textwrap import dedent

from .utils import logger
from mesa import Agent as MesaAgent


INFINITY = float("inf")

class Delay:
    """A delay object which can be used both as a return value and as an awaitable (in async code)."""
    __slots__ = ("delta", )
    def __init__(self, delta):
        self.delta = float(delta)

    def __float__(self):
        return self.delta
    
    def __await__(self):
        return (yield self.delta)


class DeadAgent(Exception):
    pass


class DiscreteActivation(BaseScheduler):
    default_interval = 1
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.model, 'default_interval'):
            self.default_interval = self.model.interval


class PQueueActivation(DiscreteActivation):
    """
    A scheduler which activates each agent with a delay returned by the agent's step method.
    If no delay is returned, a default of 1 is used.
    
    In each activation, each agent will update its 'next_time'.
    """

    def __init__(self, *args, shuffle=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = []
        self._shuffle = shuffle
        self.logger = getattr(self.model, "logger", logger).getChild(f"time_{ self.model }")
        self.next_time = self.time

    def add(self, agent: MesaAgent, when=None):
        if when is None:
            when = self.time
        else:
            when = float(when)

        self._schedule(agent, None, when)
        super().add(agent)

    def _schedule(self, agent, when=None, replace=False):
        if when is None:
            when = self.time
        if self._shuffle:
            key = (when, self.model.random.random())
        else:
            key = (when, agent.unique_id)
        if replace:
            heapreplace(self._queue, (key, agent))
        else:
            heappush(self._queue, (key, agent))

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """

        if self.time == INFINITY:
            return

        next_time = INFINITY

        now = self.time

        while self._queue:
            ((when, _id), agent) = self._queue[0]
            if when > now:
                next_time = when
                break

            try:
                when = agent.step() or self.default_interval
                when += now
            except DeadAgent:
                heappop(self._queue)
                continue

            if when == INFINITY:
                heappop(self._queue)
                continue

            self._schedule(agent, when, replace=True)

        self.steps += 1

        self.time = next_time

        if next_time == INFINITY:
            self.model.running = False
            self.time = INFINITY
            return


class TimedActivation(DiscreteActivation):
    '''A discrete-time scheduler that has time buckets with agents that should be woken at the same time instant.'''
    def __init__(self, *args, shuffle=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = deque()
        self._shuffle = shuffle
        self.logger = getattr(self.model, "logger", logger).getChild(f"time_{ self.model }")
        self.next_time = self.time

    def add(self, agent: MesaAgent, when=None):
        if when is None:
            when = self.time
        else:
            when = float(when)
        self._schedule(agent, None, when)
        super().add(agent)

    def _schedule(self, agent, when=None, replace=False):
        when = when or self.time
        pos = len(self._queue)
        for (ix, l) in enumerate(self._queue):
            if l[0] == when:
                l[1].append(agent)
                return
            if l[0] > when:
                pos = ix
                break
        self._queue.insert(pos, (when, [agent]))

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """
        if not self._queue:
            return

        now = self.time

        next_time = self._queue[0][0]

        if next_time > now:
            self.time = next_time
            return

        bucket = self._queue.popleft()[1]
        if self._shuffle:
            self.model.random.shuffle(bucket)
        for agent in bucket:
            try:
                when = agent.step() or self.default_interval
                when += now
            except DeadAgent:
                continue

            if when != INFINITY:
                self._schedule(agent, when, replace=True)

        self.steps += 1
        if self._queue:
            self.time = self._queue[0][0]
        else:
            self.time = INFINITY


class ShuffledTimedActivation(TimedActivation):
    '''
    A TimedActivation scheduler that processes events in random order.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=True, **kwargs)


class OrderedTimedActivation(TimedActivation):
    '''
    A TimedActivation scheduler that always processes events in
    the same order.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=False, **kwargs)


Scheduler = TimedActivation

    
class Lockstepper:
    '''
    A wrapper class to produce discrete-event schedulers that behave like
    fixed-time schedulers.
    '''
    
    def  __init__(self, scheduler: BaseScheduler, interval=1):
        self.scheduler = scheduler
        self.default_interval = interval
        self.time = scheduler.time
        self.steps = 0

    def step(self):
        end_time = self.time + self.default_interval
        res = None
        while self.scheduler.time < end_time:
            res = self.scheduler.step()
        self.time = end_time
        self.steps += 1
        return res

    def __getattr__(self, name):
        return getattr(self.scheduler, name)