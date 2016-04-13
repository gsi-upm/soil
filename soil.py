#from clase_base import *
from models import *
from nxsim import NetworkSimulation
from nxsim import BaseNetworkAgent
from nxsim import BaseLoggingAgent
import random
import numpy as np
import networkx as nx
import settings
import models
import math
import json

settings.init() # Loads all the data from settings
models.init() # Loads the models and network variables

####################
# Network creation #
####################

if settings.network_type == 0:
    G = nx.complete_graph(settings.number_of_nodes)
if settings.network_type == 1:
    G = nx.barabasi_albert_graph(settings.number_of_nodes,3)
if settings.network_type == 2:
    G = nx.margulis_gabber_galil_graph(settings.number_of_nodes, None)
# More types of networks can be added here

##############
# Simulation #
##############

sim = NetworkSimulation(topology=G, states=init_states, agent_type=BigMarketModel,
                        max_time=settings.max_time, num_trials=settings.num_trials, logging_interval=1.0)


sim.run_simulation()

###########
# Results #
###########


trial = BaseLoggingAgent.open_trial_state_history(dir_path='sim_01', trial_id=0)
status_census = [sum([1 for node_id, state in g.items() if state['id'] == 1]) for t,g in trial.items()]


#################
# Visualization #
#################


for x in range(0, settings.number_of_nodes):
    for empresa in models.networkStatus["agente_%s"%x]:
        emotionStatusAux=[]
        for tiempo in models.networkStatus["agente_%s"%x][empresa]:
            prec = 2
            output = math.floor(models.networkStatus["agente_%s"%x][empresa][tiempo] * (10 ** prec)) / (10 ** prec) #Para tener 2 decimales solo
            emotionStatusAux.append((output,tiempo,None))
        attributes = {}
        attributes[empresa] = emotionStatusAux
        G.add_node(x, attributes)


print("Done!")

with open('data.txt', 'w') as outfile:
    json.dump(models.networkStatus, outfile, sort_keys=True, indent=4, separators=(',', ': '))

nx.write_gexf(G,"test.gexf", version="1.2draft")

