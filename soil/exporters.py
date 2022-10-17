import os
import sys
from time import time as current_time
from io import BytesIO
from sqlalchemy import create_engine
from textwrap import dedent, indent


import matplotlib.pyplot as plt
import networkx as nx


from .serialization import deserialize
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
            "**Not** written to {} (dry run mode):\n\n{}\n\n".format(
                self.__fname, content
            )
        )
        super().close()


class Exporter:
    """
    Interface for all exporters. It is not necessary, but it is useful
    if you don't plan to implement all the methods.
    """

    def __init__(self, simulation, outdir=None, dry_run=None, copy_to=None):
        self.simulation = simulation
        outdir = outdir or os.path.join(os.getcwd(), "soil_output")
        self.outdir = os.path.join(outdir, simulation.group or "", simulation.name)
        self.dry_run = dry_run
        if copy_to is None and dry_run:
            copy_to = sys.stdout
        self.copy_to = copy_to

    def sim_start(self):
        """Method to call when the simulation starts"""
        pass

    def sim_end(self):
        """Method to call when the simulation ends"""
        pass

    def trial_start(self, env):
        """Method to call when a trial start"""
        pass

    def trial_end(self, env):
        """Method to call when a trial ends"""
        pass

    def output(self, f, mode="w", **kwargs):
        if self.dry_run:
            f = DryRunner(f, copy_to=self.copy_to)
        else:
            try:
                if not os.path.isabs(f):
                    f = os.path.join(self.outdir, f)
            except TypeError:
                pass
        return open_or_reuse(f, mode=mode, **kwargs)

    def get_dfs(self, env):
        yield from get_dc_dfs(env.datacollector, trial_id=env.id)


def get_dc_dfs(dc, trial_id=None):
    dfs = {
        "env": dc.get_model_vars_dataframe(),
        "agents": dc.get_agent_vars_dataframe(),
    }
    for table_name in dc.tables:
        dfs[table_name] = dc.get_table_dataframe(table_name)
    if trial_id:
        for (name, df) in dfs.items():
            df["trial_id"] = trial_id
    yield from dfs.items()


class default(Exporter):
    """Default exporter. Writes sqlite results, as well as the simulation YAML"""

    def sim_start(self):
        if self.dry_run:
            logger.info("NOT dumping results")
            return
        logger.info("Dumping results to %s", self.outdir)
        with self.output(self.simulation.name + ".dumped.yml") as f:
            f.write(self.simulation.to_yaml())
        self.dbpath = os.path.join(self.outdir, f"{self.simulation.name}.sqlite")
        try_backup(self.dbpath, remove=True)

    def trial_end(self, env):
        if self.dry_run:
            logger.info("Running in DRY_RUN mode, the database will NOT be created")
            return

        with timer(
            "Dumping simulation {} trial {}".format(self.simulation.name, env.id)
        ):

            engine = create_engine(f"sqlite:///{self.dbpath}", echo=False)

            for (t, df) in self.get_dfs(env):
                df.to_sql(t, con=engine, if_exists="append")


class csv(Exporter):

    """Export the state of each environment (and its agents) in a separate CSV file"""

    def trial_end(self, env):
        with timer(
            "[CSV] Dumping simulation {} trial {} @ dir {}".format(
                self.simulation.name, env.id, self.outdir
            )
        ):
            for (df_name, df) in self.get_dfs(env):
                with self.output("{}.{}.csv".format(env.id, df_name)) as f:
                    df.to_csv(f)


# TODO: reimplement GEXF exporting without history
class gexf(Exporter):
    def trial_end(self, env):
        if self.dry_run:
            logger.info("Not dumping GEXF in dry_run mode")
            return

        with timer(
            "[GEXF] Dumping simulation {} trial {}".format(self.simulation.name, env.id)
        ):
            with self.output("{}.gexf".format(env.id), mode="wb") as f:
                network.dump_gexf(env.history_to_graph(), f)
                self.dump_gexf(env, f)


class dummy(Exporter):
    def sim_start(self):
        with self.output("dummy", "w") as f:
            f.write("simulation started @ {}\n".format(current_time()))

    def trial_start(self, env):
        with self.output("dummy", "w") as f:
            f.write("trial started@ {}\n".format(current_time()))

    def trial_end(self, env):
        with self.output("dummy", "w") as f:
            f.write("trial ended@ {}\n".format(current_time()))

    def sim_end(self):
        with self.output("dummy", "a") as f:
            f.write("simulation ended @ {}\n".format(current_time()))


class graphdrawing(Exporter):
    def trial_end(self, env):
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
    """Print a summary of each trial to sys.stdout"""

    def trial_end(self, env):
        for (t, df) in self.get_dfs(env):
            if not len(df):
                continue
            msg = indent(str(df.describe()), "    ")
            logger.info(
                dedent(
                    f"""
            Dataframe {t}:
            """
                )
                + msg
            )
