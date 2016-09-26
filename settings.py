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
    global enterprises
    global neutral_discontent_spon_prob
    global neutral_discontent_infected_prob
    global neutral_content_spon_prob
    global neutral_content_infected_prob
    global discontent_content
    global discontent_neutral
    global content_discontent
    global content_neutral
    global variance_d_c
    global variance_c_d
    global standard_variance
    global prob_neutral_making_denier
    global prob_infect
    global prob_cured_healing_infected
    global prob_cured_vaccinate_neutral
    global prob_vaccinated_healing_infected
    global prob_vaccinated_vaccinate_neutral
    global prob_generate_anti_rumor

    network_type=1
    number_of_nodes=1000
    max_time=50
    num_trials=1
    timeout=2

    #Zombie model
    bite_prob=0.01 # 0-1
    heal_prob=0.01 # 0-1

    #Bass model
    innovation_prob=0.001
    imitation_prob=0.005

    #Sentiment Correlation model
    outside_effects_prob = 0.2
    anger_prob = 0.06
    joy_prob = 0.05
    sadness_prob = 0.02
    disgust_prob = 0.02

    #Big Market model
    ##Names
    enterprises = ["BBVA","Santander", "Bankia"]
    ##Users
    tweet_probability_users = 0.44
    tweet_relevant_probability = 0.25
    tweet_probability_about = [0.15, 0.15, 0.15]
    sentiment_about = [0, 0, 0] #Default values
    ##Enterprises
    tweet_probability_enterprises = [0.3, 0.3, 0.3]

    #SISa
    neutral_discontent_spon_prob = 0.04
    neutral_discontent_infected_prob = 0.04
    neutral_content_spon_prob = 0.18
    neutral_content_infected_prob = 0.02

    discontent_neutral = 0.13
    discontent_content = 0.07
    variance_d_c = 0.02

    content_discontent = 0.009
    variance_c_d = 0.003
    content_neutral = 0.088

    standard_variance = 0.055

    #Spread Model M2 and Control Model M2
    prob_neutral_making_denier = 0.035

    prob_infect = 0.075

    prob_cured_healing_infected = 0.035
    prob_cured_vaccinate_neutral = 0.035

    prob_vaccinated_healing_infected = 0.035
    prob_vaccinated_vaccinate_neutral = 0.035
    prob_generate_anti_rumor = 0.035



