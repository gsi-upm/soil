from .serialization import deserialize
import os
import time


def for_sim(simulation, names, dir_path=None):
    exporters = []
    for name in names:
        mod = deserialize(name, known_modules=['soil.exporters'])
        exporters.append(mod(simulation))
    return exporters


class Base:

    def __init__(self, simulation):
        self.sim = simulation

    def start(self):
        pass

    def end(self):
        pass

    def env(self):
        pass


class Dummy(Base):

    def start(self):
        with open(os.path.join(self.sim.outdir, 'dummy')) as f:
            f.write('simulation started @ {}'.format(time.time()))

    def env(self, env):
        with open(os.path.join(self.sim.outdir, 'dummy-trial-{}'.format(env.name))) as f:
            for i in env.history_to_tuples():
                f.write(','.join(i))


    def end(self):
        with open(os.path.join(self.sim.outdir, 'dummy')) as f:
            f.write('simulation ended @ {}'.format(time.time()))
