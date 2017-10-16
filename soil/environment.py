import os
import time
import csv
import weakref
import random
from copy import deepcopy
from functools import partial

import networkx as nx
import nxsim

from . import utils


class SoilEnvironment(nxsim.NetworkEnvironment):

    def __init__(self, name=None,
                 network_agents=None,
                 environment_agents=None,
                 states=None,
                 default_state=None,
                 interval=1,
                 seed=None,
                 dump=False,
                 *args, **kwargs):
        self.name = name or 'UnnamedEnvironment'
        self.states = deepcopy(states) or {}
        self.default_state = deepcopy(default_state) or {}
        super().__init__(*args, **kwargs)
        self._env_agents = {}
        self._history = {}
        self.interval = interval
        self.logger = None
        self.dump = dump
        # Add environment agents first, so their events get
        # executed before network agents
        self['SEED'] = seed or time.time()
        random.seed(self['SEED'])
        self.environment_agents = environment_agents or []
        self.network_agents = network_agents or []
        self.process(self.save_state())

    @property
    def agents(self):
        yield from self.environment_agents
        yield from self.network_agents

    @property
    def environment_agents(self):
        for ref in self._env_agents.values():
            yield ref()

    @environment_agents.setter
    def environment_agents(self, environment_agents):
        # Set up environmental agent
        self._env_agents = {}
        for item in environment_agents:
            kwargs = deepcopy(item)
            atype = kwargs.pop('agent_type')
            kwargs['agent_id'] = kwargs.get('agent_id', atype.__name__)
            kwargs['state'] = kwargs.get('state', {})
            a = atype(environment=self, **kwargs)
            self._env_agents[a.id] = weakref.ref(a)

    @property
    def network_agents(self):
        for i in self.G.nodes():
            node = self.G.node[i]
            if 'agent' in node:
                yield node['agent']

    @network_agents.setter
    def network_agents(self, network_agents):
        for ix in self.G.nodes():
            i = ix
            node = self.G.node[i]
            agent, state = utils.agent_from_distribution(network_agents)
            self.set_agent(i, agent_type=agent, state=state)

    def set_agent(self, agent_id, agent_type, state=None):
        node = self.G.nodes[agent_id]
        defstate = deepcopy(self.default_state)
        defstate.update(self.states.get(agent_id, {}))
        if state:
            defstate.update(state)
        state = defstate
        state.update(node.get('state', {}))
        a = agent_type(environment=self,
                       agent_id=agent_id,
                       state=state)
        node['agent'] = a
        return a

    def add_node(self, agent_type, state=None):
        agent_id = int(len(self.G.nodes()))
        self.G.add_node(agent_id)
        a = self.set_agent(agent_id, agent_type, state)
        a['visible'] = True
        return a

    def add_edge(self, agent1, agent2, attrs=None):
        return self.G.add_edge(agent1, agent2)

    def run(self, *args, **kwargs):
        self._save_state()
        super().run(*args, **kwargs)
        self._save_state()

    def _save_state(self):
        # for agent in self.agents:
        #     agent.save_state()
        nowd = self._history[self.now] = {}
        nowd['env'] = deepcopy(self.environment_params)
        for agent in self.agents:
            nowd[agent.id] = deepcopy(agent.state)

    def save_state(self):
        while True:
            ev = self.event()
            ev._ok = True
            # Schedule the event with minimum priority so
            # that it executes after all agents are done
            self.schedule(ev, -1, self.interval)
            yield ev
            self._save_state()

    def __getitem__(self, key):
        if isinstance(key, tuple):
            t_step, agent_id, k = key

            def key_or_dict(d, k, nfunc):
                if k is None:
                    if d is None:
                        return {}
                    return {k: nfunc(v) for k, v in d.items()}
                if k in d:
                    return nfunc(d[k])
                return {}

            f1 = partial(key_or_dict, k=k, nfunc=lambda x: x)
            f2 = partial(key_or_dict, k=agent_id, nfunc=f1)
            return key_or_dict(self._history, t_step, f2)
        return self.environment_params[key]

    def __setitem__(self, key, value):
        self.environment_params[key] = value

    def __contains__(self, key):
        return key in self.environment_params

    def get(self, key, default=None):
        return self[key] if key in self else default

    def get_path(self, dir_path=None):
        dir_path = dir_path or self.sim().dir_path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return dir_path

    def get_agent(self, agent_id):
        return self.G.node[agent_id]['agent']

    def get_agents(self):
        return list(self.agents)

    def dump_csv(self, dir_path=None):
        csv_name = os.path.join(self.get_path(dir_path),
                                '{}.environment.csv'.format(self.name))

        with open(csv_name, 'w') as f:
            cr = csv.writer(f)
            cr.writerow(('agent_id', 'tstep', 'attribute', 'value'))
            for i in self.history_to_tuples():
                cr.writerow(i)

    def dump_gexf(self, dir_path=None):
        G = self.history_to_graph()
        graph_path = os.path.join(self.get_path(dir_path),
                                  self.name+".gexf")
        nx.write_gexf(G, graph_path, version="1.2draft")

    def history_to_tuples(self):
        for tstep, states in self._history.items():
            for a_id, state in states.items():
                for attribute, value in state.items():
                    yield (a_id, tstep, attribute, value)

    def history_to_graph(self):
        G = nx.Graph(self.G)

        for agent in self.agents:

            attributes = {'agent': str(agent.__class__)}
            lastattributes = {}
            spells = []
            lastvisible = False
            laststep = None
            for t_step, state in reversed(list(self[None, agent.id, None].items())):
                for attribute, value in state.items():
                    if attribute == 'visible':
                        nowvisible = state[attribute]
                        if nowvisible and not lastvisible:
                            laststep = t_step
                        if not nowvisible and lastvisible:
                            spells.append((laststep, t_step))

                        lastvisible = nowvisible
                    else:
                        if attribute not in lastattributes or lastattributes[attribute][0] != value:
                            laststep = lastattributes.get(attribute,
                                                          (None, None))[1]
                            value = (state[attribute], t_step, laststep)
                            key = 'attr_' + attribute
                            if key not in attributes:
                                attributes[key] = list()
                            attributes[key].append(value)
                            lastattributes[attribute] = (state[attribute], t_step)
            if lastvisible:
                spells.append((laststep, None))
            if spells:
                G.add_node(agent.id, spells=spells, **attributes)
            else:
                G.add_node(agent.id, **attributes)

        return G
