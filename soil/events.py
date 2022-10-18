from .time import Cond
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

class Event:
    pass

@dataclass
class Message:
    payload: Any
    sender: Any = None
    expiration: float = None
    id: int = field(default_factory=uuid4)

    def expired(self, when):
        return self.expiration is not None and self.expiration < when

class Reply(Message):
    source: Message


class Ask(Message):
    reply: Message = None

    def replied(self, expiration=None):
        def ready(agent):
            return self.reply is not None or agent.now > expiration

        def value(agent):
            if agent.now > expiration:
                raise TimedOut(f'No answer received for {self}')
            return self.reply

        return Cond(func=ready, return_func=value)


class Tell(Message):
    pass


class TimedOut(Exception):
    pass
