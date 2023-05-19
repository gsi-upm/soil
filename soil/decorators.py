from functools import wraps
from .time import INFINITY

def report(f: property):
    if isinstance(f, property):
        setattr(f.fget, "add_to_report", True)
    else:
        setattr(f, "add_to_report", True)
    return f


def syncify(func, method=True):
    _coroutine = None

    @wraps(func)
    def wrapped(*args, **kwargs):
        if not method:
            nonlocal _coroutine
        else:
            _coroutine = getattr(args[0], "_coroutine", None)
        _coroutine = _coroutine or func(*args, **kwargs)
        try:
            val = _coroutine.send(None)
        except StopIteration as ex:
            _coroutine = None
            val = ex.value
        finally:
            if method:
                args[0]._coroutine = _coroutine
        return val

    return wrapped


def while_alive(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if self.alive:
            return func(self, *args, **kwargs)
        return INFINITY

    return wrapped