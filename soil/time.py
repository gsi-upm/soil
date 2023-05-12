from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop, heapreplace
from collections import deque, defaultdict
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

class When:
    def __init__(self, when):
        raise Exception("The use of When is deprecated. Use the `Agent.at` and `Agent.delay` methods instead")
class Delta:
    def __init__(self, delta):
        raise Exception("The use of Delay is deprecated. Use the `Agent.at` and `Agent.delay` methods instead")

class DeadAgent(Exception):
    pass


class PQueueActivation(BaseScheduler):
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
        self.agents_by_type = defaultdict(dict)

    def add(self, agent: MesaAgent, when=None):
        if when is None:
            when = self.time
        else:
            when = float(when)
        agent_class = type(agent)
        self.agents_by_type[agent_class][agent.unique_id] = agent
        super().add(agent)
        self.add_callback(agent.step, when)
    
    def add_callback(self, callback, when=None, replace=False):
        if when is None:
            when = self.time
        else:
            when = float(when)
        if self._shuffle:
            key = (when, self.model.random.random())
        else:
            key = when
        if replace:
            heapreplace(self._queue, (key, callback))
        else:
            heappush(self._queue, (key, callback))

    def remove(self, agent):
        del self._agents[agent.unique_id]
        del self._agents[type(agent)][agent.unique_id]
        for i, (key, callback) in enumerate(self._queue):
            if callback == agent.step:
                del self._queue[i]
                break

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

            when = agent.step() or 1

            if when == INFINITY:
                heappop(self._queue)
                continue
            when += now

            self.add_callback(agent, when, replace=True)

        self.steps += 1

        self.time = next_time

        if next_time == INFINITY:
            self.model.running = False
            self.time = INFINITY
            return


class TimedActivation(BaseScheduler):
    def __init__(self, *args, shuffle=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = deque()
        self._shuffle = shuffle
        self.logger = getattr(self.model, "logger", logger).getChild(f"time_{ self.model }")
        self.next_time = self.time
        self.agents_by_type = defaultdict(dict)

    def add(self, agent: MesaAgent, when=None):
        self.add_callback(agent.step, when)
        agent_class = type(agent)
        self.agents_by_type[agent_class][agent.unique_id] = agent
        super().add(agent)
    
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

    def add_callback(self, func, when=None, replace=False):
        lst = self._find_loc(when)
        lst.append(func)
    
    def add_bulk(self, funcs, when=None):
        lst = self._find_loc(when)
        lst.extend(funcs)

    def remove(self, agent):
        del self._agents[agent.unique_id]
        del self.agents_by_type[type(agent)][agent.unique_id]

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
        next_batch = defaultdict(list)
        for func in bucket:
            when = func() or 1

            if when != INFINITY:
                when += now
                next_batch[when].append(func) 
        
        for (when, bucket) in next_batch.items():
            self.add_bulk(bucket, when)

        self.steps += 1
        if self._queue:
            self.time = self._queue[0][0]
        else:
            self.model.running = False
            self.time = INFINITY


class ShuffledTimedActivation(TimedActivation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=True, **kwargs)


class OrderedTimedActivation(TimedActivation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, shuffle=False, **kwargs)


