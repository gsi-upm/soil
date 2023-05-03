import os
import sys
from time import time as current_time
from io import BytesIO
from textwrap import dedent, indent


import networkx as nx
import pandas as pd


from .serialization import deserialize, serialize
from .utils import try_backup, open_or_reuse, logger, timer


from . import utils, network


class DryRunner(BytesIO):
    def __init__(self, fname, *args, copy_to=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__fname = fname
        self.__copy_to = copy_to

    def write(self, txt):
        if self.__copy_to:
            self.__copy_to.write("{}:::{}".format(self.__fname, txt))
        try:
            super().write(txt)
        except TypeError:
            super().write(bytes(txt, "utf-8"))

    def close(self):
        content = "(binary data not shown)"
        try:
            content = self.getvalue().decode()
        except UnicodeDecodeError:
            pass
        logger.info(
            "**Not** written to {} (no_dump mode):\n\n{}\n\n".format(
                self.__fname, content
            )
        )
        super().close()


class Exporter:
    """
    Interface for all exporters. It is not necessary, but it is useful
    if you don't plan to implement all the methods.
    """

    def __init__(self, simulation, outdir=None, dump=True, copy_to=None):
        self.simulation = simulation
        outdir = outdir or os.path.join(os.getcwd(), "soil_output")
        self.outdir = os.path.join(outdir, simulation.group or "", simulation.name)
        self.dump = dump
        if copy_to is None and not dump:
            copy_to = sys.stdout
        self.copy_to = copy_to

    def sim_start(self):
        """Method to call when the simulation starts"""
        pass

    def sim_end(self):
        """Method to call when the simulation ends"""
        pass

    def iteration_start(self, env):
        """Method to call when a iteration start"""
        pass

    def iteration_end(self, env, params, params_id):
        """Method to call when a iteration ends"""
        pass

    def output(self, f, mode="w", **kwargs):
        if not self.dump:
            f = DryRunner(f, copy_to=self.copy_to)
        else:
            try:
                if not os.path.isabs(f):
                    f = os.path.join(self.outdir, f)
            except TypeError:
                pass
        return open_or_reuse(f, mode=mode, backup=self.simulation.backup, **kwargs)

    def get_dfs(self, env, **kwargs):
        yield from get_dc_dfs(env.datacollector,
                              simulation_id=self.simulation.id,
                              iteration_id=env.id,
                              **kwargs)


def get_dc_dfs(dc, **kwargs):
    dfs = {}
    dfe = dc.get_model_vars_dataframe()
    dfe.index.rename("step", inplace=True)
    dfs["env"] = dfe
    try:
        dfa = dc.get_agent_vars_dataframe() 
        dfa.index.rename(["step", "agent_id"], inplace=True)
        dfs["agents"] = dfa
    except UserWarning:
        pass
    for table_name in dc.tables:
        dfs[table_name] = dc.get_table_dataframe(table_name)
    for (name, df) in dfs.items():
        for (k, v) in kwargs.items():
            df[k] = v
        df.set_index(["simulation_id", "iteration_id"], append=True, inplace=True)
    
    yield from dfs.items()


class SQLite(Exporter):
    """Writes sqlite results"""
    sim_started = False

    def sim_start(self):
        if not self.dump:
            logger.debug("NOT dumping results")
            return

        from sqlalchemy import create_engine

        self.dbpath = os.path.join(self.outdir, f"{self.simulation.name}.sqlite")
        logger.info("Dumping results to %s", self.dbpath)
        if self.simulation.backup:
            try_backup(self.dbpath, remove=True)
        
        if self.simulation.overwrite:
            if os.path.exists(self.dbpath):
                os.remove(self.dbpath)
        
        self.engine = create_engine(f"sqlite:///{self.dbpath}", echo=False)

        sim_dict = {k: serialize(v)[0] for (k,v) in self.simulation.to_dict().items()}
        sim_dict["simulation_id"] = self.simulation.id
        df = pd.DataFrame([sim_dict])
        df.to_sql("configuration", con=self.engine, if_exists="append")

    def iteration_end(self, env, params, params_id, *args, **kwargs):
        if not self.dump:
            logger.info("Running in NO DUMP mode. Results will NOT be saved to a DB.")
            return

        with timer(
            "Dumping simulation {} iteration {}".format(self.simulation.name, env.id)
        ):

            pd.DataFrame([{"simulation_id": self.simulation.id,
                           "params_id": params_id,
                           "iteration_id": env.id,
                           "key": k,
                           "value": serialize(v)[0]} for (k,v) in params.items()]).to_sql("parameters", con=self.engine, if_exists="append")

            for (t, df) in self.get_dfs(env, params_id=params_id):
                df.to_sql(t, con=self.engine, if_exists="append")

class csv(Exporter):
    """Export the state of each environment (and its agents) a CSV file for the simulation"""

    def sim_start(self):
        super().sim_start()

    def iteration_end(self, env, params, params_id, *args, **kwargs):
        with timer(
            "[CSV] Dumping simulation {} iteration {} @ dir {}".format(
                self.simulation.name, env.id, self.outdir
            )
        ):
            for (df_name, df) in self.get_dfs(env, params_id=params_id):
                with self.output("{}.{}.csv".format(env.id, df_name), mode="a") as f:
                    df.to_csv(f)


class gexf(Exporter):
    def iteration_end(self, env, *args, **kwargs):
        if not self.dump:
            logger.info("Not dumping GEXF (NO_DUMP mode)")
            return

        with timer(
            "[GEXF] Dumping simulation {} iteration {}".format(self.simulation.name, env.id)
        ):
            with self.output("{}.gexf".format(env.id), mode="wb") as f:
                nx.write_gexf(env.G, f)


class dummy(Exporter):
    def sim_start(self):
        with self.output("dummy", "w") as f:
            f.write("simulation started @ {}\n".format(current_time()))

    def iteration_start(self, env):
        with self.output("dummy", "w") as f:
            f.write("iteration started@ {}\n".format(current_time()))

    def iteration_end(self, env, *args, **kwargs):
        with self.output("dummy", "w") as f:
            f.write("iteration ended@ {}\n".format(current_time()))

    def sim_end(self):
        with self.output("dummy", "a") as f:
            f.write("simulation ended @ {}\n".format(current_time()))


class graphdrawing(Exporter):
    def iteration_end(self, env, *args, **kwargs):
        import matplotlib.pyplot as plt
        # Outside effects
        f = plt.figure()
        nx.draw(
            env.G,
            node_size=10,
            width=0.2,
            pos=nx.spring_layout(env.G, scale=100),
            ax=f.add_subplot(111),
        )
        with open("graph-{}.png".format(env.id)) as f:
            f.savefig(f)


class summary(Exporter):
    """Print a summary of each iteration to sys.stdout"""

    def iteration_end(self, env, *args, **kwargs):
        msg = ""
        for (t, df) in self.get_dfs(env):
            if not len(df):
                continue
            tabs = "\t" * 2
            description = indent(str(df.describe()), tabs)
            last_line = indent(str(df.iloc[-1:]), tabs)
            # value_counts = indent(str(df.value_counts()), tabs)
            value_counts = indent(str(df.apply(lambda x: x.value_counts()).T.stack()), tabs)

            msg += dedent("""
            Dataframe {t}:
                Last line: :
            {last_line}

                Description:
            {description}

                Value counts:
            {value_counts}

            """).format(**locals())
        logger.info(msg)

class YAML(Exporter):
    """Writes the configuration of the simulation to a YAML file"""

    def sim_start(self):
        if not self.dump:
            logger.debug("NOT dumping results")
            return
        with self.output(self.simulation.id + ".dumped.yml") as f:
            logger.info(f"Dumping simulation configuration to {self.outdir}")
            f.write(self.simulation.to_yaml())

class default(Exporter):
    """Default exporter. Writes sqlite results, as well as the simulation YAML"""

    def __init__(self, *args, exporter_cls=[], **kwargs):
        exporter_cls = exporter_cls or [YAML, SQLite]
        self.inner = [cls(*args, **kwargs) for cls in exporter_cls]

    def sim_start(self, *args, **kwargs):
        for exporter in self.inner:
            exporter.sim_start(*args, **kwargs)

    def sim_end(self, *args, **kwargs):
        for exporter in self.inner:
            exporter.sim_end(*args, **kwargs)

    def iteration_end(self, *args, **kwargs):
        for exporter in self.inner:
            exporter.iteration_end(*args, **kwargs)
