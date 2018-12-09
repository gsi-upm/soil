import os
import ast
import yaml
import logging
import importlib
import time
from glob import glob
from random import random
from copy import deepcopy

import networkx as nx

from contextlib import contextmanager


logger = logging.getLogger('soil')
logger.setLevel(logging.INFO)


def load_network(network_params, dir_path=None):
    if network_params is None:
        return nx.Graph()
    path = network_params.get('path', None)
    if path:
        if dir_path and not os.path.isabs(path):
            path = os.path.join(dir_path, path)
        extension = os.path.splitext(path)[1][1:]
        kwargs = {}
        if extension == 'gexf':
            kwargs['version'] = '1.2draft'
            kwargs['node_type'] = int
        try:
            method = getattr(nx.readwrite, 'read_' + extension)
        except AttributeError:
            raise AttributeError('Unknown format')
        return method(path, **kwargs)

    net_args = network_params.copy()
    net_type = net_args.pop('generator')

    method = getattr(nx.generators, net_type)
    return method(**net_args)


def load_file(infile):
    with open(infile, 'r') as f:
        return list(yaml.load_all(f))


def load_files(*patterns):
    for pattern in patterns:
        for i in glob(pattern):
            for config in load_file(i):
                yield config, os.path.abspath(i)


def load_config(config):
    if isinstance(config, dict):
        yield config, None
    else:
        yield from load_files(config)


@contextmanager
def timer(name='task', pre="", function=logger.info, to_object=None):
    start = time.time()
    function('{}Starting {} at {}.'.format(pre, name,
                                           time.strftime("%X", time.gmtime(start))))
    yield start
    end = time.time()
    function('{}Finished {} at {} in {} seconds'.format(pre, name,
                                                        time.strftime("%X", time.gmtime(end)),
                                                        str(end-start)))
    if to_object:
        to_object.start = start
        to_object.end = end


builtins = importlib.import_module('builtins')

def name(value, known_modules=[]):
    '''Return a name that can be imported, to serialize/deserialize an object'''
    if value is None:
        return 'None'
    if not isinstance(value, type):  # Get the class name first
        value = type(value)
    tname = value.__name__
    if hasattr(builtins, tname):
        return tname
    modname = value.__module__
    if modname == '__main__':
        return tname
    if known_modules and modname in known_modules:
        return tname
    for kmod in known_modules:
        if not kmod:
            continue
        module = importlib.import_module(kmod)
        if hasattr(module, tname):
            return tname
    return '{}.{}'.format(modname, tname)


def serializer(type_):
    if type_ != 'str' and hasattr(builtins, type_):
        return repr
    return lambda x: x


def serialize(v, known_modules=[]):
    '''Get a text representation of an object.'''
    tname = name(v, known_modules=known_modules)
    func = serializer(tname)
    return func(v), tname

def deserializer(type_, known_modules=[]):
    if type_ == 'str':
        return lambda x='': x
    if type_ == 'None':
        return lambda x=None: None
    if hasattr(builtins, type_):  # Check if it's a builtin type
        cls = getattr(builtins, type_)
        return lambda x=None: ast.literal_eval(x) if x is not None else cls()
    # Otherwise, see if we can find the module and the class
    modules = known_modules or []
    options = []

    for mod in modules:
        if mod:
            options.append((mod, type_))

    if '.' in type_:  # Fully qualified module
        module, type_ = type_.rsplit(".", 1)
        options.append ((module, type_))

    errors = []
    for modname, tname in options:
        try:
            module = importlib.import_module(modname)
            cls = getattr(module, tname)
            return getattr(cls, 'deserialize', cls)
        except (ImportError, AttributeError) as ex:
            errors.append((modname, tname, ex))
    raise Exception('Could not find type {}. Tried: {}'.format(type_, errors))


def deserialize(type_, value=None, **kwargs):
    '''Get an object from a text representation'''
    if not isinstance(type_, str):
        return type_
    des = deserializer(type_, **kwargs)
    if value is None:
        return des
    return des(value)
