import argparse
from server import ModularServer
from simulator import Simulator


def run(simulator, name="SOIL", port=8001, verbose=False):
    server = ModularServer(simulator, name=(name[0] if isinstance(name, list) else name), verbose=verbose)
    server.port = port
    server.launch()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Visualization of a Graph Model')

    parser.add_argument('--name', '-n', nargs=1, default='SOIL', help='name of the simulation')
    parser.add_argument('--dump', '-d', help='dumping results in folder output', action='store_true')
    parser.add_argument('--port', '-p', nargs=1, default=8001, help='port for launching the server')
    parser.add_argument('--verbose', '-v', help='verbose mode', action='store_true')
    args = parser.parse_args()

    soil = Simulator(dump=args.dump)
    run(soil, name=args.name, port=(args.port[0] if isinstance(args.port, list) else args.port), verbose=args.verbose)
