from abc import ABCMeta
from copy import copy
from functools import wraps
from .. import time
from ..decorators import syncify, while_alive

import types
import inspect


class MetaAnnotations(ABCMeta):
    """This metaclass sets default values for agents based on class attributes"""
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
            if (
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

        return super().__new__(mcls, name, bases, new_nmspc)


class AutoAgent(ABCMeta):
    def __new__(mcls, name, bases, namespace):
        if "step" in namespace:
            func = namespace["step"]
            namespace["_orig_step"] = func
            if inspect.isfunction(func):
                if inspect.isgeneratorfunction(func) or inspect.iscoroutinefunction(func):
                    func = syncify(func, method=True)
                namespace["step"] = while_alive(func)
            elif inspect.isasyncgenfunction(func):
                raise ValueError("Illegal step function: {}. It probably mixes both async/await and yield".format(func))
            else:
                raise ValueError("Illegal step function: {}".format(func))

        # Add attributes for their use in the decorated functions
        return super().__new__(mcls, name, bases, namespace)


class MetaAgent(AutoAgent, MetaAnnotations):
    """This metaclass sets default values for agents based on class attributes"""
    pass

