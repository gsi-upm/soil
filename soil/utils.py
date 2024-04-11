import logging
from time import time as current_time, strftime, gmtime, localtime
import os
import traceback

from functools import partial
from shutil import copyfile, move
from multiprocessing import Pool, cpu_count

from contextlib import contextmanager

logger = logging.getLogger("soil")
logger.setLevel(logging.WARNING)

timeformat = "%H:%M:%S"

if os.environ.get("SOIL_VERBOSE", ""):
    logformat = "[%(levelname)-5.5s][%(asctime)s][%(name)s]:  %(message)s"
else:
    logformat = "[%(levelname)-5.5s][%(asctime)s] %(message)s"

logFormatter = logging.Formatter(logformat, timeformat)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)

logging.basicConfig(
    level=logging.WARNING,
    handlers=[
        consoleHandler,
    ],
)


@contextmanager
def timer(name="task", pre="", function=logger.info, to_object=None):
    start = current_time()
    function("{}Starting {} at {}.".format(pre, name, strftime("%X", gmtime(start))))
    yield start
    end = current_time()
    function(
        "{}Finished {} at {} in {} seconds".format(
            pre, name, strftime("%X", gmtime(end)), str(end - start)
        )
    )
    if to_object:
        to_object.start = start
        to_object.end = end


def try_backup(path, remove=False):
    if not os.path.exists(path):
        return None
    outdir = os.path.dirname(path)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)
    creation = os.path.getctime(path)
    stamp = strftime("%Y-%m-%d_%H.%M.%S", localtime(creation))

    backup_dir = os.path.join(outdir, "backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    newpath = os.path.join(backup_dir, "{}@{}".format(os.path.basename(path), stamp))
    if remove:
        move(path, newpath)
    else:
        copyfile(path, newpath)
    return newpath


def safe_open(path, mode="r", backup=True, **kwargs):
    outdir = os.path.dirname(path)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)
    if backup and "w" in mode:
        try_backup(path)
    return open(path, mode=mode, **kwargs)


@contextmanager
def open_or_reuse(f, *args, **kwargs):
    try:
        with safe_open(f, *args, **kwargs) as f:
            yield f
    except (AttributeError, TypeError) as ex:
        yield f


def flatten_dict(d):
    if not isinstance(d, dict):
        return d
    return dict(_flatten_dict(d))


def _flatten_dict(d, prefix=""):
    if not isinstance(d, dict):
        # print('END:', prefix, d)
        yield prefix, d
        return
    if prefix:
        prefix = prefix + "."
    for k, v in d.items():
        # print(k, v)
        res = list(_flatten_dict(v, prefix="{}{}".format(prefix, k)))
        # print('RES:', res)
        yield from res


def unflatten_dict(d):
    out = {}
    for k, v in d.items():
        target = out
        if not isinstance(k, str):
            target[k] = v
            continue
        tokens = k.split(".")
        if len(tokens) < 2:
            target[k] = v
            continue
        for token in tokens[:-1]:
            if token not in target:
                target[token] = {}
            target = target[token]
        target[tokens[-1]] = v
    return out


def run_and_return_exceptions(func, *args, **kwargs):
    """
    A wrapper for a function that catches exceptions and returns them.
    It is meant for async simulations.
    """
    try:
        return func(*args, **kwargs)
    except Exception as ex:
        if ex.__cause__ is not None:
            ex = ex.__cause__
        ex.message = "".join(
            traceback.format_exception(type(ex), ex, ex.__traceback__)[:]
        )
        return ex


def run_parallel(func, iterable, num_processes=1, **kwargs):
    if num_processes > 1 and not os.environ.get("SOIL_DEBUG", None):
        if num_processes < 1:
            num_processes = cpu_count() - num_processes
        p = Pool(processes=num_processes)
        wrapped_func = partial(run_and_return_exceptions, func, **kwargs)
        for i in p.imap_unordered(wrapped_func, iterable):
            if isinstance(i, Exception):
                logger.error("Trial failed:\n\t%s", i.message)
                continue
            yield i
    else:
        for i in iterable:
            yield func(i, **kwargs)


def int_seed(seed: str):
    return int.from_bytes(seed.encode(), "little")