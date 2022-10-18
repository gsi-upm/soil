from __future__ import annotations

import importlib
import sys
import os
import logging
import traceback
from contextlib import contextmanager

from .version import __version__

try:
    basestring
except NameError:
    basestring = str

from .agents import *
from . import agents
from .simulation import *
from .environment import Environment, EventedEnvironment
from . import serialization
from .utils import logger
from .time import *


def main(
    cfg="simulation.yml",
    exporters=None,
    parallel=None,
    output="soil_output",
    *,
    do_run=False,
    debug=False,
    pdb=False,
    **kwargs,
):

    if isinstance(cfg, Simulation):
        sim = cfg
    import argparse
    from . import simulation

    logger.info("Running SOIL version: {}".format(__version__))

    parser = argparse.ArgumentParser(description="Run a SOIL simulation")
    parser.add_argument(
        "file",
        type=str,
        nargs="?",
        default=cfg if sim is None else '',
        help="Configuration file for the simulation (e.g., YAML or JSON)",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show version info and exit"
    )
    parser.add_argument(
        "--module",
        "-m",
        type=str,
        help="file containing the code of any custom agents.",
    )
    parser.add_argument(
        "--dry-run",
        "--dry",
        action="store_true",
        help="Do not store the results of the simulation to disk, show in terminal instead.",
    )
    parser.add_argument(
        "--pdb", action="store_true", help="Use a pdb console in case of exception."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run a customized version of a pdb console to debug a simulation.",
    )
    parser.add_argument(
        "--graph",
        "-g",
        action="store_true",
        help="Dump each trial's network topology as a GEXF graph. Defaults to false.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Dump all data collected in CSV format. Defaults to false.",
    )
    parser.add_argument("--level", type=str, help="Logging level")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=output or "soil_output",
        help="folder to write results to. It defaults to the current directory.",
    )
    if parallel is None:
        parser.add_argument(
            "--synchronous",
            action="store_true",
            help="Run trials serially and synchronously instead of in parallel. Defaults to false.",
        )

    parser.add_argument(
        "-e",
        "--exporter",
        action="append",
        default=[],
        help="Export environment and/or simulations using this exporter",
    )

    parser.add_argument(
        "--only-convert",
        "--convert",
        action="store_true",
        help="Do not run the simulation, only convert the configuration file(s) and output them.",
    )

    parser.add_argument(
        "--set",
        metavar="KEY=VALUE",
        action="append",
        help="Set a number of parameters that will be passed to the simulation."
        "(do not put spaces before or after the = sign). "
        "If a value contains spaces, you should define "
        "it with double quotes: "
        'foo="this is a sentence". Note that '
        "values are always treated as strings.",
    )

    args = parser.parse_args()
    logger.setLevel(getattr(logging, (args.level or "INFO").upper()))

    if args.version:
        return

    if parallel is None:
        parallel = not args.synchronous

    exporters = exporters or [
        "default",
    ]
    for exp in args.exporter:
        if exp not in exporters:
            exporters.append(exp)
    if args.csv:
        exporters.append("csv")
    if args.graph:
        exporters.append("gexf")

    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    if args.module:
        importlib.import_module(args.module)
    if output is None:
        output = args.output



    debug = debug or args.debug

    if args.pdb or debug:
        args.synchronous = True
        os.environ["SOIL_POSTMORTEM"] = "true"

    res = []
    try:
        exp_params = {}

        if sim:
            logger.info("Loading simulation instance")
            sims = [sim, ]
        else:
            logger.info("Loading config file: {}".format(args.file))
            if not os.path.exists(args.file):
                logger.error("Please, input a valid file")
                return

            sims = list(simulation.iter_from_config(
                args.file,
                dry_run=args.dry_run,
                exporters=exporters,
                parallel=parallel,
                outdir=output,
                exporter_params=exp_params,
                **kwargs,
            ))

        for sim in sims:

            if args.set:
                for s in args.set:
                    k, v = s.split("=", 1)[:2]
                    v = eval(v)
                    tail, *head = k.rsplit(".", 1)[::-1]
                    target = sim
                    if head:
                        for part in head[0].split("."):
                            try:
                                target = getattr(target, part)
                            except AttributeError:
                                target = target[part]
                    try:
                        setattr(target, tail, v)
                    except AttributeError:
                        target[tail] = v

            if args.only_convert:
                print(sim.to_yaml())
                continue
            if do_run:
                res.append(sim.run())
            else:
                print("not running")
                res.append(sim)

    except Exception as ex:
        if args.pdb:
            from .debugging import post_mortem

            print(traceback.format_exc())
            post_mortem()
        else:
            raise
    if debug:
        from .debugging import set_trace

        os.environ["SOIL_DEBUG"] = "true"
        set_trace()
    return res


@contextmanager
def easy(cfg, pdb=False, debug=False, **kwargs):
    try:
        yield main(cfg, **kwargs)[0]
    except Exception as e:
        if os.environ.get("SOIL_POSTMORTEM"):
            from .debugging import post_mortem

            print(traceback.format_exc())
            post_mortem()
        raise


if __name__ == "__main__":
    main(do_run=True)
