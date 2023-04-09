

What are the main changes between version 0.3 and 0.2?
######################################################

Version 0.3 is a major rewrite of the Soil system, focused on simplifying the API, aligning it with Mesa, and making it easier to use.
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

In principle, the generation of the network topology and the assignment of agents to nodes are two separate processes.
There is a mechanism to initialize the agents, a mechanism to initialize the topology, and a mechanism to assign agents to nodes.

However, there are a myriad of ways to do this, and it is not clear which is the best way to do it.
Earlier versions of Soil approached it by providing a fairly complex method of agent and node generation.
The result was a very complex and difficult to understand system, which is was also prone to bugs and changes between versions.

Starting with version 0.3, the approach is to provide a simplified yet flexible system for generating the network topology and assigning agents to nodes.
This is based on these methods:

- `create_network`
- `add_agents` (and `add_agent`)
- `populate_network`

The default implementation of `soil.Environment` accepts some parameters that will automatically do these steps for the most common case.
All other cases can be handled by overriding the `init(self)` method and explicitly using these methods.


Can Soil environments include more than one network / topology?
###############################################################

Yes, but each network has to be included manually.
Somewhere between 0.20 and 0.30 we included the ability to include multiple networks, but it was deemed too complex and was removed.
