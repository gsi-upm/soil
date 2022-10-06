import os
from time import time as current_time, strftime 
import importlib
import sys
import yaml
import traceback
import logging
import networkx as nx

from dataclasses import dataclass, field, asdict
from typing import Union


from networkx.readwrite import json_graph
from multiprocessing import Pool
from functools import partial
import pickle

from . import serialization, utils, basestring, agents
from .environment import Environment
from .utils import logger, run_and_return_exceptions
from .exporters import default
from .time import INFINITY

from .config import Config, convert_old


#TODO: change documentation for simulation
@dataclass
class Simulation:
    """
    Parameters
    ---------
    config (optional): :class:`config.Config`
        name of the Simulation

    kwargs: parameters to use to initialize a new configuration, if one has not been provided.
    """
    name: str = 'Unnamed simulation'
    group: str = None
    model_class: Union[str, type] = 'soil.Environment'
    model_params: dict = field(default_factory=dict)
    seed: str = field(default_factory=lambda: current_time())
    dir_path: str = field(default_factory=lambda: os.getcwd())
    max_time: float = float('inf')
    max_steps: int = -1
    num_trials: int = 3
    dry_run: bool = False

    def run_simulation(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        '''Run the simulation and return the list of resulting environments'''
        return list(self.run_gen(*args, **kwargs))

    def _run_sync_or_async(self, parallel=False, **kwargs):
        if parallel and not os.environ.get('SENPY_DEBUG', None):
            p = Pool()
            func = partial(run_and_return_exceptions, self.run_trial, **kwargs)
            for i in p.imap_unordered(func, self.num_trials):
                if isinstance(i, Exception):
                    logger.error('Trial failed:\n\t%s', i.message)
                    continue
                yield i
        else:
            for i in range(self.num_trials):
                yield self.run_trial(trial_id=i,
                                     **kwargs)

    def run_gen(self, parallel=False, dry_run=False,
                exporters=[default, ], outdir=None, exporter_params={},
                log_level=None,
                **kwargs):
        '''Run the simulation and yield the resulting environments.'''
        if log_level:
            logger.setLevel(log_level)
        logger.info('Using exporters: %s', exporters or [])
        logger.info('Output directory: %s', outdir)
        exporters = serialization.deserialize_all(exporters,
                                                  simulation=self,
                                                  known_modules=['soil.exporters', ],
                                                  dry_run=dry_run,
                                                  outdir=outdir,
                                                  **exporter_params)

        with utils.timer('simulation {}'.format(self.name)):
            for exporter in exporters:
                exporter.sim_start()

            for env in self._run_sync_or_async(parallel=parallel,
                                               log_level=log_level,
                                               **kwargs):

                for exporter in exporters:
                    exporter.trial_start(env)

                for exporter in exporters:
                    exporter.trial_end(env)

                yield env

            for exporter in exporters:
                exporter.sim_end()

    def run_model(self, until=None, *args, **kwargs):
        until = until or float('inf')

        while self.schedule.next_time < until:
            self.step()
            utils.logger.debug(f'Simulation step {self.schedule.time}/{until}. Next: {self.schedule.next_time}')
        self.schedule.time = until

    def get_env(self, trial_id=0, **kwargs):
        '''Create an environment for a trial of the simulation'''
        def deserialize_reporters(reporters):
            for (k, v) in reporters.items():
                if isinstance(v, str) and v.startswith('py:'):
                    reporters[k] = serialization.deserialize(value.lsplit(':', 1)[1])

        model_params = self.model_params.copy()
        model_params.update(kwargs)

        agent_reporters = deserialize_reporters(model_params.pop('agent_reporters', {}))
        model_reporters = deserialize_reporters(model_params.pop('model_reporters', {}))

        env =  serialization.deserialize(self.model_class)
        return env(id=f'{self.name}_trial_{trial_id}',
                   seed=f'{self.seed}_trial_{trial_id}',
                   dir_path=self.dir_path,
                   agent_reporters=agent_reporters,
                   model_reporters=model_reporters,
                   **model_params)

    def run_trial(self, trial_id=None, until=None, log_level=logging.INFO, **opts):
        """
        Run a single trial of the simulation

        """
        model = self.get_env(trial_id, **opts)
        return self.run_model(model, trial_id=trial_id, until=until, log_level=log_level)

    def run_model(self, model, trial_id=None, until=None, log_level=logging.INFO, **opts):
        trial_id = trial_id if trial_id is not None else current_time()
        if log_level:
            logger.setLevel(log_level)
        # Set-up trial environment and graph
        until = until or self.max_time

        # Set up agents on nodes
        is_done = lambda: False
        if self.max_time and hasattr(self.schedule, 'time'):
            is_done = lambda x: is_done() or self.schedule.time >= self.max_time
        if self.max_steps and hasattr(self.schedule, 'time'):
            is_done = lambda: is_done() or self.schedule.steps >= self.max_steps

        with utils.timer('Simulation {} trial {}'.format(self.name, trial_id)):
            while not is_done():
                utils.logger.debug(f'Simulation time {model.schedule.time}/{until}. Next: {getattr(model.schedule, "next_time", model.schedule.time + self.interval)}')
                model.step()
        return model

    def to_dict(self):
        d = asdict(self)
        d['model_class'] = serialization.serialize(d['model_class'])[0]
        d['model_params'] = serialization.serialize(d['model_params'])[0]
        d['dir_path'] = str(d['dir_path'])

        return d

    def to_yaml(self):
        return yaml.dump(self.asdict())


def iter_from_config(config):
    configs = list(serialization.load_config(config))
    for config, path in configs:
        d = dict(config)
        if 'dir_path' not in d:
            d['dir_path'] = os.path.dirname(path)
        if d.get('version', '2') == '1' or 'agents' in d or 'network_agents' in d or 'environment_agents' in d:
            d = convert_old(d)
        d.pop('version', None)
        yield Simulation(**d)


def from_config(conf_or_path):
    lst = list(iter_from_config(conf_or_path))
    if len(lst) > 1:
        raise AttributeError('Provide only one configuration')
    return lst[0]


def run_from_config(*configs, **kwargs):
    for sim in iter_from_config(configs):
        logger.info(f"Using config(s): {sim.id}")
        sim.run_simulation(**kwargs)
