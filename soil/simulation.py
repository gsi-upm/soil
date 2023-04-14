import os
from time import time as current_time, strftime
import importlib
import sys
import yaml
import traceback
import inspect
import logging
import networkx as nx

from textwrap import dedent

from dataclasses import dataclass, field, asdict, replace
from typing import Any, Dict, Union, Optional, List


from networkx.readwrite import json_graph
from functools import partial
from contextlib import contextmanager
import pickle

from . import serialization, exporters, utils, basestring, agents
from .environment import Environment
from .utils import logger, run_and_return_exceptions
from .debugging import set_trace

_AVOID_RUNNING = False
_QUEUED = []

@contextmanager
def do_not_run(): 
    global _AVOID_RUNNING
    _AVOID_RUNNING = True
    try:
        logger.debug("NOT RUNNING")
        yield
    finally:
        logger.debug("RUNNING AGAIN")
        _AVOID_RUNNING = False


def _iter_queued():
    while _QUEUED:
        (cls, args, kwargs) = _QUEUED.pop(0)
        yield replace(cls, **kwargs)


# TODO: change documentation for simulation
@dataclass
class Simulation:
    """
    A simulation is a collection of agents and a model. It is responsible for running the model and agents, and collecting data from them.

    Args:
        version: The version of the simulation. This is used to determine how to load the simulation.
        name: The name of the simulation.
        description: A description of the simulation.
        group: The group that the simulation belongs to.
        model: The model to use for the simulation. This can be a string or a class.
        model_params: The parameters to pass to the model.
        seed: The seed to use for the simulation.
        dir_path: The directory path to use for the simulation.
        max_time: The maximum time to run the simulation.
        max_steps: The maximum number of steps to run the simulation.
        interval: The interval to use for the simulation.
        num_trials: The number of trials (times) to run the simulation.
        num_processes: The number of processes to use for the simulation. If greater than one, simulations will be performed in parallel. This may make debugging and error handling difficult.
        tables: The tables to use in the simulation datacollector
        agent_reporters: The agent reporters to use in the datacollector
        model_reporters: The model reporters to use in the datacollector
        dry_run: Whether or not to run the simulation. If True, the simulation will not be run.
        source_file: Python file to use to find additional classes.
    """

    version: str = "2"
    source_file: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = ""
    group: str = None
    model: Union[str, type] = "soil.Environment"
    model_params: dict = field(default_factory=dict)
    seed: str = field(default_factory=lambda: current_time())
    dir_path: str = field(default_factory=lambda: os.getcwd())
    max_time: float = float("inf")
    max_steps: int = -1
    interval: int = 1
    num_trials: int = 1
    num_processes: Optional[int] = 1
    exporters: Optional[List[str]] = field(default_factory=lambda: [exporters.default])
    model_reporters: Optional[Dict[str, Any]] = field(default_factory=dict)
    agent_reporters: Optional[Dict[str, Any]] = field(default_factory=dict)
    tables: Optional[Dict[str, Any]] = field(default_factory=dict)
    outdir: Optional[str] = None
    exporter_params: Optional[Dict[str, Any]] = field(default_factory=dict)
    dry_run: bool = False
    dump: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
    skip_test: Optional[bool] = False
    debug: Optional[bool] = False

    def __post_init__(self):
        if self.name is None:
            if isinstance(self.model, str):
                self.name = self.model
            else:
                self.name = self.model.__class__.__name__

    def run_simulation(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        """Run the simulation and return the list of resulting environments"""
        logger.info(
            dedent(
                """
        Simulation:
        ---
        """
            )
            + self.to_yaml()
        )
        if _AVOID_RUNNING:
            _QUEUED.append((self, args, kwargs))
            return []
        return list(self._run_gen(*args, **kwargs))

    def _run_gen(
        self,
        num_processes=1,
        dry_run=None,
        dump=None,
        exporters=None,
        outdir=None,
        exporter_params={},
        log_level=None,
        **kwargs,
    ):
        """Run the simulation and yield the resulting environments."""
        if log_level:
            logger.setLevel(log_level)
        outdir = outdir or self.outdir
        logger.info("Using exporters: %s", exporters or [])
        logger.info("Output directory: %s", outdir)
        if dry_run is None:
            dry_run = self.dry_run
        if dump is None:
            dump = self.dump
        if exporters is None:
            exporters = self.exporters
        if not exporter_params:
            exporter_params = self.exporter_params

        exporters = serialization.deserialize_all(
            exporters,
            simulation=self,
            known_modules=[
                "soil.exporters",
            ],
            dump=dump and not dry_run,
            outdir=outdir,
            **exporter_params,
        )

        if self.source_file:
            source_file = self.source_file
            if not os.path.isabs(source_file):
                source_file = os.path.abspath(os.path.join(self.dir_path, source_file))
            serialization.add_source_file(source_file)
        try:

            with utils.timer("simulation {}".format(self.name)):
                for exporter in exporters:
                    exporter.sim_start()

                    if dry_run:
                        def func(*args, **kwargs):
                            return None
                    else:
                        func = self.run_trial

                for env in utils.run_parallel(
                    func=self.run_trial,
                    iterable=range(int(self.num_trials)),
                    num_processes=num_processes,
                    log_level=log_level,
                    **kwargs,
                ):
                    if env is None and dry_run:
                        continue

                    for exporter in exporters:
                        exporter.trial_end(env)

                    yield env

                for exporter in exporters:
                    exporter.sim_end()
        finally:
            pass
            # TODO: reintroduce
            # if self.source_file:
            #     serialization.remove_source_file(self.source_file)

    def get_env(self, trial_id=0, model_params=None, **kwargs):
        """Create an environment for a trial of the simulation"""

        def deserialize_reporters(reporters):
            for (k, v) in reporters.items():
                if isinstance(v, str) and v.startswith("py:"):
                    reporters[k] = serialization.deserialize(v.split(":", 1)[1])
            return reporters

        params = self.model_params.copy()
        if model_params:
            params.update(model_params)
        params.update(kwargs)

        agent_reporters = self.agent_reporters.copy()
        agent_reporters.update(deserialize_reporters(params.pop("agent_reporters", {})))
        model_reporters = self.model_reporters.copy()
        model_reporters.update(deserialize_reporters(params.pop("model_reporters", {})))
        tables = self.tables.copy()
        tables.update(deserialize_reporters(params.pop("tables", {})))

        env = serialization.deserialize(self.model)
        return env(
            id=f"{self.name}_trial_{trial_id}",
            seed=f"{self.seed}_trial_{trial_id}",
            dir_path=self.dir_path,
            interval=self.interval,
            agent_reporters=agent_reporters,
            model_reporters=model_reporters,
            tables=tables,
            **params,
        )

    def run_trial(
        self, trial_id=None, until=None, log_file=False, log_level=logging.INFO, **opts
    ):
        """
        Run a single trial of the simulation

        """
        if log_level:
            logger.setLevel(log_level)
        model = self.get_env(trial_id, **opts)
        trial_id = trial_id if trial_id is not None else current_time()
        with utils.timer("Simulation {} trial {}".format(self.name, trial_id)):
            return self.run_model(
                model=model, trial_id=trial_id, until=until, log_level=log_level
            )

    def run_model(self, model, until=None, **opts):
        # Set-up trial environment and graph
        until = float(until or self.max_time or "inf")

        # Set up agents on nodes
        def is_done():
            return not model.running

        if until and hasattr(model.schedule, "time"):
            prev = is_done

            def is_done():
                return prev() or model.schedule.time >= until
            
        if not model.schedule.agents:
            raise Exception("No agents in model. This is probably a bug. Make sure that the model has agents scheduled after its initialization.")

        if self.max_steps and self.max_steps > 0 and hasattr(model.schedule, "steps"):
            prev_steps = is_done

            def is_done():
                return prev_steps() or model.schedule.steps >= self.max_steps

        newline = "\n"
        logger.info(
            dedent(
                f"""
Model stats:
  Agent count: { model.schedule.get_agent_count() }):
  Topology size: { len(model.G) if hasattr(model, "G") else 0 }
        """
            )
        )

        if self.debug:
            set_trace()

        while not is_done():
            utils.logger.debug(
                f'Simulation time {model.schedule.time}/{until}.'
            )
            model.step()

        return model

    def to_dict(self):
        d = asdict(self)
        return serialization.serialize_dict(d)

    def to_yaml(self):
        return yaml.dump(self.to_dict())


def iter_from_file(*files, **kwargs):
    for f in files:
        try:
            yield from iter_from_py(f, **kwargs)
        except ValueError as ex:
            yield from iter_from_config(f, **kwargs)


def from_file(*args, **kwargs):
    return list(iter_from_file(*args, **kwargs))


def iter_from_config(*cfgs, **kwargs):
    for config in cfgs:
        configs = list(serialization.load_config(config))
        for config, path in configs:
            d = dict(config)
            d.update(kwargs)
            if "dir_path" not in d:
                d["dir_path"] = os.path.dirname(path)
            yield Simulation(**d)


def from_config(conf_or_path):
    lst = list(iter_from_config(conf_or_path))
    if len(lst) > 1:
        raise AttributeError("Provide only one configuration")
    return lst[0]


def iter_from_py(pyfile, module_name='custom_simulation', **kwargs):
    """Try to load every Simulation instance in a given Python file"""
    import importlib
    import inspect
    added = False
    sims = []
    assert not _AVOID_RUNNING
    with do_not_run():
        assert _AVOID_RUNNING
        spec = importlib.util.spec_from_file_location(module_name, pyfile)
        folder = os.path.dirname(pyfile)
        if folder not in sys.path:
            added = True
            sys.path.append(folder)
        if not spec:
            raise ValueError(f"{pyfile} does not seem to be a Python module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        for (_name, sim) in inspect.getmembers(module, lambda x: isinstance(x, Simulation)):
            sims.append(sim)
        for sim in _iter_queued():
            sims.append(sim)
        if not sims:
            for (_name, sim) in inspect.getmembers(module, lambda x: inspect.isclass(x) and issubclass(x, Simulation)):
                sims.append(sim(**kwargs))
        del sys.modules[module_name]
    assert not _AVOID_RUNNING
    if not sims:
        raise AttributeError(f"No valid configurations found in {pyfile}")
    if added:
        sys.path.remove(folder)
    for sim in sims:
        yield replace(sim, **kwargs)


def from_py(pyfile):
    return next(iter_from_py(pyfile))


def run_from_file(*files, **kwargs):
    for sim in iter_from_file(*files):
        logger.info(f"Using config(s): {sim.name}")
        sim.run_simulation(**kwargs)
