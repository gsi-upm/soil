import importlib
import sys
import os
import pdb
import logging

from .version import __version__

try:
    basestring
except NameError:
    basestring = str

from . import agents
from .simulation import *
from .environment import Environment
from .history import History
from . import serialization
from . import analysis

def main():
    import argparse
    from . import simulation

    logging.basicConfig(level=logging.INFO)
    logging.info('Running SOIL version: {}'.format(__version__))

    parser = argparse.ArgumentParser(description='Run a SOIL simulation')
    parser.add_argument('file', type=str,
                        nargs="?",
                        default='simulation.yml',
                        help='python module containing the simulation configuration.')
    parser.add_argument('--module', '-m', type=str,
                        help='file containing the code of any custom agents.')
    parser.add_argument('--dry-run', '--dry', action='store_true',
                        help='Do not store the results of the simulation.')
    parser.add_argument('--pdb', action='store_true',
                        help='Use a pdb console in case of exception.')
    parser.add_argument('--graph', '-g', action='store_true',
                        help='Dump GEXF graph. Defaults to false.')
    parser.add_argument('--csv', action='store_true',
                        help='Dump history in CSV format. Defaults to false.')
    parser.add_argument('--output', '-o', type=str, default="soil_output",
                        help='folder to write results to. It defaults to the current directory.')
    parser.add_argument('--synchronous', action='store_true',
                        help='Run trials serially and synchronously instead of in parallel. Defaults to false.')
    parser.add_argument('-e', '--exporter', action='append',
                        help='Export environment and/or simulations using this exporter')

    args = parser.parse_args()

    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    if args.module:
        importlib.import_module(args.module)

    logging.info('Loading config file: {}'.format(args.file))

    try:
        exporters = list(args.exporter or ['default', ])
        if args.csv:
            exporters.append('csv')
        if args.graph:
            exporters.append('gexf')
        exp_params = {}
        if args.dry_run:
            exp_params['copy_to'] = sys.stdout
        simulation.run_from_config(args.file,
                                   dry_run=args.dry_run,
                                   exporters=exporters,
                                   parallel=(not args.synchronous),
                                   outdir=args.output,
                                   exporter_params=exp_params)
    except Exception:
        if args.pdb:
            pdb.post_mortem()
        else:
            raise


if __name__ == '__main__':
    main()
