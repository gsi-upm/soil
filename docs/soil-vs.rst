### MESA

Starting with version 0.3, Soil has been redesigned to complement Mesa, while remaining compatible with it.
That means that every component in Soil (i.e., Models, Environments, etc.) can be mixed with existing mesa components.
In fact, there are examples that show how that integration may be used, in the `examples/mesa` folder in the repository.

Here are some reasons to use Soil instead of plain mesa:

- Less boilerplate for common scenarios (by some definitions of common)
- Functions to automatically populate a topology with an agent distribution (i.e., different ratios of agent class and state)
- The `soil.Simulation` class allows you to run multiple instances of the same experiment (i.e., multiple trials with the same parameters but a different randomness seed)
- Reporting functions that aggregate multiple
