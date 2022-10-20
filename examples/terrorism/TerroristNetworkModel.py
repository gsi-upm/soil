import networkx as nx
from soil.agents import Geo, NetworkAgent, FSM, state, default_state
from soil import Environment


class TerroristSpreadModel(FSM, Geo):
    """
    Settings:
        information_spread_intensity

        terrorist_additional_influence

        min_vulnerability (optional else zero)

        max_vulnerability

        prob_interaction
    """

    def __init__(self, model=None, unique_id=0, state=()):
        super().__init__(model=model, unique_id=unique_id, state=state)

        self.information_spread_intensity = model.environment_params[
            "information_spread_intensity"
        ]
        self.terrorist_additional_influence = model.environment_params[
            "terrorist_additional_influence"
        ]
        self.prob_interaction = model.environment_params["prob_interaction"]

        if self["id"] == self.civilian.id:  # Civilian
            self.mean_belief = self.random.uniform(0.00, 0.5)
        elif self["id"] == self.terrorist.id:  # Terrorist
            self.mean_belief = self.random.uniform(0.8, 1.00)
        elif self["id"] == self.leader.id:  # Leader
            self.mean_belief = 1.00
        else:
            raise Exception("Invalid state id: {}".format(self["id"]))

        if "min_vulnerability" in model.environment_params:
            self.vulnerability = self.random.uniform(
                model.environment_params["min_vulnerability"],
                model.environment_params["max_vulnerability"],
            )
        else:
            self.vulnerability = self.random.uniform(
                0, model.environment_params["max_vulnerability"]
            )

    @state
    def civilian(self):
        neighbours = list(self.get_neighbors(agent_class=TerroristSpreadModel))
        if len(neighbours) > 0:
            # Only interact with some of the neighbors
            interactions = list(
                n for n in neighbours if self.random.random() <= self.prob_interaction
            )
            influence = sum(self.degree(i) for i in interactions)
            mean_belief = sum(
                i.mean_belief * self.degree(i) / influence for i in interactions
            )
            mean_belief = (
                mean_belief * self.information_spread_intensity
                + self.mean_belief * (1 - self.information_spread_intensity)
            )
            self.mean_belief = mean_belief * self.vulnerability + self.mean_belief * (
                1 - self.vulnerability
            )

        if self.mean_belief >= 0.8:
            return self.terrorist

    @state
    def leader(self):
        self.mean_belief = self.mean_belief ** (1 - self.terrorist_additional_influence)
        for neighbour in self.get_neighbors(
            state_id=[self.terrorist.id, self.leader.id]
        ):
            if self.betweenness(neighbour) > self.betweenness(self):
                return self.terrorist

    @state
    def terrorist(self):
        neighbours = self.get_agents(
            state_id=[self.terrorist.id, self.leader.id],
            agent_class=TerroristSpreadModel,
            limit_neighbors=True,
        )
        if len(neighbours) > 0:
            influence = sum(self.degree(n) for n in neighbours)
            mean_belief = sum(
                n.mean_belief * self.degree(n) / influence for n in neighbours
            )
            mean_belief = mean_belief * self.vulnerability + self.mean_belief * (
                1 - self.vulnerability
            )
            self.mean_belief = self.mean_belief ** (
                1 - self.terrorist_additional_influence
            )

        # Check if there are any leaders in the group
        leaders = list(filter(lambda x: x.state.id == self.leader.id, neighbours))
        if not leaders:
            # Check if this is the potential leader
            # Stop once it's found. Otherwise, set self as leader
            for neighbour in neighbours:
                if self.betweenness(self) < self.betweenness(neighbour):
                    return
            return self.leader

    def ego_search(self, steps=1, center=False, node=None, **kwargs):
        """Get a list of nodes in the ego network of *node* of radius *steps*"""
        node = as_node(node if node is not None else self)
        G = self.subgraph(**kwargs)
        return nx.ego_graph(G, node, center=center, radius=steps).nodes()

    def degree(self, node, force=False):
        node = as_node(node)
        if (
            force
            or (not hasattr(self.model, "_degree"))
            or getattr(self.model, "_last_step", 0) < self.now
        ):
            self.model._degree = nx.degree_centrality(self.G)
            self.model._last_step = self.now
        return self.model._degree[node]

    def betweenness(self, node, force=False):
        node = as_node(node)
        if (
            force
            or (not hasattr(self.model, "_betweenness"))
            or getattr(self.model, "_last_step", 0) < self.now
        ):
            self.model._betweenness = nx.betweenness_centrality(self.G)
            self.model._last_step = self.now
        return self.model._betweenness[node]


class TrainingAreaModel(FSM, Geo):
    """
    Settings:
        training_influence

        min_vulnerability

    Requires TerroristSpreadModel.
    """

    def __init__(self, model=None, unique_id=0, state=()):
        super().__init__(model=model, unique_id=unique_id, state=state)
        self.training_influence = model.environment_params["training_influence"]
        if "min_vulnerability" in model.environment_params:
            self.min_vulnerability = model.environment_params["min_vulnerability"]
        else:
            self.min_vulnerability = 0

    @default_state
    @state
    def terrorist(self):
        for neighbour in self.get_neighbors(agent_class=TerroristSpreadModel):
            if neighbour.vulnerability > self.min_vulnerability:
                neighbour.vulnerability = neighbour.vulnerability ** (
                    1 - self.training_influence
                )


class HavenModel(FSM, Geo):
    """
    Settings:
        haven_influence

        min_vulnerability

        max_vulnerability

    Requires TerroristSpreadModel.
    """

    def __init__(self, model=None, unique_id=0, state=()):
        super().__init__(model=model, unique_id=unique_id, state=state)
        self.haven_influence = model.environment_params["haven_influence"]
        if "min_vulnerability" in model.environment_params:
            self.min_vulnerability = model.environment_params["min_vulnerability"]
        else:
            self.min_vulnerability = 0
        self.max_vulnerability = model.environment_params["max_vulnerability"]

    def get_occupants(self, **kwargs):
        return self.get_neighbors(agent_class=TerroristSpreadModel, **kwargs)

    @state
    def civilian(self):
        civilians = self.get_occupants(state_id=self.civilian.id)
        if not civilians:
            return self.terrorist

        for neighbour in self.get_occupants():
            if neighbour.vulnerability > self.min_vulnerability:
                neighbour.vulnerability = neighbour.vulnerability * (
                    1 - self.haven_influence
                )
        return self.civilian

    @state
    def terrorist(self):
        for neighbour in self.get_occupants():
            if neighbour.vulnerability < self.max_vulnerability:
                neighbour.vulnerability = neighbour.vulnerability ** (
                    1 - self.haven_influence
                )
        return self.terrorist


class TerroristNetworkModel(TerroristSpreadModel):
    """
    Settings:
        sphere_influence

        vision_range

        weight_social_distance

        weight_link_distance
    """

    def __init__(self, model=None, unique_id=0, state=()):
        super().__init__(model=model, unique_id=unique_id, state=state)

        self.vision_range = model.environment_params["vision_range"]
        self.sphere_influence = model.environment_params["sphere_influence"]
        self.weight_social_distance = model.environment_params["weight_social_distance"]
        self.weight_link_distance = model.environment_params["weight_link_distance"]

    @state
    def terrorist(self):
        self.update_relationships()
        return super().terrorist()

    @state
    def leader(self):
        self.update_relationships()
        return super().leader()

    def update_relationships(self):
        if self.count_neighbors(state_id=self.civilian.id) == 0:
            close_ups = set(
                self.geo_search(
                    radius=self.vision_range, agent_class=TerroristNetworkModel
                )
            )
            step_neighbours = set(
                self.ego_search(
                    self.sphere_influence,
                    agent_class=TerroristNetworkModel,
                    center=False,
                )
            )
            neighbours = set(
                agent.id
                for agent in self.get_neighbors(agent_class=TerroristNetworkModel)
            )
            search = (close_ups | step_neighbours) - neighbours
            for agent in self.get_agents(search):
                social_distance = 1 / self.shortest_path_length(agent.id)
                spatial_proximity = 1 - self.get_distance(agent.id)
                prob_new_interaction = (
                    self.weight_social_distance * social_distance
                    + self.weight_link_distance * spatial_proximity
                )
                if (
                    agent["id"] == agent.civilian.id
                    and self.random.random() < prob_new_interaction
                ):
                    self.add_edge(agent)
                    break

    def get_distance(self, target):
        source_x, source_y = nx.get_node_attributes(self.G, "pos")[self.id]
        target_x, target_y = nx.get_node_attributes(self.G, "pos")[target]
        dx = abs(source_x - target_x)
        dy = abs(source_y - target_y)
        return (dx**2 + dy**2) ** (1 / 2)

    def shortest_path_length(self, target):
        try:
            return nx.shortest_path_length(self.G, self.id, target)
        except nx.NetworkXNoPath:
            return float("inf")
