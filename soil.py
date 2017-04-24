from models import *
from nxsim import NetworkSimulation
import numpy
from matplotlib import pyplot as plt
import networkx as nx
import settings
import models
import math
import json


####################
# Network creation #
####################

if settings.network_type == 0:
    G = nx.complete_graph(settings.number_of_nodes)
if settings.network_type == 1:
    G = nx.barabasi_albert_graph(settings.number_of_nodes, 10)
if settings.network_type == 2:
    G = nx.margulis_gabber_galil_graph(settings.number_of_nodes, None)
# More types of networks can be added here


##############
# Simulation #
##############

sim = NetworkSimulation(topology=G, states=init_states, agent_type=ControlModelM2, max_time=settings.max_time,
                        num_trials=settings.num_trials, logging_interval=1.0, **settings.environment_params)

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
    activity = False
    for x in range(0, settings.number_of_nodes):
        if attribute_plot in models.networkStatus["agent_%s" % x]:
            if real_time in models.networkStatus["agent_%s" % x][attribute_plot]:
                if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == 1:  ## Infected
                    value_infectados += 1
                    activity = True
                if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == 0:  ## Neutral
                    value_neutral += 1
                    activity = True
                if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == 2:  ## Cured
                    value_cured += 1
                    activity = True
                if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == 3:  ## Vaccinated
                    value_vaccinated += 1
                    activity = True

    if activity:
        x_values.append(real_time)
        infected_values.append(value_infectados)
        neutral_values.append(value_neutral)
        cured_values.append(value_cured)
        vaccinated_values.append(value_vaccinated)
        activity = False

infected_line = plt.plot(x_values, infected_values, label='Infected')
neutral_line = plt.plot(x_values, neutral_values, label='Neutral')
cured_line = plt.plot(x_values, cured_values, label='Cured')
vaccinated_line = plt.plot(x_values, vaccinated_values, label='Vaccinated')
plt.legend()
plt.savefig('control_model.png')
# plt.show()


#################
# Visualization #
#################

for x in range(0, settings.number_of_nodes):
    for attribute in models.networkStatus["agent_%s" % x]:
        emotionStatusAux = []
        for t_step in models.networkStatus["agent_%s" % x][attribute]:
            prec = 2
            output = math.floor(models.networkStatus["agent_%s" % x][attribute][t_step] * (10 ** prec)) / (10 ** prec)  # 2 decimals
            emotionStatusAux.append((output, t_step,None))
        attributes = {}
        attributes[attribute] = emotionStatusAux
        G.add_node(x, attributes)


print("Done!")

with open('data.txt', 'w') as outfile:
    json.dump(models.networkStatus, outfile, sort_keys=True, indent=4, separators=(',', ': '))

nx.write_gexf(G, "test.gexf", version="1.2draft")
