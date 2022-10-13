from mesa.time import BaseScheduler
from queue import Empty
from heapq import heappush, heappop, heapify
import math
from .utils import logger
from mesa import Agent as MesaAgent


INFINITY = float('inf')

class When:
    def __init__(self, time):
        if isinstance(time, When):
            return time
        self._time = time

    def abs(self, time):
        return self._time


NEVER = When(INFINITY)


class Delta(When):
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
        super().__init__(*args, **kwargs)
        self._next = {}
        self._queue = []
        self.next_time = 0
        self.logger = logger.getChild(f'time_{ self.model }')

    def add(self, agent: MesaAgent, when=None):
        if when is None:
            when = self.time
        if agent.unique_id in self._agents:
            self._queue.remove((self._next[agent.unique_id], agent.unique_id))
            del self._agents[agent.unique_id]
            heapify(self._queue)
        
        heappush(self._queue, (when, agent.unique_id))
        self._next[agent.unique_id] = when
        super().add(agent)

    def step(self) -> None:
        """
        Executes agents in order, one at a time. After each step,
        an agent will signal when it wants to be scheduled next.
        """

        self.logger.debug(f'Simulation step {self.next_time}')
        if not self.model.running:
            return

        self.time = self.next_time
        when = self.time

        while self._queue and self._queue[0][0] == self.time:
            (when, agent_id) = heappop(self._queue)
            self.logger.debug(f'Stepping agent {agent_id}')

            agent = self._agents[agent_id]
            returned = agent.step()

            if not agent.alive:
                self.remove(agent)
                continue

            when = (returned or Delta(1)).abs(self.time)
            if when < self.time:
                raise Exception("Cannot schedule an agent for a time in the past ({} < {})".format(when, self.time))

            self._next[agent_id] = when
            heappush(self._queue, (when, agent_id))

        self.steps += 1

        if not self._queue:
            self.time = INFINITY
            self.next_time = INFINITY
            self.model.running = False
            return self.time

        self.next_time = self._queue[0][0]
        self.logger.debug(f'Next step: {self.next_time}')
