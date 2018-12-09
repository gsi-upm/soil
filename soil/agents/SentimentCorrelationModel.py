import random
from . import BaseAgent


class SentimentCorrelationModel(BaseAgent):
    """
    Settings:
        outside_effects_prob
        
        anger_prob
        
        joy_prob
        
        sadness_prob
        
        disgust_prob
    """

    def __init__(self, environment, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
        self.outside_effects_prob = environment.environment_params['outside_effects_prob']
        self.anger_prob = environment.environment_params['anger_prob']
        self.joy_prob = environment.environment_params['joy_prob']
        self.sadness_prob = environment.environment_params['sadness_prob']
        self.disgust_prob = environment.environment_params['disgust_prob']
        self.state['time_awareness'] = []
        for i in range(4):  # In this model we have 4 sentiments
            self.state['time_awareness'].append(0)  # 0-> Anger, 1-> joy, 2->sadness, 3 -> disgust
        self.state['sentimentCorrelation'] = 0

    def step(self):
        self.behaviour()

    def behaviour(self):

        angry_neighbors_1_time_step = []
        joyful_neighbors_1_time_step = []
        sad_neighbors_1_time_step = []
        disgusted_neighbors_1_time_step = []

        angry_neighbors = self.get_neighboring_agents(state_id=1)
        for x in angry_neighbors:
            if x.state['time_awareness'][0] > (self.env.now-500):
                angry_neighbors_1_time_step.append(x)
        num_neighbors_angry = len(angry_neighbors_1_time_step)

        joyful_neighbors = self.get_neighboring_agents(state_id=2)
        for x in joyful_neighbors:
            if x.state['time_awareness'][1] > (self.env.now-500):
                joyful_neighbors_1_time_step.append(x)
        num_neighbors_joyful = len(joyful_neighbors_1_time_step)

        sad_neighbors = self.get_neighboring_agents(state_id=3)
        for x in sad_neighbors:
            if x.state['time_awareness'][2] > (self.env.now-500):
                sad_neighbors_1_time_step.append(x)
        num_neighbors_sad = len(sad_neighbors_1_time_step)

        disgusted_neighbors = self.get_neighboring_agents(state_id=4)
        for x in disgusted_neighbors:
            if x.state['time_awareness'][3] > (self.env.now-500):
                disgusted_neighbors_1_time_step.append(x)
        num_neighbors_disgusted = len(disgusted_neighbors_1_time_step)

        anger_prob = self.anger_prob+(len(angry_neighbors_1_time_step)*self.anger_prob)
        joy_prob = self.joy_prob+(len(joyful_neighbors_1_time_step)*self.joy_prob)
        sadness_prob = self.sadness_prob+(len(sad_neighbors_1_time_step)*self.sadness_prob)
        disgust_prob = self.disgust_prob+(len(disgusted_neighbors_1_time_step)*self.disgust_prob)
        outside_effects_prob = self.outside_effects_prob

        num = random.random()

        if num<outside_effects_prob:
            self.state['id'] = random.randint(1, 4)

            self.state['sentimentCorrelation'] = self.state['id'] # It is stored when it has been infected for the dynamic network
            self.state['time_awareness'][self.state['id']-1] = self.env.now
            self.state['sentiment'] = self.state['id']


        if(num<anger_prob):

            self.state['id'] = 1
            self.state['sentimentCorrelation'] = 1
            self.state['time_awareness'][self.state['id']-1] = self.env.now
        elif (num<joy_prob+anger_prob and num>anger_prob):

            self.state['id'] = 2
            self.state['sentimentCorrelation'] = 2
            self.state['time_awareness'][self.state['id']-1] = self.env.now
        elif (num<sadness_prob+anger_prob+joy_prob and num>joy_prob+anger_prob):

            self.state['id'] = 3
            self.state['sentimentCorrelation'] = 3
            self.state['time_awareness'][self.state['id']-1] = self.env.now
        elif (num<disgust_prob+sadness_prob+anger_prob+joy_prob and num>sadness_prob+anger_prob+joy_prob):

            self.state['id'] = 4
            self.state['sentimentCorrelation'] = 4
            self.state['time_awareness'][self.state['id']-1] = self.env.now

        self.state['sentiment'] = self.state['id']
