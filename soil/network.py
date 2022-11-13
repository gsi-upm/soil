from __future__ import annotations

from typing import Dict
import os
import sys
import random

import networkx as nx

from . import config, serialization, basestring


def from_config(cfg: config.NetConfig, dir_path: str = None):
    if not isinstance(cfg, config.NetConfig):
        cfg = config.NetConfig(**cfg)

    if cfg.path:
        path = cfg.path
        if dir_path and not os.path.isabs(path):
            path = os.path.join(dir_path, path)
        extension = os.path.splitext(path)[1][1:]
        kwargs = {}
        if extension == "gexf":
            kwargs["version"] = "1.2draft"
            kwargs["node_type"] = int
        try:
            method = getattr(nx.readwrite, "read_" + extension)
        except AttributeError:
            raise AttributeError("Unknown format")
        return method(path, **kwargs)

    if cfg.params:
        net_args = dict(cfg.params)
        net_gen = net_args.pop("generator")

        if dir_path not in sys.path:
            sys.path.append(dir_path)

        method = serialization.deserializer(
            net_gen,
            known_modules=[
                "networkx.generators",
            ],
        )
        return method(**net_args)

    if isinstance(cfg.fixed, config.Topology):
        cfg = cfg.fixed.dict()

    if isinstance(cfg, str) or isinstance(cfg, dict):
        return nx.json_graph.node_link_graph(cfg)

    return nx.Graph()


def find_unassigned(G, shuffle=False, random=random):
    """
    Link an agent to a node in a topology.

    If node_id is None, a node without an agent_id will be found.
    """
    candidates = list(G.nodes(data=True))
    if shuffle:
        random.shuffle(candidates)
    for next_id, data in candidates:
        if "agent" not in data:
            return next_id
    return None


def dump_gexf(G, f):
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

    nx.write_gexf(G, f, version="1.2draft")
