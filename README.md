# [SOIL](https://github.com/gsi-upm/soil)


Soil is an extensible and user-friendly Agent-based Social Simulator for Social Networks.
Learn how to run your own simulations with our [documentation](http://soilsim.readthedocs.io).

Follow our [tutorial](docs/tutorial/soil_tutorial.ipynb) to develop your own agent models.

> **Warning**
> Soil 1.0 introduced many fundamental changes. Check the [documention on how to update your simulations to work with newer versions](docs/notes_v1.0.rst)

## Features

* Integration with (social) networks (through `networkx`)
* Convenience functions and methods to easily assign agents to your model (and optionally to its network):
  * Following a given distribution (e.g., 2 agents of type `Foo`, 10% of the network should be agents of type `Bar`)
  * Based on the topology of the network
* **Several types of abstractions for agents**:
  * Finite state machine, where methods can be turned into a state
  * Network agents, which have convenience methods to access the model's topology
  * Generator-based agents, whose state is paused though a `yield` and resumed on the next step
* **Reporting and data collection**:
  * Soil models include data collection and record some data by default (# of agents, state of each agent, etc.)
  * All data collected are exported by default to a SQLite database and a description file
  * Options to export to other formats, such as CSV, or defining your own exporters
  * A summary of the data collected is shown in the command line, for easy inspection
* **An event-based scheduler**
  * Agents can be explicit about when their next time/step should be, and not all agents run in every step. This avoids unnecessary computation.
  * Time intervals between each step are flexible.
  * There are primitives to specify when the next execution of an agent should be (or conditions)
* **Actor-inspired** message-passing
* A simulation runner (`soil.Simulation`) that can:
  * Run models in parallel
  * Save results to different formats
* Simulation configuration files 
* A command line interface (`soil`), to quickly run simulations with different parameters
* An integrated debugger (`soil --debug`) with custom functions to print agent states and break at specific states

## Mesa compatibility

SOIL has been redesigned to integrate well with [Mesa](https://github.com/projectmesa/mesa).
For instance, it should be possible to run a `mesa.Model` models using a `soil.Simulation` and the `soil` CLI, or to integrate the `soil.TimedActivation` scheduler on a `mesa.Model`.

Note that some combinations of `mesa` and `soil` components, while technically possible, are much less useful or might yield surprising results.
For instance, you may add any `soil.agent` agent on a regular `mesa.Model` with a vanilla scheduler from `mesa.time`.
But in that case the agents will not get any of the advanced event-based scheduling, and most agent behaviors that depend on that may not work. 


## Changes in version 0.3

Version 0.3 came packed with many changes to provide much better integration with MESA.
For a long time, we tried to keep soil backwards-compatible, but it turned out to be a big endeavour and the resulting code was less readable.
This translates to harder maintenance and a worse experience for newcomers. 
In the end, we decided to make some breaking changes.

If you have an older Soil simulation, you have two options:

* Update the necessary configuration files and code. You may use the examples in the `examples` folder for reference, as well as the documentation.
* Keep using a previous `soil` version.



## Citation 


If you use Soil in your research, don't forget to cite this paper:

```bibtex
@inbook{soil-gsi-conference-2017,
    author = "S{\'a}nchez, Jes{\'u}s M. and Iglesias, Carlos A. and S{\'a}nchez-Rada, J. Fernando",
    booktitle = "Advances in Practical Applications of Cyber-Physical Multi-Agent Systems: The PAAMS Collection",
    doi = "10.1007/978-3-319-59930-4_19",
    editor = "Demazeau Y., Davidsson P., Bajo J., Vale Z.",
    isbn = "978-3-319-59929-8",
    keywords = "soil;social networks;agent based social simulation;python",
    month = "June",
    organization = "PAAMS 2017",
    pages = "234-245",
    publisher = "Springer Verlag",
    series = "LNAI",
    title = "{S}oil: {A}n {A}gent-{B}ased {S}ocial {S}imulator in {P}ython for {M}odelling and {S}imulation of {S}ocial {N}etworks",
    url = "https://link.springer.com/chapter/10.1007/978-3-319-59930-4_19",
    volume = "10349",
    year = "2017",
}

```

@Copyright GSI - Universidad Politécnica de Madrid 2017-2021

[![SOIL](logo_gsi.png)](https://www.gsi.upm.es)
