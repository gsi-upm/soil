from models import *
from nxsim import NetworkSimulation
# import numpy
from matplotlib import pyplot as plt
import networkx as nx
import settings
import models
import math
import json


#################
# Visualization #
#################

def visualization(graph_name):

    for x in range(0, settings.network_params["number_of_nodes"]):
        attributes = {}
        spells = []
        for attribute in models.networkStatus["agent_%s" % x]:
            if attribute == 'visible':
                lastvisible = False
                laststep = 0
                for t_step in models.networkStatus["agent_%s" % x][attribute]:
                    nowvisible = models.networkStatus["agent_%s" % x][attribute][t_step]
                    if nowvisible and not lastvisible:
                        laststep = t_step
                    if not nowvisible and lastvisible:
                        spells.append((laststep, t_step))

                    lastvisible = nowvisible
                if lastvisible:
                    spells.append((laststep, None))
            else:
                emotionStatusAux = []
                for t_step in models.networkStatus["agent_%s" % x][attribute]:
                    prec = 2
                    output = math.floor(models.networkStatus["agent_%s" % x][attribute][t_step] * (10 ** prec)) / (10 ** prec)  # 2 decimals
                    emotionStatusAux.append((output, t_step, t_step + settings.network_params["timeout"]))
                attributes[attribute] = emotionStatusAux
        if spells:
            G.add_node(x, attributes, spells=spells)
        else:
            G.add_node(x, attributes)

    print("Done!")

    with open('data.txt', 'w') as outfile:
        json.dump(models.networkStatus, outfile, sort_keys=True, indent=4, separators=(',', ': '))

    nx.write_gexf(G, graph_name+".gexf", version="1.2draft")


###########
# Results #
###########

def results(model_name):
    x_values = []
    infected_values = []
    neutral_values = []
    cured_values = []
    vaccinated_values = []

    attribute_plot = 'status'
    for time in range(0, settings.network_params["max_time"]):
        value_infectados = 0
        value_neutral = 0
        value_cured = 0
        value_vaccinated = 0
        real_time = time * settings.network_params["timeout"]
        activity = False
        for x in range(0, settings.network_params["number_of_nodes"]):
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

    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111)

    infected_line = ax1.plot(x_values, infected_values, label='Infected')
    neutral_line = ax1.plot(x_values, neutral_values, label='Neutral')
    cured_line = ax1.plot(x_values, cured_values, label='Cured')
    vaccinated_line = ax1.plot(x_values, vaccinated_values, label='Vaccinated')
    ax1.legend()
    fig1.savefig(model_name + '.png')
    # plt.show()


####################
# Network creation #
####################

if settings.network_params["network_type"] == 0:
    G = nx.complete_graph(settings.network_params["number_of_nodes"])
if settings.network_params["network_type"] == 1:
    G = nx.barabasi_albert_graph(settings.network_params["number_of_nodes"], 10)
if settings.network_params["network_type"] == 2:
    G = nx.margulis_gabber_galil_graph(settings.network_params["number_of_nodes"], None)
# More types of networks can be added here

##############
# Simulation #
##############

agents = settings.environment_params['agent']

print("Using Agent(s): {agents}".format(agents=agents))

if len(agents) > 1:
    for agent in agents:
        sim = NetworkSimulation(topology=G, states=init_states, agent_type=locals()[agent], max_time=settings.network_params["max_time"],
                                num_trials=settings.network_params["num_trials"], logging_interval=1.0, **settings.environment_params)
        sim.run_simulation()
        print(str(agent))
        results(str(agent))
        visualization(str(agent))
else:
    agent = agents[0]
    sim = NetworkSimulation(topology=G, states=init_states, agent_type=locals()[agent], max_time=settings.network_params["max_time"],
                            num_trials=settings.network_params["num_trials"], logging_interval=1.0, **settings.environment_params)
    sim.run_simulation()
    results(str(agent))
    visualization(str(agent))