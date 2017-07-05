from models import *
from nxsim import NetworkSimulation
# import numpy
from matplotlib import pyplot as plt
import networkx as nx
import settings
import models
import math
import json
import operator
import community



POPULATION = 0
LEADERS = 1
HAVEN = 2
TRAINING = 3

NON_RADICAL = 0
NEUTRAL = 1
RADICAL = 2
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

    for node in range(settings.network_params["number_of_nodes"]):
        G.node[node]['x'] = G.node[node]['pos'][0]
        G.node[node]['y'] = G.node[node]['pos'][1]
        G.node[node]['viz'] = {"position": {"x": G.node[node]['pos'][0], "y": G.node[node]['pos'][1], "z": 0.0}}
        del (G.node[node]['pos'])

    nx.write_gexf(G, graph_name+".gexf", version="1.2draft")

###########
# Results #
###########

def results(model_name):
    x_values = []
    neutral_values = []
    non_radical_values = []
    radical_values = []

    attribute_plot = 'status'
    for time in range(0, settings.network_params["max_time"]):
        value_neutral = 0
        value_non_radical = 0
        value_radical = 0
        real_time = time * settings.network_params["timeout"]
        activity = False
        for x in range(0, settings.network_params["number_of_nodes"]):
            if attribute_plot in models.networkStatus["agent_%s" % x]:
                if real_time in models.networkStatus["agent_%s" % x][attribute_plot]:
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == NON_RADICAL:  
                        value_non_radical += 1
                        activity = True
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == NEUTRAL:  
                        value_neutral += 1
                        activity = True
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == RADICAL:  
                        value_radical += 1
                        activity = True


        if activity:
            x_values.append(real_time)
            neutral_values.append(value_neutral)
            non_radical_values.append(value_non_radical)
            radical_values.append(value_radical)
            activity = False

    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111)

    non_radical_line = ax1.plot(x_values, non_radical_values, label='Non radical')
    neutral_line = ax1.plot(x_values, neutral_values, label='Neutral')
    radical_line = ax1.plot(x_values, radical_values, label='Radical')
    ax1.legend()
    fig1.savefig(model_name+'.png')
    plt.show()

###########
# Results #
###########

def resultadosTipo(model_name):
    x_values = []
    population_values = []
    leaders_values = []
    havens_values = []
    training_enviroments_values = []

    attribute_plot = 'type'
    for time in range(0, settings.network_params["max_time"]):
        value_population = 0
        value_leaders = 0
        value_havens = 0
        value_training_enviroments = 0
        real_time = time * settings.network_params["timeout"]
        activity = False
        for x in range(0, settings.network_params["number_of_nodes"]):
            if attribute_plot in models.networkStatus["agent_%s" % x]:
                if real_time in models.networkStatus["agent_%s" % x][attribute_plot]:
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == POPULATION:
                        value_population += 1
                        activity = True
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == LEADERS:
                        value_leaders += 1
                        activity = True
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == HAVEN:
                        value_havens += 1
                        activity = True
                    if models.networkStatus["agent_%s" % x][attribute_plot][real_time] == TRAINING:
                        value_training_enviroments += 1
                        activity = True
        if activity:
            x_values.append(real_time)
            population_values.append(value_population)
            leaders_values.append(value_leaders)
            havens_values.append(value_havens)
            training_enviroments_values.append(value_training_enviroments)
            activity = False

    fig2 = plt.figure()
    ax2 = fig2.add_subplot(111)

    population_line = ax2.plot(x_values, population_values, label='Population')
    leaders_line = ax2.plot(x_values, leaders_values, label='Leader')
    havens_line = ax2.plot(x_values, havens_values, label='Havens')
    training_enviroments_line = ax2.plot(x_values, training_enviroments_values, label='Training Enviroments')
    ax2.legend()
    fig2.savefig(model_name+'_type'+'.png')
    plt.show()

####################
# Network creation #
####################

#  nx.degree_centrality(G);

if settings.network_params["network_type"] == 0:
    G = nx.random_geometric_graph(settings.network_params["number_of_nodes"], 0.2)

    settings.partition_param = community.best_partition(G)
    settings.centrality_param = nx.betweenness_centrality(G).copy()


    # print(settings.centrality_param)
    # print(settings.partition_param)
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
        resultadosTipo(str(agent))
        visualization(str(agent))
else:
    agent = agents[0]
    sim = NetworkSimulation(topology=G, states=init_states, agent_type=locals()[agent], max_time=settings.network_params["max_time"],
                            num_trials=settings.network_params["num_trials"], logging_interval=1.0, **settings.environment_params)
    sim.run_simulation()
    results(str(agent))
    resultadosTipo(str(agent))

    visualization(str(agent))