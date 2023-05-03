Soil vs other ABM frameworks
============================

MESA
----

Starting with version 0.3, Soil has been redesigned to complement Mesa, while remaining compatible with it.
That means that every component in Soil (i.e., Models, Environments, etc.) can be mixed with existing mesa components.
In fact, there are examples that show how that integration may be used, in the `examples/mesa` folder in the repository.

Here are some reasons to use Soil instead of plain mesa:

- Less boilerplate for common scenarios (by some definitions of common)
- Functions to automatically populate a topology with an agent distribution (i.e., different ratios of agent class and state)
- The `soil.Simulation` class allows you to run multiple instances of the same experiment (i.e., multiple trials with the same parameters but a different randomness seed)
- Reporting functions that aggregate multiple

Mesa compatibility
~~~~~~~~~~~~~~~~~~

Soil is in the process of becoming fully compatible with MESA.
The idea is to provide a set of modular classes and functions that extend the functionality of mesa, whilst staying compatible.
In the end, it should be possible to add regular mesa agents to a soil simulation, or use a soil agent within a mesa simulation/model.

This is a non-exhaustive list of tasks to achieve compatibility:

.. |check| raw:: html

    ☑

.. |uncheck| raw:: html

    ☐

- |check| Integrate `soil.Simulation` with mesa's runners:

  - |check| `soil.Simulation` can replace `mesa.batchrunner`

- |check| Integrate `soil.Environment` with `mesa.Model`:

  - |check| `Soil.Environment` inherits from `mesa.Model`
  - |check| `Soil.Environment` includes a Mesa-like Scheduler (see the `soil.time` module.
  - |check| Allow for `mesa.Model` to be used in a simulation.

- |check| Integrate `soil.Agent` with `mesa.Agent`:

  - |check| Rename agent.id to unique_id
  - |check| mesa agents can be used in soil simulations (see `examples/mesa`)

- |check| Provide examples

  - |check| Using mesa modules in a soil simulation (see `examples/mesa`)
  - |uncheck| Using soil modules in a mesa simulation (see `examples/mesa`)

- |uncheck| Document the new APIs and usage