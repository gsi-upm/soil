Quickstart
----------

This section shows how to run your first simulation with Soil.
For installation instructions, see :doc:`installation`.

There are mainly two parts in a simulation: agent classes and simulation configuration.
An agent class defines how the agent will behave throughout the simulation.
The configuration includes things such as number of agents to use and their type, network topology to use, etc.


.. image:: soil.png
  :width: 80%
  :align: center


Soil includes several agent classes in the ``soil.agents`` module, and we will use them in this quickstart.
If you are interested in developing your own agents classes, see :doc:`soil_tutorial`.
The configuration is the following:

.. literalinclude:: quickstart.yml
   :language: yaml

Configuration
=============

You may :download:`download the file <quickstart.yml>` directly.
The agent type used, SISa, is a very simple model.
It only has three states (neutral, content and discontent),
Its parameters are the probabilities to change from one state to another, either spontaneously or because of contagion from neighboring agents.

Running the simulation
======================

To see the simulation in action, simply point soil to the configuration, and tell it to store the graph and the history of agent states and environment parameters at every point.

.. code::

    ❯ soil --graph --csv quickstart.yml                                                          [13:35:29]
    INFO:soil:Using config(s): quickstart
    INFO:soil:Dumping results to soil_output/quickstart : ['csv', 'gexf']
    INFO:soil:Starting simulation quickstart at 13:35:30.
    INFO:soil:Starting Simulation quickstart trial 0 at 13:35:30.
    INFO:soil:Finished Simulation quickstart trial 0 at 13:35:49 in 19.43677067756653 seconds
    INFO:soil:Starting Dumping simulation quickstart trial 0 at 13:35:49.
    INFO:soil:Finished Dumping simulation quickstart trial 0 at 13:35:51 in 1.7733407020568848 seconds
    INFO:soil:Dumping results to soil_output/quickstart
    INFO:soil:Finished simulation quickstart at 13:35:51 in 21.29862952232361 seconds


The ``CSV`` file should look like this:

.. code::

   agent_id,t_step,key,value
   env,0,neutral_discontent_spon_prob,0.05
   env,0,neutral_discontent_infected_prob,0.1
   env,0,neutral_content_spon_prob,0.2
   env,0,neutral_content_infected_prob,0.4
   env,0,discontent_neutral,0.2
   env,0,discontent_content,0.05
   env,0,content_discontent,0.05
   env,0,variance_d_c,0.05
   env,0,variance_c_d,0.1

Results and visualization
=========================

The environment variables are marked as ``agent_id`` env.
Th exported values are only stored when they change.
To find out how to get every key and value at every point in the simulation, check out the :doc:`soil_tutorial`.

The dynamic graph is exported as a .gexf file which could be visualized with
`Gephi <https://gephi.org/users/download/>`__.
Now it is your turn to experiment with the simulation.
Change some of the parameters, such as the number of agents, the probability of becoming content, or the type of network, and see how the results change.


Soil also includes a web server that allows you to upload your simulations, change parameters, and visualize the results, including a timeline of the network.
To make it work, you have to install soil like this:

```
pip install soil[web]
```

Once installed, the soil web UI can be run in two ways:

```
soil-web

OR

python -m soil.web
```