import io
import threading
import asyncio
import logging
import networkx as nx
import os
import sys
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.escape
import tornado.gen
import yaml
import webbrowser
from contextlib import contextmanager
from time import sleep
from xml.etree.ElementTree import tostring

from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

from ..simulation import Simulation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ROOT = os.path.abspath(os.path.dirname(__file__))

MAX_WORKERS = 4
LOGGING_INTERVAL = 0.5

# Workaround to let Soil load the required modules
sys.path.append(ROOT)


class PageHandler(tornado.web.RequestHandler):
    """Handler for the HTML template which holds the visualization."""

    def get(self):
        self.render(
            "index.html", port=self.application.port, name=self.application.name
        )


class SocketHandler(tornado.websocket.WebSocketHandler):
    """Handler for websocket."""

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def open(self):
        if self.application.verbose:
            logger.info("Socket opened!")

    def check_origin(self, origin):
        return True

    def on_message(self, message):
        """Receiving a message from the websocket, parse, and act accordingly."""

        msg = tornado.escape.json_decode(message)

        if msg["type"] == "config_file":

            if self.application.verbose:
                print(msg["data"])

            self.config = list(yaml.load_all(msg["data"]))

            if len(self.config) > 1:
                error = "Please, provide only one configuration."
                if self.application.verbose:
                    logger.error(error)
                self.write_message({"type": "error", "error": error})
                return

            self.config = self.config[0]
            self.send_log(
                "INFO." + self.simulation_name,
                "Using config: {name}".format(name=self.config["name"]),
            )

            if "visualization_params" in self.config:
                self.write_message(
                    {
                        "type": "visualization_params",
                        "data": self.config["visualization_params"],
                    }
                )
            self.name = self.config["name"]
            self.run_simulation()

            settings = []
            for key in self.config["environment_params"]:
                if (
                    type(self.config["environment_params"][key]) == float
                    or type(self.config["environment_params"][key]) == int
                ):
                    if self.config["environment_params"][key] <= 1:
                        setting_type = "number"
                    else:
                        setting_type = "great_number"
                elif type(self.config["environment_params"][key]) == bool:
                    setting_type = "boolean"
                else:
                    setting_type = "undefined"

                settings.append(
                    {
                        "label": key,
                        "type": setting_type,
                        "value": self.config["environment_params"][key],
                    }
                )

            self.write_message({"type": "settings", "data": settings})

        elif msg["type"] == "get_trial":
            if self.application.verbose:
                logger.info("Trial {} requested!".format(msg["data"]))
            self.send_log("INFO." + __name__, "Trial {} requested!".format(msg["data"]))
            self.write_message(
                {"type": "get_trial", "data": self.get_trial(int(msg["data"]))}
            )

        elif msg["type"] == "run_simulation":
            if self.application.verbose:
                logger.info(
                    "Running new simulation for {name}".format(name=self.config["name"])
                )
            self.send_log(
                "INFO." + self.simulation_name,
                "Running new simulation for {name}".format(name=self.config["name"]),
            )
            self.config["environment_params"] = msg["data"]
            self.run_simulation()

        elif msg["type"] == "download_gexf":
            G = self.trials[int(msg["data"])].history_to_graph()
            for node in G.nodes():
                if "pos" in G.nodes[node]:
                    G.nodes[node]["viz"] = {
                        "position": {
                            "x": G.nodes[node]["pos"][0],
                            "y": G.nodes[node]["pos"][1],
                            "z": 0.0,
                        }
                    }
                    del G.nodes[node]["pos"]
            writer = nx.readwrite.gexf.GEXFWriter(version="1.2draft")
            writer.add_graph(G)
            self.write_message(
                {
                    "type": "download_gexf",
                    "filename": self.config["name"] + "_trial_" + str(msg["data"]),
                    "data": tostring(writer.xml).decode(writer.encoding),
                }
            )

        elif msg["type"] == "download_json":
            G = self.trials[int(msg["data"])].history_to_graph()
            for node in G.nodes():
                if "pos" in G.nodes[node]:
                    G.nodes[node]["viz"] = {
                        "position": {
                            "x": G.nodes[node]["pos"][0],
                            "y": G.nodes[node]["pos"][1],
                            "z": 0.0,
                        }
                    }
                    del G.nodes[node]["pos"]
            self.write_message(
                {
                    "type": "download_json",
                    "filename": self.config["name"] + "_trial_" + str(msg["data"]),
                    "data": nx.node_link_data(G),
                }
            )

        else:
            if self.application.verbose:
                logger.info("Unexpected message!")

    def update_logging(self):
        try:
            if (
                not self.log_capture_string.closed
                and self.log_capture_string.getvalue()
            ):
                for i in range(len(self.log_capture_string.getvalue().split("\n")) - 1):
                    self.send_log(
                        "INFO." + self.simulation_name,
                        self.log_capture_string.getvalue().split("\n")[i],
                    )
                self.log_capture_string.truncate(0)
                self.log_capture_string.seek(0)
        finally:
            if self.capture_logging:
                tornado.ioloop.IOLoop.current().call_later(
                    LOGGING_INTERVAL, self.update_logging
                )

    def on_close(self):
        if self.application.verbose:
            logger.info("Socket closed!")

    def send_log(self, logger, logging):
        self.write_message({"type": "log", "logger": logger, "logging": logging})

    @property
    def simulation_name(self):
        return self.config.get("name", "NoSimulationRunning")

    @run_on_executor
    def nonblocking(self, config):
        simulation = Simulation(**config)
        return simulation.run()

    @tornado.gen.coroutine
    def run_simulation(self):
        # Run simulation and capture logs
        logger.info("Running simulation!")
        if "visualization_params" in self.config:
            del self.config["visualization_params"]
        with self.logging(self.simulation_name):
            try:
                config = dict(**self.config)
                config["outdir"] = os.path.join(self.application.outdir, config["name"])
                config["dump"] = self.application.dump
                self.trials = yield self.nonblocking(config)

                self.write_message(
                    {
                        "type": "trials",
                        "data": list(trial.name for trial in self.trials),
                    }
                )
            except Exception as ex:
                error = "Something went wrong:\n\t{}".format(ex)
                logging.info(error)
                self.write_message({"type": "error", "error": error})
                self.send_log("ERROR." + self.simulation_name, error)

    def get_trial(self, trial):
        logger.info("Available trials: %s " % len(self.trials))
        logger.info("Ask for : %s" % trial)
        trial = self.trials[trial]
        G = trial.history_to_graph()
        return nx.node_link_data(G)

    @contextmanager
    def logging(self, logger):
        self.capture_logging = True
        self.logger_application = logging.getLogger(logger)
        self.log_capture_string = io.StringIO()
        ch = logging.StreamHandler(self.log_capture_string)
        self.logger_application.addHandler(ch)
        self.update_logging()
        yield self.capture_logging

        sleep(0.2)
        self.log_capture_string.close()
        self.logger_application.removeHandler(ch)
        self.capture_logging = False
        return self.capture_logging


class ModularServer(tornado.web.Application):
    """Main visualization application."""

    port = 8001
    page_handler = (r"/", PageHandler)
    socket_handler = (r"/ws", SocketHandler)
    static_handler = (
        r"/(.*)",
        tornado.web.StaticFileHandler,
        {"path": os.path.join(ROOT, "static")},
    )
    local_handler = (r"/local/(.*)", tornado.web.StaticFileHandler, {"path": ""})

    handlers = [page_handler, socket_handler, static_handler, local_handler]
    settings = {"debug": True, "template_path": ROOT + "/templates"}

    def __init__(
        self, dump=False, outdir="output", name="SOIL", verbose=True, *args, **kwargs
    ):

        self.verbose = verbose
        self.name = name
        self.dump = dump
        self.outdir = outdir

        # Initializing the application itself:
        super().__init__(self.handlers, **self.settings)

    def launch(self, port=None):
        """Run the app."""

        if port is not None:
            self.port = port
        url = "http://127.0.0.1:{PORT}".format(PORT=self.port)
        print("Interface starting at {url}".format(url=url))
        self.listen(self.port)
        # webbrowser.open(url)
        tornado.ioloop.IOLoop.instance().start()


def run(*args, **kwargs):
    asyncio.set_event_loop(asyncio.new_event_loop())
    server = ModularServer(*args, **kwargs)
    server.launch()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Visualization of a Graph Model")

    parser.add_argument(
        "--name", "-n", nargs=1, default="SOIL", help="name of the simulation"
    )
    parser.add_argument(
        "--dump", "-d", help="dumping results in folder output", action="store_true"
    )
    parser.add_argument(
        "--port", "-p", nargs=1, default=8001, help="port for launching the server"
    )
    parser.add_argument("--verbose", "-v", help="verbose mode", action="store_true")
    args = parser.parse_args()

    run(
        name=args.name,
        port=(args.port[0] if isinstance(args.port, list) else args.port),
        verbose=args.verbose,
    )
