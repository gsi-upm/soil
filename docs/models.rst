Developing new models
---------------------
This document describes how to develop a new analysis model.

What is a model?
================

A model defines the behaviour of the agents with a view to assessing their effects on the system as a whole.
In practice, a model consists of at least two parts:

* Python module: the actual code that describes the behaviour.
* Setting up the variables in the Settings JSON file.

This separation allows us to run the simulation with different agents.

Models Code
===========

All the models are imported to the main file. The initialization look like this:

.. code:: python

    import settings

    networkStatus = {}  # Dict that will contain the status of every agent in the network

    sentimentCorrelationNodeArray = []
    for x in range(0, settings.network_params["number_of_nodes"]):
        sentimentCorrelationNodeArray.append({'id': x})
    # Initialize agent states. Let's assume everyone is normal.
    init_states = [{'id': 0, } for _ in range(settings.network_params["number_of_nodes"])]
        # add keys as as necessary, but "id" must always refer to that state category

A new model have to inherit the BaseBehaviour class which is in the same module.
There are two basics methods:

* __init__
* step: used to define the behaviour over time.

Variable Initialization
=======================

The different parameters of the model have to be initialize in the Simulation Settings JSON file which will be
passed as a parameter to the simulation.

.. code:: json

    {
        "agent": ["SISaModel","ControlModelM2"],

        "neutral_discontent_spon_prob": 0.04,
        "neutral_discontent_infected_prob": 0.04,
        "neutral_content_spon_prob": 0.18,
        "neutral_content_infected_prob": 0.02,

        "discontent_neutral": 0.13,
        "discontent_content": 0.07,
        "variance_d_c": 0.02,

        "content_discontent": 0.009,
        "variance_c_d": 0.003,
        "content_neutral": 0.088,

        "standard_variance": 0.055,


        "prob_neutral_making_denier": 0.035,

        "prob_infect": 0.075,

        "prob_cured_healing_infected": 0.035,
        "prob_cured_vaccinate_neutral": 0.035,

        "prob_vaccinated_healing_infected": 0.035,
        "prob_vaccinated_vaccinate_neutral": 0.035,
        "prob_generate_anti_rumor": 0.035
    }

In this file you will also define the models you are going to simulate. You can simulate as many models as you want.
The simulation returns one result for each model, executing each model separately. For the usage, see :doc:`usage`.

Example Model
=============

In this section, we will implement a Sentiment Correlation Model.

The class would look like this:

.. code:: python

    from ..BaseBehaviour import *
    from .. import sentimentCorrelationNodeArray

    class SentimentCorrelationModel(BaseBehaviour):

        def __init__(self, environment=None, agent_id=0, state=()):
            super().__init__(environment=environment, agent_id=agent_id, state=state)
            self.outside_effects_prob = environment.environment_params['outside_effects_prob']
            self.anger_prob = environment.environment_params['anger_prob']
            self.joy_prob = environment.environment_params['joy_prob']
            self.sadness_prob = environment.environment_params['sadness_prob']
            self.disgust_prob = environment.environment_params['disgust_prob']
            self.time_awareness = []
            for i in range(4):  # In this model we have 4 sentiments
                self.time_awareness.append(0)  # 0-> Anger, 1-> joy, 2->sadness, 3 -> disgust
            sentimentCorrelationNodeArray[self.id][self.env.now] = 0

        def step(self, now):
            self.behaviour()  # Method which define the behaviour
            super().step(now)

The variables will be modified by the user, so you have to include them in the Simulation Settings JSON file.