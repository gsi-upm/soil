Upgrading to Soil 1.0
---------------------

What are the main changes in version 1.0?
#########################################

Version 1.0 is a major rewrite of the Soil system, focused on simplifying the API, aligning it with Mesa, and making it easier to use.
Unfortunately, this comes at the cost of backwards compatibility.

We drew several lessons from the previous version of Soil, and tried to address them in this version.
Mainly:

- The split between simulation configuration and simulation code was overly complicated for most use cases. As a result, most users ended up reusing configuration.
- Storing **all** the simulation data in a database is costly and unnecessary for most use cases. For most use cases, only a handful of variables need to be stored. This fits nicely with Mesa's data collection system.
- The API was too complex, and it was difficult to understand how to use it.
- Most parts of the API were not aligned with Mesa, which made it difficult to use Mesa's features or to integrate Soil modules with Mesa code, especially for newcomers.
- Many parts of the API were tightly coupled, which made it difficult to find bugs, test the system and add new features.

The 0.30 rewrite should provide a middle ground between Soil's opinionated approach and Mesa's flexibility.
The new Soil is less configuration-centric.
It aims to provide more modular and convenient functions, most of which can be used in vanilla Mesa.

How are agents assigned to nodes in the network
###############################################

The constructor of the `NetworkAgent` class has two arguments: `node_id` and `topology`.
If `topology` is not provided, it will default to `self.model.topology`.
This assignment might err if the model does not have a `topology` attribute, but most Soil environments derive from `NetworkEnvironment`, so they include a topology by default.
If `node_id` is not provided, a random node will be selected from the topology, until a node with no agent is found.
Then, the `node_id` of that node is assigned to the agent.
If no node with no agent is found, a new node is automatically added to the topology.


Can Soil environments include more than one network / topology?
###############################################################

Yes, but each network has to be included manually.
Somewhere between 0.20 and 0.30 we included the ability to include multiple networks, but it was deemed too complex and was removed.
