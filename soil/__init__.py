import importlib
import sys
import os

__version__ = "0.9.3"

try:
    basestring
except NameError:
    basestring = str

from . import agents
from . import simulation
from . import environment
from . import utils
from . import settings


def main():
    import argparse
    from . import simulation

    parser = argparse.ArgumentParser(description='Run a SOIL simulation')
    parser.add_argument('file', type=str,
                        nargs="?",
                        default='simulation.yml',
                        help='python module containing the simulation configuration.')
    parser.add_argument('--module', '-m', type=str,
                        help='file containing the code of any custom agents.')

    args = parser.parse_args()

    if args.module:
        sys.path.append(os.getcwd())
        importlib.import_module(args.module)

    print('Loading config file: {}'.format(args.file))
    simulation.run_from_config(args.file)


if __name__ == '__main__':
    main()
