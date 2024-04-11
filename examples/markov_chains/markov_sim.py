'''
This scenario has drivers driving around a city.
In this model, drivers can only be at intersections, which are treated as nodes in the City Graph (grid).

At the start of the simulation, drivers are randomly positioned in the city grid.

The following models for agent behavior are included:

* DummyDriver: In each simulation step, this type of driver can instantly move to any of the neighboring nodes in the grid, or stay in its place.

'''

import networkx as nx
from soil import Environment, BaseAgent, state, time
from mesa.space import NetworkGrid
import mesa
import statistics


class CityGrid(NetworkGrid):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,  **kwargs)

        for (u, v, d) in self.G.edges(data=True):
            d["occupation"] = 0
        # self.dijkstras = dict(nx.all_pairs_dijkstra(self.G, weight="length"))

    # def eta(self, pos1, pos2):
    #     return self.dijkstras[pos1][0][pos2]

    def travel_time(self, pos1, pos2):
        return float(min(d["travel_time"] for d in self.G.adj[pos1][pos2].values()))

    
    def node_occupation(self):
        return {k: len(v.get("agent", [])) for (k, v) in self.G.nodes(data=True)}

    def edge_occupation(self):
        return {(u,v): d.get('occupation', 1) for (u, v, d) in self.G.edges(data=True)}


class Roamer(BaseAgent):
    waiting = False

    def step(self):
        '''
        A simple driver that just moves to a neighboring cell in the city
        '''
        yield from self.move_to(None)
        return self.delay(0)
    
    def choose_next(self):
        opts = self.model.grid.get_neighborhood(self.pos, include_center=False)
        pos = self.random.choice(opts)
        delay = self.model.grid.travel_time(self.pos, pos)
        return pos, delay

    def move_to(self, pos=None):
        self.waiting = True
        if pos is None:
            pos, delay = self.choose_next()
        if self.model.gradual_move:
            # Calculate how long it will take, and wait for that long
            if pos != self.pos:
                self.model.grid.G.edges[self.pos,pos,0]["occupation"] += 1
            yield delay
        if self.model.gradual_move and pos != self.pos:
            w1 = self.model.grid.G.edges[self.pos,pos,0]["occupation"] 
            oldpos = self.pos
            self.model.grid.G.edges[self.pos,pos,0]["occupation"] = w1 - 1
            assert self.model.grid.G.edges[self.pos,pos,0]["occupation"] == w1-1
        self.model.grid.move_agent(self, pos)
        self.waiting = False


class LazyRoamer(Roamer):
    waiting = False
    def choose_next(self):
        opts = self.model.grid.get_neighborhood(self.pos, include_center=False)
        times = [self.model.grid.travel_time(self.pos, other) for other in opts]
        idx = self.random.choices(range(len(times)), k=1, weights=[1/time for time in times])[0]
        return opts[idx], times[idx]



def gini(values):
    s = sum(values)
    
    N = len(values)
    if s == 0:
        return 0
    x = sorted(values)

    B = sum(xi * (N - i) for i, xi in enumerate(x)) / (N * s)
    return 1 + (1 / N) - 2 * B


class CityEnv(Environment):
    def __init__(self, *, G, side=20, n_assets=100, ratio_lazy=1, lockstep=True, gradual_move=True, max_weight=1, **kwargs):
        super().__init__(**kwargs)
        if lockstep:
            self.schedule = time.Lockstepper(self.schedule)
        self.n_assets = n_assets
        self.side = side
        self.max_weight = max_weight
        self.gradual_move = gradual_move
        self.grid = CityGrid(g=G)

        n_lazy = round(self.n_assets * ratio_lazy)
        n_other = self.n_assets - n_lazy
        self.add_agents(Roamer, k=n_other)
        self.add_agents(LazyRoamer, k=n_lazy)

        positions = list(self.grid.G.nodes)
        for agent in self.get_agents():
            pos = self.random.choice(positions)
            self.grid.place_agent(agent, pos)
        
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "NodeGini": lambda model: gini(model.grid.node_occupation().values()),
                "EdgeGini": lambda model: gini(model.grid.edge_occupation().values()),            
                "EdgeOccupation": lambda model: statistics.mean(model.grid.edge_occupation().values()),            
            }#, agent_reporters={"Wealth": "wealth"}
        )

class SquareCityEnv(CityEnv):
    def __init__(self, *, side=20, **kwargs):
        self.side = side
        G = nx.grid_graph(dim=[side, side])
        for (_, _, d) in G.edges(data=True):
            d["travel_time"] = self.random.randint(1, self.max_weight)

        for (k, d) in G.nodes(data=True):   
            d["pos"] = k
        super().__init__(**kwargs, G=G)

import osmnx as ox


class NamedCityEnv(CityEnv):
    def __init__(self, *, location="Chamberi, Madrid", **kwargs):
        self.location = location
        super().__init__(**kwargs, G=load_city_graph(location))


def load_city_graph(location='Chamberi, Madrid', **kwargs):
    G = ox.graph.graph_from_place(location, **kwargs)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    largest = sorted(nx.strongly_connected_components(G), key=lambda x: len(x))[-1]
    G = G.subgraph(largest)
    return G


if __name__ == "__main__":
    env = CityEnv()
    for i in range(100):
        env.step()
