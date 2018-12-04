Simulation of pubs and drinking pals that go from pub to pub.

Th custom environment includes a list of pubs and methods to allow agents to discover and enter pubs.
There are two types of agents:

* Patron. A patron will do three things, in this order:
    * Look for other patrons to drink with
    * Look for a pub where the agent and other agents in the same group can get in.
    * While in the pub, patrons only drink, until they get drunk and taken home.
* Police. There is only one police agent that will take any drunk patrons home (kick them out of the pub).
