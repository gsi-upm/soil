from . import BaseAgent

import os.path
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx


class DrawingAgent(BaseAgent):
    """
    Agent that draws the state of the network.
    """

    def step(self):
        # Outside effects
        f = plt.figure()
        nx.draw(self.env.G, node_size=10, width=0.2, pos=nx.spring_layout(self.env.G, scale=100), ax=f.add_subplot(111))
        f.savefig(os.path.join(self.env.get_path(), "graph-"+str(self.env.now)+".png"))
