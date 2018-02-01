import os
import networkx as nx
from server import VisualizationElement
from soil.simulation import SoilSimulation
from xml.etree import ElementTree


class Model():

    def __init__(self, dump=True, dir_path='output'):
        self.name = 'soil'
        self.dump = dump
        self.dir_path = dir_path

    def run(self, config):
        name = config['name']
        print('Using config(s): {name}'.format(name=name))

        sim = SoilSimulation(**config)
        sim.dir_path = os.path.join(self.dir_path, name)
        sim.dump = self.dump

        print('Dumping results to {} : {}'.format(sim.dir_path, sim.dump))
        
        sim.run_simulation()


    def get_trial(self, name, trial):
        graph = nx.read_gexf(os.path.join(self.dir_path, name, '{}_trial_{}.gexf'.format(name, trial)))

        attributes = self.get_attributes(os.path.join(self.dir_path, name, '{}_trial_{}.gexf'.format(name, trial)))
        json = {}
        json['graph'] = nx.node_link_data(graph)
        json['models'] = attributes
        return json

    def reset(self):
        pass

    def get_attributes(self, path_gexf):
        attributes = {}
        tree = ElementTree.parse(path_gexf)
        root = tree.getroot()

        ns = { 'gexf': 'http://www.gexf.net/1.2draft' }

        for mode in root[0].findall('gexf:attributes', ns):
            attributes[mode.attrib['mode']] = []
            for attribute in mode:
                values = {
                    'id'    : attribute.attrib['id'],
                    'title' : attribute.attrib['title'],
                    'type'  : attribute.attrib['type']
                }
                attributes[mode.attrib['mode']].append(values)

        return attributes


class GraphVisualization(VisualizationElement):
    package_includes = []

    # TODO: esta por definir todos los ajustes de simulacion
    def __init__(self, params=None):
        new_element = ("new funcion()")
        self.js_code = "elements.push(" + new_element + ");"

    def render(self, model):
        pass
