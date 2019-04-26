import logging
import time

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
