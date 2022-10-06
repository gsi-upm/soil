from networkx import Graph
import networkx as nx

def mygenerator(n=5, n_edges=5):
    '''
    Just a simple generator that creates a network with n nodes and
    n_edges edges. Edges are assigned randomly, only avoiding self loops.
    '''
    G = nx.Graph()

    for i in range(n):
        G.add_node(i)
    
    for i in range(n_edges):
        nodes = list(G.nodes)
        n_in = self.random.choice(nodes)
        nodes.remove(n_in)  # Avoid loops
        n_out = self.random.choice(nodes)
        G.add_edge(n_in, n_out)
    return G
    




    
