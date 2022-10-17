from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop, heapify
import math

from inspect import getsource
from numbers import Number

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

    def next(self, time):
        return self._time

    def abs(self, time):
        return self

    def __repr__(self):
        return str(f"When({self._time})")

    def __lt__(self, other):
        if isinstance(other, Number):
            return self._time < other
        return self._time < other.next(self._time)

    def __gt__(self, other):
        if isinstance(other, Number):
            return self._time > other
        return self._time > other.next(self._time)

    def ready(self, agent):
        return self._time <= agent.model.schedule.time


class Cond(When):
    def __init__(self, func, delta=1):
        self._func = func
        self._delta = delta
        self._checked = False

    def next(self, time):
        if self._checked:
            return time + self._delta
        return time

    def abs(self, time):
        return self

    def ready(self, agent):
        self._checked = True
        return self._func(agent)

    def __eq__(self, other):
        return False

    def __lt__(self, other):
        return True

    def __gt__(self, other):
        return False

    def __repr__(self):
        return str(f'Cond("{getsource(self._func)}")')


NEVER = When(INFINITY)


class Delta(When):
    def __init__(self, delta):
        self._delta = delta

    def __eq__(self, other):
        if isinstance(other, Delta):
            return self._delta == other._delta
        return False

    def abs(self, time):
        return When(self._delta + time)

    def next(self, time):
        return time + self._delta

    def __repr__(self):
        return str(f"Delta({self._delta})")


class TimedActivation(BaseScheduler):
    """A scheduler which activates each agent when the agent requests.
    In each activation, each agent will update its 'next_time'.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._next = {}
        self._queue = []
        self.next_time = 0
        self.logger = logger.getChild(f"time_{ self.model }")

    def add(self, agent: MesaAgent, when=None):
        if when is None:
            when = When(self.time)
        elif not isinstance(when, When):
            when = When(when)
        if agent.unique_id in self._agents:
            del self._agents[agent.unique_id]
            if agent.unique_id in self._next:
                self._queue.remove((self._next[agent.unique_id], agent))
                heapify(self._queue)

        self._next[agent.unique_id] = when
        heappush(self._queue, (when, agent))
        super().add(agent)

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """

        self.logger.debug(f"Simulation step {self.time}")
        if not self.model.running:
            return

        when = NEVER

        to_process = []
        skipped = []
        next_time = INFINITY

        ix = 0

        while self._queue:
            (when, agent) = self._queue[0]
            if when > self.time:
                break
            heappop(self._queue)
            if when.ready(agent):
                to_process.append(agent)
                self._next.pop(agent.unique_id, None)
                continue

            next_time = min(next_time, when.next(self.time))
            self._next[agent.unique_id] = next_time
            skipped.append((when, agent))

        if self._queue:
            next_time = min(next_time, self._queue[0][0].next(self.time))

        self._queue = [*skipped, *self._queue]

        for agent in to_process:
            self.logger.debug(f"Stepping agent {agent}")

            try:
                returned = ((agent.step() or Delta(1))).abs(self.time)
            except DeadAgent:
                if agent.unique_id in self._next:
                    del self._next[agent.unique_id]
                agent.alive = False
                continue

            if not getattr(agent, "alive", True):
                self.remove(agent)
                continue

            value = returned.next(self.time)

            if value < self.time:
                raise Exception(
                    f"Cannot schedule an agent for a time in the past ({when} < {self.time})"
                )
            if value < INFINITY:
                next_time = min(value, next_time)

                self._next[agent.unique_id] = returned
                heappush(self._queue, (returned, agent))
            else:
                assert not self._next[agent.unique_id]

        self.steps += 1
        self.logger.debug(f"Updating time step: {self.time} -> {next_time}")
        self.time = next_time

        if not self._queue or next_time == INFINITY:
            self.model.running = False
            return self.time
