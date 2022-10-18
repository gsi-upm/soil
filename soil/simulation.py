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

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Union, Optional, List


from networkx.readwrite import json_graph
from functools import partial
import pickle

from . import serialization, exporters, utils, basestring, agents
from .environment import Environment
from .utils import logger, run_and_return_exceptions
from .config import Config, convert_old


# TODO: change documentation for simulation
@dataclass
class Simulation:
    """
    Parameters
    ---------
    config (optional): :class:`config.Config`
        name of the Simulation

    kwargs: parameters to use to initialize a new configuration, if one not been provided.
    """

    version: str = "2"
    name: str = "Unnamed simulation"
    description: Optional[str] = ""
    group: str = None
    model_class: Union[str, type] = "soil.Environment"
    model_params: dict = field(default_factory=dict)
    seed: str = field(default_factory=lambda: current_time())
    dir_path: str = field(default_factory=lambda: os.getcwd())
    max_time: float = float("inf")
    max_steps: int = -1
    interval: int = 1
    num_trials: int = 1
    parallel: Optional[bool] = None
    exporters: Optional[List[str]] = field(default_factory=list)
    outdir: Optional[str] = None
    exporter_params: Optional[Dict[str, Any]] = field(default_factory=dict)
    dry_run: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, env, **kwargs):

        ignored = {
            k: v for k, v in env.items() if k not in inspect.signature(cls).parameters
        }

        d = {k: v for k, v in env.items() if k not in ignored}
        if ignored:
            d.setdefault("extra", {}).update(ignored)
        if ignored:
            print(f'Warning: Ignoring these parameters (added to "extra"): { ignored }')
        d.update(kwargs)

        return cls(**d)

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
        return list(self.run_gen(*args, **kwargs))

    def run_gen(
        self,
        parallel=False,
        dry_run=None,
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
            dry_run=dry_run,
            outdir=outdir,
            **exporter_params,
        )

        with utils.timer("simulation {}".format(self.name)):
            for exporter in exporters:
                exporter.sim_start()

            for env in utils.run_parallel(
                func=self.run_trial,
                iterable=range(int(self.num_trials)),
                parallel=parallel,
                log_level=log_level,
                **kwargs,
            ):

                for exporter in exporters:
                    exporter.trial_start(env)

                for exporter in exporters:
                    exporter.trial_end(env)

                yield env

            for exporter in exporters:
                exporter.sim_end()

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

        agent_reporters = deserialize_reporters(params.pop("agent_reporters", {}))
        model_reporters = deserialize_reporters(params.pop("model_reporters", {}))

        env = serialization.deserialize(self.model_class)
        return env(
            id=f"{self.name}_trial_{trial_id}",
            seed=f"{self.seed}_trial_{trial_id}",
            dir_path=self.dir_path,
            agent_reporters=agent_reporters,
            model_reporters=model_reporters,
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

        if self.max_steps and self.max_steps > 0 and hasattr(model.schedule, "steps"):
            prev_steps = is_done

            def is_done():
                return prev_steps() or model.schedule.steps >= self.max_steps

        newline = "\n"
        logger.info(
            dedent(
                f"""
Model stats:
  Agents (total: { model.schedule.get_agent_count() }):
      - { (newline + '      - ').join(str(a) for a in model.schedule.agents) }

  Topology size: { len(model.G) if hasattr(model, "G") else 0 }
        """
            )
        )

        while not is_done():
            utils.logger.debug(
                f'Simulation time {model.schedule.time}/{until}. Next: {getattr(model.schedule, "next_time", model.schedule.time + self.interval)}'
            )
            model.step()

        if (
            model.schedule.time < until
        ):  # Simulation ended (no more steps) before the expected time
            model.schedule.time = until
        return model

    def to_dict(self):
        d = asdict(self)
        if not isinstance(d["model_class"], str):
            d["model_class"] = serialization.name(d["model_class"])
        d["model_params"] = serialization.serialize_dict(d["model_params"])
        d["dir_path"] = str(d["dir_path"])
        d["version"] = "2"
        return d

    def to_yaml(self):
        return yaml.dump(self.to_dict())


def iter_from_config(*cfgs, **kwargs):
    for config in cfgs:
        configs = list(serialization.load_config(config))
        for config, path in configs:
            d = dict(config)
            if "dir_path" not in d:
                d["dir_path"] = os.path.dirname(path)
            yield Simulation.from_dict(d, **kwargs)


def from_config(conf_or_path):
    lst = list(iter_from_config(conf_or_path))
    if len(lst) > 1:
        raise AttributeError("Provide only one configuration")
    return lst[0]


def run_from_config(*configs, **kwargs):
    for sim in iter_from_config(*configs):
        logger.info(f"Using config(s): {sim.name}")
        sim.run_simulation(**kwargs)
