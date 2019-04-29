import logging
import time
import os

from contextlib import contextmanager

logger = logging.getLogger('soil')
logger.setLevel(logging.INFO)


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


def safe_open(path, *args, **kwargs):
    outdir = os.path.dirname(path)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)
    return open(path, *args, **kwargs)


def open_or_reuse(f, *args, **kwargs):
    try:
        return safe_open(f, *args, **kwargs)
    except TypeError:
        return f
