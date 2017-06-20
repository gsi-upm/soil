import weakref
import os
import csv
import time
import yaml
import networkx as nx
from networkx.readwrite import json_graph

from copy import deepcopy
from random import random
from matplotlib import pyplot as plt

import pickle

from nxsim import NetworkSimulation

from . import agents, utils, environment, basestring


class SoilSimulation(NetworkSimulation):
    """
    Subclass of nsim.NetworkSimulation with three main differences:
        1) agent type can be specified by name or by class.
        2) instead of just one type, an network_agents can be used.
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
                 default_state=None, interval=1,
                 dir_path=None, num_trials=3, max_time=100,
                 agent_module=None,
                 environment_agents=None, environment_params=None):

        if topology is None:
            topology = utils.load_network(network_params,
                                          dir_path=dir_path)
        elif isinstance(topology, basestring) or isinstance(topology, dict):
            topology = json_graph.node_link_graph(topology)

        self.topology = nx.Graph(topology)
        self.network_params = network_params
        self.name = name or 'UnnamedSimulation'
        self.num_trials = num_trials
        self.max_time = max_time
        self.default_state = default_state or {}
        self.dir_path = dir_path or os.getcwd()
        self.interval = interval
        self.environment_params = environment_params or {}

        environment_agents = environment_agents or []
        self.environment_agents = self._convert_agent_types(environment_agents)

        distro = self.calculate_distribution(network_agents,
                                             agent_type)
        self.network_agents = self._convert_agent_types(distro)

        self.states = self.validate_states(states,
                                           topology)

    def calculate_distribution(self,
                               network_agents=None,
                               agent_type=None):
        if network_agents:
            network_agents = deepcopy(network_agents)
        elif agent_type:
            network_agents = [{'agent_type': agent_type}]
        else:
            return []

        # Calculate the thresholds
        total = sum(x.get('weight', 1) for x in network_agents)
        acc = 0
        for v in network_agents:
            upper = acc + (v.get('weight', 1)/total)
            v['threshold'] = [acc, upper]
            acc = upper
        return network_agents

    def serialize_distribution(self):
        d = self._convert_agent_types(self.network_agents,
                                      to_string=True)
        for v in d:
            if 'threshold' in v:
                del v['threshold']
        return d

    def _convert_agent_types(self, ind, to_string=False):
        d = deepcopy(ind)
        for v in d:
            agent_type = v['agent_type']
            if to_string and not isinstance(agent_type, str):
                v['agent_type'] = str(agent_type.__name__)
            elif not to_string and isinstance(agent_type, str):
                v['agent_type'] = agents.agent_types[agent_type]
        return d

    def validate_states(self, states, topology):
        states = states or []
        # Validate states to avoid ignoring states during
        # initialization
        if isinstance(states, dict):
            for x in states:
                assert x in self.topology.node
        else:
            assert len(states) <= len(self.topology)
        return states

    def run_simulation(self):
        return self.run()

    def run(self):
        return list(self.run_simulation_gen())

    def run_simulation_gen(self):
        with utils.timer('simulation'):
            for i in range(self.num_trials):
                yield self.run_trial(i)

    def run_trial(self, trial_id=0):
        """Run a single trial of the simulation

        Parameters
        ----------
        trial_id : int
        """
        # Set-up trial environment and graph
        print('Trial: {}'.format(trial_id))
        env_name = '{}_trial_{}'.format(self.name, trial_id)
        env = environment.SoilEnvironment(name=env_name,
                                          topology=self.topology.copy(),
                                          initial_time=0,
                                          interval=self.interval,
                                          network_agents=self.network_agents,
                                          states=self.states,
                                          default_state=self.default_state,
                                          environment_agents=self.environment_agents,
                                          **self.environment_params)

        env.sim = weakref.ref(self)
        # Set up agents on nodes
        print('\tRunning')
        with utils.timer('trial'):
            env.run(until=self.max_time)
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
        state['network_agents'] = self.serialize_distribution()
        state['environment_agents'] = self._convert_agent_types(self.environment_agents,
                                                          to_string=True)
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.topology = json_graph.node_link_graph(state['topology'])
        self.network_agents = self._convert_agent_types(self.network_agents)
        self.environment_agents = self._convert_agent_types(self.environment_agents)
        return state


def from_config(config, G=None):
    config = list(utils.load_config(config))
    if len(config) > 1:
        raise AttributeError('Provide only one configuration')
    config = config[0][0]
    sim = SoilSimulation(**config)
    return sim


def run_from_config(*configs, dump=True, results_dir=None, timestamp=False):
    if not results_dir:
        results_dir = 'soil_output'
    for config_def in configs:
        for config, cpath in utils.load_config(config_def):
            name = config.get('name', 'unnamed')
            print("Using config(s): {name}".format(name=name))

            sim = SoilSimulation(**config)
            if timestamp:
                sim_folder = '{}_{}'.format(sim.name,
                                            time.strftime("%Y-%m-%d_%H:%M:%S"))
            else:
                sim_folder = sim.name
            dir_path = os.path.join(results_dir,
                                    sim_folder)
            results = sim.run_simulation()

            if dump:
                sim.dump_pickle(dir_path)
                sim.dump_yaml(dir_path)
                for env in results:
                    env.dump_gexf(dir_path)
                    env.dump_csv(dir_path)
