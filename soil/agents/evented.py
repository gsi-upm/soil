from . import BaseAgent
from ..events import Message, Tell, Ask, TimedOut
from functools import partial
from collections import deque
from types import coroutine


class EventedAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inbox = deque()
        self._processed = 0

    def on_receive(self, *args, **kwargs):
        pass

    @coroutine
    def received(self, expiration=None, timeout=60, delay=1, process=True):
        if not expiration:
            expiration = self.now + timeout
        while self.now < expiration:
            if self._inbox:
                msgs = self._inbox
                if process:
                    self.process_messages()
                return msgs
            yield self.delay(delay)
        raise TimedOut("No message received")

    def tell(self, msg, sender=None):
        self._inbox.append(Tell(timestamp=self.now, payload=msg, sender=sender))

    @coroutine
    def ask(self, msg, expiration=None, timeout=None, delay=1):
        ask = Ask(timestamp=self.now, payload=msg, sender=self)
        self._inbox.append(ask)
        expiration = float("inf") if timeout is None else self.now + timeout
        while self.now < expiration:
            if ask.reply:
                return ask.reply
            yield self.delay(delay)
        raise TimedOut("No reply received")

    def process_messages(self):
        valid = list()
        for msg in self._inbox:
            self._processed += 1
            if msg.expired(self.now):
                continue
            valid.append(msg)
            reply = self.on_receive(msg.payload, sender=msg.sender)
            if isinstance(msg, Ask):
                msg.reply = reply
        self._inbox.clear()
        return valid


Evented = EventedAgent
