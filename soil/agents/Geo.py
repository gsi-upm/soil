from scipy.spatial import cKDTree as KDTree
import networkx as nx
from . import NetworkAgent


class Geo(NetworkAgent):
    """In this type of network, nodes have a "pos" attribute."""

    def geo_search(self, radius, center=False, **kwargs):
        """Get a list of nodes whose coordinates are closer than *radius* to *node*."""
        node = self.node_id

        G = self.subgraph(**kwargs)

        pos = nx.get_node_attributes(G, "pos")
        if not pos:
            return []
        nodes, coords = list(zip(*pos.items()))
        kdtree = KDTree(coords)  # Cannot provide generator.
        indices = kdtree.query_ball_point(pos[node], radius)
        return [nodes[i] for i in indices if center or (nodes[i] != node)]