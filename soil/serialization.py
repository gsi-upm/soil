import os
import logging
import ast
import sys
import re
import importlib
import importlib.machinery, importlib.util
from glob import glob
from itertools import product, chain

from contextlib import contextmanager

import yaml
import networkx as nx

from . import config

from jinja2 import Template


logger = logging.getLogger("soil")


def load_file(infile):
    folder = os.path.dirname(infile)
    if folder not in sys.path:
        sys.path.append(folder)
    with open(infile, "r") as f:
        return list(chain.from_iterable(map(expand_template, load_string(f))))


def load_string(string):
    yield from yaml.load_all(string, Loader=yaml.FullLoader)


def expand_template(config):
    if "template" not in config:
        yield config
        return
    if "vars" not in config:
        raise ValueError(
            ("You must provide a definition of variables" " for the template.")
        )

    template = config["template"]

    if not isinstance(template, str):
        template = yaml.dump(template)

    template = Template(template)

    params = params_for_template(config)

    blank_str = template.render({k: 0 for k in params[0].keys()})
    blank = list(load_string(blank_str))
    if len(blank) > 1:
        raise ValueError("Templates must not return more than one configuration")
    if "name" in blank[0]:
        raise ValueError("Templates cannot be named, use group instead")

    for ps in params:
        string = template.render(ps)
        for c in load_string(string):
            yield c


def params_for_template(config):
    sampler_config = config.get("sampler", {"N": 100})
    sampler = sampler_config.pop("method", "SALib.sample.morris.sample")
    sampler = deserializer(sampler)
    bounds = config["vars"]["bounds"]

    problem = {
        "num_vars": len(bounds),
        "names": list(bounds.keys()),
        "bounds": list(v for v in bounds.values()),
    }
    samples = sampler(problem, **sampler_config)

    lists = config["vars"].get("lists", {})
    names = list(lists.keys())
    values = list(lists.values())
    combs = list(product(*values))

    allnames = names + problem["names"]
    allvalues = [(list(i[0]) + list(i[1])) for i in product(combs, samples)]
    params = list(map(lambda x: dict(zip(allnames, x)), allvalues))
    return params


def load_files(*patterns, **kwargs):
    for pattern in patterns:
        for i in glob(pattern, **kwargs, recursive=True):
            for cfg in load_file(i):
                path = os.path.abspath(i)
                yield cfg, path


def load_config(cfg):
    if isinstance(cfg, dict):
        yield config.load_config(cfg), os.getcwd()
    else:
        yield from load_files(cfg)


_BUILTINS = None

def builtins():
    global _BUILTINS
    if not _BUILTINS:
        _BUILTINS = importlib.import_module("builtins")
    return _BUILTINS

KNOWN_MODULES = {
    'soil': None,

}

MODULE_FILES = {}

def _add_source_file(file):
    """Add a file to the list of known modules"""
    file = os.path.abspath(file)
    if file in MODULE_FILES:
        logger.warning(f"File {file} already added as module {MODULE_FILES[file]}. Reloading")
        _remove_source_file(file)
    modname = f"imported_module_{len(MODULE_FILES)}"
    loader = importlib.machinery.SourceFileLoader(modname, file)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    my_module = importlib.util.module_from_spec(spec)
    loader.exec_module(my_module)
    MODULE_FILES[file] = modname
    KNOWN_MODULES[modname] = my_module

def _remove_source_file(file):
    """Remove a file from the list of known modules"""
    file = os.path.abspath(file)
    modname = None
    try:
        modname = MODULE_FILES.pop(file)
        KNOWN_MODULES.pop(modname)
    except KeyError as ex:
        raise ValueError(f"File {file} had not been added as a module: {ex}")


@contextmanager
def with_source(file=None):
    """Add a file to the list of known modules, and remove it afterwards"""
    if file:
        _add_source_file(file)
    try:
        yield
    finally:
        if file:
            _remove_source_file(file)

def get_module(modname):
    """Get a module from the list of known modules"""
    if modname not in KNOWN_MODULES or KNOWN_MODULES[modname] is None:
        module = importlib.import_module(modname)
        KNOWN_MODULES[modname] = module
    return KNOWN_MODULES[modname]


def name(value, known_modules=KNOWN_MODULES):
    """Return a name that can be imported, to serialize/deserialize an object"""
    if value is None:
        return "None"
    if not isinstance(value, type):  # Get the class name first
        value = type(value)
    tname = value.__name__
    if hasattr(builtins(), tname):
        return tname
    modname = value.__module__
    if modname == "__main__":
        return tname
    if known_modules and modname in known_modules:
        return tname
    for kmod in known_modules:
        module = get_module(kmod)
        if hasattr(module, tname):
            return tname
    return "{}.{}".format(modname, tname)


def serializer(type_):
    if type_ != "str":
        return repr
    return lambda x: x


def serialize(v, known_modules=KNOWN_MODULES):
    """Get a text representation of an object."""
    tname = name(v, known_modules=known_modules)
    func = serializer(tname)
    return func(v), tname


def serialize_dict(d, known_modules=KNOWN_MODULES):
    try:
        d = dict(d)
    except (ValueError, TypeError) as ex:
        return serialize(d)[0]
    for (k, v) in reversed(list(d.items())):
        if isinstance(v, dict):
            d[k] = serialize_dict(v, known_modules=known_modules)
        elif isinstance(v, list):
            for ix in range(len(v)):
                v[ix] = serialize_dict(v[ix], known_modules=known_modules)
        elif isinstance(v, type):
            d[k] = serialize(v, known_modules=known_modules)[1]
    return d


IS_CLASS = re.compile(r"<class '(.*)'>")


def deserializer(type_, known_modules=KNOWN_MODULES):
    if type(type_) != str:  # Already deserialized
        return type_
    if type_ == "str":
        return lambda x="": x
    if type_ == "None":
        return lambda x=None: None
    if hasattr(builtins(), type_):  # Check if it's a builtin type
        cls = getattr(builtins(), type_)
        return lambda x=None: ast.literal_eval(x) if x is not None else cls()
    match = IS_CLASS.match(type_)
    if match:
        modname, tname = match.group(1).rsplit(".", 1)
        module = get_module(modname)
        cls = getattr(module, tname)
        return getattr(cls, "deserialize", cls)

    # Otherwise, see if we can find the module and the class
    options = []

    for mod in known_modules:
        if mod:
            options.append((mod, type_))

    if "." in type_:  # Fully qualified module
        module, type_ = type_.rsplit(".", 1)
        options.append((module, type_))

    errors = []
    for modname, tname in options:
        try:
            module = get_module(modname)
            cls = getattr(module, tname)
            return getattr(cls, "deserialize", cls)
        except (ImportError, AttributeError) as ex:
            errors.append((modname, tname, ex))
    raise ValueError('Could not find type "{}". Tried: {}'.format(type_, errors))


def deserialize(type_, value=None, globs=None, **kwargs):
    """Get an object from a text representation"""
    if not isinstance(type_, str):
        return type_
    if globs and type_ in globs:
        des = globs[type_]
    else:
        try:
            des = deserializer(type_, **kwargs)
        except ValueError as ex:
            try:
                des = eval(type_)
            except Exception:
                raise ex
    if value is None:
        return des
    return des(value)


def deserialize_all(names, *args, known_modules=KNOWN_MODULES, **kwargs):
    """Return the list of deserialized objects"""
    objects = []
    for name in names:
        mod = deserialize(name, known_modules=known_modules)
        objects.append(mod(*args, **kwargs))
    return objects
