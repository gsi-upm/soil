from nxsim import NetworkSimulation
from nxsim import BaseNetworkAgent
from nxsim import BaseLoggingAgent
from random import randint
from matplotlib import pyplot as plt
import random
import numpy as np
import networkx as nx
import settings
import math

settings.init() # Loads all the data from settings

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


##############################
# Variables initializitation #
##############################

myList=[] # List just for debugging
networkStatus=[] # This list will contain the status of every node of the network
emotionStatus=[]
enterprise1Status=[]
enterprise2Status=[]
for x in range(0, settings.number_of_nodes):
    networkStatus.append({'id':x})
    emotionStatus.append({'id':x})
    enterprise1Status.append({'id':x})
    enterprise2Status.append({'id':x})


# Initialize agent states. Let's assume everyone is normal.
init_states = [{'id': 0, } for _ in range(settings.number_of_nodes)]  # add keys as as necessary, but "id" must always refer to that state category

# Seed a zombie, just for zombie model
#init_states[5] = {'id': 1}
#init_states[3] = {'id': 1}

####################
# Available models #
####################

class BigMarketModel(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.time_awareness = 0
        self.type = ""

        if self.id == 0:            #Empresa 1
            self.state['id']=0
            self.type="Enterprise"
            self.tweet_probability = settings.tweet_probability_enterprises[0]

        elif self.id == 1:          #Empresa 2
            self.state['id']=1
            self.type="Enterprise"
            self.tweet_probability = settings.tweet_probability_enterprises[1]
        else:                       #Usuarios normales
            self.state['id']=2
            self.type="User"
            self.tweet_probability = settings.tweet_probability_users
            self.tweet_relevant_probability = settings.tweet_relevant_probability
            self.tweet_probability_about = settings.tweet_probability_about #Lista
            self.sentiment_about = settings.sentiment_about #Lista

        #networkStatus[self.id][self.env.now]=self.state['id']
        #emotionStatus[self.id][self.env.now]=0

    def run(self):
        while True:
            if(self.id < 2): # Empresa
                self.enterpriseBehaviour()
            else:  # Usuario
                #self.userBehaviour()
                pass
            yield self.env.timeout(settings.timeout)



    def enterpriseBehaviour(self):

        if random.random()< self.tweet_probability: #Twittea
            aware_neighbors = self.get_neighboring_agents(state_id=2) #Nodos vecinos usuarios
            for x in aware_neighbors:
                if random.uniform(0,10) < 5:
                    x.sentiment_about[self.id] += 0.1 #Aumenta para empresa
                else:
                    x.sentiment_about[self.id] -= 0.1 #Reduce para empresa

                # Establecemos limites
                if x.sentiment_about[self.id] > 1:
                    x.sentiment_about[self.id] = 1
                if x.sentiment_about[self.id] < -1:
                    x.sentiment_about[self.id] = -1

                #Visualización
                if self.id == 0:
                    enterprise1Status[x.id][self.env.now]=x.sentiment_about[self.id]
                if self.id == 1:
                    enterprise2Status[x.id][self.env.now]=x.sentiment_about[self.id]




    def userBehaviour(self):

        if random.random() < self.tweet_probability: #Twittea
            if random.random() < self.tweet_relevant_probability: #Twittea algo relevante
                #Probabilidad de tweet para cada empresa
                for i in range(len(self.tweet_probability_about)):
                    random_num = random.random()
                    if random_num < self.tweet_probability_about[i]:
                        #Se ha cumplido la condicion, evaluo los sentimientos hacia esa empresa
                        if self.sentiment_about[i] < 0:
                            #NEGATIVO
                            self.userTweets("negative",i)
                        elif self.sentiment_about[i] == 0:
                            #NEUTRO
                            pass
                        else:
                            #POSITIVO
                            self.userTweets("positive",i)


    def userTweets(self,sentiment,enterprise):
        aware_neighbors = self.get_neighboring_agents(state_id=2) #Nodos vecinos usuarios
        for x in aware_neighbors:
            if sentiment == "positive":
                x.sentiment_about[enterprise] +=0.003
            elif sentiment == "negative":
                x.sentiment_about[enterprise] -=0.003
            else:
                pass

            # Establecemos limites
            if x.sentiment_about[enterprise] > 1:
                x.sentiment_about[enterprise] = 1
            if x.sentiment_about[enterprise] < -1:
                x.sentiment_about[enterprise] = -1

            #Visualización
            if enterprise == 0:
                enterprise1Status[x.id][self.env.now]=x.sentiment_about[enterprise]
            if enterprise == 1:
                enterprise2Status[x.id][self.env.now]=x.sentiment_about[enterprise]


    def checkLimits(sentimentValue):
        if sentimentValue > 1:
            return 1
        if sentimentValue < -1:
            return -1






################################################


class SentimentCorrelationModel(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.outside_effects_prob = settings.outside_effects_prob
        self.anger_prob = settings.anger_prob
        self.joy_prob = settings.joy_prob
        self.sadness_prob = settings.sadness_prob
        self.disgust_prob = settings.disgust_prob
        self.time_awareness=[]
        for i in range(4):  #En este modelo tenemos 4 sentimientos
            self.time_awareness.append(0)     #0-> Anger, 1-> joy, 2->sadness, 3 -> disgust
        networkStatus[self.id][self.env.now]=0


    def run(self):
        while True:

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


            anger_prob= settings.anger_prob+(len(angry_neighbors_1_time_step)*settings.anger_prob)
            joy_prob= settings.joy_prob+(len(joyful_neighbors_1_time_step)*settings.joy_prob)
            sadness_prob = settings.sadness_prob+(len(sad_neighbors_1_time_step)*settings.sadness_prob)
            disgust_prob = settings.disgust_prob+(len(disgusted_neighbors_1_time_step)*settings.disgust_prob)
            outside_effects_prob= settings.outside_effects_prob


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


##############
# Simulation #
##############

sim = NetworkSimulation(topology=G, states=init_states, agent_type=BigMarketModel,
                        max_time=settings.max_time, num_trials=settings.num_trials, logging_interval=1.0)


sim.run_simulation()

###########
# Results #
###########

myList = sorted(myList, key=int)
#print("Los zombies son: " + str(myList))

trial = BaseLoggingAgent.open_trial_state_history(dir_path='sim_01', trial_id=0)
status_census = [sum([1 for node_id, state in g.items() if state['id'] == 1]) for t,g in trial.items()]


#################
# Visualization #
#################

print("Empresa1")
print (enterprise1Status)
print("Empresa2")
print (enterprise2Status)

for x in range(0, settings.number_of_nodes):
    emotionStatusAux=[]

    # for tiempo in emotionStatus[x]:
    #     if tiempo != 'id':
    #         prec = 2
    #         output = math.floor(emotionStatus[x][tiempo] * (10 ** prec)) / (10 ** prec) #Para tener 2 decimales solo
    #         emotionStatusAux.append((output,tiempo,None))
    # G.add_node(x, emotion= emotionStatusAux)
    # del emotionStatusAux[:]
    for tiempo in enterprise1Status[x]:
        if tiempo != 'id':
            prec = 2
            output = math.floor(enterprise1Status[x][tiempo] * (10 ** prec)) / (10 ** prec) #Para tener 2 decimales solo
            emotionStatusAux.append((output,tiempo,None))
    G.add_node(x, enterprise1emotion= emotionStatusAux)

for x in range(0, settings.number_of_nodes):
    emotionStatusAux2=[]
    for tiempo in enterprise2Status[x]:
        if tiempo != 'id':
            prec = 2
            output = math.floor(enterprise2Status[x][tiempo] * (10 ** prec)) / (10 ** prec) #Para tener 2 decimales solo
            emotionStatusAux2.append((output,tiempo,None))
    G.add_node(x, enterprise2emotion= emotionStatusAux2)


#lista = nx.nodes(G)
#print('Nodos: ' + str(lista))
# for x in range(0, settings.number_of_nodes):
#     networkStatusAux=[]
#     for tiempo in networkStatus[x]:
#         if tiempo != 'id':
#             networkStatusAux.append((networkStatus[x][tiempo],tiempo,None))
#     G.add_node(x, status= networkStatusAux)
#print(networkStatus)


nx.write_gexf(G,"test.gexf", version="1.2draft")
plt.plot(status_census)
plt.draw()  # pyplot draw()
plt.savefig("status.png")
#print(networkStatus)
#nx.draw(G)
#plt.show()
#plt.savefig("path.png")

