from nxsim import NetworkSimulation
from nxsim import BaseNetworkAgent
from nxsim import BaseLoggingAgent
from random import randint
from matplotlib import pyplot as plt
import random
import numpy as np
import networkx as nx
import settings


settings.init()

if settings.network_type == 0:
    G = nx.complete_graph(settings.number_of_nodes)
if settings.network_type == 1:
    G = nx.barabasi_albert_graph(settings.number_of_nodes,3)
if settings.network_type == 2:
    G = nx.margulis_gabber_galil_graph(settings.number_of_nodes, None)


myList=[]
networkStatus=[]
for x in range(0, settings.number_of_nodes):
    networkStatus.append({'id':x})



# # Just like subclassing a process in SimPy
# class MyAgent(BaseNetworkAgent):
#     def __init__(self, environment=None, agent_id=0, state=()):  # Make sure to have these three keyword arguments
#         super().__init__(environment=environment, agent_id=agent_id, state=state)
#         # Add your own attributes here

#     def run(self):
#         # Add your behaviors here




class SentimentCorrelationModel(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.outside_effects_prob = settings.outside_effects_prob
        self.anger_prob = settings.anger_prob
        self.joy_prob = settings.joy_prob
        self.sadness_prob = settings.sadness_prob
        self.disgust_prob = settings.disgust_prob
        self.time_awareness=[]
        for i in range(4):
            self.time_awareness.append(0)     #0-> Anger, 1-> joy, 2->sadness, 3 -> disgust
        networkStatus[self.id][self.env.now]=0


    def run(self):
        while True:
            if self.env.now > 10:
                G.add_node(205)
                G.add_edge(205,0)
            angry_neighbors_1_time_step=[]
            joyful_neighbors_1_time_step=[]
            sad_neighbors_1_time_step=[]
            disgusted_neighbors_1_time_step=[]


            angry_neighbors = self.get_neighboring_agents(state_id=1)
            for x in angry_neighbors:
                if x.time_awareness[0] > (self.env.now-500):
                    angry_neighbors_1_time_step.append(x)
            num_neighbors_angry = len(angry_neighbors_1_time_step)


            joyful_neighbors = self.get_neighboring_agents(state_id=2)
            for x in joyful_neighbors:
                if x.time_awareness[1] > (self.env.now-500):
                    joyful_neighbors_1_time_step.append(x)
            num_neighbors_joyful = len(joyful_neighbors_1_time_step)


            sad_neighbors = self.get_neighboring_agents(state_id=3)
            for x in sad_neighbors:
                if x.time_awareness[2] > (self.env.now-500):
                    sad_neighbors_1_time_step.append(x)
            num_neighbors_sad = len(sad_neighbors_1_time_step)


            disgusted_neighbors = self.get_neighboring_agents(state_id=4)
            for x in disgusted_neighbors:
                if x.time_awareness[3] > (self.env.now-500):
                    disgusted_neighbors_1_time_step.append(x)
            num_neighbors_disgusted = len(disgusted_neighbors_1_time_step)

            # #Outside effects. Asignamos un estado aleatorio
            # if random.random() < settings.outside_effects_prob:
            #     if self.state['id'] == 0:
            #         self.state['id'] = random.randint(1,4)
            #         myList.append(self.id)
            #         networkStatus[self.id][self.env.now]=self.state['id'] #Almaceno cuando se ha infectado para la red dinamica
            #         self.time_awareness = self.env.now #Para saber cuando se han contagiado
            #         yield self.env.timeout(settings.timeout)
            #     else:
            #         yield self.env.timeout(settings.timeout)


            # #Imitation effects-Joy

            # if random.random() < (settings.joy_prob*(num_neighbors_joyful)/10):
            #     myList.append(self.id)
            #     self.state['id'] = 2
            #     networkStatus[self.id][self.env.now]=2
            #     yield self.env.timeout(settings.timeout)


            # #Imitation effects-Sadness

            # if random.random() < (settings.sadness_prob*(num_neighbors_sad)/10):
            #     myList.append(self.id)
            #     self.state['id'] = 3
            #     networkStatus[self.id][self.env.now]=3
            #     yield self.env.timeout(settings.timeout)


            # #Imitation effects-Disgust

            # if random.random() < (settings.disgust_prob*(num_neighbors_disgusted)/10):
            #     myList.append(self.id)
            #     self.state['id'] = 4
            #     networkStatus[self.id][self.env.now]=4
            #     yield self.env.timeout(settings.timeout)

            # #Imitation effects-Anger

            # if random.random() < (settings.anger_prob*(num_neighbors_angry)/10):
            #     myList.append(self.id)
            #     self.state['id'] = 1
            #     networkStatus[self.id][self.env.now]=1
            #     yield self.env.timeout(settings.timeout)

            # yield self.env.timeout(settings.timeout)

###########################################


            anger_prob= settings.anger_prob+(len(angry_neighbors_1_time_step)*settings.anger_prob)
            print("anger_prob " + str(anger_prob))
            joy_prob= settings.joy_prob+(len(joyful_neighbors_1_time_step)*settings.joy_prob)
            print("joy_prob " + str(joy_prob))
            sadness_prob = settings.sadness_prob+(len(sad_neighbors_1_time_step)*settings.sadness_prob)
            print("sadness_prob "+ str(sadness_prob))
            disgust_prob = settings.disgust_prob+(len(disgusted_neighbors_1_time_step)*settings.disgust_prob)
            print("disgust_prob " + str(disgust_prob))
            outside_effects_prob= settings.outside_effects_prob
            print("outside_effects_prob " + str(outside_effects_prob))


            num = random.random()


            if(num<outside_effects_prob):
                self.state['id'] = random.randint(1,4)
                myList.append(self.id)
                networkStatus[self.id][self.env.now]=self.state['id'] #Almaceno cuando se ha infectado para la red dinamica
                self.time_awareness[self.state['id']-1] = self.env.now
                yield self.env.timeout(settings.timeout)


            if(num<anger_prob):

                myList.append(self.id)
                self.state['id'] = 1
                networkStatus[self.id][self.env.now]=1
                self.time_awareness[self.state['id']-1] = self.env.now
            elif (num<joy_prob+anger_prob and num>anger_prob):

                myList.append(self.id)
                self.state['id'] = 2
                networkStatus[self.id][self.env.now]=2
                self.time_awareness[self.state['id']-1] = self.env.now
            elif (num<sadness_prob+anger_prob+joy_prob and num>joy_prob+anger_prob):

                myList.append(self.id)
                self.state['id'] = 3
                networkStatus[self.id][self.env.now]=3
                self.time_awareness[self.state['id']-1] = self.env.now
            elif (num<disgust_prob+sadness_prob+anger_prob+joy_prob and num>sadness_prob+anger_prob+joy_prob):

                myList.append(self.id)
                self.state['id'] = 4
                networkStatus[self.id][self.env.now]=4
                self.time_awareness[self.state['id']-1] = self.env.now

            yield self.env.timeout(settings.timeout)


            # anger_propagation = settings.anger_prob*num_neighbors_angry/10
            # joy_propagation = anger_propagation + (settings.joy_prob*num_neighbors_joyful/10)
            # sadness_propagation = joy_propagation + (settings.sadness_prob*num_neighbors_sad/10)
            # disgust_propagation = sadness_propagation + (settings.disgust_prob*num_neighbors_disgusted/10)
            # outside_effects_propagation = disgust_propagation + settings.outside_effects_prob

            # if (num<anger_propagation):
            #     if(self.state['id'] !=0):
            #         myList.append(self.id)
            #         self.state['id'] = 1
            #         networkStatus[self.id][self.env.now]=1
            #         yield self.env.timeout(settings.timeout)
            # if (num<joy_propagation):
            #     if(self.state['id'] !=0):
            #         myList.append(self.id)
            #         self.state['id'] = 2
            #         networkStatus[self.id][self.env.now]=2
            #         yield self.env.timeout(settings.timeout)
            # if(num<sadness_propagation):
            #     if(self.state['id'] !=0):
            #         myList.append(self.id)
            #         self.state['id'] = 3
            #         networkStatus[self.id][self.env.now]=3
            #         yield self.env.timeout(settings.timeout)
            # # if(num<disgust_propagation):
            # #     if(self.state['id'] !=0):
            # #         myList.append(self.id)
            # #         self.state['id'] = 4
            # #         networkStatus[self.id][self.env.now]=4
            # #         yield self.env.timeout(settings.timeout)
            # if(num <outside_effects_propagation):
            #     if self.state['id'] == 0:
            #         self.state['id'] = random.randint(1,4)
            #         myList.append(self.id)
            #         networkStatus[self.id][self.env.now]=self.state['id'] #Almaceno cuando se ha infectado para la red dinamica
            #         self.time_awareness = self.env.now #Para saber cuando se han contagiado
            #         yield self.env.timeout(settings.timeout)
            #     else:
            #         yield self.env.timeout(settings.timeout)
            # else:
            #     yield self.env.timeout(settings.timeout)





class BassModel(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.innovation_prob = settings.innovation_prob
        self.imitation_prob = settings.imitation_prob
        networkStatus[self.id][self.env.now]=0

    def run(self):
        while True:


            #Outside effects
            if random.random() < settings.innovation_prob:
                if self.state['id'] == 0:
                    self.state['id'] = 1
                    myList.append(self.id)
                    networkStatus[self.id][self.env.now]=1
                    yield self.env.timeout(settings.timeout)
                else:
                    yield self.env.timeout(settings.timeout)

            #Imitation effects
            if self.state['id'] == 0:
                aware_neighbors = self.get_neighboring_agents(state_id=1)
                num_neighbors_aware = len(aware_neighbors)
                if random.random() < (settings.imitation_prob*num_neighbors_aware):
                    myList.append(self.id)
                    self.state['id'] = 1
                    networkStatus[self.id][self.env.now]=1
                    yield self.env.timeout(settings.timeout)
                else:
                    yield self.env.timeout(settings.timeout)

class IndependentCascadeModel(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.innovation_prob = settings.innovation_prob
        self.imitation_prob = settings.imitation_prob
        self.time_awareness = 0
        networkStatus[self.id][self.env.now]=0

    def run(self):
        while True:
            aware_neighbors_1_time_step=[]
            #Outside effects
            if random.random() < settings.innovation_prob:
                if self.state['id'] == 0:
                    self.state['id'] = 1
                    myList.append(self.id)
                    networkStatus[self.id][self.env.now]=1
                    self.time_awareness = self.env.now #Para saber cuando se han contagiado
                    yield self.env.timeout(settings.timeout)
                else:
                    yield self.env.timeout(settings.timeout)

            #Imitation effects
            if self.state['id'] == 0:
                aware_neighbors = self.get_neighboring_agents(state_id=1)
                for x in aware_neighbors:
                    if x.time_awareness == (self.env.now-1):
                        aware_neighbors_1_time_step.append(x)
                num_neighbors_aware = len(aware_neighbors_1_time_step)
                if random.random() < (settings.imitation_prob*num_neighbors_aware):
                    myList.append(self.id)
                    self.state['id'] = 1
                    networkStatus[self.id][self.env.now]=1
                    yield self.env.timeout(settings.timeout)
                else:
                    yield self.env.timeout(settings.timeout)


class ZombieOutbreak(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.bite_prob = settings.bite_prob
        networkStatus[self.id][self.env.now]=0


    def run(self):
        while True:
            if random.random() < settings.heal_prob:
                if self.state['id'] == 1:
                    self.zombify()
                    yield self.env.timeout(settings.timeout)
                else:
                    yield self.env.timeout(settings.timeout)
            else:
                if self.state['id'] == 1:
                    print("Soy el zombie " + str(self.id) + " y me voy a curar porque el num aleatorio ha sido " + str(num))
                    networkStatus[self.id][self.env.now]=0
                    if self.id in myList:
                        myList.remove(self.id)
                    self.state['id'] = 0
                    yield self.env.timeout(settings.timeout)
                else:
                    yield self.env.timeout(settings.timeout)


    def zombify(self):
        normal_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in normal_neighbors:
            if random.random() < self.bite_prob:
                print("Soy el zombie " + str(self.id) + " y voy a contagiar a " + str(neighbor.id))
                neighbor.state['id'] = 1 # zombie
                myList.append(neighbor.id)
                networkStatus[self.id][self.env.now]=1
                networkStatus[neighbor.id][self.env.now]=1
                print(self.env.now, "Soy el zombie: "+ str(self.id), "Mi vecino es: "+ str(neighbor.id), sep='\t')
                break


# Initialize agent states. Let's assume everyone is normal.
init_states = [{'id': 0, } for _ in range(settings.number_of_nodes)]  # add keys as as necessary, but "id" must always refer to that state category

# Seed a zombie
#init_states[5] = {'id': 1}
#init_states[3] = {'id': 1}

sim = NetworkSimulation(topology=G, states=init_states, agent_type=SentimentCorrelationModel,
                        max_time=settings.max_time, num_trials=settings.num_trials, logging_interval=1.0)


sim.run_simulation()

myList = sorted(myList, key=int)
#print("Los zombies son: " + str(myList))

trial = BaseLoggingAgent.open_trial_state_history(dir_path='sim_01', trial_id=0)
zombie_census = [sum([1 for node_id, state in g.items() if state['id'] == 1]) for t,g in trial.items()]

#for x in range(len(myList)):
#    G.node[myList[x]]['viz'] = {'color': {'r': 255, 'g': 0, 'b': 0, 'a': 0}}

#G.node[1]['viz'] = {'color': {'r': 255, 'g': 0, 'b': 0, 'a': 0}}

#lista = nx.nodes(G)
#print('Nodos: ' + str(lista))
for x in range(0, settings.number_of_nodes):
    networkStatusAux=[]
    for tiempo in networkStatus[x]:
        if tiempo != 'id':
	        networkStatusAux.append((networkStatus[x][tiempo],tiempo,None))
    G.add_node(x, zombie= networkStatusAux)
#print(networkStatus)


nx.write_gexf(G,"test.gexf", version="1.2draft")
plt.plot(zombie_census)
plt.draw()  # pyplot draw()
plt.savefig("zombie.png")
#print(networkStatus)
#nx.draw(G)
#plt.show()
#plt.savefig("path.png")
