import os
import yaml
import logging
import importlib
from time import time
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
    start = time()
    function('{}Starting {} at {}.'.format(pre, name, start))
    yield start
    end = time()
    function('{}Finished {} in {} seconds'.format(pre, name, str(end-start)))
    if to_object:
        to_object.start = start
        to_object.end = end


def repr(v):
    func = serializer(v)
    tname = name(v)
    return func(v), tname


def name(v):
    return type(v).__name__


def serializer(type_):
    if type_ == 'bool':
        return lambda x:  "true" if x else ""
    return lambda x: x


def deserializer(type_):
    try:
        # Check if it's a builtin type
        module = importlib.import_module('builtins')
        cls = getattr(module, type_)
    except AttributeError:
        # if not, separate module and class
        module, type_ = type_.rsplit(".", 1)
        module = importlib.import_module(module)
        cls = getattr(module, type_)
    return cls


def convert(value, type_):
    return deserializer(type_)(value)
