import os
from server import VisualizationElement
from soil.simulation import SoilSimulation
from xml.etree import ElementTree


class Model():

    def __init__(self, dump=False, dir_path='output'):
        self.name = 'soil'
        self.dump = dump
        self.dir_path = dir_path
        self.simulation = list()

    def run(self, config):
        name = config['name']
        print('Using config(s): {name}'.format(name=name))

        sim = SoilSimulation(**config)
        sim.dir_path = os.path.join(self.dir_path, name)
        sim.dump = self.dump

        print('Dumping results to {} : {}'.format(sim.dir_path, sim.dump))
        
        return sim.run_simulation()

    def reset(self):
        pass


class GraphVisualization(VisualizationElement):
    package_includes = []

    # TODO: esta por definir todos los ajustes de simulacion
    def __init__(self, params=None):
        new_element = ("new funcion()")
        self.js_code = "elements.push(" + new_element + ");"

    def render(self, model):
        pass
