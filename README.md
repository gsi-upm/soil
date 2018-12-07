# Graph Visualization with D3.js

The aim of this software is to provide a useful tool for visualising and analysing the result of different simulations based on graph. Once you run the simulation, you will be able to interact with the simulation in real time.

For this purpose, a model which tries to simulate the spread of information to comprehend the radicalism spread in a society is included. Whith all this, the main project goals could be divided in five as it is shown in the following.

* Simulate the spread of information through a network applied to radicalism.
* Visualize the results of the simulation.
* Interact with the simulation in real time.
* Extract data from the results.
* Show data in a right way for its research.

## Deploying the server

For deploying the application, you will only need to run the following command.

`python3 run.py [--name NAME] [--dump] [--port PORT] [--verbose]`

Where the options are detailed in the following table.

| Option | Description |
| --- | --- |
| `--name NAME` | The name of the simulation. It will appear on the app. |
| `--dump` | For dumping the results in server side. |
| `--port PORT` | The port where the server will listen. |
| `--verbose` | Verbose mode. |

> You can dump the results of the simulation in server side. Anyway, you will be able to download them in GEXF or JSON Graph format directly from the browser.

## Visualization Params

The configuration of the simulation is based on the simulator configuration. In this case, it follows the [SOIL](https://github.com/gsi-upm/soil) configuration syntax and for visualising the results in a more comfortable way, more params can be added in `visualization_params` dictionary.

* For setting a background image, the tag needed is `background image`. You can also add a `background_opacity` and `background_filter_color` if the image is so clear than you can difficult view the nodes.
* For setting colors to the nodes, you can do it based on their properties values. Using the `color` tag, you will need to indicate the attribute key and value, and then the color you want to apply.
* The shapes applied to a group of nodes are always the same. This means than it won't change dynamically, so you will have to indicate the property with the `shape_property` tag and add a dictionary called `shapes` in which for each value, you indicate the shape.
  All shapes have to had been downloaded before in SVG format and added to the server.

An example of this configuration applied to the TerroristNetworkModel is presented.

```yaml
visualization_params:
  # Icons downloaded from https://www.iconfinder.com/
  shape_property: agent
  shapes:
    TrainingAreaModel: target
    HavenModel: home
    TerroristNetworkModel: person
  colors:
    - attr_id: 0
      color: '#40de40'
    - attr_id: 1
      color: red
    - attr_id: 2
      color: '#c16a6a'
  background_image: 'map_4800x2860.jpg'
  background_opacity: '0.9'
  background_filter_color: 'blue'
```
