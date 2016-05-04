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
    G = nx.barabasi_albert_graph(settings.number_of_nodes,10)
if settings.network_type == 2:
    G = nx.margulis_gabber_galil_graph(settings.number_of_nodes, None)
# More types of networks can be added here

##############
# Simulation #
##############

sim = NetworkSimulation(topology=G, states=init_states, agent_type=SpreadModelM2,
                        max_time=settings.max_time, num_trials=settings.num_trials, logging_interval=1.0)


sim.run_simulation()

###########
# Results #
###########
x_values = []
infected_values = []
neutral_values = []
cured_values = []
vaccinated_values = []

attribute_plot = 'status'
for time in range(0, settings.max_time):
    value_infectados = 0
    value_neutral = 0
    value_cured = 0
    value_vaccinated = 0
    real_time = time * settings.timeout
    activity= False
    for x in range(0, settings.number_of_nodes):
        if attribute_plot in models.networkStatus["agente_%s" % x]:
            if real_time in models.networkStatus["agente_%s" % x][attribute_plot]:
                if models.networkStatus["agente_%s" % x][attribute_plot][real_time] == 1: ##Representar infectados
                    value_infectados += 1
                    activity = True
                if models.networkStatus["agente_%s" % x][attribute_plot][real_time] == 0:  ##Representar neutrales
                    value_neutral += 1
                    activity = True
                if models.networkStatus["agente_%s" % x][attribute_plot][real_time] == 2:  ##Representar cured
                    value_cured += 1
                    activity = True
                if models.networkStatus["agente_%s" % x][attribute_plot][real_time] == 3:  ##Representar vaccinated
                    value_vaccinated += 1
                    activity = True

    if activity:
        x_values.append(real_time)
        infected_values.append(value_infectados)
        neutral_values.append(value_neutral)
        cured_values.append(value_cured)
        vaccinated_values.append(value_vaccinated)
        activity=False

infected_line = plt.plot(x_values,infected_values,label='Infected')
neutral_line = plt.plot(x_values,neutral_values, label='Neutral')
cured_line = plt.plot(x_values,cured_values, label='Cured')
vaccinated_line = plt.plot(x_values,vaccinated_values, label='Vaccinated')
plt.legend()
plt.savefig('spread_model.png')
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

