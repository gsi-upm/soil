from . import BaseAgent


class NetworkAgent(BaseAgent):
    def __init__(self, *args, topology=None, init=True, node_id=None, **kwargs):
        super().__init__(*args, init=False, **kwargs)

        self.G = topology or self.model.G
        assert self.G is not None, "Network agents should have a network"
        if node_id is None:
            nodes = self.random.choices(list(self.G.nodes), k=len(self.G))
            for n_id in nodes:
                if "agent" not in self.G.nodes[n_id] or self.G.nodes[n_id]["agent"] is None:
                    node_id = n_id
                    break
            else:
                node_id = len(self.G)
                self.info(f"All nodes ({len(self.G)}) have an agent assigned, adding a new node to the graph for agent {self.unique_id}")
                self.G.add_node(node_id)
        assert node_id is not None
        self.G.nodes[node_id]["agent"] = self
        self.node_id = node_id
        if init:
            self.init()

    def count_neighbors(self, state_id=None, **kwargs):
        return len(self.get_neighbors(state_id=state_id, **kwargs))

    def iter_neighbors(self, **kwargs):
        return self.iter_agents(limit_neighbors=True, **kwargs)

    def get_neighbors(self, **kwargs):
        return list(self.iter_neighbors(**kwargs))

    @property
    def node(self):
        return self.G.nodes[self.node_id]

    def iter_agents(self, unique_id=None, *, limit_neighbors=False, **kwargs):
        unique_ids = None
        if unique_ids is not None:
            try:
                unique_ids = set(unique_id)
            except TypeError:
                unique_ids = set([unique_id])

        if limit_neighbors:
            neighbor_ids = set()
            for node_id in self.G.neighbors(self.node_id):
                agent = self.G.nodes[node_id].get("agent")
                if agent is not None:
                    neighbor_ids.add(agent.unique_id)
            if unique_ids:
                unique_ids = unique_ids & neighbor_ids
            else:
                unique_ids = neighbor_ids
            if not unique_ids:
                return
            unique_ids = list(unique_ids)
        yield from super().iter_agents(unique_id=unique_ids, **kwargs)

    def subgraph(self, center=True, **kwargs):
        include = [self] if center else []
        G = self.G.subgraph(
            n.node_id for n in list(self.get_agents(**kwargs) + include)
        )
        return G

    def remove_node(self):
        self.debug(f"Removing node for {self.unique_id}: {self.node_id}")
        self.G.remove_node(self.node_id)
        self.node_id = None

    def add_edge(self, other, edge_attr_dict=None, *edge_attrs):
        if self.node_id not in self.G.nodes(data=False):
            raise ValueError(
                "{} not in list of existing agents in the network".format(
                    self.unique_id
                )
            )
        if other.node_id not in self.G.nodes(data=False):
            raise ValueError(
                "{} not in list of existing agents in the network".format(other)
            )

        self.G.add_edge(
            self.node_id, other.node_id, edge_attr_dict=edge_attr_dict, *edge_attrs
        )

    def die(self, remove=True):
        if not self.alive:
            return None
        if remove:
            self.remove_node()
        return super().die()


NetAgent = NetworkAgent
