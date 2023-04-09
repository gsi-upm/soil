from __future__ import annotations

from typing import Dict
import os
import sys
import random

import networkx as nx

from . import config, serialization, basestring


def from_topology(topology, dir_path: str = None):
    if topology is None:
        return nx.Graph()
    if isinstance(topology, nx.Graph):
        return topology

    # If it's a dict, assume it's a node-link graph
    if isinstance(topology, dict):
        try:
            return nx.json_graph.node_link_graph(topology)
        except Exception as ex:
            raise ValueError("Unknown topology format")
    
    # Otherwise, treat like a path
    path = topology
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


def from_params(generator, dir_path: str = None, **params):

    if dir_path not in sys.path:
        sys.path.append(dir_path)

    method = serialization.deserializer(
        generator,
        known_modules=[
            "networkx.generators",
        ],
    )
    return method(**params)


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
