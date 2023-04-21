from .time import BaseCond
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
    timestamp: float = None
    id: int = field(default_factory=uuid4)

    def expired(self, when):
        return self.expiration is not None and self.expiration < when


class Reply(Message):
    source: Message


class ReplyCond(BaseCond):
    def __init__(self, ask, *args, **kwargs):
        self._ask = ask
        super().__init__(*args, **kwargs)

    def ready(self, agent, time):
        return self._ask.reply is not None or self._ask.expired(time)

    def return_value(self, agent):
        if self._ask.expired(agent.now):
            raise TimedOut()
        return self._ask.reply

    def __repr__(self):
        return f"ReplyCond({self._ask.id})"


class Ask(Message):
    reply: Message = None

    def replied(self, expiration=None):
        return ReplyCond(self)


class Tell(Message):
    pass


class TimedOut(Exception):
    pass
