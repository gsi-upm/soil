import logging
import time
import os

from shutil import copyfile

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


def safe_open(path, mode='r', backup=True, **kwargs):
    outdir = os.path.dirname(path)
    if outdir and not os.path.exists(outdir):
        os.makedirs(outdir)
    if backup and 'w' in mode and os.path.exists(path):
        creation = os.path.getctime(path)
        stamp = time.strftime('%Y-%m-%d_%H:%M', time.localtime(creation))

        backup_dir = os.path.join(outdir, stamp)
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        newpath = os.path.join(backup_dir, os.path.basename(path))
        if os.path.exists(newpath):
            newpath = '{}@{}'.format(newpath, time.time())
        copyfile(path, newpath)
    return open(path, mode=mode, **kwargs)


def open_or_reuse(f, *args, **kwargs):
    try:
        return safe_open(f, *args, **kwargs)
    except (AttributeError, TypeError):
        return f
