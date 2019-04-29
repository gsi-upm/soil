# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
