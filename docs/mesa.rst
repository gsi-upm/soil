Mesa compatibility
------------------

Soil is in the process of becoming fully compatible with MESA.
The idea is to provide a set of modular classes and functions that extend the functionality of mesa, whilst staying compatible.
In the end, it should be possible to add regular mesa agents to a soil simulation, or use a soil agent within a mesa simulation/model.

This is a non-exhaustive list of tasks to achieve compatibility:

- [ ] Integrate `soil.Simulation` with mesa's runners:
  - [ ] `soil.Simulation` could mimic/become a `mesa.batchrunner`
- [ ] Integrate `soil.Environment` with `mesa.Model`:
  - [x] `Soil.Environment` inherits from `mesa.Model`
  - [x] `Soil.Environment` includes a Mesa-like Scheduler (see the `soil.time` module.
  - [ ] Allow for `mesa.Model` to be used in a simulation.
- [ ] Integrate `soil.Agent` with `mesa.Agent`:
  - [x] Rename agent.id to unique_id?
  - [x] mesa agents can be used in soil simulations (see `examples/mesa`)
- [ ] Provide examples
  - [ ] Using mesa modules in a soil simulation
  - [ ] Using soil modules in a mesa simulation
- [ ] Document the new APIs and usage