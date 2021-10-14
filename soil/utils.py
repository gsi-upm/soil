import logging
import time
import os

from shutil import copyfile

from contextlib import contextmanager

logger = logging.getLogger('soil')
# logging.basicConfig()
# logger.setLevel(logging.INFO)


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
        stamp = time.strftime('%Y-%m-%d_%H.%M.%S', time.localtime(creation))

        backup_dir = os.path.join(outdir, 'backup')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        newpath = os.path.join(backup_dir, '{}@{}'.format(os.path.basename(path),
                                                               stamp))
        copyfile(path, newpath)
    return open(path, mode=mode, **kwargs)


def open_or_reuse(f, *args, **kwargs):
    try:
        return safe_open(f, *args, **kwargs)
    except (AttributeError, TypeError):
        return f

def flatten_dict(d):
    if not isinstance(d, dict):
        return d
    return dict(_flatten_dict(d))

def _flatten_dict(d, prefix=''):
    if not isinstance(d, dict):
        # print('END:', prefix, d)
        yield prefix, d
        return
    if prefix:
        prefix = prefix + '.'
    for k, v in d.items():
        # print(k, v)
        res = list(_flatten_dict(v, prefix='{}{}'.format(prefix, k)))
        # print('RES:', res)
        yield from res


def unflatten_dict(d):
    out = {}
    for k, v in d.items():
        target = out
        if not isinstance(k, str):
            target[k] = v
            continue
        tokens = k.split('.')
        if len(tokens) < 2:
            target[k] = v
            continue
        for token in tokens[:-1]:
            if token not in target:
                target[token] = {}
            target = target[token]
        target[tokens[-1]] = v
    return out
