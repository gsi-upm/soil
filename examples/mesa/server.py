from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import Slider, Choice
from mesa.visualization.modules import ChartModule, NetworkModule, CanvasGrid
from social_wealth import MoneyEnv, graph_generator, SocialMoneyAgent
import networkx as nx


class MyNetwork(NetworkModule):
    def render(self, model):
        return self.portrayal_method(model)


def network_portrayal(env):
    # The model ensures there is 0 or 1 agent per node

    portrayal = dict()
    wealths = {
        node_id: data["agent"].wealth for (node_id, data) in env.G.nodes(data=True)
    }
    portrayal["nodes"] = [
        {
            "id": node_id,
            "size": 2 * (wealth + 1),
            "color": "#CC0000" if wealth == 0 else "#007959",
            # "color": "#CC0000",
            "label": f"{node_id}: {wealth}",
        }
        for (node_id, wealth) in wealths.items()
    ]

    portrayal["edges"] = [
        {"id": edge_id, "source": source, "target": target, "color": "#000000"}
        for edge_id, (source, target) in enumerate(env.G.edges)
    ]

    return portrayal


def gridPortrayal(agent):
    """
    This function is registered with the visualization server to be called
    each tick to indicate how to draw the agent in its current state.
    :param agent:  the agent in the simulation
    :return: the portrayal dictionary
    """
    color = max(10, min(agent.wealth * 10, 100))
    return {
        "Shape": "rect",
        "w": 1,
        "h": 1,
        "Filled": "true",
        "Layer": 0,
        "Label": agent.unique_id,
        "Text": agent.unique_id,
        "x": agent.pos[0],
        "y": agent.pos[1],
        "Color": f"rgba(31, 10, 255, 0.{color})",
    }


grid = MyNetwork(network_portrayal, 500, 500)
chart = ChartModule(
    [{"Label": "Gini", "Color": "Black"}], data_collector_name="datacollector"
)

parameters = {
    "N": Slider(
        "N",
        5,
        1,
        10,
        1,
        description="Choose how many agents to include in the model",
    ),
    "height": Slider(
        "height",
        5,
        5,
        10,
        1,
        description="Grid height",
    ),
    "width": Slider(
        "width",
        5,
        5,
        10,
        1,
        description="Grid width",
    ),
    "agent_class": Choice(
        "Agent class",
        value="MoneyAgent",
        choices=["MoneyAgent", "SocialMoneyAgent"],
    ),
    "generator": graph_generator,
}


canvas_element = CanvasGrid(
    gridPortrayal, parameters["width"].value, parameters["height"].value, 500, 500
)


server = ModularServer(
    MoneyEnv, [grid, chart, canvas_element], "Money Model", parameters
)
server.port = 8521

if __name__ == '__main__':
    server.launch(open_browser=False)
