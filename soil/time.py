from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop
import math
from .utils import logger
from mesa import Agent


class When:
    def __init__(self, time):
        self._time = float(time)

    def abs(self, time):
        return self._time


class Delta:
    def __init__(self, delta):
        self._delta = delta

    def __eq__(self, other):
        return self._delta == other._delta

    def abs(self, time):
        return time + self._delta


class TimedActivation(BaseScheduler):
    """A scheduler which activates each agent when the agent requests.
    In each activation, each agent will update its 'next_time'.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self)
        self._queue = []
        self.next_time = 0

    def add(self, agent: Agent):
        if agent.unique_id not in self._agents:
            heappush(self._queue, (self.time, agent.unique_id))
            super().add(agent)

    def step(self, until: float =float('inf')) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """

        when = None
        agent_id = None
        unsched = []
        until = until or float('inf')

        if not self._queue:
            self.time = until
            self.next_time = float('inf')
            return

        (when, agent_id) = self._queue[0]

        if until and when > until:
            self.time = until
            self.next_time = when
            return

        self.time = when
        next_time = float("inf")

        while when == self.time:
            heappop(self._queue)
            logger.debug(f'Stepping agent {agent_id}')
            when = (self._agents[agent_id].step() or Delta(1)).abs(self.time)
            heappush(self._queue, (when, agent_id))
            if when < next_time:
                next_time = when

            if not self._queue or self._queue[0][0] > self.time:
                agent_id = None
                break
            else:
                (when, agent_id) = self._queue[0]

        if when and when < self.time:
            raise Exception("Invalid scheduling time")

        self.next_time = next_time
        self.steps += 1
