import os
import logging
import ast
import sys
import importlib
from glob import glob
from itertools import product, chain

import yaml
import networkx as nx

from jinja2 import Template


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
    if 'generator' not in net_args:
        return nx.Graph()

    net_gen = net_args.pop('generator')

    if dir_path not in sys.path:
        sys.path.append(dir_path)

    method = deserializer(net_gen,
                          known_modules=['networkx.generators',])

    return method(**net_args)


def load_file(infile):
    with open(infile, 'r') as f:
        return list(chain.from_iterable(map(expand_template, load_string(f))))


def load_string(string):
    yield from yaml.load_all(string, Loader=yaml.FullLoader)


def expand_template(config):
    if 'template' not in config:
        yield config
        return
    if 'vars' not in config:
        raise ValueError(('You must provide a definition of variables'
                          ' for the template.'))

    template = Template(config['template'])

    sampler_name = config.get('sampler', 'SALib.sample.morris.sample')
    n_samples = int(config.get('samples', 100))
    sampler = deserializer(sampler_name)
    bounds = config['vars']['bounds']

    problem = {
        'num_vars': len(bounds),
        'names': list(bounds.keys()),
        'bounds': list(v for v in bounds.values())
    }
    samples = sampler(problem, n_samples)

    lists = config['vars'].get('lists', {})
    names = list(lists.keys())
    values = list(lists.values())
    combs = list(product(*values))

    allnames = names + problem['names']
    allvalues = [(list(i[0])+list(i[1])) for i in product(combs, samples)]
    params = list(map(lambda x: dict(zip(allnames, x)), allvalues))


    blank_str = template.render({k: 0 for k in allnames})
    blank = list(load_string(blank_str))
    if len(blank) > 1:
        raise ValueError('Templates must not return more than one configuration')
    if 'name' in blank[0]:
        raise ValueError('Templates cannot be named, use group instead')

    confs = []
    for ps in params:
        string = template.render(ps)
        for c in load_string(string):
            yield c


def load_files(*patterns, **kwargs):
    for pattern in patterns:
        for i in glob(pattern, **kwargs):
            for config in load_file(i):
                path = os.path.abspath(i)
                if 'dir_path' not in config:
                    config['dir_path'] = os.path.dirname(path)
                yield config, path


def load_config(config):
    if isinstance(config, dict):
        yield config, None
    else:
        yield from load_files(config)


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
    if type(type_) != str:  # Already deserialized
        return type_
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
