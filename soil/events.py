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
    def __post_init__(self):
        assert self.sender is not None, "Tell requires a sender"



class TimedOut(Exception):
    pass
