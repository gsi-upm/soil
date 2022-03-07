'''
Example of setting a 
Example of a fully programmatic simulation, without definition files.
'''
from soil import Simulation, agents
from soil.time import Delta
from random import expovariate
import logging



class MyAgent(agents.FSM):
    '''
    An agent that first does a ping
    '''

    defaults = {'pong_counts': 2}

    @agents.default_state
    @agents.state
    def ping(self):
        self.info('Ping')
        return self.pong, Delta(expovariate(1/16))

    @agents.state
    def pong(self):
        self.info('Pong')
        self.pong_counts -= 1
        self.info(str(self.pong_counts))
        if self.pong_counts < 1:
            return self.die()
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