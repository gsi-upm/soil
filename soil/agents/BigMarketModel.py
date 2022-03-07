import random
from . import FSM, state, default_state


class BigMarketModel(FSM):
    """
    Settings:
        Names:
            enterprises [Array]
            
            tweet_probability_enterprises [Array]
        Users:
            tweet_probability_users
            
            tweet_relevant_probability
            
            tweet_probability_about [Array]
            
            sentiment_about [Array]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enterprises = self.env.environment_params['enterprises']
        self.type = ""

        if self.id < len(self.enterprises):  # Enterprises
            self.set_state(self.enterprise.id)
            self.type = "Enterprise"
            self.tweet_probability = environment.environment_params['tweet_probability_enterprises'][self.id]
        else:  # normal users
            self.type = "User"
            self.set_state(self.user.id)
            self.tweet_probability = environment.environment_params['tweet_probability_users']
            self.tweet_relevant_probability = environment.environment_params['tweet_relevant_probability']
            self.tweet_probability_about = environment.environment_params['tweet_probability_about']  # List
            self.sentiment_about = environment.environment_params['sentiment_about']  # List

    @state
    def enterprise(self):

        if random.random() < self.tweet_probability:  # Tweets
            aware_neighbors = self.get_neighboring_agents(state_id=self.number_of_enterprises)  # Nodes neighbour users
            for x in aware_neighbors:
                if random.uniform(0,10) < 5:
                    x.sentiment_about[self.id] += 0.1  # Increments for enterprise
                else:
                    x.sentiment_about[self.id] -= 0.1  # Decrements for enterprise

                # Establecemos limites
                if x.sentiment_about[self.id] > 1:
                    x.sentiment_about[self.id] = 1
                if x.sentiment_about[self.id]< -1:
                    x.sentiment_about[self.id] = -1

                x.attrs['sentiment_enterprise_%s'% self.enterprises[self.id]] = x.sentiment_about[self.id]

    @state
    def user(self):
        if random.random() < self.tweet_probability:  # Tweets
            if random.random() < self.tweet_relevant_probability:  # Tweets something relevant
                # Tweet probability per enterprise
                for i in range(len(self.enterprises)):
                    random_num = random.random()
                    if random_num < self.tweet_probability_about[i]:
                        # The condition is fulfilled, sentiments are evaluated towards that enterprise
                        if self.sentiment_about[i] < 0:
                            # NEGATIVO
                            self.userTweets("negative",i)
                        elif self.sentiment_about[i] == 0:
                            # NEUTRO
                            pass
                        else:
                            # POSITIVO
                            self.userTweets("positive",i)
        for i in range(len(self.enterprises)):  # So that it never is set to 0 if there are not changes (logs)
            self.attrs['sentiment_enterprise_%s'% self.enterprises[i]] = self.sentiment_about[i]

    def userTweets(self, sentiment,enterprise):
        aware_neighbors = self.get_neighboring_agents(state_id=self.number_of_enterprises)  # Nodes neighbours users
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
