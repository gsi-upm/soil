from typing import Optional

import sys
import threading

import matplotlib.pyplot as plt
import reacton.ipywidgets as widgets
import solara
from solara.alias import rv

import mesa.experimental.components.matplotlib as components_matplotlib
from mesa.experimental.jupyter_viz import *
from matplotlib.figure import Figure
import networkx as nx


class Controller:
    '''
    A visualization controller that holds a reference to a model so that it can be modified or queried while the simulation is still running.
    '''
    def __init__(self):
        self.model = None


def JupyterViz(*args, **kwargs):
    c = Controller()
    page = JupyterPage(*args, controller=c, **kwargs)
    page.controller = c
    return page


@solara.component
def JupyterPage(
    model_class,
    model_params,
    controller=None,
    measures=None,
    name="Mesa Model",
    agent_portrayal=None,
    space_drawer="default",
    play_interval=150,
    columns=2,
):
    """Initialize a component to visualize a model.
    Args:
        model_class: class of the model to instantiate
        model_params: parameters for initializing the model
        measures: list of callables or data attributes to plot
        name: name for display
        agent_portrayal: options for rendering agents (dictionary)
        space_drawer: method to render the agent space for
            the model; default implementation is the `SpaceMatplotlib` component;
            simulations with no space to visualize should
            specify `space_drawer=False`
        play_interval: play interval (default: 150)
    """
    if controller is None:
        controller = Controller()

    current_step = solara.use_reactive(0)

    # 1. Set up model parameters
    user_params, fixed_params = split_model_params(model_params)
    model_parameters, set_model_parameters = solara.use_state(
        {**fixed_params, **{k: v["value"] for k, v in user_params.items()}}
    )

    # 2. Set up Model
    def make_model():
        model = model_class(**model_parameters)
        current_step.value = 0
        controller.model = model
        return model

    reset_counter = solara.use_reactive(0)
    model = solara.use_memo(
        make_model, dependencies=[*list(model_parameters.values()), reset_counter.value]
    )

    def handle_change_model_params(name: str, value: any):
        set_model_parameters({**model_parameters, name: value})

    # 3. Set up UI
    with solara.AppBar():
        solara.AppBarTitle(name)

    with solara.GridFixed(columns=2):
        UserInputs(user_params, on_change=handle_change_model_params)
        ModelController(model, play_interval, current_step, reset_counter)
        solara.Markdown(md_text=f"###Step: {current_step} - Time: {model.schedule.time } ")

    with solara.GridFixed(columns=columns):
        # 4. Space
        if space_drawer == "default":
            # draw with the default implementation
            components_matplotlib.SpaceMatplotlib(
                model, agent_portrayal, dependencies=[current_step.value]
            )
        elif space_drawer:
            # if specified, draw agent space with an alternate renderer
            space_drawer(model, agent_portrayal, dependencies=[current_step.value])
        # otherwise, do nothing (do not draw space)

        # 5. Plots
        for measure in measures:
            if callable(measure):
                # Is a custom object
                measure(model)
            else:
                components_matplotlib.make_plot(model, measure)


@solara.component
def NetworkDrawer(model, network_portrayal, dependencies: Optional[list[any]] = None):
    space_fig = Figure()
    space_ax = space_fig.subplots()
    graph = model.grid.G
    nx.draw(
        graph,
        ax=space_ax,
        **network_portrayal(graph),
    )
    solara.FigureMatplotlib(space_fig, format="png", dependencies=dependencies)


try:
    import osmnx as ox

    @solara.component
    def GeoNetworkDrawer(model, network_portrayal, dependencies: Optional[list[any]] = None):
        space_fig = Figure()
        space_ax = space_fig.subplots()
        graph = model.grid.G
        ox.plot_graph(
            graph,
            ax=space_ax,
            **network_portrayal(graph),
        )
        solara.FigureMatplotlib(space_fig, format="png", dependencies=dependencies)
except ImportError:
    pass
