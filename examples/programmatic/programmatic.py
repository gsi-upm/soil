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
        self.debug('I am running')
        if agents.prob(0.2):
            self.info('This runs 2/10 times on average')


s = Simulation(name='Programmatic',
               network_params={'generator': mygenerator},
               num_trials=1,
               max_time=100,
               agent_type=MyAgent,
               dry_run=True)


# By default, logging will only print WARNING logs (and above).
# You need to choose a lower logging level to get INFO/DEBUG traces
logging.basicConfig(level=logging.INFO)
envs = s.run()

# Uncomment this to output the simulation to a YAML file
# s.dump_yaml('simulation.yaml')
