from models import *
from nxsim import NetworkSimulation
import numpy
from matplotlib import pyplot as plt
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

sim = NetworkSimulation(topology=G, states=init_states, agent_type=SISaModel,
                        max_time=settings.max_time, num_trials=settings.num_trials, logging_interval=1.0)


sim.run_simulation()

###########
# Results #
###########
x_values = []
y_values = []

for time in range(0, settings.max_time):
    value = settings.sentiment_about[0]
    real_time = time * settings.timeout
    for x in range(0, settings.number_of_nodes):
        if "sentiment_enterprise_BBVA" in models.networkStatus["agente_%s" % x]:
            if real_time in models.networkStatus["agente_%s" % x]["sentiment_enterprise_BBVA"]:
                value += models.networkStatus["agente_%s" % x]["sentiment_enterprise_BBVA"][real_time]

    x_values.append(real_time)
    y_values.append(value)

plt.plot(x_values,y_values)
#plt.show()


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

