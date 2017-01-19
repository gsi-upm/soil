from nxsim import BaseNetworkAgent
import numpy as np
import random
import settings

settings.init()

##############################
# Variables initialization #
##############################
def init():
    global networkStatus
    networkStatus = {}  # Dict that will contain the status of every agent in the network

sentimentCorrelationNodeArray=[]
for x in range(0, settings.number_of_nodes):
    sentimentCorrelationNodeArray.append({'id':x})
# Initialize agent states. Let's assume everyone is normal.
init_states = [{'id': 0, } for _ in range(settings.number_of_nodes)]  # add keys as as necessary, but "id" must always refer to that state category


####################
# Available models #
####################

class BaseBehaviour(BaseNetworkAgent):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self._attrs = {}

    @property
    def attrs(self):
        now = self.env.now
        if now not in self._attrs:
            self._attrs[now] = {}
        return self._attrs[now]

    @attrs.setter
    def attrs(self, value):
        self._attrs[self.env.now] = value

    def run(self):
        while True:
            self.step(self.env.now)
            yield self.env.timeout(settings.timeout)

    def step(self, now):
        networkStatus['agent_%s'% self.id] = self.to_json()

    def to_json(self):
        final = {}
        for stamp, attrs in self._attrs.items():
            for a in attrs:
                if a not in final:
                   final[a] = {}
                final[a][stamp] = attrs[a]
        return final

class ControlModelM2(BaseBehaviour):
    #Init infected
    init_states[random.randint(0,settings.number_of_nodes-1)] = {'id':1}
    init_states[random.randint(0,settings.number_of_nodes-1)] = {'id':1}

    # Init beacons
    init_states[random.randint(0, settings.number_of_nodes-1)] = {'id': 4}
    init_states[random.randint(0, settings.number_of_nodes-1)] = {'id': 4}
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.prob_neutral_making_denier = np.random.normal(settings.prob_neutral_making_denier, settings.standard_variance)

        self.prob_infect = np.random.normal(settings.prob_infect, settings.standard_variance)

        self.prob_cured_healing_infected = np.random.normal(settings.prob_cured_healing_infected, settings.standard_variance)
        self.prob_cured_vaccinate_neutral = np.random.normal(settings.prob_cured_vaccinate_neutral, settings.standard_variance)

        self.prob_vaccinated_healing_infected = np.random.normal(settings.prob_vaccinated_healing_infected, settings.standard_variance)
        self.prob_vaccinated_vaccinate_neutral = np.random.normal(settings.prob_vaccinated_vaccinate_neutral, settings.standard_variance)
        self.prob_generate_anti_rumor = np.random.normal(settings.prob_generate_anti_rumor, settings.standard_variance)

    def step(self, now):

        if self.state['id'] == 0:  #Neutral
            self.neutral_behaviour()
        elif self.state['id'] == 1:  #Infected
            self.infected_behaviour()
        elif self.state['id'] == 2:  #Cured
            self.cured_behaviour()
        elif self.state['id'] == 3:  #Vaccinated
            self.vaccinated_behaviour()
        elif self.state['id'] == 4:  #Beacon-off
            self.beacon_off_behaviour()
        elif self.state['id'] == 5:  #Beacon-on
            self.beacon_on_behaviour()

        self.attrs['status'] = self.state['id']
        super().step(now)


    def neutral_behaviour(self):

        # Infected
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors)>0:
            if random.random() < self.prob_neutral_making_denier:
                self.state['id'] = 3   # Vaccinated making denier

    def infected_behaviour(self):

        # Neutral
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_infect:
                neighbor.state['id'] = 1  # Infected

    def cured_behaviour(self):

        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured


    def vaccinated_behaviour(self):

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured


        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Generate anti-rumor
        infected_neighbors_2 = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors_2:
            if random.random() < self.prob_generate_anti_rumor:
                neighbor.state['id'] = 2  # Cured

    def beacon_off_behaviour(self):
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors) > 0:
            self.state['id'] == 5  #Beacon on

    def beacon_on_behaviour(self):

        # Cure (M2 feature added)
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_generate_anti_rumor:
                neighbor.state['id'] = 2  # Cured
            neutral_neighbors_infected = neighbor.get_neighboring_agents(state_id=0)
            for neighbor in neutral_neighbors_infected:
                if random.random() < self.prob_generate_anti_rumor:
                    neighbor.state['id'] = 3  # Vaccinated
            infected_neighbors_infected = neighbor.get_neighboring_agents(state_id=1)
            for neighbor in infected_neighbors_infected:
                if random.random() < self.prob_generate_anti_rumor:
                    neighbor.state['id'] = 2  # Cured


        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated


class SpreadModelM2(BaseBehaviour):
    init_states[random.randint(0,settings.number_of_nodes)] = {'id':1}
    init_states[random.randint(0,settings.number_of_nodes)] = {'id':1}
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.prob_neutral_making_denier = np.random.normal(settings.prob_neutral_making_denier, settings.standard_variance)

        self.prob_infect = np.random.normal(settings.prob_infect, settings.standard_variance)

        self.prob_cured_healing_infected = np.random.normal(settings.prob_cured_healing_infected, settings.standard_variance)
        self.prob_cured_vaccinate_neutral = np.random.normal(settings.prob_cured_vaccinate_neutral, settings.standard_variance)

        self.prob_vaccinated_healing_infected = np.random.normal(settings.prob_vaccinated_healing_infected, settings.standard_variance)
        self.prob_vaccinated_vaccinate_neutral = np.random.normal(settings.prob_vaccinated_vaccinate_neutral, settings.standard_variance)
        self.prob_generate_anti_rumor = np.random.normal(settings.prob_generate_anti_rumor, settings.standard_variance)

    def step(self, now):

        if self.state['id'] == 0:  #Neutral
            self.neutral_behaviour()
        elif self.state['id'] == 1:  #Infected
            self.infected_behaviour()
        elif self.state['id'] == 2:  #Cured
            self.cured_behaviour()
        elif self.state['id'] == 3:  #Vaccinated
            self.vaccinated_behaviour()

        self.attrs['status'] = self.state['id']
        super().step(now)


    def neutral_behaviour(self):

        # Infected
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        if len(infected_neighbors)>0:
            if random.random() < self.prob_neutral_making_denier:
                self.state['id'] = 3   # Vaccinated making denier

    def infected_behaviour(self):

        # Neutral
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_infect:
                neighbor.state['id'] = 1  # Infected

    def cured_behaviour(self):

        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured


    def vaccinated_behaviour(self):

        # Cure
        infected_neighbors = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors:
            if random.random() < self.prob_cured_healing_infected:
                neighbor.state['id'] = 2  # Cured


        # Vaccinate
        neutral_neighbors = self.get_neighboring_agents(state_id=0)
        for neighbor in neutral_neighbors:
            if random.random() < self.prob_cured_vaccinate_neutral:
                neighbor.state['id'] = 3  # Vaccinated

        # Generate anti-rumor
        infected_neighbors_2 = self.get_neighboring_agents(state_id=1)
        for neighbor in infected_neighbors_2:
            if random.random() < self.prob_generate_anti_rumor:
                neighbor.state['id'] = 2  # Cured


class SISaModel(BaseBehaviour):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)

        self.neutral_discontent_spon_prob = np.random.normal(settings.neutral_discontent_spon_prob, settings.standard_variance)
        self.neutral_discontent_infected_prob = np.random.normal(settings.neutral_discontent_infected_prob,settings.standard_variance)
        self.neutral_content_spon_prob = np.random.normal(settings.neutral_content_spon_prob,settings.standard_variance)
        self.neutral_content_infected_prob = np.random.normal(settings.neutral_content_infected_prob,settings.standard_variance)

        self.discontent_neutral = np.random.normal(settings.discontent_neutral,settings.standard_variance)
        self.discontent_content = np.random.normal(settings.discontent_content,settings.variance_d_c)

        self.content_discontent = np.random.normal(settings.content_discontent,settings.variance_c_d)
        self.content_neutral = np.random.normal(settings.content_neutral,settings.standard_variance)

    def step(self, now):

        if self.state['id'] == 0:
            self.neutral_behaviour()
        if self.state['id'] == 1:
            self.discontent_behaviour()
        if self.state['id'] == 2:
            self.content_behaviour()

        self.attrs['status'] = self.state['id']
        super().step(now)


    def neutral_behaviour(self):

        #Spontaneus effects
        if random.random() < self.neutral_discontent_spon_prob:
            self.state['id'] = 1
        if random.random() < self.neutral_content_spon_prob:
            self.state['id'] = 2

        #Infected
        discontent_neighbors = self.get_neighboring_agents(state_id=1)
        if random.random() < len(discontent_neighbors)*self.neutral_discontent_infected_prob:
            self.state['id'] = 1
        content_neighbors = self.get_neighboring_agents(state_id=2)
        if random.random() < len(content_neighbors)*self.neutral_content_infected_prob:
            self.state['id'] = 2

    def discontent_behaviour(self):

        #Healing
        if random.random() < self.discontent_neutral:
            self.state['id'] = 0

        #Superinfected
        content_neighbors = self.get_neighboring_agents(state_id=2)
        if random.random() < len(content_neighbors)*self.discontent_content:
            self.state['id'] = 2

    def content_behaviour(self):

        #Healing
        if random.random() < self.content_neutral:
            self.state['id'] = 0

        #Superinfected
        discontent_neighbors = self.get_neighboring_agents(state_id=1)
        if random.random() < len(discontent_neighbors)*self.content_discontent:
            self.state['id'] = 1


class BigMarketModel(BaseBehaviour):

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.enterprises = settings.enterprises
        self.type = ""
        self.number_of_enterprises = len(settings.enterprises)

        if self.id < self.number_of_enterprises: #Empresas
            self.state['id']=self.id
            self.type="Enterprise"
            self.tweet_probability = settings.tweet_probability_enterprises[self.id]
        else:                       #Usuarios normales
            self.state['id']=self.number_of_enterprises
            self.type="User"
            self.tweet_probability = settings.tweet_probability_users
            self.tweet_relevant_probability = settings.tweet_relevant_probability
            self.tweet_probability_about = settings.tweet_probability_about #Lista
            self.sentiment_about = settings.sentiment_about #Lista

    def step(self, now):

        if(self.id < self.number_of_enterprises): # Empresa
            self.enterpriseBehaviour()
        else:  # Usuario
            self.userBehaviour()
            for i in range(self.number_of_enterprises):       # Para que nunca este a 0 si no ha habido cambios(logs)
                self.attrs['sentiment_enterprise_%s'% self.enterprises[i]] = self.sentiment_about[i]

        super().step(now)

    def enterpriseBehaviour(self):

        if random.random()< self.tweet_probability: #Twittea
            aware_neighbors = self.get_neighboring_agents(state_id=self.number_of_enterprises) #Nodos vecinos usuarios
            for x in aware_neighbors:
                if random.uniform(0,10) < 5:
                    x.sentiment_about[self.id] += 0.1 #Aumenta para empresa
                else:
                    x.sentiment_about[self.id] -= 0.1 #Reduce para empresa

                # Establecemos limites
                if x.sentiment_about[self.id] > 1:
                    x.sentiment_about[self.id] = 1
                if x.sentiment_about[self.id]< -1:
                    x.sentiment_about[self.id] = -1

                x.attrs['sentiment_enterprise_%s'% self.enterprises[self.id]] = x.sentiment_about[self.id]


    def userBehaviour(self):

        if random.random() < self.tweet_probability: #Twittea
            if random.random() < self.tweet_relevant_probability: #Twittea algo relevante
                #Probabilidad de tweet para cada empresa
                for i in range(self.number_of_enterprises):
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
        aware_neighbors = self.get_neighboring_agents(state_id=self.number_of_enterprises) #Nodos vecinos usuarios
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

            x.attrs['sentiment_enterprise_%s'% self.enterprises[enterprise]] = x.sentiment_about[enterprise]

class SentimentCorrelationModel(BaseBehaviour):

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
        sentimentCorrelationNodeArray[self.id][self.env.now]=0


    def step(self, now):
        self.behaviour()
        super().step(now)

    def behaviour(self):

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

            sentimentCorrelationNodeArray[self.id][self.env.now]=self.state['id'] #Almaceno cuando se ha infectado para la red dinamica
            self.time_awareness[self.state['id']-1] = self.env.now
            self.attrs['sentiment'] = self.state['id']



        if(num<anger_prob):

            self.state['id'] = 1
            sentimentCorrelationNodeArray[self.id][self.env.now]=1
            self.time_awareness[self.state['id']-1] = self.env.now
        elif (num<joy_prob+anger_prob and num>anger_prob):

            self.state['id'] = 2
            sentimentCorrelationNodeArray[self.id][self.env.now]=2
            self.time_awareness[self.state['id']-1] = self.env.now
        elif (num<sadness_prob+anger_prob+joy_prob and num>joy_prob+anger_prob):


            self.state['id'] = 3
            sentimentCorrelationNodeArray[self.id][self.env.now]=3
            self.time_awareness[self.state['id']-1] = self.env.now
        elif (num<disgust_prob+sadness_prob+anger_prob+joy_prob and num>sadness_prob+anger_prob+joy_prob):


            self.state['id'] = 4
            sentimentCorrelationNodeArray[self.id][self.env.now]=4
            self.time_awareness[self.state['id']-1] = self.env.now

        self.attrs['sentiment'] = self.state['id']


class BassModel(BaseBehaviour):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.innovation_prob = settings.innovation_prob
        self.imitation_prob = settings.imitation_prob
        sentimentCorrelationNodeArray[self.id][self.env.now]=0

    def step(self, now):
        self.behaviour()
        super().step(now)

    def behaviour(self):
        #Outside effects
        if random.random() < settings.innovation_prob:
            if self.state['id'] == 0:
                self.state['id'] = 1
                sentimentCorrelationNodeArray[self.id][self.env.now]=1
            else:
                pass

            self.attrs['status'] = self.state['id']
            return

        #Imitation effects
        if self.state['id'] == 0:
            aware_neighbors = self.get_neighboring_agents(state_id=1)
            num_neighbors_aware = len(aware_neighbors)
            if random.random() < (settings.imitation_prob*num_neighbors_aware):
                self.state['id'] = 1
                sentimentCorrelationNodeArray[self.id][self.env.now]=1

            else:
                pass
            self.attrs['status'] = self.state['id']


class IndependentCascadeModel(BaseBehaviour):
    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.innovation_prob = settings.innovation_prob
        self.imitation_prob = settings.imitation_prob
        self.time_awareness = 0
        sentimentCorrelationNodeArray[self.id][self.env.now]=0

    def step(self,now):
        self.behaviour()
        super().step(now)

    def behaviour(self):
        aware_neighbors_1_time_step=[]
            #Outside effects
        if random.random() < settings.innovation_prob:
            if self.state['id'] == 0:
                self.state['id'] = 1
                sentimentCorrelationNodeArray[self.id][self.env.now]=1
                self.time_awareness = self.env.now #Para saber cuando se han contagiado

            else:
                pass

            self.attrs['status'] = self.state['id']
            return

        #Imitation effects
        if self.state['id'] == 0:
            aware_neighbors = self.get_neighboring_agents(state_id=1)
            for x in aware_neighbors:
                if x.time_awareness == (self.env.now-1):
                    aware_neighbors_1_time_step.append(x)
            num_neighbors_aware = len(aware_neighbors_1_time_step)
            if random.random() < (settings.imitation_prob*num_neighbors_aware):
                self.state['id'] = 1
                sentimentCorrelationNodeArray[self.id][self.env.now]=1
            else:
                pass

            self.attrs['status'] = self.state['id']
            return
