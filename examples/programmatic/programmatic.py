"""
Example of a fully programmatic simulation, without definition files.
"""
from soil import Simulation, agents
from networkx import Graph
import logging


def mygenerator():
    # Add only a node
    G = Graph()
    G.add_node(1)
    G.add_node(2)
    return G


class MyAgent(agents.FSM):
    times_run = 0
    @agents.default_state
    @agents.state
    def neutral(self):
        self.debug("I am running")
        if self.prob(0.2):
            self.times_run += 1
            self.info("This runs 2/10 times on average")


simulation = Simulation(
    name="Programmatic",
    model_params={
        'topology': {
            'params': {
                'generator': mygenerator
            },
        },
        'agents': {
            'distribution': [{
                'agent_class': MyAgent,
                'topology': True,
            }]
        }
    },
    seed='Program',
    agent_reporters={'times_run': 'times_run'},
    num_trials=1,
    max_time=100,
    dry_run=True,
)

if __name__ == "__main__":
    # By default, logging will only print WARNING logs (and above).
    # You need to choose a lower logging level to get INFO/DEBUG traces
    logging.basicConfig(level=logging.INFO)
    envs = simulation.run()

    for agent in envs[0].agents:
        print(agent.times_run)
