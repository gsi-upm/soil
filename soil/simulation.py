import os
import time
import imp
import sys
import yaml
import networkx as nx
from networkx.readwrite import json_graph
from multiprocessing import Pool
from functools import partial

import pickle

from nxsim import NetworkSimulation

from . import utils, environment, basestring, agents
from .utils import logger


class SoilSimulation(NetworkSimulation):
    """
    Subclass of nsim.NetworkSimulation with three main differences:
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
    """
    def __init__(self, name=None, topology=None, network_params=None,
                 network_agents=None, agent_type=None, states=None,
                 default_state=None, interval=1, dump=None, dry_run=False,
                 dir_path=None, num_trials=1, max_time=100,
                 agent_module=None, load_module=None, seed=None,
                 environment_agents=None, environment_params=None):

        if topology is None:
            topology = utils.load_network(network_params,
                                          dir_path=dir_path)
        elif isinstance(topology, basestring) or isinstance(topology, dict):
            topology = json_graph.node_link_graph(topology)

        self.load_module = load_module
        self.topology = nx.Graph(topology)
        self.network_params = network_params
        self.name = name or 'UnnamedSimulation'
        self.num_trials = num_trials
        self.max_time = max_time
        self.default_state = default_state or {}
        self.dir_path = dir_path or os.getcwd()
        self.interval = interval
        self.seed = str(seed) or str(time.time())
        self.dump = dump
        self.dry_run = dry_run
        self.environment_params = environment_params or {}

        if load_module:
            path = sys.path + [self.dir_path, os.getcwd()]
            f, fp, desc = imp.find_module(load_module, path)
            imp.load_module('soil.agents.custom', f, fp, desc)

        environment_agents = environment_agents or []
        self.environment_agents = agents._convert_agent_types(environment_agents)

        distro = agents.calculate_distribution(network_agents,
                                               agent_type)
        self.network_agents = agents._convert_agent_types(distro)

        self.states = agents._validate_states(states,
                                              self.topology)

    def run_simulation(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        return list(self.run_simulation_gen(*args, **kwargs))

    def run_simulation_gen(self, *args, parallel=False, dry_run=False,
                           **kwargs):
        p = Pool()
        with utils.timer('simulation {}'.format(self.name)):
            if parallel:
                func = partial(self.run_trial, dry_run=dry_run or self.dry_run,
                               return_env=not parallel, **kwargs)
                for i in p.imap_unordered(func, range(self.num_trials)):
                    yield i
            else:
                for i in range(self.num_trials):
                    yield self.run_trial(i, dry_run=dry_run or self.dry_run, **kwargs)
            if not (dry_run or self.dry_run):
                logger.info('Dumping results to {}'.format(self.dir_path))
                self.dump_pickle(self.dir_path)
                self.dump_yaml(self.dir_path)
            else:
                logger.info('NOT dumping results')

    def get_env(self, trial_id=0, **kwargs):
        opts = self.environment_params.copy()
        env_name = '{}_trial_{}'.format(self.name, trial_id)
        opts.update({
            'name': env_name,
            'topology': self.topology.copy(),
            'seed': self.seed+env_name,
            'initial_time': 0,
            'dry_run': self.dry_run,
            'interval': self.interval,
            'network_agents': self.network_agents,
            'states': self.states,
            'default_state': self.default_state,
            'environment_agents': self.environment_agents,
            'dir_path': self.dir_path,
        })
        opts.update(kwargs)
        env = environment.SoilEnvironment(**opts)
        return env

    def run_trial(self, trial_id=0, until=None, return_env=True, **opts):
        """Run a single trial of the simulation

        Parameters
        ----------
        trial_id : int
        """
        # Set-up trial environment and graph
        until = until or self.max_time
        env = self.get_env(trial_id=trial_id, **opts)
        # Set up agents on nodes
        with utils.timer('Simulation {} trial {}'.format(self.name, trial_id)):
            env.run(until)
        if self.dump and not self.dry_run:
            with utils.timer('Dumping simulation {} trial {}'.format(self.name, trial_id)):
                env.dump(formats=self.dump)
        if return_env:
            return env

    def to_dict(self):
        return self.__getstate__()

    def to_yaml(self):
        return yaml.dump(self.to_dict())

    def dump_yaml(self, dir_path=None, file_name=None):
        dir_path = dir_path or self.dir_path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not file_name:
            file_name = os.path.join(dir_path,
                                     '{}.dumped.yml'.format(self.name))
        with open(file_name, 'w') as f:
            f.write(self.to_yaml())

    def dump_pickle(self, dir_path=None, pickle_name=None):
        dir_path = dir_path or self.dir_path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not pickle_name:
            pickle_name = os.path.join(dir_path,
                                       '{}.simulation.pickle'.format(self.name))
        with open(pickle_name, 'wb') as f:
            pickle.dump(self, f)

    def __getstate__(self):
        state = self.__dict__.copy()
        state['topology'] = json_graph.node_link_data(self.topology)
        state['network_agents'] = agents._serialize_distribution(self.network_agents)
        state['environment_agents'] = agents._convert_agent_types(self.environment_agents,
                                                                 to_string=True)
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.topology = json_graph.node_link_graph(state['topology'])
        self.network_agents = agents.calculate_distribution(agents._convert_agent_types(self.network_agents))
        self.environment_agents = agents._convert_agent_types(self.environment_agents)
        return state


def from_config(config):
    config = list(utils.load_config(config))
    if len(config) > 1:
        raise AttributeError('Provide only one configuration')
    config = config[0][0]
    sim = SoilSimulation(**config)
    return sim


def run_from_config(*configs, results_dir='soil_output', dry_run=False, dump=None, timestamp=False,  **kwargs):
    for config_def in configs:
        # logger.info("Found {} config(s)".format(len(ls)))
        for config, _ in utils.load_config(config_def):
            name = config.get('name', 'unnamed')
            logger.info("Using config(s): {name}".format(name=name))

            if timestamp:
                sim_folder = '{}_{}'.format(name,
                                            time.strftime("%Y-%m-%d_%H:%M:%S"))
            else:
                sim_folder = name
            dir_path = os.path.join(results_dir, sim_folder)
            sim = SoilSimulation(dir_path=dir_path, dump=dump, **config)
            logger.info('Dumping results to {} : {}'.format(sim.dir_path, sim.dump))
            sim.run_simulation(**kwargs)
