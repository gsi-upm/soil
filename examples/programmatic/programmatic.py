'''
Example of a fully programmatic simulation, without definition files.
'''
from soil import Simulation, agents
from networkx import Graph
import logging


def mygenerator():
    # Add only a node
    G = Graph()
    G.add_node(1)
    return G


class MyAgent(agents.FSM):

    @agents.default_state
    @agents.state
    def neutral(self):
        self.info('I am running')


s = Simulation(name='Programmatic',
               network_params={'generator': mygenerator},
               num_trials=1,
               max_time=100,
               agent_type=MyAgent,
               dry_run=True)


logging.basicConfig(level=logging.INFO)
envs = s.run()

s.dump_yaml()

for env in envs:
    env.dump_csv()
