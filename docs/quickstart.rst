Quickstart
----------

This section shows how to run simulations from simulation configuration files.
First of all, you need to install the package (See :doc:`installation`)

Simulation configuration files are ``json`` or ``yaml`` files that define all the parameters of a simulation.
Here's an example (``example.yml``).

.. code:: yaml
          
    ---
    name: MyExampleSimulation
    max_time: 50
    num_trials: 3
    timeout: 2
    network_params:
        network_type: barabasi_albert_graph
        n: 100
        m: 2
    agent_distribution:
        - agent_type: SISaModel
            weight: 1
            state:
            id: content
        - agent_type: SISaModel
            weight: 1
            state:
            id: discontent
        - agent_type: SISaModel
            weight: 8
            state:
            id: neutral
    environment_params:
        prob_infect: 0.075

Now run the simulation with the command line tool:

.. code:: bash

   soil example.yml

Once the simulation finishes, its results will be stored in a folder named ``MyExampleSimulation``.
Four types of objects are saved by default: a pickle of the simulation, a ``YAML`` representation of the simulation (to re-launch it), for every trial, a csv file with the content of the state of every network node and the environment parameters at every step of the simulation as well as the network in gephi format (``gexf``).


.. code::

    soil_output
    ├── Sim_prob_0
    │   ├── Sim_prob_0.dumped.yml
    │   ├── Sim_prob_0.simulation.pickle
    │   ├── Sim_prob_0_trial_0.environment.csv
    │   └── Sim_prob_0_trial_0.gexf


This example configuration will run three trials of a simulation containing a randomly generated network.
The 100 nodes in the network will be SISaModel agents, 10% of them will start in the content state, 10% in the discontent state, and the remaining 80% in the neutral state.
All agents will have access to the environment, which only contains one variable, ``prob_infected``.
The state of the agents will be updated every 2 seconds (``timeout``).


Network
=======

The network topology for the simulation can be loaded from an existing network file or generated with one of the random network generation methods from networkx.

Loading a network
#################

To load an existing network, specify its path in the configuration:

.. code:: yaml

   ---
   network_params:
      path: /tmp/mynetwork.gexf

Soil will try to guess what networkx method to use to read the file based on its extension.
However, we only test using ``gexf`` files.

Generating a random network
###########################

To generate a random network using one of networkx's built-in methods, specify the `graph generation algorithm <https://networkx.github.io/documentation/development/reference/generators.html>`_ and other parameters.
For example, the following configuration is equivalent to :code:`nx.complete_graph(100)`:

.. code:: yaml

    network_params:
        network_type: complete_graph
        n: 100

Environment
============
The environment is the place where the shared state of the simulation is stored.
For instance, the probability of certain events.
The configuration file may specify the initial value of the environment parameters:

.. code:: yaml

    environment_params:
        daily_probability_of_earthquake: 0.001
        number_of_earthquakes: 0

Agents
======
Agents are a way of modelling behavior.
Agents can be characterized with two variables: an agent type (``agent_type``) and its state.
Only one agent is executed at a time (generally, every ``timeout`` seconds), and it has access to its state and the environment parameters.
Through the environment, it can access the network topology and the state of other agents.

There are three three types of agents according to how they are added to the simulation: network agents, environment agent, and other agents.

Network Agents
##############
Network agents are attached to a node in the topology.
The configuration file allows you to specify how agents will be mapped to topology nodes.

The simplest way is to specify a single type of agent.
Hence, every node in the network will have an associated agent of that type.

.. code:: yaml

   agent_type: SISaModel

It is also possible to add more than one type of agent to the simulation, and to control the ratio of each type (``weight``).
For instance, with following configuration, it is five times more likely for a node to be assigned a CounterModel type than a SISaModel type.

.. code:: yaml

   agent_distribution:
      - agent_type: SISaModel
        weight: 1
      - agent_type: CounterModel
        weight: 5

In addition to agent type, you may also add a custom initial state to the distribution.
This is very useful to add the same agent type with different states.
e.g., to populate the network with SISaModel, roughly 10% of them with a discontent state:

.. code:: yaml

    agent_distribution:
        - agent_type: SISaModel
            weight: 9
            state:
            id: neutral
        - agent_type: SISaModel
            weight: 1
            state:
            id: discontent

Lastly, the configuration may include initial state for one or more nodes.
For instance, to add a state for the two nodes in this configuration:

.. code:: yaml

   agent_type: SISaModel
   network:
      network_type: complete_graph
      n: 2
   states:
     - id: content
     - id: discontent


Or to add state only to specific nodes (by ``id``).
For example, to apply special skills to Linux Torvalds in a simulation:

.. literalinclude:: ../examples/torvalds.yml
   :language: yaml


Environment Agents
##################
In addition to network agents, more agents can be added to the simulation.
These agens are programmed in much the same way as network agents, the only difference is that they will not be assigned to network nodes.


.. code::

   environment_agents:
       - agent_type: MyAgent
         state:
           mood: happy
       - agent_type: DummyAgent


Visualizing the results
=======================

The simulation will return a dynamic graph .gexf file which could be visualized with
`Gephi <https://gephi.org/users/download/>`__.
