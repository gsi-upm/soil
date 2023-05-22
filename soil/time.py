from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop, heapreplace
from collections import deque, defaultdict
import math
import logging

from inspect import getsource
from numbers import Number
from textwrap import dedent
import random as random_std

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

    def __eq__(self, other):
        return float(self) == float(other)

    def __await__(self):
        return (yield self.delta)

class When:
    def __init__(self, when):
        raise Exception("The use of When is deprecated. Use the `Agent.at` and `Agent.delay` methods instead")

class Delta:
    def __init__(self, delta):
        raise Exception("The use of Delay is deprecated. Use the `Agent.at` and `Agent.delay` methods instead")

class DeadAgent(Exception):
    pass


class Event(object):
    def __init__(self, when: float, func, order=1):
        self.when = when
        self.func = func
        self.order = order

    def __repr__(self):
        return f'Event @ {self.when} - Func: {self.func}'

    def __lt__(self, other):
        return (self.when < other.when) or (self.when == other.when and self.order < other.order)


class PQueueSchedule:
    """
    A scheduler which activates each function with a delay returned by the function at each step.
    If no delay is returned, a default of 1 is used.
    """

    def __init__(self, shuffle=True, seed=None, time=0, **kwargs):
        self._queue = []
        self._shuffle = shuffle
        self.time = time
        self.steps = 0
        self.random = random_std.Random(seed)
        self.next_time = self.time

    def insert(self, when, callback, replace=False):
        if when is None:
            when = self.time
        else:
            when = float(when)
        order = 1
        if self._shuffle:
            order = self.random.random()
        event = Event(when, callback, order=order)
        if replace:
            heapreplace(self._queue, event)
        else:
            heappush(self._queue, event)

    def remove(self, callback):
        for i, event in enumerate(self._queue):
            if callback == event.func:
                del self._queue[i]
                break

    def __len__(self):
        return len(self._queue)

    def step(self) -> None:
        """
        Executes events in order, one at a time. After each step,
        an event will signal when it wants to be scheduled next.
        """

        if self.time == INFINITY:
            return

        next_time = INFINITY

        now = self.time

        while self._queue:
            event = self._queue[0]
            when = event.when
            if when > now:
                next_time = when
                break

            when = event.func() 
            when = float(when) if when is not None else 1.0

            if when == INFINITY:
                heappop(self._queue)
                continue

            when += now

            self.insert(when, event.func, replace=True)

        self.steps += 1

        self.time = next_time

        if next_time == INFINITY:
            self.time = INFINITY
            return


class Schedule:
    def __init__(self, shuffle=True, seed=None, time=0, **kwargs):
        self._queue = deque()
        self._shuffle = shuffle
        self.time = time
        self.steps = 0
        self.random = random_std.Random(seed)
        self.next_time = self.time

    def _find_loc(self, when=None):
        if when is None:
            when = self.time
        else:
            when = float(when)
        when = when or self.time
        pos = len(self._queue)
        for (ix, l) in enumerate(self._queue):
            if l[0] == when:
                return l[1]
            if l[0] > when:
                pos = ix
                break
        lst = []
        self._queue.insert(pos, (when, lst))
        return lst

    def insert(self, when, func, replace=False):
        if when == INFINITY:
            return
        lst = self._find_loc(when)
        lst.append(func)
    
    def add_bulk(self, funcs, when=None):
        lst = self._find_loc(when)
        n = len(funcs)
        #TODO: remove for performance
        before = len(self)
        lst.extend(funcs)
        assert len(self) == before + n

    def remove(self, func):
        for bucket in self._queue:
            for (ix, e) in enumerate(bucket):
                if e == func:
                    bucket.remove(ix)
                    return

    def __len__(self):
        return sum(len(bucket[1]) for bucket in self._queue)

    def step(self) -> None:
        """
        Executes events in order, one at a time. After each step,
        an event will signal when it wants to be scheduled next.
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
            self.random.shuffle(bucket)
        next_batch = defaultdict(list)
        for func in bucket:
            when = func()
            when = float(when) if when is not None else 1

            if when == INFINITY:
                continue

            when += now
            next_batch[when].append(func) 
        
        for (when, bucket) in next_batch.items():
            self.add_bulk(bucket, when)

        self.steps += 1
        if self._queue:
            self.time = self._queue[0][0]
        else:
            self.time = INFINITY


class InnerActivation(BaseScheduler):
    inner_class = Schedule

    def __init__(self, model, shuffle=True, time=0, **kwargs):
        self.model = model
        self.logger = getattr(self.model, "logger", logger).getChild(f"time_{ self.model }")
        self._agents = {}
        self.agents_by_type = defaultdict(dict)
        self.inner = self.inner_class(shuffle=shuffle, seed=self.model._seed, time=time)

    @property
    def steps(self):
        return self.inner.steps

    @property
    def time(self):
        return self.inner.time

    def add(self, agent: MesaAgent, when=None):
        when = when or self.inner.time
        self.inner.insert(when, agent.step)
        agent_class = type(agent)
        self.agents_by_type[agent_class][agent.unique_id] = agent
        super().add(agent)
    
    def add_callback(self, when, cb):
        self.inner.insert(when, cb)

    def remove_callback(self, when, cb):
        self.inner.remove(cb)
    
    def remove(self, agent):
        del self._agents[agent.unique_id]
        del self.agents_by_type[type(agent)][agent.unique_id]
        self.inner.remove(agent.step)

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """
        self.inner.step()

    def __len__(self):
        return len(self.inner)


class BucketTimedActivation(InnerActivation):
    inner_class = Schedule


class PQueueActivation(InnerActivation):
    inner_class = PQueueSchedule


#Set the bucket implementation as default
TimedActivation = BucketTimedActivation

try:
    from soilent.soilent import BucketScheduler, PQueueScheduler

    class SoilentActivation(InnerActivation):
        inner_class = BucketScheduler
    class SoilentPQueueActivation(InnerActivation):
        inner_class = PQueueScheduler

    # TimedActivation = SoilentBucketActivation
except ImportError:
    pass


class ShuffledTimedActivation(TimedActivation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=True, **kwargs)


class OrderedTimedActivation(TimedActivation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=False, **kwargs)
