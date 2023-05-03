import os
import sys
import sqlalchemy
import pandas as pd
from collections import namedtuple

def plot(env, agent_df=None, model_df=None, steps=False, ignore=["agent_count", ]):
    """Plot the model dataframe and agent dataframe together."""
    if model_df is None:
        model_df = env.model_df()
    ignore = list(ignore)
    if not steps:
        ignore.append("step")
    else:
        ignore.append("time")

    ax = model_df.drop(ignore, axis='columns').plot();
    if agent_df is None:
        try:
            agent_df = env.agent_df()
        except UserWarning:
            print("No agent dataframe provided and no agent reporters found. Skipping agent plot.", file=sys.stderr)
            return
    if not agent_df.empty:
        agent_df.unstack().apply(lambda x: x.value_counts(),
                                 axis=1).fillna(0).plot(ax=ax,
                                                        secondary_y=True)


Results = namedtuple("Results", ["config", "parameters", "env", "agents"])
#TODO implement reading from CSV

def read_sql(fpath=None, name=None, include_agents=False):
    if not (fpath is None) ^ (name is None):
        raise ValueError("Specify either a path or a simulation name")
    if name:
        fpath = os.path.join("soil_output", name, f"{name}.sqlite")
    fpath = os.path.abspath(fpath)
    # TODO: improve url parsing. This is a hacky way to check we weren't given a URL
    if "://" not in fpath:
        fpath = f"sqlite:///{fpath}"
    engine = sqlalchemy.create_engine(fpath)
    with engine.connect() as conn:
        env = pd.read_sql_table("env", con=conn,
                                index_col="step").reset_index().set_index([
                                    "simulation_id", "params_id",
                                    "iteration_id", "step"
                                ])
        agents = pd.read_sql_table("agents", con=conn, index_col=["simulation_id", "params_id", "iteration_id", "step", "agent_id"])
        config = pd.read_sql_table("configuration", con=conn, index_col="simulation_id")
        parameters = pd.read_sql_table("parameters", con=conn, index_col=["iteration_id", "params_id", "simulation_id"])
        try:
            parameters = parameters.pivot(columns="key", values="value")
        except Exception as e:
            print(f"warning: coult not pivot parameters: {e}")

        return Results(config, parameters, env, agents)
