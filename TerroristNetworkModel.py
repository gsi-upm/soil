import random
import networkx as nx
from soil.agents import BaseAgent, FSM, state, default_state
from scipy.spatial import cKDTree as KDTree

global betweenness_centrality_global
global degree_centrality_global

betweenness_centrality_global = None
degree_centrality_global = None

class TerroristSpreadModel(FSM):
    """
    Settings:
        information_spread_intensity

        terrorist_additional_influence

        min_vulnerability (optional else zero)

        max_vulnerability

        prob_interaction
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        global betweenness_centrality_global
        global degree_centrality_global
        
        if betweenness_centrality_global == None:
            betweenness_centrality_global = nx.betweenness_centrality(self.global_topology)
        if degree_centrality_global == None:
            degree_centrality_global = nx.degree_centrality(self.global_topology)

        self.information_spread_intensity = environment.environment_params['information_spread_intensity']
        self.terrorist_additional_influence = environment.environment_params['terrorist_additional_influence']
        self.prob_interaction = environment.environment_params['prob_interaction']

        if self['id'] == self.civilian.id:       # Civilian
            self.initial_belief = random.uniform(0.00, 0.5)
        elif self['id'] == self.terrorist.id:     # Terrorist
            self.initial_belief = random.uniform(0.8, 1.00)
        elif self['id'] == self.leader.id:     # Leader
            self.initial_belief = 1.00
        else:
            raise Exception('Invalid state id: {}'.format(self['id']))

        if 'min_vulnerability' in environment.environment_params:
            self.vulnerability = random.uniform( environment.environment_params['min_vulnerability'], environment.environment_params['max_vulnerability'] )
        else :
            self.vulnerability = random.uniform( 0, environment.environment_params['max_vulnerability'] )

        self.mean_belief = self.initial_belief
        self.betweenness_centrality = betweenness_centrality_global[self.id]
        self.degree_centrality = degree_centrality_global[self.id]

        # self.state['radicalism'] = self.mean_belief

    def count_neighboring_agents(self, state_id=None):
        if isinstance(state_id, list):
            return len(self.get_neighboring_agents(state_id))
        else:
            return len(super().get_agents(state_id, limit_neighbors=True))

    def get_neighboring_agents(self, state_id=None):
        if isinstance(state_id, list):
            _list = []
            for i in state_id:
                _list += super().get_agents(i, limit_neighbors=True)
            return [ neighbour for neighbour in _list if isinstance(neighbour, TerroristSpreadModel) ]
        else:
            _list = super().get_agents(state_id, limit_neighbors=True) 
            return [ neighbour for neighbour in _list if isinstance(neighbour, TerroristSpreadModel) ]

    @state
    def civilian(self):
        if self.count_neighboring_agents() > 0:
            neighbours = []
            for neighbour in self.get_neighboring_agents():
                if random.random() < self.prob_interaction:
                    neighbours.append(neighbour)
            influence = sum( neighbour.degree_centrality for neighbour in neighbours )
            mean_belief = sum( neighbour.mean_belief * neighbour.degree_centrality / influence for neighbour in neighbours )
            self.initial_belief = self.mean_belief
            mean_belief = mean_belief * self.information_spread_intensity + self.initial_belief * ( 1 - self.information_spread_intensity )
            self.mean_belief = mean_belief * self.vulnerability + self.initial_belief * ( 1 - self.vulnerability )
        
        if self.mean_belief >= 0.8:
            return self.terrorist

    @state
    def leader(self):
        self.mean_belief = self.mean_belief ** ( 1 - self.terrorist_additional_influence )
        if self.count_neighboring_agents(state_id=[self.terrorist.id, self.leader.id]) > 0:
            for neighbour in self.get_neighboring_agents(state_id=[self.terrorist.id, self.leader.id]):
                if neighbour.betweenness_centrality > self.betweenness_centrality:
                    return self.terrorist

    @state
    def terrorist(self):
        if self.count_neighboring_agents(state_id=[self.terrorist.id, self.leader.id]) > 0:
            neighbours = self.get_neighboring_agents(state_id=[self.terrorist.id, self.leader.id])
            influence = sum( neighbour.degree_centrality for neighbour in neighbours )
            mean_belief = sum( neighbour.mean_belief * neighbour.degree_centrality / influence for neighbour in neighbours )
            self.initial_belief = self.mean_belief
            self.mean_belief = mean_belief * self.vulnerability + self.initial_belief * ( 1 - self.vulnerability )
            self.mean_belief = self.mean_belief ** ( 1 - self.terrorist_additional_influence )

        if self.count_neighboring_agents(state_id=self.leader.id) == 0 and self.count_neighboring_agents(state_id=self.terrorist.id) > 0:
            max_betweenness_centrality = self
            for neighbour in self.get_neighboring_agents(state_id=self.terrorist.id):
                if neighbour.betweenness_centrality > max_betweenness_centrality.betweenness_centrality:
                    max_betweenness_centrality = neighbour
            if max_betweenness_centrality == self:
                return self.leader

    def add_edge(self, G, source, target):
        G.add_edge(source.id, target.id, start=self.env._now)

    def link_search(self, G, node, radius):
        pos = nx.get_node_attributes(G, 'pos')
        nodes, coords = list(zip(*pos.items()))
        kdtree = KDTree(coords)  # Cannot provide generator.
        edge_indexes = kdtree.query_pairs(radius, 2)
        _list = [ edge[int(not edge.index(node))] for edge in edge_indexes if node in edge ]
        return [ G.nodes()[index]['agent'] for index in _list ]

    def social_search(self, G, node, steps):
        nodes = list(nx.ego_graph(G, node, radius=steps).nodes())
        nodes.remove(node)
        return [ G.nodes()[index]['agent'] for index in nodes ]


class TrainingAreaModel(FSM):
    """
    Settings:
        training_influence

        min_vulnerability

    Requires TerroristSpreadModel.
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.training_influence = environment.environment_params['training_influence']
        if 'min_vulnerability' in environment.environment_params:
            self.min_vulnerability = environment.environment_params['min_vulnerability']
        else: self.min_vulnerability = 0

    @default_state
    @state
    def terrorist(self):
        for neighbour in self.get_neighboring_agents():
            if isinstance(neighbour, TerroristSpreadModel) and neighbour.vulnerability > self.min_vulnerability:
                neighbour.vulnerability = neighbour.vulnerability ** ( 1 - self.training_influence )        


class HavenModel(FSM):
    """
    Settings:
        haven_influence

        min_vulnerability

        max_vulnerability

    Requires TerroristSpreadModel.
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.haven_influence = environment.environment_params['haven_influence']
        if 'min_vulnerability' in environment.environment_params:
            self.min_vulnerability = environment.environment_params['min_vulnerability']
        else: self.min_vulnerability = 0
        self.max_vulnerability = environment.environment_params['max_vulnerability']

    @state
    def civilian(self):
        for neighbour_agent in self.get_neighboring_agents():
            if isinstance(neighbour_agent, TerroristSpreadModel) and neighbour_agent['id'] == neighbour_agent.civilian.id:
                for neighbour in self.get_neighboring_agents():
                    if isinstance(neighbour, TerroristSpreadModel) and neighbour.vulnerability > self.min_vulnerability:
                        neighbour.vulnerability = neighbour.vulnerability * ( 1 - self.haven_influence )
                return self.civilian
        return self.terrorist

    @state
    def terrorist(self):
        for neighbour in self.get_neighboring_agents():
            if isinstance(neighbour, TerroristSpreadModel) and neighbour.vulnerability < self.max_vulnerability:
                neighbour.vulnerability = neighbour.vulnerability ** ( 1 - self.haven_influence )
        return self.terrorist

        
class TerroristNetworkModel(TerroristSpreadModel):
    """
    Settings:
        sphere_influence

        vision_range

        weight_social_distance

        weight_link_distance
    """

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.vision_range = environment.environment_params['vision_range']
        self.sphere_influence = environment.environment_params['sphere_influence']
        self.weight_social_distance = environment.environment_params['weight_social_distance']
        self.weight_link_distance = environment.environment_params['weight_link_distance']

    @state
    def terrorist(self):
        self.update_relationships()
        return super().terrorist()

    @state
    def leader(self):
        self.update_relationships()
        return super().leader()

    def update_relationships(self):
        if self.count_neighboring_agents(state_id=self.civilian.id) == 0:
            close_ups = self.link_search(self.global_topology, self.id, self.vision_range)
            step_neighbours = self.social_search(self.global_topology, self.id, self.sphere_influence)
            search = list(set(close_ups).union(step_neighbours))
            neighbours = self.get_neighboring_agents()
            search = [item for item in search if not item in neighbours and isinstance(item, TerroristNetworkModel)]
            for agent in search:
                social_distance = 1 / self.shortest_path_length(self.global_topology, self.id, agent.id)
                spatial_proximity = ( 1 - self.get_distance(self.global_topology, self.id, agent.id) )
                prob_new_interaction = self.weight_social_distance * social_distance + self.weight_link_distance * spatial_proximity
                if agent['id'] == agent.civilian.id and random.random() < prob_new_interaction:
                    self.add_edge(self.global_topology, self, agent)
                    break

    def get_distance(self, G, source, target):
        source_x, source_y = nx.get_node_attributes(G, 'pos')[source]
        target_x, target_y = nx.get_node_attributes(G, 'pos')[target]
        dx = abs( source_x - target_x )
        dy = abs( source_y - target_y )
        return ( dx ** 2 + dy ** 2 ) ** ( 1 / 2 )

    def shortest_path_length(self, G, source, target):
        try:
            return nx.shortest_path_length(G, source, target)
        except nx.NetworkXNoPath:
            return float('inf')
