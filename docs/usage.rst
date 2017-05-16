Usage
-----

First of all, you need to install the package. See :doc:`installation` for installation instructions.

Simulation Settings
===================

Once installed, before running a simulation, you need to configure it.

* In the Settings JSON file you will find the configuration of the network.

  .. code:: python

    {
        "network_type": 1,
        "number_of_nodes": 1000,
        "max_time": 50,
        "num_trials": 1,
        "timeout": 2
    }

* In the Settings JSON file, you will also find the configuration of the models.

Network Types
=============

There are three types of network implemented, but you could add more.

.. code:: python

    if settings.network_type == 0:
        G = nx.complete_graph(settings.number_of_nodes)
    if settings.network_type == 1:
        G = nx.barabasi_albert_graph(settings.number_of_nodes, 10)
    if settings.network_type == 2:
        G = nx.margulis_gabber_galil_graph(settings.number_of_nodes, None)
    # More types of networks can be added here

Models Settings
===============

After having configured the simulation, the next step is setting up the variables of the models.
For this, you will need to modify the Settings JSON file again.

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

In this file you will define the different models you are going to simulate. You can simulate as many models
as you want. Each model will be simulated separately.

After setting up the models, you have to initialize the parameters of each one. You will find the parameters needed
in the documentation of each model.

Parameter validation will fail if a required parameter without a default has not been provided.

Running the Simulation
======================

After setting all the configuration, you will be able to run the simulation. All you need to do is execute:

.. code:: bash

    python3 soil.py

The simulation will return a dynamic graph .gexf file which could be visualized with
`Gephi <https://gephi.org/users/download/>`__.

It will also return one .png picture for each model simulated.
