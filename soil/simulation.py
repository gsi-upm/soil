import os
from time import time as current_time, strftime
import sys
import yaml
import hashlib

import inspect
import logging
import networkx as nx

from tqdm.auto import tqdm

from textwrap import dedent

from dataclasses import dataclass, field, asdict, replace
from typing import Any, Dict, Union, Optional, List


from functools import partial
from contextlib import contextmanager
from itertools import product
import json


from . import serialization, exporters, utils, basestring, agents
from . import environment
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
        (cls, params) = _QUEUED.pop(0)
        yield replace(cls, parameters=params)


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
        parameters: The parameters to pass to the model.
        matrix: A matrix of values for each parameter.
        seed: The seed to use for the simulation.
        dir_path: The directory path to use for the simulation.
        max_time: The maximum time to run the simulation.
        max_steps: The maximum number of steps to run the simulation.
        iterations: The number of iterations (times) to run the simulation.
        num_processes: The number of processes to use for the simulation. If greater than one, simulations will be performed in parallel. This may make debugging and error handling difficult.
        tables: The tables to use in the simulation datacollector
        agent_reporters: The agent reporters to use in the datacollector
        model_reporters: The model reporters to use in the datacollector
        dry_run: Whether or not to run the simulation. If True, the simulation will not be run.
        backup: Whether or not to backup the simulation. If True, the simulation files will be backed up to a different directory.
        overwrite: Whether or not to replace existing simulation data.
        source_file: Python file to use to find additional classes.
    """

    version: str = "2"
    source_file: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = ""
    group: str = None
    backup: bool = False
    overwrite: bool = False
    dry_run: bool = False
    dump: bool = False
    model: Union[str, type] = "soil.Environment"
    parameters: dict = field(default_factory=dict)
    matrix: dict = field(default_factory=dict)
    seed: str = "default"
    dir_path: str = field(default_factory=lambda: os.getcwd())
    max_time: float = None
    max_steps: int = None
    iterations: int = 1
    num_processes: Optional[int] = 1
    exporters: Optional[List[str]] = field(default_factory=lambda: [exporters.default])
    model_reporters: Optional[Dict[str, Any]] = field(default_factory=dict)
    agent_reporters: Optional[Dict[str, Any]] = field(default_factory=dict)
    tables: Optional[Dict[str, Any]] = field(default_factory=dict)
    outdir: str = field(default_factory=lambda: os.path.join(os.getcwd(), "soil_output"))
    # outdir: Optional[str] = None
    exporter_params: Optional[Dict[str, Any]] = field(default_factory=dict)
    level: int = logging.INFO
    skip_test: Optional[bool] = False
    debug: Optional[bool] = False

    def __post_init__(self):
        if self.name is None:
            if isinstance(self.model, str):
                self.name = self.model
            else:
                self.name = self.model.__name__
        self.logger = logger.getChild(self.name)
        self.logger.setLevel(self.level)

        if self.source_file and (not os.path.isabs(self.source_file)):
            self.source_file = os.path.abspath(os.path.join(self.dir_path, self.source_file))
        with serialization.with_source(self.source_file):

            if isinstance(self.model, str):
                self.model = serialization.deserialize(self.model)

            self.agent_reporters = self.agent_reporters
            self.model_reporters = self.model_reporters
            self.tables = self.tables
            self.id = f"{self.name}_{current_time()}"

    def run(self, **kwargs):
        """Run the simulation and return the list of resulting environments"""
        if kwargs:
            return replace(self, **kwargs).run()

        param_combinations = self._collect_params(**kwargs)
        if _AVOID_RUNNING:
            _QUEUED.extend((self, param) for param in param_combinations)
            return []

        self.logger.debug("Using exporters: %s", self.exporters or [])

        exporters = serialization.deserialize_all(
            self.exporters,
            simulation=self,
            known_modules=[
                "soil.exporters",
            ],
            dump=self.dump and not self.dry_run,
            outdir=self.outdir,
            **self.exporter_params,
        )

        results = []
        for exporter in exporters:
            exporter.sim_start()

        for params in tqdm(param_combinations, desc=self.name, unit="configuration"):
            tqdm.write("- Running for parameters: ")
            for (k, v) in params.items():
                tqdm.write(f"  {k} = {v}")
            sha = hashlib.sha256()
            sha.update(repr(sorted(params.items())).encode())
            params_id = sha.hexdigest()[:7]
            for env in self._run_iters_for_params(params):
                for exporter in exporters:
                    exporter.iteration_end(env, params, params_id)
                results.append(env)

        for exporter in exporters:
            exporter.sim_end()

        return results

    def _collect_params(self):

        parameters = []
        if self.parameters:
            parameters.append(self.parameters)
        if self.matrix:
            assert isinstance(self.matrix, dict)
            for values in product(*(self.matrix.values())):
                parameters.append(dict(zip(self.matrix.keys(), values)))

        if not parameters:
            parameters = [{}]
        if self.dump:
            self.logger.info("Output directory: %s", self.outdir)

        return parameters

    def _run_iters_for_params(
        self,
        params
    ):
        """Run the simulation and yield the resulting environments."""

        with serialization.with_source(self.source_file):
            with utils.timer(f"running for config {params}"):
                if self.dry_run:
                    def func(*args, **kwargs):
                        return None
                else:
                    func = self._run_model

                for env in tqdm(utils.run_parallel(
                    func=func,
                    iterable=range(self.iterations),
                    **params,
                ), total=self.iterations, leave=False):
                    if env is None and self.dry_run:
                        continue

                    yield env

    def _get_env(self, iteration_id, params):
        """Create an environment for a iteration of the simulation"""

        iteration_id = str(iteration_id)

        agent_reporters = self.agent_reporters
        agent_reporters.update(params.pop("agent_reporters", {}))
        model_reporters = self.model_reporters
        model_reporters.update(params.pop("model_reporters", {}))

        return self.model(
            id=iteration_id,
            seed=f"{self.seed}_iteration_{iteration_id}",
            dir_path=self.dir_path,
            logger=self.logger.getChild(iteration_id),
            agent_reporters=agent_reporters,
            model_reporters=model_reporters,
            tables=self.tables,
            **params,
        )

    def _run_model(self, iteration_id, **params):
        """
        Run a single iteration of the simulation

        """
        # Set-up iteration environment and graph
        model = self._get_env(iteration_id, params)
        with utils.timer("Simulation {} iteration {}".format(self.name, iteration_id)):

            max_time = self.max_time 
            max_steps = self.max_steps

            if (max_time is not None) and (max_steps is not None):
                is_done = lambda model: (not model.running) or (model.schedule.time >= max_time) or (model.schedule.steps >= max_steps)
            elif max_time is not None:
                is_done = lambda model: (not model.running) or (model.schedule.time >= max_time)
            elif max_steps is not None:
                is_done = lambda model: (not model.running) or (model.schedule.steps >= max_steps)
            else:
                is_done = lambda model: not model.running
            
            if not model.schedule.agents:
                raise Exception("No agents in model. This is probably a bug. Make sure that the model has agents scheduled after its initialization.")

            newline = "\n"
            self.logger.debug(
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

            while not is_done(model):
                self.logger.debug(
                    f'Simulation time {model.schedule.time}/{max_time}.'
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


def iter_from_py(pyfile, module_name='imported_file', **kwargs):
    """Try to load every Simulation instance in a given Python file"""
    import importlib
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
            for (_name, env) in inspect.getmembers(module,
                                                   lambda x: inspect.isclass(x) and
                                                   issubclass(x, environment.Environment) and
                                                   (getattr(x, "__module__", None) != environment.__name__)):
                sims.append(Simulation(model=env, **kwargs))
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

def run(env, iterations=1, num_processes=1, dump=False, name="test", **kwargs):
    return Simulation(model=env, iterations=iterations, name=name, dump=dump, num_processes=num_processes, **kwargs).run()