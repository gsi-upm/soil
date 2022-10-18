from . import BaseAgent
from ..events import Message, Tell, Ask, Reply, TimedOut
from ..time import Cond
from functools import partial
from collections import deque


class Evented(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._inbox = deque()
        self._received = 0
        self._processed = 0


    def on_receive(self, *args, **kwargs):
        pass

    def received(self, expiration=None, timeout=None):
        current = self._received
        if expiration is None:
            expiration = float('inf') if timeout is None else self.now + timeout

        if expiration < self.now:
            raise ValueError("Invalid expiration time")

        def ready(agent):
            return agent._received > current or agent.now >= expiration

        def value(agent):
            if agent.now > expiration:
                raise TimedOut("No message received")

        c = Cond(func=ready, return_func=value)
        c._checked = True
        return c

    def tell(self, msg, sender):
        self._received += 1
        self._inbox.append(Tell(payload=msg, sender=sender))

    def ask(self, msg, timeout=None):
        self._received += 1
        ask = Ask(payload=msg)
        self._inbox.append(ask)
        expiration = float('inf') if timeout is None else self.now + timeout
        return ask.replied(expiration=expiration)

    def check_messages(self):
        while self._inbox:
            msg = self._inbox.popleft()
            self._processed += 1
            if msg.expired(self.now):
                continue
            reply = self.on_receive(msg.payload, sender=msg.sender)
            if isinstance(msg, Ask):
                msg.reply = reply
