import os
from time import time as current_time, strftime 
import importlib
import sys
import yaml
import traceback
import logging
import networkx as nx

from networkx.readwrite import json_graph
from multiprocessing import Pool
from functools import partial
import pickle

from . import serialization, utils, basestring, agents
from .environment import Environment
from .utils import logger
from .exporters import default
from .stats import defaultStats

from .config import Config, convert_old


#TODO: change documentation for simulation
class Simulation:
    """
    Parameters
    ---------
    config (optional): :class:`config.Config`
        name of the Simulation

    kwargs: parameters to use to initialize a new configuration, if one has not been provided.
    """

    def __init__(self, config=None,
                 **kwargs):
        if kwargs:
            cfg = {}
            if config:
                cfg.update(config.dict(include_defaults=False))
            cfg.update(kwargs)
            config = Config(**cfg)
        if not config:
            raise ValueError("You need to specify a simulation configuration")

        self.config = config


    @property
    def name(self) -> str:
        return self.config.general.id

    def run_simulation(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        '''Run the simulation and return the list of resulting environments'''
        return list(self.run_gen(*args, **kwargs))

    def _run_sync_or_async(self, parallel=False, **kwargs):
        if parallel and not os.environ.get('SENPY_DEBUG', None):
            p = Pool()
            func = partial(self.run_trial_exceptions, **kwargs)
            for i in p.imap_unordered(func, range(self.config.general.num_trials)):
                if isinstance(i, Exception):
                    logger.error('Trial failed:\n\t%s', i.message)
                    continue
                yield i
        else:
            for i in range(self.config.general.num_trials):
                yield self.run_trial(trial_id=i,
                                     **kwargs)

    def run_gen(self, parallel=False, dry_run=False,
                exporters=[default, ], stats=[], outdir=None, exporter_params={},
                stats_params={}, log_level=None,
                **kwargs):
        '''Run the simulation and yield the resulting environments.'''
        if log_level:
            logger.setLevel(log_level)
        logger.info('Using exporters: %s', exporters or [])
        logger.info('Output directory: %s', outdir)
        exporters = serialization.deserialize_all(exporters,
                                                  simulation=self,
                                                  known_modules=['soil.exporters',],
                                                  dry_run=dry_run,
                                                  outdir=outdir,
                                                  **exporter_params)
        stats = serialization.deserialize_all(simulation=self,
                                             names=stats,
                                             known_modules=['soil.stats',],
                                             **stats_params)

        with utils.timer('simulation {}'.format(self.config.general.id)):
            for stat in stats:
                stat.sim_start()

            for exporter in exporters:
                exporter.start()

            for env in self._run_sync_or_async(parallel=parallel,
                                               log_level=log_level,
                                               **kwargs):

                for exporter in exporters:
                    exporter.trial_start(env)

                collected = list(stat.trial_end(env) for stat in stats)

                saved = self._update_stats(collected, t_step=env.now, trial_id=env.name)

                for exporter in exporters:
                    exporter.trial_end(env, saved)

                yield env

            collected = list(stat.end() for stat in stats)
            saved = self._update_stats(collected)

            for exporter in exporters:
                exporter.sim_end(saved)

    def _update_stats(self, collection, **kwargs):
        stats = dict(kwargs)
        for stat in collection:
            stats.update(stat)
        return stats

    def log_stats(self, stats):
        logger.info('Stats: \n{}'.format(yaml.dump(stats, default_flow_style=False)))

    def get_env(self, trial_id=0, **kwargs):
        '''Create an environment for a trial of the simulation'''
        opts = self.environment_params.copy()
        opts.update({
            'name': '{}_trial_{}'.format(self.name, trial_id),
            'topology': self.topology.copy(),
            'network_params': self.network_params,
            'seed': '{}_trial_{}'.format(self.seed, trial_id),
            'initial_time': 0,
            'interval': self.interval,
            'network_agents': self.network_agents,
            'initial_time': 0,
            'states': self.states,
            'dir_path': self.dir_path,
            'default_state': self.default_state,
            'history': bool(self._history),
            'environment_agents': self.environment_agents,
        })
        opts.update(kwargs)
        env = self.environment_class(**opts)
        return env

    def run_trial(self, trial_id=None, until=None, log_level=logging.INFO, **opts):
        """
        Run a single trial of the simulation

        """
        trial_id = trial_id if trial_id is not None else current_time()
        if log_level:
            logger.setLevel(log_level)
        # Set-up trial environment and graph
        until = until or self.config.general.max_time

        env = Environment.from_config(self.config, trial_id=trial_id)
        # Set up agents on nodes
        with utils.timer('Simulation {} trial {}'.format(self.config.general.id, trial_id)):
            env.run(until)
        return env

    def run_trial_exceptions(self, *args, **kwargs):
        '''
        A wrapper for run_trial that catches exceptions and returns them.
        It is meant for async simulations
        '''
        try:
            return self.run_trial(*args, **kwargs)
        except Exception as ex:
            if ex.__cause__ is not None:
                ex = ex.__cause__
            ex.message = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__)[:])
            return ex


def all_from_config(config):
    configs = list(serialization.load_config(config))
    for config, _ in configs:
        sim = Simulation(**config)
        yield sim


def from_config(conf_or_path):
    config = list(serialization.load_config(conf_or_path))
    if len(config) > 1:
        raise AttributeError('Provide only one configuration')
    config = config[0][0]
    sim = Simulation(**config)
    return sim

def from_old_config(conf_or_path):
    config = list(serialization.load_config(conf_or_path))
    if len(config) > 1:
        raise AttributeError('Provide only one configuration')
    config = convert_old(config[0][0])
    return Simulation(config)


def run_from_config(*configs, **kwargs):
    for config_def in configs:
        # logger.info("Found {} config(s)".format(len(ls)))
        for config, path in serialization.load_config(config_def):
            name = config.general.id
            logger.info("Using config(s): {name}".format(name=name))

            dir_path = config.general.dir_path or os.path.dirname(path)
            sim = Simulation(dir_path=dir_path,
                             **config)
            sim.run_simulation(**kwargs)
