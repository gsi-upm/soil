import os
import csv
import weakref
from random import random
from copy import deepcopy

import networkx as nx
import nxsim


class SoilEnvironment(nxsim.NetworkEnvironment):

    def __init__(self, name=None,
                 network_agents=None,
                 environment_agents=None,
                 states=None,
                 default_state=None,
                 interval=1,
                 *args, **kwargs):
        self.name = name or 'UnnamedEnvironment'
        self.states = deepcopy(states) or {}
        self.default_state = deepcopy(default_state) or {}
        super().__init__(*args, **kwargs)
        self._env_agents = {}
        self._history = {}
        self.interval = interval
        self.logger = None
        # Add environment agents first, so their events get
        # executed before network agents
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
            v = random()
            found = False
            for d in network_agents:
                threshold = d['threshold']
                if v >= threshold[0] and v < threshold[1]:
                    agent = d['agent_type']
                    state = None
                    if 'state' in d:
                        state = deepcopy(d['state'])
                    else:
                        try:
                            state = self.states[i]
                        except (IndexError, KeyError):
                            state = deepcopy(self.default_state)
                    node['agent'] = agent(environment=self,
                                          agent_id=i,
                                          state=state)
                    found = True
                    break
            assert found

    def run(self, *args, **kwargs):
        self._save_state()
        super().run(*args, **kwargs)
        self._save_state()

    def _save_state(self):
        for agent in self.agents:
            agent.save_state()
        self._history[self.now] = deepcopy(self.environment_params)

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
        return self.environment_params[key]

    def __setitem__(self, key, value):
        self.environment_params[key] = value

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
        for tstep, state in self._history.items():
            for attribute, value in state.items():
                yield ('env', tstep, attribute, value)
        for agent in self.agents:
            for tstep, state in agent._history.items():
                for attribute, value in state.items():
                    yield (agent.id, tstep, attribute, value)

    def history_to_graph(self):
        G = nx.Graph(self.G)

        for agent in self.agents:

            attributes = {'agent': str(agent.__class__)}
            lastattributes = {}
            spells = []
            lastvisible = False
            laststep = None
            for t_step, state in reversed(list(agent._history.items())):
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
