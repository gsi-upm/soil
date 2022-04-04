import yaml
import os
import sys
import networkx as nx
import collections.abc

from . import serialization, utils, basestring, agents

class Config(collections.abc.Mapping):
    """

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
    topology (optional): networkx.Graph instance or Node-Link topology as a dict or string (will be loaded with `json_graph.node_link_graph(topology`).
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
        Maximum step/time for each simulation
    environment_params : dict, optional
        Dictionary of globally-shared environmental parameters
    environment_agents: dict, optional
        Similar to network_agents. Distribution of Agents that control the environment
    environment_class: soil.environment.Environment subclass, optional
        Class for the environment. It defailts to soil.environment.Environment
    """
    __slots__ = 'name', 'agent_type', 'group', 'network_agents', 'environment_agents', 'states', 'default_state', 'interval', 'network_params', 'seed', 'num_trials', 'max_time', 'topology', 'schedule', 'initial_time', 'environment_params', 'environment_class', 'dir_path', '_added_to_path'

    def __init__(self, name=None,
                 group=None,
                 agent_type='BaseAgent',
                 network_agents=None,
                 environment_agents=None,
                 states=None,
                 default_state=None,
                 interval=1,
                 network_params=None,
                 seed=None,
                 num_trials=1,
                 max_time=None,
                 topology=None,
                 schedule=None,
                 initial_time=0,
                 environment_params={},
                 environment_class='soil.Environment',
                 dir_path=None):

        self.network_params = network_params
        self.name = name or 'Unnamed'
        self.seed = str(seed or name)
        self.group = group or ''
        self.num_trials = num_trials
        self.max_time = max_time
        self.default_state = default_state or {}
        self.dir_path = dir_path or os.getcwd()
        self.interval = interval

        self._added_to_path = list(x for x in [os.getcwd(), self.dir_path] if x not in sys.path)
        sys.path += self._added_to_path

        self.topology = topology

        self.schedule = schedule
        self.initial_time = initial_time


        self.environment_class = environment_class
        self.environment_params = dict(environment_params)

        #TODO: Check agent distro vs fixed agents
        self.environment_agents = environment_agents or []
        
        self.agent_type = agent_type

        self.network_agents = network_agents or {}

        self.states = states or {}


    def validate(self):
        agents._validate_states(self.states,
                                self._topology)

    def restore_path(self):
        for added in self._added_to_path:
            sys.path.remove(added)

    def to_yaml(self):
        return yaml.dump(self.to_dict())

    def dump_yaml(self, f=None, outdir=None):
        if not f and not outdir:
            raise ValueError('specify a file or an output directory')

        if not f:
            f = os.path.join(outdir, '{}.dumped.yml'.format(self.name))

        with utils.open_or_reuse(f, 'w') as f:
            f.write(self.to_yaml())

    def to_yaml(self):
        return yaml.dump(self.to_dict())

    # TODO: See note on getstate
    def to_dict(self):
        return self.__getstate__()

    def dump_yaml(self, f=None, outdir=None):
        if not f and not outdir:
            raise ValueError('specify a file or an output directory')

        if not f:
            f = os.path.join(outdir, '{}.dumped.yml'.format(self.name))

        with utils.open_or_reuse(f, 'w') as f:
            f.write(self.to_yaml())

    def __getitem__(self, key):
        return getattr(self, key)

    def __iter__(self):
        return (k for k in self.__slots__ if k[0] != '_')

    def __len__(self):
        return len(self.__slots__)

    def dump_pickle(self, f=None, outdir=None):
        if not outdir and not f:
            raise ValueError('specify a file or an output directory')

        if not f:
            f = os.path.join(outdir,
                             '{}.simulation.pickle'.format(self.name))
        with utils.open_or_reuse(f, 'wb') as f:
            pickle.dump(self, f)

    # TODO: remove this. A config should be sendable regardless. Non-pickable objects could be computed via properties and the like
    # def __getstate__(self):
    #     state={}
    #     for k, v in self.__dict__.items():
    #         if k[0] != '_':
    #             state[k] = v
    #             state['topology'] = json_graph.node_link_data(self.topology)
    #             state['network_agents'] = agents.serialize_definition(self.network_agents,
    #                                                                   known_modules = [])
    #             state['environment_agents'] = agents.serialize_definition(self.environment_agents,
    #                                                                       known_modules = [])
    #             state['environment_class'] = serialization.serialize(self.environment_class,
    #                                                                  known_modules=['soil.environment'])[1]  # func, name
    #     if state['load_module'] is None:
    #         del state['load_module']
    #     return state

    # # TODO: remove, same as __getstate__
    # def __setstate__(self, state):
    #     self.__dict__ = state
    #     self.load_module = getattr(self, 'load_module', None)
    #     if self.dir_path not in sys.path:
    #         sys.path += [self.dir_path, os.getcwd()]
    #     self.topology = json_graph.node_link_graph(state['topology'])
    #     self.network_agents = agents.calculate_distribution(agents._convert_agent_types(self.network_agents))
    #     self.environment_agents = agents._convert_agent_types(self.environment_agents,
    #                                                           known_modules=[self.load_module])
    #     self.environment_class = serialization.deserialize(self.environment_class,
                                                           # known_modules=[self.load_module,
                                                           #                'soil.environment', ])  # func, name

class CalculatedConfig(Config):
    def __init__(self, config):
        """
        Returns a configuration object that replaces some "plain" attributes (e.g., `environment_class` string) into
        a Python object (`soil.environment.Environment` class).
        """
        self._config = config
        values = dict(config)
        values['environment_class'] = self._environment_class()
        values['environment_agents'] = self._environment_agents()
        values['topology'] = self._topology()
        values['network_agents'] = self._network_agents()
        values['agent_type'] = serialization.deserialize(self.agent_type, known_modules=['soil.agents'])

        return values

    def _topology(self):
        topology = self._config.topology
        if topology is None:
            topology = serialization.load_network(self._config.network_params,
                                                  dir_path=self._config.dir_path)

        elif isinstance(topology, basestring) or isinstance(topology, dict):
            topology = json_graph.node_link_graph(topology)

        return nx.Graph(topology)

    def _environment_class(self):
        return serialization.deserialize(self._config.environment_class,
                                         known_modules=['soil.environment', ]) or Environment

    def _environment_agents(self):
        return agents._convert_agent_types(self._config.environment_agents)

    def _network_agents(self):
        distro = agents.calculate_distribution(self._config.network_agents,
                                               self._config.agent_type)
        return agents._convert_agent_types(distro)

    def _environment_class(self):
        return serialization.deserialize(self._config.environment_class,
                                         known_modules=['soil.environment', ])  # func, name

