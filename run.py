import argparse
from server import ModularServer
from visualization import GraphVisualization, Model


def run(model, name="SOIL Model", verbose=False, params=None):
    graphVisualization = GraphVisualization(params)
    server = ModularServer(model, graphVisualization, name=(name[0] if isinstance(name, list) else name), verbose=verbose)
    server.port = 8001
    server.launch()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Visualization of a Graph Model')

    parser.add_argument('--name', '-n', nargs=1, default='SOIL Model', help='name of the simulation')
    parser.add_argument('--dump', '-d', help='dumping results in folder output', action='store_true')
    parser.add_argument('--verbose', '-v', help='verbose mode', action='store_true')
    args = parser.parse_args()

    soil = Model(dump=args.dump)
    run(soil, name=args.name, verbose=args.verbose)
