# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
### Added
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