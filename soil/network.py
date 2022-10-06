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
        if extension == 'gexf':
            kwargs['version'] = '1.2draft'
            kwargs['node_type'] = int
        try:
            method = getattr(nx.readwrite, 'read_' + extension)
        except AttributeError:
            raise AttributeError('Unknown format')
        return method(path, **kwargs)

    if cfg.params:
        net_args = cfg.params.dict()
        net_gen = net_args.pop('generator')

        if dir_path not in sys.path:
            sys.path.append(dir_path)

        method = serialization.deserializer(net_gen,
                                            known_modules=['networkx.generators',])
        return method(**net_args)

    if isinstance(cfg.topology, basestring) or isinstance(cfg.topology, dict):
        return nx.json_graph.node_link_graph(cfg.topology)

    return nx.Graph()


def agent_to_node(G, agent_id, node_id=None, shuffle=False, random=random):
    '''
    Link an agent to a node in a topology.

    If node_id is None, a node without an agent_id will be found.
    '''
    #TODO: test
    if node_id is None:
        candidates = list(G.nodes(data=True))
        if shuffle:
            random.shuffle(candidates)
        for next_id, data in candidates:
            if data.get('agent_id', None) is None:
                node_id = next_id
                data['agent_id'] = agent_id
                break

    if node_id is None:
        raise ValueError(f"Not enough nodes in topology to assign one to agent {agent_id}")
    return node_id
