import os
import sys
from time import time as current_time
from io import BytesIO
from sqlalchemy import create_engine


import matplotlib.pyplot as plt
import networkx as nx


from .serialization import deserialize
from .utils import open_or_reuse, logger, timer


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


class default(Exporter):
    """Default exporter. Writes sqlite results, as well as the simulation YAML"""

    def sim_start(self):
        if not self.dry_run:
            logger.info("Dumping results to %s", self.outdir)
            with self.output(self.simulation.name + ".dumped.yml") as f:
                f.write(self.simulation.to_yaml())
        else:
            logger.info("NOT dumping results")

    def trial_end(self, env):
        if self.dry_run:
            logger.info("Running in DRY_RUN mode, the database will NOT be created")
            return

        with timer(
            "Dumping simulation {} trial {}".format(self.simulation.name, env.id)
        ):

            fpath = os.path.join(self.outdir, f"{env.id}.sqlite")
            engine = create_engine(f"sqlite:///{fpath}", echo=False)

            dc = env.datacollector
            for (t, df) in get_dc_dfs(dc):
                df.to_sql(t, con=engine, if_exists="append")


def get_dc_dfs(dc):
    dfs = {
        "env": dc.get_model_vars_dataframe(),
        "agents": dc.get_agent_vars_dataframe(),
    }
    for table_name in dc.tables:
        dfs[table_name] = dc.get_table_dataframe(table_name)
    yield from dfs.items()


class csv(Exporter):

    """Export the state of each environment (and its agents) in a separate CSV file"""

    def trial_end(self, env):
        with timer(
            "[CSV] Dumping simulation {} trial {} @ dir {}".format(
                self.simulation.name, env.id, self.outdir
            )
        ):
            for (df_name, df) in get_dc_dfs(env.datacollector):
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


"""
Convert an environment into a NetworkX graph
"""


def env_to_graph(env, history=None):
    G = nx.Graph(env.G)

    for agent in env.network_agents:

        attributes = {"agent": str(agent.__class__)}
        lastattributes = {}
        spells = []
        lastvisible = False
        laststep = None
        if not history:
            history = sorted(list(env.state_to_tuples()))
        for _, t_step, attribute, value in history:
            if attribute == "visible":
                nowvisible = value
                if nowvisible and not lastvisible:
                    laststep = t_step
                if not nowvisible and lastvisible:
                    spells.append((laststep, t_step))

                lastvisible = nowvisible
                continue
            key = "attr_" + attribute
            if key not in attributes:
                attributes[key] = list()
            if key not in lastattributes:
                lastattributes[key] = (value, t_step)
            elif lastattributes[key][0] != value:
                last_value, laststep = lastattributes[key]
                commit_value = (last_value, laststep, t_step)
                if key not in attributes:
                    attributes[key] = list()
                attributes[key].append(commit_value)
                lastattributes[key] = (value, t_step)
        for k, v in lastattributes.items():
            attributes[k].append((v[0], v[1], None))
        if lastvisible:
            spells.append((laststep, None))
        if spells:
            G.add_node(agent.id, spells=spells, **attributes)
        else:
            G.add_node(agent.id, **attributes)

    return G
