import networkx as nx
from soil.agents import Geo, NetworkAgent, FSM, custom, state, default_state
from soil import Environment, Simulation
from soil.parameters import *


class TerroristEnvironment(Environment):
    n: Integer = 100
    radius: Float = 0.2

    information_spread_intensity: probability = 0.7
    terrorist_additional_influence: probability = 0.03
    terrorist_additional_influence: probability = 0.035
    max_vulnerability: probability = 0.7
    prob_interaction: probability = 0.5

    # TrainingAreaModel and HavenModel
    training_influence: probability = 0.20
    haven_influence: probability = 0.20

    # TerroristNetworkModel
    vision_range: Float = 0.30
    sphere_influence: Integer = 2
    weight_social_distance: Float = 0.035
    weight_link_distance: Float = 0.035

    ratio_civil: probability = 0.8
    ratio_leader: probability = 0.1
    ratio_training: probability = 0.05
    ratio_haven: probability = 0.05

    def init(self):
        self.create_network(generator=self.generator, n=self.n, radius=self.radius)
        self.populate_network([
            TerroristNetworkModel.w(state_id='civilian'),
            TerroristNetworkModel.w(state_id='leader'),
            TrainingAreaModel,
            HavenModel
        ], [self.ratio_civil, self.ratio_leader, self.ratio_training, self.ratio_haven])

    @staticmethod
    def generator(*args, **kwargs):
        return nx.random_geometric_graph(*args, **kwargs)

class TerroristSpreadModel(FSM, Geo):
    """
    Settings:
        information_spread_intensity

        terrorist_additional_influence

        min_vulnerability (optional else zero)

        max_vulnerability
    """

    information_spread_intensity = 0.1
    terrorist_additional_influence = 0.1
    min_vulnerability = 0
    max_vulnerability = 1

    def init(self):
        if self.state_id == self.civilian.id:  # Civilian
            self.mean_belief = self.model.random.uniform(0.00, 0.5)
        elif self.state_id == self.terrorist.id:  # Terrorist
            self.mean_belief = self.random.uniform(0.8, 1.00)
        elif self.state_id == self.leader.id:  # Leader
            self.mean_belief = 1.00
        else:
            raise Exception("Invalid state id: {}".format(self["id"]))

        self.vulnerability = self.random.uniform(
            self.get("min_vulnerability", 0), self.get("max_vulnerability", 1)
        )

    @default_state
    @state
    def civilian(self):
        neighbours = list(self.get_neighbors(agent_class=TerroristSpreadModel))
        if len(neighbours) > 0:
            # Only interact with some of the neighbors
            interactions = list(
                n for n in neighbours if self.random.random() <= self.model.prob_interaction
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
        leaders = list(filter(lambda x: x.state_id == self.leader.id, neighbours))
        if not leaders:
            # Check if this is the potential leader
            # Stop once it's found. Otherwise, set self as leader
            for neighbour in neighbours:
                if self.betweenness(self) < self.betweenness(neighbour):
                    return
            return self.leader

    def ego_search(self, steps=1, center=False, agent=None, **kwargs):
        """Get a list of nodes in the ego network of *node* of radius *steps*"""
        node = agent.node_id
        G = self.subgraph(**kwargs)
        return nx.ego_graph(G, node, center=center, radius=steps).nodes()

    def degree(self, agent, force=False):
        if (
            force
            or (not hasattr(self.model, "_degree"))
            or getattr(self.model, "_last_step", 0) < self.now
        ):
            self.model._degree = nx.degree_centrality(self.G)
            self.model._last_step = self.now
        return self.model._degree[agent.node_id]

    def betweenness(self, agent, force=False):
        if (
            force
            or (not hasattr(self.model, "_betweenness"))
            or getattr(self.model, "_last_step", 0) < self.now
        ):
            self.model._betweenness = nx.betweenness_centrality(self.G)
            self.model._last_step = self.now
        return self.model._betweenness[agent.node_id]


class TrainingAreaModel(FSM, Geo):
    """
    Settings:
        training_influence

        min_vulnerability

    Requires TerroristSpreadModel.
    """

    training_influence = 0.1
    min_vulnerability = 0

    def init(self):
        self.mean_believe = 1
        self.vulnerability = 0

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

    min_vulnerability = 0
    haven_influence = 0.1
    max_vulnerability = 0.5

    def init(self):
        self.mean_believe = 0
        self.vulnerability = 0

    def get_occupants(self, **kwargs):
        return self.get_neighbors(agent_class=TerroristSpreadModel,
                                  **kwargs)

    @default_state
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

    sphere_influence: float = 1
    vision_range: float = 1
    weight_social_distance: float = 0.5
    weight_link_distance: float = 0.2

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


sim = Simulation(
    model=TerroristEnvironment,
    num_trials=1,
    name="TerroristNetworkModel_sim",
    max_steps=150,
    skip_test=False,
    dump=False,
)

# TODO: integrate visualization
# visualization_params:
#   # Icons downloaded from https://www.iconfinder.com/
#   shape_property: agent
#   shapes:
#     TrainingAreaModel: target
#     HavenModel: home
#     TerroristNetworkModel: person
#   colors:
#     - attr_id: civilian
#       color: '#40de40'
#     - attr_id: terrorist
#       color: red
#     - attr_id: leader
#       color: '#c16a6a'
#   background_image: 'map_4800x2860.jpg'
#   background_opacity: '0.9'
#   background_filter_color: 'blue'