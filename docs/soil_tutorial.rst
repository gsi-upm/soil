Soil Tutorial
=============

Introduction
------------

This notebook is an introduction to the soil agent-based social network
simulation framework. In particular, we will focus on a specific use
case: studying the propagation of news in a social network.

The steps we will follow are:

-  Modelling the behavior of agents
-  Running the simulation using different configurations
-  Analysing the results of each simulation

But before that, let’s import the soil module and networkx.

.. code:: ipython3

    import soil
    import networkx as nx
     
    %load_ext autoreload
    %autoreload 2
    
    %matplotlib inline
    # To display plots in the notebooed_

Basic concepts
--------------

There are three main elements in a soil simulation:

-  The network topology. A simulation may use an existing NetworkX
   topology, or generate one on the fly
-  Agents. There are two types: 1) network agents, which are linked to a
   node in the topology, and 2) environment agents, which are freely
   assigned to the environment.
-  The environment. It assigns agents to nodes in the network, and
   stores the environment parameters (shared state for all agents).

Soil is based on ``simpy``, which is an event-based network simulation
library. Soil provides several abstractions over events to make
developing agents easier. This means you can use events (timeouts,
delays) in soil, but for the most part we will assume your models will
be step-based.

Modeling behaviour
------------------

Our first step will be to model how every person in the social network
reacts when it comes to news. We will follow a very simple model (a
finite state machine).

There are two types of people, those who have heard about a newsworthy
event (infected) or those who have not (neutral). A neutral person may
heard about the news either on the TV (with probability
**prob_tv_spread**) or through their friends. Once a person has heard
the news, they will spread it to their friends (with a probability
**prob_neighbor_spread**). Some users do not have a TV, so they only
rely on their friends.

The spreading probabilities will change over time due to different
factors. We will represent this variance using an environment agent.

Network Agents
~~~~~~~~~~~~~~

A basic network agent in Soil would typically inherit from
``soil.agents.NetworkAgent``, and define its behaviour in every step of
the simulation by implementing a ``run(self)`` method. The most
important attributes of the agent are:

-  ``agent.state``, a dictionary with the state of the agent. This tate
   will be saved in every step of the simulation. It can be accessed
   from the agent as well:

.. code:: py

   a = soil.agents.NetworkAgent(env=env)
   agent.state['hours_of_sleep'] = 10
   # is the same as
   a['hours_of_sleep'] = 10

The state of the agent is stored in every step of the simulation:
``py   print(a['hours_of_sleep', 10]) # hours of sleep before step #10   print(a[None, 0]) # whole state of the agent before step #0``

-  ``agent.env``, a reference to the environment. Most commonly used to
   get access to the environment parameters and the topology: \```py
   a.env.G.nodes() # Get all nodes ids in the topology
   a.env[‘minimum_hours_of_sleep’]

   \``\`

Since our model is a finite state machine, we will be basing it on
``soil.agents.FSM``.

Agents that inherit from ``soil.agents.FSM`` do not need to specify a
``step`` method. Instead, we describe each finite state with a function.
To change to another state, a function may return the new state, or the
``id`` of a state. If no state is returned, the state remains unchanged.

The current state of the agent can be checked with
``agent.state['id']``. That state id can be used to look for other
networks in that specific state

Our agent will have of two states, ``neutral`` (default) and
``infected``.

Here’s the code:

.. code:: ipython3

    import random
    
    class NewsSpread(soil.agents.FSM):
        @soil.agents.default_state
        @soil.agents.state
        def neutral(self):
            r = random.random()
            if self['has_tv'] and r <= self.env['prob_tv_spread']:
                    return self.infected
            return
        
        @soil.agents.state
        def infected(self):
            prob_infect = self.env['prob_neighbor_spread']
            for neighbor in self.get_neighboring_agents(state_id=self.neutral.id):
                r = random.random()
                if r < prob_infect:
                    neighbor.set_state(self.infected.id)
            return
            

Environment agents
~~~~~~~~~~~~~~~~~~

Environment agents allow us to control the state of the environment. In
this case, we will use an environment agent to simulate a very viral
event.

When the event happens, the agent will modify the probability of
spreading the rumor.

.. code:: ipython3

    NEIGHBOR_FACTOR = 0.9
    TV_FACTOR = 0.5
    
    
    class NewsEnvironmentAgent(soil.agents.NetworkAgent):
        def step(self):
            if self.now == self['event_time']:
                self.env['prob_tv_spread'] = 1
                self.env['prob_neighbor_spread'] = 1
            elif self.now > self['event_time']:
                self.env['prob_tv_spread'] = self.env['prob_tv_spread'] * TV_FACTOR
                self.env['prob_neighbor_spread'] = self.env['prob_neighbor_spread'] * NEIGHBOR_FACTOR

Testing the agents
~~~~~~~~~~~~~~~~~~

Feel free to skip this section if this is your first time with soil.

Testing agents is not easy, and this is not a thorough testing process
for agents. Rather, this section is aimed to show you how to access
internal pats of soil so you can test your agents.

First of all, let’s check if our network agent has the states we would
expect:

.. code:: ipython3

    NewsSpread.states




.. parsed-literal::

    {'neutral': <function __main__.NewsSpread.neutral(self)>,
     'infected': <function __main__.NewsSpread.infected(self)>}



Now, let’s run a simulation on a simple network. It is comprised of
three nodes:

.. code:: ipython3

    G = nx.Graph()
    G.add_edge(0, 1)
    G.add_edge(0, 2)
    G.add_edge(2, 3)
    G.add_node(4)
    pos = nx.spring_layout(G)
    nx.draw_networkx(G, pos, node_color='red')
    nx.draw_networkx(G, pos, nodelist=[0], node_color='blue')



.. image:: output_21_0.png


Let’s run a simple simulation that assigns a NewsSpread agent to all the
nodes in that network. Notice how node 0 is the only one with a TV.

.. code:: ipython3

    import importlib
    importlib.reload(soil.agents)




.. parsed-literal::

    <module 'soil.agents' from '/mnt/data/home/j/git/lab.gsi/soil/soil/soil/agents/__init__.py'>



.. code:: ipython3

    env_params = {
        'prob_tv_spread': 0,
        'prob_neighbor_spread': 0
    }
    
    MAX_TIME = 100
    EVENT_TIME = 10
    
    sim = soil.Simulation(topology=G,
                          num_trials=1,
                          max_time=MAX_TIME,
                          environment_agents=[{'agent_type': NewsEnvironmentAgent,
                                               'state': {
                                               'event_time': EVENT_TIME
                                             }}],
                          network_agents=[{'agent_type': NewsSpread,
                                          'weight': 1}],
                          states={0: {'has_tv': True}},
                          default_state={'has_tv': False},
                          environment_params=env_params)
    env = sim.run_simulation(dry_run=True)[0]

Now we can access the results of the simulation and compare them to our
expected results

.. code:: ipython3

    agents = list(env.network_agents)
    
    # Until the event, all agents are neutral
    for t in range(10):
        for a in agents:
            assert a['state_id', t] == a.neutral.id
            
    # After the event, the node with a TV is infected, the rest are not
    assert agents[0]['has_tv']
    assert agents[0]['state_id', 11] == NewsSpread.infected.id
    assert not agents[2]['has_tv']
    assert agents[2]['state_id', 11] == NewsSpread.neutral.id
    
    
    # At the end, the agents connected to the infected one will probably be infected, too.
    assert agents[1]['state_id', MAX_TIME] == NewsSpread.infected.id
    assert agents[2]['state_id', MAX_TIME] == NewsSpread.infected.id
    
    # But the node with no friends should not be affected
    assert agents[4]['state_id', MAX_TIME] == NewsSpread.neutral.id
            

Lastly, let’s see if the probabilities have decreased as expected:

.. code:: ipython3

    assert abs(env.environment_params['prob_neighbor_spread'] - (NEIGHBOR_FACTOR**(MAX_TIME-1-10))) < 10e-4
    assert abs(env.environment_params['prob_tv_spread'] - (TV_FACTOR**(MAX_TIME-1-10))) < 10e-6

Running the simulation
----------------------

To run a simulation, we need a configuration. Soil can load
configurations from python dictionaries as well as JSON and YAML files.
For this demo, we will use a python dictionary:

.. code:: ipython3

    config = {
        'name': 'ExampleSimulation',
        'max_time': 20,
        'interval': 1,
        'num_trials': 1,
        'network_params': {
           'generator': 'complete_graph',
            'n': 500,
        },
        'network_agents': [
            {
                'agent_type': NewsSpread,
                'weight': 1,
                'state': {
                    'has_tv': False
                }
            },
            {
                'agent_type': NewsSpread,
                'weight': 2,
                'state': {
                    'has_tv': True
                }
            }
        ],
        'environment_agents':[
            {'agent_type': NewsEnvironmentAgent,
             'state': {
                 'event_time': 10
             }
            }
        ],
        'states': [ {'has_tv': True} ],
        'environment_params':{
            'prob_tv_spread': 0.01,
            'prob_neighbor_spread': 0.5
        }
    }

Let’s run our simulation:

.. code:: ipython3

    soil.simulation.run_from_config(config, dry_run=True)

In real life, you probably want to run several simulations, varying some
of the parameters so that you can compare and answer your research
questions.

For instance:

-  Does the outcome depend on the structure of our network? We will use
   different generation algorithms to compare them (Barabasi-Albert and
   Erdos-Renyi)
-  How does neighbor spreading probability affect my simulation? We will
   try probability values in the range of [0, 0.4], in intervals of 0.1.

.. code:: ipython3

    network_1 = {
           'generator': 'erdos_renyi_graph',
            'n': 500,
            'p': 0.1
    }
    network_2 = {
           'generator': 'barabasi_albert_graph',
            'n': 500,
            'm': 2
    }
    
    
    for net in [network_1, network_2]:
        for i in range(5):
            prob = i / 10
            config['environment_params']['prob_neighbor_spread'] = prob
            config['network_params'] = net
            config['name'] = 'Spread_{}_prob_{}'.format(net['generator'], prob)
            s = soil.simulation.run_from_config(config, exporters=['default', 'csv'])

The results are conveniently stored in sqlite (history of agent and
environment state) and the configuration is saved in a YAML file.

You can also export the results to GEXF format (dynamic network) and CSV
using .\ ``run_from_config(config, dump=['gexf', 'csv'])`` or the
command line flags ``--graph --csv``.

.. code:: ipython3

    !tree soil_output
    !du -xh soil_output/*


.. parsed-literal::

    [01;34msoil_output[00m
    ├── [01;34mSpread_barabasi_albert_graph_prob_0.0[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.dumped.yml@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.dumped.yml@2023-03-23_14.06.30
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.dumped.yml@2023-03-23_14.19.33
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.dumped.yml@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.sqlite@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.sqlite@2023-03-23_14.19.33
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0.sqlite@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.csv@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.csv@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.csv@2023-03-23_14.19.33
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.csv@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite@2023-03-23_14.19.33
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.stats.csv@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.stats.csv@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.stats.csv@2023-03-23_14.19.33
    │   │   └── Spread_barabasi_albert_graph_prob_0.0_trial_0.stats.csv@2023-03-23_14.30.56
    │   ├── Spread_barabasi_albert_graph_prob_0.0.dumped.yml
    │   ├── Spread_barabasi_albert_graph_prob_0.0.sqlite
    │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.csv
    │   ├── Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite
    │   └── Spread_barabasi_albert_graph_prob_0.0_trial_0.stats.csv
    ├── [01;34mSpread_barabasi_albert_graph_prob_0.1[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.dumped.yml@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.dumped.yml@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.dumped.yml@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.dumped.yml@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.sqlite@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.sqlite@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1.sqlite@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.csv@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.csv@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.csv@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.csv@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.sqlite@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.sqlite@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.sqlite@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.stats.csv@2023-03-23_12.57.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.stats.csv@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.stats.csv@2023-03-23_14.19.34
    │   │   └── Spread_barabasi_albert_graph_prob_0.1_trial_0.stats.csv@2023-03-23_14.30.56
    │   ├── Spread_barabasi_albert_graph_prob_0.1.dumped.yml
    │   ├── Spread_barabasi_albert_graph_prob_0.1.sqlite
    │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.csv
    │   ├── Spread_barabasi_albert_graph_prob_0.1_trial_0.sqlite
    │   └── Spread_barabasi_albert_graph_prob_0.1_trial_0.stats.csv
    ├── [01;34mSpread_barabasi_albert_graph_prob_0.2[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.dumped.yml@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.dumped.yml@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.dumped.yml@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.dumped.yml@2023-03-23_14.30.56
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.sqlite@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.sqlite@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2.sqlite@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.csv@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.csv@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.csv@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.csv@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.sqlite@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.sqlite@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.sqlite@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.stats.csv@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.stats.csv@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.stats.csv@2023-03-23_14.19.34
    │   │   └── Spread_barabasi_albert_graph_prob_0.2_trial_0.stats.csv@2023-03-23_14.30.57
    │   ├── Spread_barabasi_albert_graph_prob_0.2.dumped.yml
    │   ├── Spread_barabasi_albert_graph_prob_0.2.sqlite
    │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.csv
    │   ├── Spread_barabasi_albert_graph_prob_0.2_trial_0.sqlite
    │   └── Spread_barabasi_albert_graph_prob_0.2_trial_0.stats.csv
    ├── [01;34mSpread_barabasi_albert_graph_prob_0.3[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.dumped.yml@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.dumped.yml@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.dumped.yml@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.dumped.yml@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.sqlite@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.sqlite@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.sqlite@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3.sqlite@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.csv@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.csv@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.csv@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.csv@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.sqlite@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.sqlite@2023-03-23_14.06.31
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.sqlite@2023-03-23_14.19.34
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.sqlite@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.stats.csv@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.stats.csv@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.stats.csv@2023-03-23_14.19.34
    │   │   └── Spread_barabasi_albert_graph_prob_0.3_trial_0.stats.csv@2023-03-23_14.30.57
    │   ├── Spread_barabasi_albert_graph_prob_0.3.dumped.yml
    │   ├── Spread_barabasi_albert_graph_prob_0.3.sqlite
    │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.csv
    │   ├── Spread_barabasi_albert_graph_prob_0.3_trial_0.sqlite
    │   └── Spread_barabasi_albert_graph_prob_0.3_trial_0.stats.csv
    ├── [01;34mSpread_barabasi_albert_graph_prob_0.4[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.dumped.yml@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.dumped.yml@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.dumped.yml@2023-03-23_14.19.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.dumped.yml@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.sqlite@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.sqlite@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.sqlite@2023-03-23_14.19.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4.sqlite@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.csv@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.csv@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.csv@2023-03-23_14.19.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.csv@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.sqlite@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.sqlite@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.sqlite@2023-03-23_14.19.35
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.sqlite@2023-03-23_14.30.57
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.stats.csv@2023-03-23_12.57.36
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.stats.csv@2023-03-23_14.06.32
    │   │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.stats.csv@2023-03-23_14.19.35
    │   │   └── Spread_barabasi_albert_graph_prob_0.4_trial_0.stats.csv@2023-03-23_14.30.57
    │   ├── Spread_barabasi_albert_graph_prob_0.4.dumped.yml
    │   ├── Spread_barabasi_albert_graph_prob_0.4.sqlite
    │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.csv
    │   ├── Spread_barabasi_albert_graph_prob_0.4_trial_0.sqlite
    │   └── Spread_barabasi_albert_graph_prob_0.4_trial_0.stats.csv
    ├── [01;34mSpread_erdos_renyi_graph_prob_0.0[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.dumped.yml@2023-03-23_12.57.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.dumped.yml@2023-03-23_14.06.21
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.dumped.yml@2023-03-23_14.19.24
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.dumped.yml@2023-03-23_14.30.47
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.sqlite@2023-03-23_12.57.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.sqlite@2023-03-23_14.06.22
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.sqlite@2023-03-23_14.19.25
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0.sqlite@2023-03-23_14.30.47
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.csv@2023-03-23_12.57.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.csv@2023-03-23_14.06.22
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.csv@2023-03-23_14.19.25
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.csv@2023-03-23_14.30.47
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.sqlite@2023-03-23_12.57.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.sqlite@2023-03-23_14.06.22
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.sqlite@2023-03-23_14.19.25
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.sqlite@2023-03-23_14.30.47
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.stats.csv@2023-03-23_12.57.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.stats.csv@2023-03-23_14.06.22
    │   │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.stats.csv@2023-03-23_14.19.25
    │   │   └── Spread_erdos_renyi_graph_prob_0.0_trial_0.stats.csv@2023-03-23_14.30.47
    │   ├── Spread_erdos_renyi_graph_prob_0.0.dumped.yml
    │   ├── Spread_erdos_renyi_graph_prob_0.0.sqlite
    │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.csv
    │   ├── Spread_erdos_renyi_graph_prob_0.0_trial_0.sqlite
    │   └── Spread_erdos_renyi_graph_prob_0.0_trial_0.stats.csv
    ├── [01;34mSpread_erdos_renyi_graph_prob_0.1[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.dumped.yml@2023-03-23_12.57.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.dumped.yml@2023-03-23_14.06.24
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.dumped.yml@2023-03-23_14.19.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.dumped.yml@2023-03-23_14.30.49
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.sqlite@2023-03-23_12.57.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.sqlite@2023-03-23_14.06.24
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.sqlite@2023-03-23_14.19.27
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1.sqlite@2023-03-23_14.30.49
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.csv@2023-03-23_12.57.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.csv@2023-03-23_14.06.24
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.csv@2023-03-23_14.19.27
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.csv@2023-03-23_14.30.49
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.sqlite@2023-03-23_12.57.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.sqlite@2023-03-23_14.06.24
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.sqlite@2023-03-23_14.19.27
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.sqlite@2023-03-23_14.30.49
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.stats.csv@2023-03-23_12.57.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.stats.csv@2023-03-23_14.06.24
    │   │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.stats.csv@2023-03-23_14.19.27
    │   │   └── Spread_erdos_renyi_graph_prob_0.1_trial_0.stats.csv@2023-03-23_14.30.49
    │   ├── Spread_erdos_renyi_graph_prob_0.1.dumped.yml
    │   ├── Spread_erdos_renyi_graph_prob_0.1.sqlite
    │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.csv
    │   ├── Spread_erdos_renyi_graph_prob_0.1_trial_0.sqlite
    │   └── Spread_erdos_renyi_graph_prob_0.1_trial_0.stats.csv
    ├── [01;34mSpread_erdos_renyi_graph_prob_0.2[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.dumped.yml@2023-03-23_12.57.30
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.dumped.yml@2023-03-23_14.06.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.dumped.yml@2023-03-23_14.19.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.dumped.yml@2023-03-23_14.30.51
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.sqlite@2023-03-23_12.57.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.sqlite@2023-03-23_14.06.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.sqlite@2023-03-23_14.19.29
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2.sqlite@2023-03-23_14.30.51
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.csv@2023-03-23_12.57.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.csv@2023-03-23_14.06.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.csv@2023-03-23_14.19.29
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.csv@2023-03-23_14.30.51
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.sqlite@2023-03-23_12.57.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.sqlite@2023-03-23_14.06.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.sqlite@2023-03-23_14.19.29
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.sqlite@2023-03-23_14.30.51
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.stats.csv@2023-03-23_12.57.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.stats.csv@2023-03-23_14.06.26
    │   │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.stats.csv@2023-03-23_14.19.29
    │   │   └── Spread_erdos_renyi_graph_prob_0.2_trial_0.stats.csv@2023-03-23_14.30.51
    │   ├── Spread_erdos_renyi_graph_prob_0.2.dumped.yml
    │   ├── Spread_erdos_renyi_graph_prob_0.2.sqlite
    │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.csv
    │   ├── Spread_erdos_renyi_graph_prob_0.2_trial_0.sqlite
    │   └── Spread_erdos_renyi_graph_prob_0.2_trial_0.stats.csv
    ├── [01;34mSpread_erdos_renyi_graph_prob_0.3[00m
    │   ├── [01;34mbackup[00m
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.dumped.yml@2023-03-23_12.57.32
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.dumped.yml@2023-03-23_14.06.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.dumped.yml@2023-03-23_14.19.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.dumped.yml@2023-03-23_14.30.53
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.sqlite@2023-03-23_12.57.33
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.sqlite@2023-03-23_14.06.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.sqlite@2023-03-23_14.19.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3.sqlite@2023-03-23_14.30.53
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.csv@2023-03-23_12.57.33
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.csv@2023-03-23_14.06.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.csv@2023-03-23_14.19.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.csv@2023-03-23_14.30.53
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.sqlite@2023-03-23_12.57.33
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.sqlite@2023-03-23_14.06.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.sqlite@2023-03-23_14.19.31
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.sqlite@2023-03-23_14.30.53
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.stats.csv@2023-03-23_12.57.33
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.stats.csv@2023-03-23_14.06.28
    │   │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.stats.csv@2023-03-23_14.19.31
    │   │   └── Spread_erdos_renyi_graph_prob_0.3_trial_0.stats.csv@2023-03-23_14.30.53
    │   ├── Spread_erdos_renyi_graph_prob_0.3.dumped.yml
    │   ├── Spread_erdos_renyi_graph_prob_0.3.sqlite
    │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.csv
    │   ├── Spread_erdos_renyi_graph_prob_0.3_trial_0.sqlite
    │   └── Spread_erdos_renyi_graph_prob_0.3_trial_0.stats.csv
    └── [01;34mSpread_erdos_renyi_graph_prob_0.4[00m
        ├── [01;34mbackup[00m
        │   ├── Spread_erdos_renyi_graph_prob_0.4.dumped.yml@2023-03-23_12.57.34
        │   ├── Spread_erdos_renyi_graph_prob_0.4.dumped.yml@2023-03-23_14.06.30
        │   ├── Spread_erdos_renyi_graph_prob_0.4.dumped.yml@2023-03-23_14.19.33
        │   ├── Spread_erdos_renyi_graph_prob_0.4.dumped.yml@2023-03-23_14.30.55
        │   ├── Spread_erdos_renyi_graph_prob_0.4.sqlite@2023-03-23_12.57.35
        │   ├── Spread_erdos_renyi_graph_prob_0.4.sqlite@2023-03-23_14.06.30
        │   ├── Spread_erdos_renyi_graph_prob_0.4.sqlite@2023-03-23_14.19.33
        │   ├── Spread_erdos_renyi_graph_prob_0.4.sqlite@2023-03-23_14.30.56
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.csv@2023-03-23_12.57.35
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.csv@2023-03-23_14.06.30
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.csv@2023-03-23_14.19.33
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.csv@2023-03-23_14.30.56
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.sqlite@2023-03-23_12.57.35
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.sqlite@2023-03-23_14.06.30
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.sqlite@2023-03-23_14.19.33
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.sqlite@2023-03-23_14.30.56
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.stats.csv@2023-03-23_12.57.35
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.stats.csv@2023-03-23_14.06.30
        │   ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.stats.csv@2023-03-23_14.19.33
        │   └── Spread_erdos_renyi_graph_prob_0.4_trial_0.stats.csv@2023-03-23_14.30.56
        ├── Spread_erdos_renyi_graph_prob_0.4.dumped.yml
        ├── Spread_erdos_renyi_graph_prob_0.4.sqlite
        ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.csv
        ├── Spread_erdos_renyi_graph_prob_0.4_trial_0.sqlite
        └── Spread_erdos_renyi_graph_prob_0.4_trial_0.stats.csv
    
    20 directories, 250 files
    1.3M	soil_output/Spread_barabasi_albert_graph_prob_0.0/backup
    1.7M	soil_output/Spread_barabasi_albert_graph_prob_0.0
    1.3M	soil_output/Spread_barabasi_albert_graph_prob_0.1/backup
    1.7M	soil_output/Spread_barabasi_albert_graph_prob_0.1
    1.3M	soil_output/Spread_barabasi_albert_graph_prob_0.2/backup
    1.6M	soil_output/Spread_barabasi_albert_graph_prob_0.2
    1.3M	soil_output/Spread_barabasi_albert_graph_prob_0.3/backup
    1.7M	soil_output/Spread_barabasi_albert_graph_prob_0.3
    1.3M	soil_output/Spread_barabasi_albert_graph_prob_0.4/backup
    1.7M	soil_output/Spread_barabasi_albert_graph_prob_0.4
    2.7M	soil_output/Spread_erdos_renyi_graph_prob_0.0/backup
    3.4M	soil_output/Spread_erdos_renyi_graph_prob_0.0
    2.7M	soil_output/Spread_erdos_renyi_graph_prob_0.1/backup
    3.4M	soil_output/Spread_erdos_renyi_graph_prob_0.1
    2.7M	soil_output/Spread_erdos_renyi_graph_prob_0.2/backup
    3.4M	soil_output/Spread_erdos_renyi_graph_prob_0.2
    2.7M	soil_output/Spread_erdos_renyi_graph_prob_0.3/backup
    3.4M	soil_output/Spread_erdos_renyi_graph_prob_0.3
    2.7M	soil_output/Spread_erdos_renyi_graph_prob_0.4/backup
    3.4M	soil_output/Spread_erdos_renyi_graph_prob_0.4


Analysing the results
---------------------

Loading data
~~~~~~~~~~~~

Once the simulations are over, we can use soil to analyse the results.

Soil allows you to load results for specific trials, or for a set of
trials if you specify a pattern. The specific methods are:

-  ``analysis.read_data(<directory pattern>)`` to load all the results
   from a directory. e.g. \ ``read_data('my_simulation/')``. For each
   trial it finds in each folder matching the pattern, it will return
   the dumped configuration for the simulation, the results of the
   trial, and the configuration itself. By default, it will try to load
   data from the sqlite database.
-  ``analysis.read_csv(<csv_file>)`` to load all the results from a CSV
   file.
   e.g. \ ``read_csv('my_simulation/my_simulation_trial0.environment.csv')``
-  ``analysis.read_sql(<sqlite_file>)`` to load all the results from a
   sqlite database .
   e.g. \ ``read_sql('my_simulation/my_simulation_trial0.db.sqlite')``

Let’s see it in action by loading the stored results into a pandas
dataframe:

.. code:: ipython3

    from soil import analysis
    import pandas as pd

.. code:: ipython3

    df = analysis.read_csv('soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0_trial_0.csv')
    df




.. raw:: html

    <div>
    <style scoped>
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
    
        .dataframe tbody tr th {
            vertical-align: top;
        }
    
        .dataframe thead tr th {
            text-align: left;
        }
    
        .dataframe thead tr:last-of-type th {
            text-align: right;
        }
    </style>
    <table border="1" class="dataframe">
      <thead>
        <tr>
          <th>key</th>
          <th>SEED</th>
          <th colspan="9" halign="left">alive</th>
          <th>...</th>
          <th colspan="10" halign="left">state_id</th>
        </tr>
        <tr>
          <th>agent_id</th>
          <th>env</th>
          <th>0</th>
          <th>1</th>
          <th>10</th>
          <th>100</th>
          <th>101</th>
          <th>102</th>
          <th>103</th>
          <th>104</th>
          <th>105</th>
          <th>...</th>
          <th>90</th>
          <th>91</th>
          <th>92</th>
          <th>93</th>
          <th>94</th>
          <th>95</th>
          <th>96</th>
          <th>97</th>
          <th>98</th>
          <th>99</th>
        </tr>
        <tr>
          <th>t_step</th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>0.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>1.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>2.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>3.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>4.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>5.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>6.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>7.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>8.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>9.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>10.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>11.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>neutral</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>12.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>13.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>14.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>15.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>16.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>17.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>18.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>19.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
      </tbody>
    </table>
    <p>20 rows × 2507 columns</p>
    </div>



Soil can also process the data for us and split the results into
environment attributes and agent attributes:

.. code:: ipython3

    env, agents = analysis.split_processed(df)

.. code:: ipython3

    agents




.. raw:: html

    <div>
    <style scoped>
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
    
        .dataframe tbody tr th {
            vertical-align: top;
        }
    
        .dataframe thead tr th {
            text-align: left;
        }
    
        .dataframe thead tr:last-of-type th {
            text-align: right;
        }
    </style>
    <table border="1" class="dataframe">
      <thead>
        <tr>
          <th>key</th>
          <th colspan="10" halign="left">alive</th>
          <th>...</th>
          <th colspan="10" halign="left">state_id</th>
        </tr>
        <tr>
          <th>agent_id</th>
          <th>0</th>
          <th>1</th>
          <th>10</th>
          <th>100</th>
          <th>101</th>
          <th>102</th>
          <th>103</th>
          <th>104</th>
          <th>105</th>
          <th>106</th>
          <th>...</th>
          <th>90</th>
          <th>91</th>
          <th>92</th>
          <th>93</th>
          <th>94</th>
          <th>95</th>
          <th>96</th>
          <th>97</th>
          <th>98</th>
          <th>99</th>
        </tr>
        <tr>
          <th>t_step</th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>0.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>1.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>2.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>3.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>4.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>5.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>6.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>7.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>8.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>9.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>10.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>11.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>neutral</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>12.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>13.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>14.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>15.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>16.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>17.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>18.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>19.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
      </tbody>
    </table>
    <p>20 rows × 2504 columns</p>
    </div>



The index of the results are the simulation step. Hence, we can access
the state of the simulation at a given step (e.g., 13):

.. code:: ipython3

    agents.loc[13, 'state_id']




.. parsed-literal::

    agent_id
    0      infected
    1      infected
    10     infected
    100    infected
    101    infected
             ...   
    95     infected
    96     infected
    97     infected
    98     infected
    99     infected
    Name: 13.0, Length: 500, dtype: object



Or, we can perform more complex tasks such as showing the agents that
have changed their state between two simulation steps (2 and 1):

.. code:: ipython3

    (agents.loc[2]['state_id'] != agents.loc[1]['state_id']).sum()




.. parsed-literal::

    2



To focus on specific agents, we can swap the levels of the index:

.. code:: ipython3

    agents.swaplevel(axis=1)




.. raw:: html

    <div>
    <style scoped>
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
    
        .dataframe tbody tr th {
            vertical-align: top;
        }
    
        .dataframe thead tr th {
            text-align: left;
        }
    
        .dataframe thead tr:last-of-type th {
            text-align: right;
        }
    </style>
    <table border="1" class="dataframe">
      <thead>
        <tr>
          <th>agent_id</th>
          <th>0</th>
          <th>1</th>
          <th>10</th>
          <th>100</th>
          <th>101</th>
          <th>102</th>
          <th>103</th>
          <th>104</th>
          <th>105</th>
          <th>106</th>
          <th>...</th>
          <th>90</th>
          <th>91</th>
          <th>92</th>
          <th>93</th>
          <th>94</th>
          <th>95</th>
          <th>96</th>
          <th>97</th>
          <th>98</th>
          <th>99</th>
        </tr>
        <tr>
          <th>key</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>alive</th>
          <th>...</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
          <th>state_id</th>
        </tr>
        <tr>
          <th>t_step</th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>0.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>1.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>2.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>3.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>4.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>5.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>6.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>7.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>8.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>9.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>10.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>11.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>neutral</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>12.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>13.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>14.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>15.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>16.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>17.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>18.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>19.0</th>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
      </tbody>
    </table>
    <p>20 rows × 2504 columns</p>
    </div>



Plotting data
~~~~~~~~~~~~~

If you don’t want to work with pandas, you can also use some pre-defined
functions from soil to conveniently plot the results:

.. code:: ipython3

    analysis.plot_all('soil_output/Spread_barabasi_albert_graph_prob_0.0/', analysis.get_count, 'state_id');



.. image:: output_55_0.png


.. code:: ipython3

    analysis.plot_all('soil_output/Spread_barabasi_albert_graph_prob_0.3/', analysis.get_count, 'state_id');



.. image:: output_56_0.png


You can use wildcards in the results path:

.. code:: ipython3

    analysis.plot_all('soil_output/Spread_barabasi*/', analysis.get_count, 'state_id');



.. image:: output_58_0.png



.. image:: output_58_1.png



.. image:: output_58_2.png



.. image:: output_58_3.png



.. image:: output_58_4.png


If we compare these results to those of the other graph model (a
fully-connected graph), we can see a stark difference:

.. code:: ipython3

    analysis.plot_all('soil_output/Spread_erdos*', analysis.get_count, 'state_id');



.. image:: output_60_0.png



.. image:: output_60_1.png



.. image:: output_60_2.png



.. image:: output_60_3.png



.. image:: output_60_4.png


The previous cells were using the ``count_value`` function for
aggregation. There’s another function to plot numeral values:

.. code:: ipython3

    analysis.plot_all('soil_output/Spread_erdos*', analysis.get_value, 'prob_tv_spread');



.. image:: output_62_0.png



.. image:: output_62_1.png



.. image:: output_62_2.png



.. image:: output_62_3.png



.. image:: output_62_4.png


Manually plotting with pandas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although the simplest way to visualize the results of a simulation is to
use the built-in methods in the analysis module, sometimes the setup is
more complicated and we need to explore the data a little further.

For that, we can use native pandas over the results.

Soil provides some convenience methods to simplify common operations:

-  ``analysis.split_df`` to separate a history dataframe into
   environment and agent parameters.
-  ``analysis.get_count`` to get a dataframe with the value counts for
   different attributes during the simulation.
-  ``analysis.get_value`` to get the evolution of the value of an
   attribute during the simulation.

And, as we saw earlier, ``analysis.process`` can turn a dataframe in
canonical form into a dataframe with a column per attribute.

.. code:: ipython3

    !ls soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0*


.. parsed-literal::

    soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0.dumped.yml
    soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0.sqlite
    soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0_trial_0.csv
    soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite
    soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0_trial_0.stats.csv


.. code:: ipython3

    df = analysis.read_sql('soil_output/Spread_barabasi_albert_graph_prob_0.0/Spread_barabasi_albert_graph_prob_0.0_trial_0.sqlite')
    df




.. raw:: html

    <div>
    <style scoped>
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
    
        .dataframe tbody tr th {
            vertical-align: top;
        }
    
        .dataframe thead tr th {
            text-align: left;
        }
    
        .dataframe thead tr:last-of-type th {
            text-align: right;
        }
    </style>
    <table border="1" class="dataframe">
      <thead>
        <tr>
          <th>key</th>
          <th>SEED</th>
          <th colspan="9" halign="left">alive</th>
          <th>...</th>
          <th colspan="10" halign="left">state_id</th>
        </tr>
        <tr>
          <th>dict_id</th>
          <th>env</th>
          <th>0</th>
          <th>1</th>
          <th>10</th>
          <th>100</th>
          <th>101</th>
          <th>102</th>
          <th>103</th>
          <th>104</th>
          <th>105</th>
          <th>...</th>
          <th>90</th>
          <th>91</th>
          <th>92</th>
          <th>93</th>
          <th>94</th>
          <th>95</th>
          <th>96</th>
          <th>97</th>
          <th>98</th>
          <th>99</th>
        </tr>
        <tr>
          <th>t_step</th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>0.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>1.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>2.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>3.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>4.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>5.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>6.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>7.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>8.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>9.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>10.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>neutral</td>
          <td>infected</td>
          <td>neutral</td>
          <td>neutral</td>
        </tr>
        <tr>
          <th>11.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>neutral</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>12.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>13.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>14.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>15.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>16.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>17.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>18.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
        <tr>
          <th>19.0</th>
          <td>Spread_barabasi_albert_graph_prob_0.0_trial_0</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>True</td>
          <td>...</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
          <td>infected</td>
        </tr>
      </tbody>
    </table>
    <p>20 rows × 3008 columns</p>
    </div>



Let’s look at the evolution of agent parameters in the simulation

.. code:: ipython3

    df.plot()




.. parsed-literal::

    <Axes: xlabel='t_step'>




.. image:: output_68_1.png


As we can see, ``event_time`` and ``interval`` are cluttering our
results,

.. code:: ipython3

    del df['interval']
    del df['event_time']
    df.plot()




.. parsed-literal::

    <Axes: xlabel='t_step'>




.. image:: output_70_1.png


The ``soil.analysis`` module also provides convenient functions to count
the number of agents in a given state:

.. code:: ipython3

    analysis.get_count(agents, 'state_id').plot();



.. image:: output_72_0.png


Dealing with bigger data
------------------------

.. code:: ipython3

    from soil import analysis

.. code:: ipython3

    !du -xsh ../rabbits/soil_output/rabbits_example/


.. parsed-literal::

    1.1M	../rabbits/soil_output/rabbits_example/


If we tried to load the entire history, we would probably run out of
memory. Hence, it is recommended that you also specify the attributes
you are interested in.

.. code:: ipython3

    p = analysis.plot_all('../rabbits/soil_output/rabbits_example/', analysis.get_count, 'state_id')



.. image:: output_77_0.png


.. code:: ipython3

    !ls ../rabbits/soil_output/rabbits_example


.. parsed-literal::

    backup			    rabbits_example.sqlite
    rabbits_example.dumped.yml  rabbits_example_trial_0.sqlite


.. code:: ipython3

    df = analysis.read_sql('../rabbits/soil_output/rabbits_example/rabbits_example_trial_0.sqlite', keys=['state_id', 'rabbits_alive'])

.. code:: ipython3

    df




.. raw:: html

    <div>
    <style scoped>
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
    
        .dataframe tbody tr th {
            vertical-align: top;
        }
    
        .dataframe thead tr th {
            text-align: left;
        }
    
        .dataframe thead tr:last-of-type th {
            text-align: right;
        }
    </style>
    <table border="1" class="dataframe">
      <thead>
        <tr>
          <th>key</th>
          <th>rabbits_alive</th>
          <th colspan="20" halign="left">state_id</th>
        </tr>
        <tr>
          <th>dict_id</th>
          <th>env</th>
          <th>0</th>
          <th>1</th>
          <th>10</th>
          <th>100</th>
          <th>101</th>
          <th>102</th>
          <th>103</th>
          <th>104</th>
          <th>105</th>
          <th>...</th>
          <th>90</th>
          <th>91</th>
          <th>92</th>
          <th>93</th>
          <th>94</th>
          <th>95</th>
          <th>96</th>
          <th>97</th>
          <th>98</th>
          <th>99</th>
        </tr>
        <tr>
          <th>t_step</th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>0.0</th>
          <td>0</td>
          <td>newborn</td>
          <td>newborn</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>...</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
        </tr>
        <tr>
          <th>2.0</th>
          <td>0</td>
          <td>fertile</td>
          <td>fertile</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>...</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
        </tr>
        <tr>
          <th>16.0</th>
          <td>0</td>
          <td>pregnant</td>
          <td>fertile</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>...</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
        </tr>
        <tr>
          <th>49.0</th>
          <td>8</td>
          <td>fertile</td>
          <td>fertile</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>...</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
        </tr>
        <tr>
          <th>51.0</th>
          <td>8</td>
          <td>fertile</td>
          <td>fertile</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>...</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
          <td>nan</td>
        </tr>
        <tr>
          <th>...</th>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
          <td>...</td>
        </tr>
        <tr>
          <th>739.0</th>
          <td>15</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>...</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
        </tr>
        <tr>
          <th>742.0</th>
          <td>14</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>...</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
        </tr>
        <tr>
          <th>743.0</th>
          <td>12</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>...</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
        </tr>
        <tr>
          <th>744.0</th>
          <td>10</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>...</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
        </tr>
        <tr>
          <th>751.0</th>
          <td>9</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>...</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>fertile</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
          <td>dead</td>
        </tr>
      </tbody>
    </table>
    <p>326 rows × 349 columns</p>
    </div>



.. code:: ipython3

    states = analysis.get_count(df, 'state_id')
    states.plot();



.. image:: output_81_0.png


.. code:: ipython3

    alive = analysis.get_value(df, 'rabbits_alive', aggfunc='sum').apply(pd.to_numeric)
    alive.plot()




.. parsed-literal::

    <Axes: xlabel='t_step'>




.. image:: output_82_1.png


.. code:: ipython3

    h = pd.concat([alive, states]);
    h.plot();



.. image:: output_83_0.png

