from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop
import math
from .utils import logger
from mesa import Agent


INFINITY = float('inf')

class When:
    def __init__(self, time):
        self._time = time

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

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """

        if self.next_time == INFINITY:
            return

        self.time = self.next_time
        when = self.time

        while self._queue and self._queue[0][0] == self.time:
            (when, agent_id) = heappop(self._queue)
            logger.debug(f'Stepping agent {agent_id}')

            when = (self._agents[agent_id].step() or Delta(1)).abs(self.time)
            if when < self.time:
                raise Exception("Cannot schedule an agent for a time in the past ({} < {})".format(when, self.time))

            heappush(self._queue, (when, agent_id))

        self.steps += 1

        if not self._queue:
            self.time = INFINITY
            self.next_time = INFINITY
            return

        self.next_time = self._queue[0][0]

