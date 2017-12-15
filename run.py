
from server import ModularServer
from visualization import GraphVisualization, Model


def run(model, params=None):
    graphVisualization = GraphVisualization(params)
    server = ModularServer(model, graphVisualization, name="SOIL Model")
    server.port = 8001
    server.launch()


if __name__ == "__main__":
    soil = Model(dump=False)
    run(soil)
