'''
Example of setting a 
Example of a fully programmatic simulation, without definition files.
'''
from soil import Simulation, agents
from soil.time import Delta
from networkx import Graph
from random import expovariate
import logging



class MyAgent(agents.FSM):

    @agents.default_state
    @agents.state
    def neutral(self):
        self.info('I am running')
        return None, Delta(expovariate(1/16))

s = Simulation(name='Programmatic',
               network_agents=[{'agent_type': MyAgent, 'id': 0}],
               topology={'nodes': [{'id': 0}], 'links': []},
               num_trials=1,
               max_time=100,
               agent_type=MyAgent,
               dry_run=True)


logging.basicConfig(level=logging.INFO)
envs = s.run()
