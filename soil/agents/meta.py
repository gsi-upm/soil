from abc import ABCMeta
from copy import copy
from functools import wraps
from .. import time

import types
import inspect

def decorate_generator_step(func, name):
    @wraps(func)
    def decorated(self):
        if not self.alive:
            return time.INFINITY

        if self._coroutine is None:
            self._coroutine = func(self)
        try:
            if self._last_except:
                val = self._coroutine.throw(self._last_except)
            else:
                val = self._coroutine.send(self._last_return)
        except StopIteration as ex:
            self._coroutine = None
            val = ex.value
        finally:
            self._last_return = None
            self._last_except = None
        return float(val) if val is not None else val
    return decorated


def decorate_normal_step(func, name):
    @wraps(func)
    def decorated(self):
        # if not self.alive:
        #     return time.INFINITY
        val = func(self)
        return float(val) if val is not None else val
    return decorated


class MetaAgent(ABCMeta):
    def __new__(mcls, name, bases, namespace):
        defaults = {}

        # Re-use defaults from inherited classes
        for i in bases:
            if isinstance(i, MetaAgent):
                defaults.update(i._defaults)

        new_nmspc = {
            "_defaults": defaults,
        }

        for attr, func in namespace.items():
            if attr == "step":
                if inspect.isgeneratorfunction(func) or inspect.iscoroutinefunction(func):
                    func = decorate_generator_step(func, attr)
                    new_nmspc.update({
                        "_last_return": None,
                        "_last_except": None,
                        "_coroutine": None,
                    })
                elif inspect.isasyncgenfunction(func):
                    raise ValueError("Illegal step function: {}. It probably mixes both async/await and yield".format(func))
                elif inspect.isfunction(func):
                    func = decorate_normal_step(func, attr)
                else:
                    raise ValueError("Illegal step function: {}".format(func))
                new_nmspc[attr] = func
            elif (
                isinstance(func, types.FunctionType)
                or isinstance(func, property)
                or isinstance(func, classmethod)
                or attr[0] == "_"
            ):
                new_nmspc[attr] = func
            elif attr == "defaults":
                defaults.update(func)
            elif inspect.isfunction(func):
                new_nmspc[attr] = func
            else:
                defaults[attr] = copy(func)


        # Add attributes for their use in the decorated functions
        return super().__new__(mcls, name, bases, new_nmspc)