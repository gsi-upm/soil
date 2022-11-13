"""
This is an example that adds soil agents and environment in a normal
mesa workflow.
"""
from mesa import Agent as MesaAgent
from mesa.space import MultiGrid

# from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from mesa.batchrunner import BatchRunner

import networkx as nx

from soil import NetworkAgent, Environment, serialization


def compute_gini(model):
    agent_wealths = [agent.wealth for agent in model.agents]
    x = sorted(agent_wealths)
    N = len(list(model.agents))
    B = sum(xi * (N - i) for i, xi in enumerate(x)) / (N * sum(x))
    return 1 + (1 / N) - 2 * B


class MoneyAgent(MesaAgent):
    """
    A MESA agent with fixed initial wealth.
    It will only share wealth with neighbors based on grid proximity
    """

    def __init__(self, unique_id, model, wealth=1, **kwargs):
        super().__init__(unique_id=unique_id, model=model)
        self.wealth = wealth

    def move(self):
        possible_steps = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

    def give_money(self):
        cellmates = self.model.grid.get_cell_list_contents([self.pos])
        if len(cellmates) > 1:
            other = self.random.choice(cellmates)
            other.wealth += 1
            self.wealth -= 1

    def step(self):
        print("Crying wolf", self.pos)
        self.move()
        if self.wealth > 0:
            self.give_money()


class SocialMoneyAgent(NetworkAgent, MoneyAgent):
    wealth = 1

    def give_money(self):
        cellmates = set(self.model.grid.get_cell_list_contents([self.pos]))
        friends = set(self.get_neighbors())
        self.info("Trying to give money")
        self.info("Cellmates: ", cellmates)
        self.info("Friends: ", friends)

        nearby_friends = list(cellmates & friends)

        if len(nearby_friends):
            other = self.random.choice(nearby_friends)
            other.wealth += 1
            self.wealth -= 1


def graph_generator(n=5):
    G = nx.Graph()
    for ix in range(n):
        G.add_edge(0, ix)
    return G


class MoneyEnv(Environment):
    """A model with some number of agents."""

    def __init__(
        self,
        width,
        height,
        N,
        generator=graph_generator,
        agent_class=SocialMoneyAgent,
        topology=None,
        **kwargs
    ):

        generator = serialization.deserialize(generator)
        agent_class = serialization.deserialize(agent_class, globs=globals())
        topology = generator(n=N)
        super().__init__(topology=topology, N=N, **kwargs)
        self.grid = MultiGrid(width, height, False)

        self.populate_network(agent_class=agent_class)

        # Create agents
        for agent in self.agents:
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(agent, (x, y))

        self.datacollector = DataCollector(
            model_reporters={"Gini": compute_gini}, agent_reporters={"Wealth": "wealth"}
        )


if __name__ == "__main__":

    fixed_params = {
        "generator": nx.complete_graph,
        "width": 10,
        "network_agents": [{"agent_class": SocialMoneyAgent, "weight": 1}],
        "height": 10,
    }

    variable_params = {"N": range(10, 100, 10)}

    batch_run = BatchRunner(
        MoneyEnv,
        variable_parameters=variable_params,
        fixed_parameters=fixed_params,
        iterations=5,
        max_steps=100,
        model_reporters={"Gini": compute_gini},
    )
    batch_run.run_all()

    run_data = batch_run.get_model_vars_dataframe()
    run_data.head()
    print(run_data.Gini)
