# [SOIL](https://github.com/gsi-upm/soil)

Soil is an extensible and user-friendly Agent-based Social Simulator for Social Networks.
Learn how to run your own simulations with our [documentation](http://soilsim.readthedocs.io).

Follow our [tutorial](examples/tutorial/soil_tutorial.ipynb) to develop your own agent models.


# Changes in version 0.3

Version 0.3 came packed with many changes to provide much better integration with MESA.
For a long time, we tried to keep soil backwards-compatible, but it turned out to be a big endeavour and the resulting code was less readable.
This translates to harder maintenance and a worse experience for newcomers. 
In the end, we decided to make some breaking changes.

If you have an older Soil simulation, you have two options:

* Update the necessary configuration files and code. You may use the examples in the `examples` folder for reference, as well as the documentation.
* Keep using a previous `soil` version.

## Mesa compatibility

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
