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


class Ask(Message):
    reply: Message = None


class Tell(Message):
    pass


class TimedOut(Exception):
    pass
