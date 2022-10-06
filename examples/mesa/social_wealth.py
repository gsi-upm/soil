'''
This is an example that adds soil agents and environment in a normal
mesa workflow.
'''
from mesa import Agent as MesaAgent
from mesa.space import MultiGrid
# from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from mesa.batchrunner import BatchRunner

import networkx as nx

from soil import NetworkAgent, Environment

def compute_gini(model):
    agent_wealths = [agent.wealth for agent in model.agents]
    x = sorted(agent_wealths)
    N = len(list(model.agents))
    B = sum( xi * (N-i) for i,xi in enumerate(x) ) / (N*sum(x))
    return (1 + (1/N) - 2*B)

class MoneyAgent(MesaAgent):
    """
    A MESA agent with fixed initial wealth.
    It will only share wealth with neighbors based on grid proximity
    """

    def __init__(self, unique_id, model):
        super().__init__(unique_id=unique_id, model=model)
        self.wealth = 1

    def move(self):
        possible_steps = self.model.grid.get_neighborhood(
            self.pos,
            moore=True,
            include_center=False)
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

    def give_money(self):
        cellmates = self.model.grid.get_cell_list_contents([self.pos])
        if len(cellmates) > 1:
            other = self.random.choice(cellmates)
            other.wealth += 1
            self.wealth -= 1

    def step(self):
        self.info("Crying wolf", self.pos)
        self.move()
        if self.wealth > 0:
            self.give_money()


class SocialMoneyAgent(NetworkAgent, MoneyAgent):
    wealth = 1

    def give_money(self):
        cellmates = set(self.model.grid.get_cell_list_contents([self.pos]))
        friends = set(self.get_neighboring_agents())
        self.info("Trying to give money")
        self.debug("Cellmates: ", cellmates)
        self.debug("Friends: ", friends)

        nearby_friends = list(cellmates & friends)

        if len(nearby_friends):
            other = self.random.choice(nearby_friends)
            other.wealth += 1
            self.wealth -= 1


class MoneyEnv(Environment):
    """A model with some number of agents."""
    def __init__(self, width, height, *args, topologies, **kwargs):

        super().__init__(*args, topologies=topologies, **kwargs)
        self.grid = MultiGrid(width, height, False)

        # Create agents
        for agent in self.agents:
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(agent, (x, y))

        self.datacollector = DataCollector(
            model_reporters={"Gini": compute_gini},
            agent_reporters={"Wealth": "wealth"})


def graph_generator(n=5):
    G = nx.Graph()
    for ix in range(n):
        G.add_edge(0, ix)
    return G

if __name__ == '__main__':


    G = graph_generator()
    fixed_params = {"topology": G,
                    "width": 10,
                    "network_agents": [{"agent_class": SocialMoneyAgent,
                                       'weight': 1}],
                    "height": 10}

    variable_params = {"N": range(10, 100, 10)}

    batch_run = BatchRunner(MoneyEnv,
                            variable_parameters=variable_params,
                            fixed_parameters=fixed_params,
                            iterations=5,
                            max_steps=100,
                            model_reporters={"Gini": compute_gini})
    batch_run.run_all()

    run_data = batch_run.get_model_vars_dataframe()
    run_data.head()
    print(run_data.Gini)

