# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.30 UNRELEASED]
### Added
* Simple debugging capabilities in `soil.debugging`, with a custom `pdb.Debugger` subclass that exposes commands to list agents and their status and set breakpoints on states (for FSM agents). Try it with `soil --debug <simulation file>`
* Ability to run mesa simulations
* The `soil.exporters` module to export the results of datacollectors (model.datacollector) into files at the end of trials/simulations
* A modular set of classes for environments/models. Now the ability to configure the agents through an agent definition and a topology through a network configuration is split into two classes (`soil.agents.BaseEnvironment` for agents, `soil.agents.NetworkEnvironment` to add topology).
* FSM agents can now have generators as states. They work similar to normal states, with one caveat. Only `time` values can be yielded, not a state. This is because the state will not change, it will be resumed after the yield, at the appropriate time. The return value *can* be a state, or a `(state, time)` tuple, just like in normal states.
### Changed
* Configuration schema is very simplified
### Removed
* Any `tsih` and `History` integration in the main classes. To record the state of environments/agents, just use a datacollector. In some cases this may be slower or consume more memory than the previous system. However, few cases actually used the full potential of the history, and it came at the cost of unnecessary complexity and worse performance for the majority of cases.


## [0.20.7]
### Changed
* Creating a `time.When` from another `time.When` does not nest them anymore (it returns the argument)
### Fixed
* Bug with time.NEVER/time.INFINITY
## [0.20.6]
### Fixed
* Agents now return `time.INFINITY` when dead, instead of 'inf'
* `soil.__init__` does not re-export built-in time (change in `soil.simulation`. It used to create subtle import conflicts when importing soil.time.
* Parallel simulations were broken because lambdas cannot be pickled properly, which is needed for multiprocessing.
### Changed
* Some internal simulation methods do not accept `*args` anymore, to avoid ambiguity and bugs.
## [0.20.5]
### Changed
* Defaults are now set in the agent __init__, not in the environment. This decouples both classes a bit more, and it is more intuitive 
## [0.20.4]
### Added
* Agents can now be given any kwargs, which will be used to set their state
* Environments have a default logger `self.logger` and a log method, just like agents
## [0.20.3]
### Fixed
* Default state values are now deepcopied again.
* Seeds for environments only concatenate the trial id (i.e., a number), to provide repeatable results.
* `Environment.run` now calls `Environment.step`, to allow for easy overloading of the environment step
### Removed
* Datacollectors are not being used for now.
* `time.TimedActivation.step` does not use an `until` parameter anymore.
### Changed
* Simulations now run right up to `until` (open interval)
* Time instants (`time.When`) don't need to be floats anymore. Now we can avoid precision issues with big numbers by using ints.
* Rabbits simulation is more idiomatic (using subclasses)

## [0.20.2]
### Fixed
* CI/CD testing issues
## [0.20.1]
### Fixed
* Agents would run another step after dying.
## [0.20.0]
### Added
* Integration with MESA
* `not_agent_ids` parameter to get sql in history
### Changed
* `soil.Environment` now also inherits from `mesa.Model`
* `soil.Agent` now also inherits from `mesa.Agent`
* `soil.time` to replace `simpy` events, delays, duration, etc.
* `agent.id` is not `agent.unique_id` to be compatible with `mesa`. A property `BaseAgent.id` has been added for compatibility.
* `agent.environment` is now `agent.model`, for the same reason as above. The parameter name in `BaseAgent.__init__` has also been renamed.
### Removed
* `simpy` dependency and compatibility. Each agent used to be a simpy generator, but that made debugging and error handling more complex. That has been replaced by a scheduler within the `soil.Environment` class, similar to how `mesa` does it.
* `soil.history` is now a separate package named `tsih`. The keys namedtuple uses `dict_id` instead of `agent_id`.
### Added
* An option to choose whether a database should be used for history 
## [0.15.2]
### Fixed
* Pass the right known_modules and parameters to stats discovery in simulation
* The configuration file must exist when launching through the CLI. If it doesn't, an error will be logged
* Minor changes in the documentation of the CLI arguments
### Changed
* Stats are now exported by default
## [0.15.1]
### Added
* read-only `History`
### Fixed
* Serialization problem with the `Environment` on parallel mode.
* Analysis functions now work as they should in the tutorial
## [0.15.0]
### Added
* Control logging level in CLI and simulation
* `Stats` to calculate trial and simulation-wide statistics
* Simulation statistics are stored in a separate table in history (see `History.get_stats` and `History.save_stats`, as well as `soil.stats`)
* Aliased `NetworkAgent.G` to `NetworkAgent.topology`.
### Changed
* Templates in config files can be given as dictionaries in addition to strings
* Samplers are used more explicitly
* Removed nxsim dependency. We had already made a lot of changes, and nxsim has not been updated in 5 years.
* Exporter methods renamed to `trial` and `end`. Added `start`.
* `Distribution` exporter now a stats class
* `global_topology` renamed to `topology`
* Moved topology-related methods to `NetworkAgent`
### Fixed
* Temporary files used for history in dry_run mode are not longer left open 

## [0.14.9]
### Changed
* Seed random before environment initialization
## [0.14.8]
### Fixed
* Invalid directory names in Windows gsi-upm/soil#5
## [0.14.7]
### Changed
* Minor change to traceback handling in async simulations
### Fixed
* Incomplete example in the docs (example.yml) caused an exception
## [0.14.6]
### Fixed
* Bug with newer versions of networkx (0.24) where the Graph.node attribute has been removed. We have updated our calls, but the code in nxsim is not under our control, so we have pinned the networkx version until that issue is solved.
### Changed
* Explicit yaml.SafeLoader to avoid deprecation warnings when using yaml.load. It should not break any existing setups, but we could move to the FullLoader in the future if needed.

## [0.14.4]
### Fixed
* Bug in `agent.get_agents()` when `state_id` is passed as a string. The tests have been modified accordingly.
## [0.14.3]
### Fixed
* Incompatibility with py3.3-3.6 due to ModuleNotFoundError and TypeError in DryRunner
## [0.14.2]
### Fixed
* Output path for exporters is now soil_output
### Changed 
* CSV output to stdout in dry_run mode
## [0.14.1]
### Changed
* Exporter names in lower case
* Add default exporter in runs
## [0.14.0]
### Added
* Loading configuration from template definitions in the yaml, in preparation for SALib support.
The definition of the variables and their possible values (i.e., a problem in SALib terms), as well as a sampler function, can be provided.
Soil uses this definition and the template to generate a set of configurations.
* Simulation group names, to link related simulations. For now, they are only used to group all simulations in the same group under the same folder.
* Exporters unify exporting/dumping results and other files to disk. If `dry_run` is set to `True`, exporters will write to stdout instead of a file (useful for testing/debugging).
* Distribution exporter, to write statistics about values and value_counts in every simulation. The results are dumped to two CSV files.

### Changed
* `dir_path` is now the directory for resources (modules, files)
* Environments and simulations do not export or write anything by default. That task is delegated to Exporters

### Removed
* The output dir for environments and simulations (see Exporters)
* DrawingAgent, because it wrote to disk and was not being used. We provide a partial alternative in the form of the GraphDrawing exporter. A complete alternative will be provided once the network at each state can be accessed by exporters.

## Fixed
* Modules with custom agents/environments failed to load when they were run from outside the directory of the definition file. Modules are now loaded from the directory of the simulation file in addition to the working directory
* Memory databases (in history) can now be shared between threads.
* Testing all examples, not just subdirectories

## [0.13.8]
### Changed
* Moved TerroristNetworkModel to examples
### Added
* `get_agents` and `count_agents` methods now accept lists as inputs. They can be used to retrieve agents from node ids
* `subgraph` in BaseAgent
* `agents.select` method, to filter out agents
* `skip_test` property in yaml definitions, to force skipping some examples
* `agents.Geo`, with a search function based on postition
* `BaseAgent.ego_search` to get nodes from the ego network of a node
* `BaseAgent.degree` and `BaseAgent.betweenness`
### Fixed

## [0.13.7]
### Changed
* History now defaults to not backing up! This makes it more intuitive to load the history for examination, at the expense of rewriting something. That should not happen because History is only created in the Environment, and that has `backup=True`.
### Added
* Agent names are assigned based on their agent types
* Agent logging uses the agent name.
* FSM agents can now return a timeout in addition to a new state. e.g. `return self.idle, self.env.timeout(2)` will execute the *different_state* in 2 *units of time* (`t_step=now+2`).
* Example of using timeouts in FSM (custom_timeouts)
* `network_agents` entries may include an `ids` entry. If set, it should be a list of node ids that should be assigned that agent type. This complements the previous behavior of setting agent type with `weights`.
