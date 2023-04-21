from . import BaseAgent
from ..events import Message, Tell, Ask, TimedOut
from ..time import BaseCond
from functools import partial
from collections import deque


class ReceivedOrTimeout(BaseCond):
    def __init__(
        self, agent, expiration=None, timeout=None, check=True, ignore=False, **kwargs
    ):
        if expiration is None:
            if timeout is not None:
                expiration = agent.now + timeout
        self.expiration = expiration
        self.ignore = ignore
        self.check = check
        super().__init__(**kwargs)

    def expired(self, time):
        return self.expiration and self.expiration < time

    def ready(self, agent, time):
        return len(agent._inbox) or self.expired(time)

    def return_value(self, agent):
        if not self.ignore and self.expired(agent.now):
            raise TimedOut("No messages received")
        if self.check:
            agent.check_messages()
        return None

    def schedule_next(self, time, delta, first=False):
        if self._delta is not None:
            delta = self._delta
        return (time + delta, self)

    def __repr__(self):
        return f"ReceivedOrTimeout(expires={self.expiration})"


class EventedAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inbox = deque()
        self._processed = 0

    def on_receive(self, *args, **kwargs):
        pass

    def received(self, *args, **kwargs):
        return ReceivedOrTimeout(self, *args, **kwargs)

    def tell(self, msg, sender=None):
        self._inbox.append(Tell(timestamp=self.now, payload=msg, sender=sender))

    def ask(self, msg, timeout=None, **kwargs):
        ask = Ask(timestamp=self.now, payload=msg, sender=self)
        self._inbox.append(ask)
        expiration = float("inf") if timeout is None else self.now + timeout
        return ask.replied(expiration=expiration, **kwargs)

    def check_messages(self):
        changed = False
        while self._inbox:
            msg = self._inbox.popleft()
            self._processed += 1
            if msg.expired(self.now):
                continue
            changed = True
            reply = self.on_receive(msg.payload, sender=msg.sender)
            if isinstance(msg, Ask):
                msg.reply = reply
        return changed


Evented = EventedAgent
