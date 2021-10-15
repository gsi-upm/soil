import os
import time
import importlib
import sys
import yaml
import traceback
import logging
import networkx as nx
from networkx.readwrite import json_graph
from multiprocessing import Pool
from functools import partial
from tsih import History

import pickle

from . import serialization, utils, basestring, agents
from .environment import Environment
from .utils import logger
from .exporters import default
from .stats import defaultStats


#TODO: change documentation for simulation

class Simulation:
    """
    Similar to nsim.NetworkSimulation with three main differences:
        1) agent type can be specified by name or by class.
        2) instead of just one type, a network agents distribution can be used.
           The distribution specifies the weight (or probability) of each
           agent type in the topology. This is an example distribution: ::

                  [
                    {'agent_type': 'agent_type_1',
                     'weight': 0.2,
                     'state': {
                         'id': 0
                      }
                    },
                    {'agent_type': 'agent_type_2',
                     'weight': 0.8,
                     'state': {
                         'id': 1
                      }
                    }
                  ]

          In this example, 20% of the nodes will be marked as type
          'agent_type_1'.
        3) if no initial state is given, each node's state will be set
           to `{'id': 0}`.

    Parameters
    ---------
    name : str, optional
        name of the Simulation
    group : str, optional
        a group name can be used to link simulations
    topology : networkx.Graph instance, optional
    network_params : dict
        parameters used to create a topology with networkx, if no topology is given
    network_agents : dict
        definition of agents to populate the topology with
    agent_type : NetworkAgent subclass, optional
        Default type of NetworkAgent to use for nodes not specified in network_agents
    states : list, optional
        List of initial states corresponding to the nodes in the topology. Basic form is a list of integers
        whose value indicates the state
    dir_path: str, optional
        Directory path to load simulation assets (files, modules...)
    seed : str, optional
        Seed to use for the random generator
    num_trials : int, optional
        Number of independent simulation runs
    max_time : int, optional
        Time how long the simulation should run
    environment_params : dict, optional
        Dictionary of globally-shared environmental parameters
    environment_agents: dict, optional
        Similar to network_agents. Distribution of Agents that control the environment
    environment_class: soil.environment.Environment subclass, optional
        Class for the environment. It defailts to soil.environment.Environment
    load_module : str, module name, deprecated
        If specified, soil will load the content of this module under 'soil.agents.custom'


    """

    def __init__(self, name=None, group=None, topology=None, network_params=None,
                 network_agents=None, agent_type=None, states=None,
                 default_state=None, interval=1, num_trials=1,
                 max_time=100, load_module=None, seed=None,
                 dir_path=None, environment_agents=None,
                 environment_params=None, environment_class=None,
                 **kwargs):

        self.load_module = load_module
        self.network_params = network_params
        self.name = name or 'Unnamed'
        self.seed = str(seed or name)
        self._id = '{}_{}'.format(self.name, time.strftime("%Y-%m-%d_%H.%M.%S"))
        self.group = group or ''
        self.num_trials = num_trials
        self.max_time = max_time
        self.default_state = default_state or {}
        self.dir_path = dir_path or os.getcwd()
        self.interval = interval

        sys.path += list(x for x in [os.getcwd(), self.dir_path] if x not in sys.path)

        if topology is None:
            topology = serialization.load_network(network_params,
                                                  dir_path=self.dir_path)
        elif isinstance(topology, basestring) or isinstance(topology, dict):
            topology = json_graph.node_link_graph(topology)
        self.topology = nx.Graph(topology)


        self.environment_params = environment_params or {}
        self.environment_class = serialization.deserialize(environment_class,
                                                   known_modules=['soil.environment', ]) or Environment

        environment_agents = environment_agents or []
        self.environment_agents = agents._convert_agent_types(environment_agents,
                                                              known_modules=[self.load_module])

        distro = agents.calculate_distribution(network_agents,
                                               agent_type)
        self.network_agents = agents._convert_agent_types(distro,
                                                          known_modules=[self.load_module])

        self.states = agents._validate_states(states,
                                              self.topology)

        self._history = History(name=self.name,
                                backup=False)

    def run_simulation(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        '''Run the simulation and return the list of resulting environments'''
        return list(self.run_gen(*args, **kwargs))

    def _run_sync_or_async(self, parallel=False, *args, **kwargs):
        if parallel and not os.environ.get('SENPY_DEBUG', None):
            p = Pool()
            func = partial(self.run_trial_exceptions,
                           *args,
                           **kwargs)
            for i in p.imap_unordered(func, range(self.num_trials)):
                if isinstance(i, Exception):
                    logger.error('Trial failed:\n\t%s', i.message)
                    continue
                yield i
        else:
            for i in range(self.num_trials):
                yield self.run_trial(*args,
                                     **kwargs)

    def run_gen(self, *args, parallel=False, dry_run=False,
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

        with utils.timer('simulation {}'.format(self.name)):
            for stat in stats:
                stat.start()

            for exporter in exporters:
                exporter.start()
            for env in self._run_sync_or_async(*args,
                                               parallel=parallel,
                                               log_level=log_level,
                                               **kwargs):

                collected = list(stat.trial(env) for stat in stats)

                saved = self.save_stats(collected, t_step=env.now, trial_id=env.name)

                for exporter in exporters:
                    exporter.trial(env, saved)

                yield env


            collected = list(stat.end() for stat in stats)
            saved = self.save_stats(collected)

            for exporter in exporters:
                exporter.end(saved)


    def save_stats(self, collection, **kwargs):
        stats = dict(kwargs)
        for stat in collection:
            stats.update(stat)
        self._history.save_stats(utils.flatten_dict(stats))
        return stats

    def get_stats(self, **kwargs):
        return self._history.get_stats(**kwargs)

    def log_stats(self, stats):
        logger.info('Stats: \n{}'.format(yaml.dump(stats, default_flow_style=False)))
    

    def get_env(self, trial_id=0, **kwargs):
        '''Create an environment for a trial of the simulation'''
        opts = self.environment_params.copy()
        opts.update({
            'name': trial_id,
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
            'environment_agents': self.environment_agents,
        })
        opts.update(kwargs)
        env = self.environment_class(**opts)
        return env

    def run_trial(self, until=None, log_level=logging.INFO, **opts):
        """
        Run a single trial of the simulation

        """
        trial_id = '{}_trial_{}'.format(self.name, time.time()).replace('.', '-')
        if log_level:
            logger.setLevel(log_level)
        # Set-up trial environment and graph
        until = until or self.max_time
        env = self.get_env(trial_id=trial_id, **opts)
        # Set up agents on nodes
        with utils.timer('Simulation {} trial {}'.format(self.name, trial_id)):
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

    def to_dict(self):
        return self.__getstate__()

    def to_yaml(self):
        return yaml.dump(self.to_dict())


    def dump_yaml(self, f=None, outdir=None):
        if not f and not outdir:
            raise ValueError('specify a file or an output directory')

        if not f:
            f = os.path.join(outdir, '{}.dumped.yml'.format(self.name))

        with utils.open_or_reuse(f, 'w') as f:
            f.write(self.to_yaml())

    def dump_pickle(self, f=None, outdir=None):
        if not outdir and not f:
            raise ValueError('specify a file or an output directory')

        if not f:
            f = os.path.join(outdir,
                             '{}.simulation.pickle'.format(self.name))
        with utils.open_or_reuse(f, 'wb') as f:
            pickle.dump(self, f)

    def dump_sqlite(self, f):
        return self._history.dump(f)

    def __getstate__(self):
        state={}
        for k, v in self.__dict__.items():
            if k[0] != '_':
                state[k] = v
                state['topology'] = json_graph.node_link_data(self.topology)
                state['network_agents'] = agents.serialize_definition(self.network_agents,
                                                                      known_modules = [])
                state['environment_agents'] = agents.serialize_definition(self.environment_agents,
                                                                          known_modules = [])
                state['environment_class'] = serialization.serialize(self.environment_class,
                                                                     known_modules=['soil.environment'])[1]  # func, name
        if state['load_module'] is None:
            del state['load_module']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.load_module = getattr(self, 'load_module', None)
        if self.dir_path not in sys.path:
            sys.path += [self.dir_path, os.getcwd()]
        self.topology = json_graph.node_link_graph(state['topology'])
        self.network_agents = agents.calculate_distribution(agents._convert_agent_types(self.network_agents))
        self.environment_agents = agents._convert_agent_types(self.environment_agents,
                                                              known_modules=[self.load_module])
        self.environment_class = serialization.deserialize(self.environment_class,
                                                   known_modules=[self.load_module, 'soil.environment', ])  # func, name


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


def run_from_config(*configs, **kwargs):
    for config_def in configs:
        # logger.info("Found {} config(s)".format(len(ls)))
        for config, path in serialization.load_config(config_def):
            name = config.get('name', 'unnamed')
            logger.info("Using config(s): {name}".format(name=name))

            dir_path = config.pop('dir_path', os.path.dirname(path))
            sim = Simulation(dir_path=dir_path,
                             **config)
            sim.run_simulation(**kwargs)
