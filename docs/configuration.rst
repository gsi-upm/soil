Configuring a simulation
------------------------

There are two ways to configure a simulation: programmatically and with a configuration file.
In both cases, the parameters used are the same.
The advantage of a configuration file is that it is a clean declarative description, and it makes it easier to reproduce.

Simulation configuration files can be formatted in ``json`` or ``yaml`` and they define all the parameters of a simulation.
Here's an example (``example.yml``).

.. literalinclude:: example.yml
   :language: yaml


This example configuration will run three trials (``num_trials``) of a simulation containing a randomly generated network (``network_params``).
The 100 nodes in the network will be SISaModel agents (``network_agents.agent_type``), which is an agent behavior that is included in Soil.
10% of the agents (``weight=1``) will start in the content state, 10% in the discontent state, and the remaining 80% (``weight=8``) in the neutral state.
All agents will have access to the environment (``environment_params``), which only contains one variable, ``prob_infected``.
The state of the agents will be updated every 2 seconds (``interval``).

Now run the simulation with the command line tool:

.. code:: bash

   soil example.yml

Once the simulation finishes, its results will be stored in a folder named ``MyExampleSimulation``.
Three types of objects are saved by default: a pickle of the simulation; a ``YAML`` representation of the simulation (which can be used to re-launch it); and for every trial, a ``sqlite`` file with the content of the state of every network node and the environment parameters at every step of the simulation.


.. code::

    soil_output
    └── MyExampleSimulation
        ├── MyExampleSimulation.dumped.yml
        ├── MyExampleSimulation.simulation.pickle
        ├── MyExampleSimulation_trial_0.db.sqlite
        ├── MyExampleSimulation_trial_1.db.sqlite
        └── MyExampleSimulation_trial_2.db.sqlite


You may also ask soil to export the states in a ``csv`` file, and the network in gephi format (``gexf``).

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

For simple networks, you may also include them in the configuration itself using , using the ``topology`` parameter like so:

.. code:: yaml

   ---
   topology:
       nodes:
          - id: First
          - id: Second
       links:
          - source: First
            target: Second


Generating a random network
###########################

To generate a random network using one of networkx's built-in methods, specify the `graph generation algorithm <https://networkx.github.io/documentation/development/reference/generators.html>`_ and other parameters.
For example, the following configuration is equivalent to :code:`nx.complete_graph(n=100)`:

.. code:: yaml

    network_params:
        generator: complete_graph
        n: 100

Environment
============

The environment is the place where the shared state of the simulation is stored.
That means both global parameters, such as the probability of disease outbreak.
But it also means other data, such as a map, or a network topology that connects multiple agents.
As a result, it is also typical to add custom functions in an environment that help agents interact with each other and with the state of the simulation.

Last but not least, an environment controls when and how its agents will be executed.
By default, soil environments incorporate a ``soil.time.TimedActivation`` model for agent execution (more on this on the following section).

Soil environments are very similar, and often interchangeable with, mesa models (``mesa.Model``).

A configuration may specify the initial value of the environment parameters:

.. code:: yaml

    environment_params:
        daily_probability_of_earthquake: 0.001
        number_of_earthquakes: 0

All agents have access to the environment (and its parameters).

In some scenarios, it is useful to have a custom environment, to provide additional methods or to control the way agents update environment state.
For example, if our agents play the lottery, the environment could provide a method to decide whether the agent wins, instead of leaving it to the agent.

Agents
======

Agents are a way of modelling behavior.
Agents can be characterized with two variables: agent type (``agent_type``) and state.
The agent type is a ``soil.Agent`` class, which contains the code that encapsulates the behavior of the agent.
The state is a set of variables, which may change during the simulation, and that the code may use to control the behavior.
All agents provide a ``step`` method either explicitly or implicitly (by inheriting it from a superclass), which controls how the agent will behave in each step of the simulation.

When and how agent steps are executed in a simulation depends entirely on the ``environment``.
Most environments will internally use a scheduler (``mesa.time.BaseScheduler``), which controls the activation of agents.

In soil, we generally used the ``soil.time.TimedActivation`` scheduler, which allows agents to specify when their next activation will happen, defaulting to a 

When an agent's step is executed (generally, every ``interval`` seconds), the agent has access to its state and the environment.
Through the environment, it can access the network topology and the state of other agents.

There are two types of agents according to how they are added to the simulation: network agents and environment agent.

Network Agents
##############

Network agents are attached to a node in the topology.
The configuration file allows you to specify how agents will be mapped to topology nodes.

The simplest way is to specify a single type of agent.
Hence, every node in the network will be associated to an agent of that type.

.. code:: yaml

   agent_type: SISaModel

It is also possible to add more than one type of agent to the simulation.

To control the ratio of each type (using the ``weight`` property).
For instance, with following configuration, it is five times more likely for a node to be assigned a CounterModel type than a SISaModel type.

.. code:: yaml

    network_agents:
          - agent_type: SISaModel
            weight: 1
          - agent_type: CounterModel
            weight: 5

The third option is to specify the type of agent on the node itself, e.g.:


.. code:: yaml

   topology:
       nodes:
           - id: first
   agent_type: BaseAgent
   states:
       first:
         agent_type: SISaModel
          

This would also work with a randomly generated network:


.. code:: yaml

   network:
       generator: complete
       n: 5
   agent_type: BaseAgent
   states:
       - agent_type: SISaModel

              

In addition to agent type, you may add a custom initial state to the distribution.
This is very useful to add the same agent type with different states.
e.g., to populate the network with SISaModel, roughly 10% of them with a discontent state:

.. code:: yaml

    network_agents:
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
      generator: complete_graph
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
These agents are programmed in much the same way as network agents, the only difference is that they will not be assigned to network nodes.


.. code::

   environment_agents:
       - agent_type: MyAgent
         state:
           mood: happy
       - agent_type: DummyAgent


You may use environment agents to model events that a normal agent cannot control, such as natural disasters or chance.
They are also useful to add behavior that has little to do with the network and the interactions within that network.

Templating
==========

Sometimes, it is useful to parameterize a simulation and run it over a range of values in order to compare each run and measure the effect of those parameters in the simulation.
For instance, you may want to run a simulation with different agent distributions.

This can be done in Soil using **templates**.
A template is a configuration where some of the values are specified with a variable.
e.g.,  ``weight: "{{ var1 }}"`` instead of ``weight: 1``.
There are two types of variables, depending on how their values are decided:

* Fixed. A list of values is provided, and a new simulation is run for each possible value. If more than a variable is given, a new simulation will be run per combination of values.
* Bounded/Sampled. The bounds of the variable are provided, along with a sampler method, which will be used to compute all the configuration combinations.

When fixed and bounded variables are mixed, Soil generates a new configuration per combination of fixed values and bounded values.

Here is an example with a single fixed variable and two bounded variable:

.. literalinclude:: ../examples/template.yml
   :language: yaml
