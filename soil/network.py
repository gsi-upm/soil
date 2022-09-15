from typing import Dict
import os
import sys

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
