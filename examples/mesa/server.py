from mesa.visualization.ModularVisualization import ModularServer
from soil.visualization import UserSettableParameter
from mesa.visualization.modules import ChartModule, NetworkModule, CanvasGrid
from social_wealth import MoneyEnv, graph_generator, SocialMoneyAgent


class MyNetwork(NetworkModule):
    def render(self, model):
        return self.portrayal_method(model)


def network_portrayal(env):
    # The model ensures there is 0 or 1 agent per node

    portrayal = dict()
    portrayal["nodes"] = [
        {
            "id": agent_id,
            "size": env.get_agent(agent_id).wealth,
            # "color": "#CC0000" if not agents or agents[0].wealth == 0 else "#007959",
            "color": "#CC0000",
            "label": f"{agent_id}: {env.get_agent(agent_id).wealth}",
        }
        for (agent_id) in env.G.nodes
    ]
    # import pdb;pdb.set_trace()

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
    color = max(10, min(agent.wealth*10, 100))
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
        "Color": f"rgba(31, 10, 255, 0.{color})"
    }


grid = MyNetwork(network_portrayal, 500, 500, library="sigma")
chart = ChartModule(
    [{"Label": "Gini", "Color": "Black"}], data_collector_name="datacollector"
)

model_params = {
    "N": UserSettableParameter(
        "slider",
        "N",
        1,
        1,
        10,
        1,
        description="Choose how many agents to include in the model",
    ),
    "network_agents": [{"agent_type": SocialMoneyAgent}],
    "height": UserSettableParameter(
        "slider",
        "height",
        5,
        5,
        10,
        1,
        description="Grid height",
        ),
    "width": UserSettableParameter(
        "slider",
        "width",
        5,
        5,
        10,
        1,
        description="Grid width",
        ),
    "network_params": {
        'generator': graph_generator
    },
}

canvas_element = CanvasGrid(gridPortrayal, model_params["width"].value, model_params["height"].value, 500, 500)


server = ModularServer(
    MoneyEnv, [grid, chart, canvas_element], "Money Model", model_params
)
server.port = 8521

server.launch(open_browser=False)
