# settings.py
def init():
    global number_of_nodes
    global max_time
    global num_trials
    global bite_prob
    global network_type
    global heal_prob
    global innovation_prob
    global imitation_prob
    global timeout
    global outside_effects_prob
    global anger_prob
    global joy_prob
    global sadness_prob
    global disgust_prob
    global tweet_probability_users
    global tweet_relevant_probability
    global tweet_probability_about
    global sentiment_about
    global tweet_probability_enterprises

    network_type=1
    number_of_nodes=200
    max_time=1000
    num_trials=1
    timeout=10

    #Zombie model
    bite_prob=0.01 # 0-1
    heal_prob=0.01 # 0-1

    #Bass model
    innovation_prob=0.01
    imitation_prob=0.01

    #Sentiment Correlation model
    outside_effects_prob = 0.2
    anger_prob = 0.08
    joy_prob = 0.05
    sadness_prob = 0.02
    disgust_prob = 0.02

    #Big Market model
    ##Users
    tweet_probability_users = 0.44
    tweet_relevant_probability = 0.25
    tweet_probability_about = [0, 0]
    sentiment_about = [0, 0] #Valores por defecto
    ##Enterprises
    tweet_probability_enterprises = [0.5, 0.5]

