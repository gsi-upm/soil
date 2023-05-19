from . import BaseAgent
from ..events import Message, Tell, Ask, TimedOut
from .. import environment, events
from functools import partial
from collections import deque
from types import coroutine

# from soilent import Scheduler


class EventedAgent(BaseAgent):
    # scheduler_class = Scheduler
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert isinstance(self.model, environment.EventedEnvironment), "EventedAgent requires an EventedEnvironment"
        self.model.register(self)

    def received(self, **kwargs):
        return self.model.received(agent=self, **kwargs)

    def tell(self, msg, **kwargs):
        return self.model.tell(msg, recipient=self, **kwargs)

    def broadcast(self, msg, **kwargs):
        return self.model.broadcast(msg, sender=self, **kwargs)

    def ask(self, msg, **kwargs):
        return self.model.ask(msg, recipient=self, **kwargs)

    def process_messages(self):
        return self.model.process_messages(self.model.inbox_for(self))


Evented = EventedAgent
