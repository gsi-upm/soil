from __future__ import annotations

import importlib
from importlib.resources import path
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

from pathlib import Path
from .agents import *
from . import agents
from .simulation import *
from .environment import Environment, EventedEnvironment
from .datacollection import SoilCollector
from . import serialization
from .utils import logger
from .time import *
from .decorators import *


def main(
    cfg="simulation.yml",
    exporters=None,
    num_processes=1,
    output="soil_output",
    *,
    debug=False,
    pdb=False,
    **kwargs,
):

    sim = None
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
        default=cfg if sim is None else "",
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
        help="Do not run the simulation",
    )
    parser.add_argument(
        "--no-dump",
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
        help="Dump each iteration's network topology as a GEXF graph. Defaults to false.",
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
    parser.add_argument(
        "--num-processes",
        default=num_processes,
        help="Number of processes to use for parallel execution. Defaults to 1.",
    )

    parser.add_argument(
        "-e",
        "--exporter",
        action="append",
        default=[],
        help="Export environment and/or simulations using this exporter",
    )
    parser.add_argument(
        "--max_time",
        default="-1",
        help="Set maximum time for the simulation to run. ",
    )

    parser.add_argument(
        "--max_steps",
        default="-1",
        help="Set maximum number of steps for the simulation to run.",
    )

    parser.add_argument(
        "--iterations",
        default="",
        help="Set maximum number of iterations (runs) for the simulation.",
    )

    parser.add_argument(
        "--seed",
        default=None,
        help="Manually set a seed for the simulation.",
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
    level = getattr(logging, (args.level or "INFO").upper())
    logger.setLevel(level)

    if args.version:
        return

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
        opts = dict(
                    dry_run=args.dry_run,
                    dump=not args.no_dump,
                    debug=debug,
                    exporters=exporters,
                    num_processes=args.num_processes,
                    level=level,
                    outdir=output,
                    exporter_params=exp_params,
                    **kwargs)
        if args.seed is not None:
            opts["seed"] = args.seed
        if args.iterations:
            opts["iterations"] =int(args.iterations)

        if sim:
            logger.info("Loading simulation instance")
            for (k, v) in opts.items():
                setattr(sim, k, v)
            sims = [sim]
        else:
            logger.info("Loading config file: {}".format(args.file))
            if not os.path.exists(args.file):
                logger.error("Please, input a valid file")
                return

            assert opts["debug"] == debug
            sims = list(
                simulation.iter_from_file(
                    args.file,
                    **opts,
                )
            )

        for sim in sims:
            assert sim.debug == debug

            if args.set:
                for s in args.set:
                    k, v = s.split("=", 1)[:2]
                    v = eval(v)
                    tail, *head = k.rsplit(".", 1)[::-1]
                    target = sim.parameters
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
            max_time = float(args.max_time) if args.max_time != "-1" else None
            max_steps = float(args.max_steps) if args.max_steps != "-1" else None
            res.append(sim.run(max_time=max_time, max_steps=max_steps))

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
        return main(cfg, debug=debug, pdb=pdb, **kwargs)[0]
    except Exception as e:
        if os.environ.get("SOIL_POSTMORTEM"):
            from .debugging import post_mortem

            print(traceback.format_exc())
            post_mortem()
        raise


if __name__ == "__main__":
    main()
