import random
import time

settings = {
    "empresas": ["BBVA", "Santander"]
}

class BaseNetworkAgent:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = random.random()

    @property
    def env(self):
        class T(object):
            pass

        temp = T()
        temp.now = time.time()
        return temp


def agentes_a_json(agentes):
    final = {}
    for agente in agentes:
        for stamp, attrs in self._attrs.items():
            for a in attrs:
                if a not in final:
                   final[a] = {}
                final[a][stamp] = attrs[a]
    return final

class ComportamientoBase(BaseNetworkAgent):
    def __init__(self, *args, **kwargs):
        self._attrs = {}

    @property
    def attrs(self):
        now = self.env.now
        if now not in self._attrs:
            self._attrs[now] = {}
        return self._attrs[now]

    @attrs.setter
    def attrs(self, value):
        self._attrs[self.env.now] = value

    def run(self):
        while True:
            self.step(self.env.now)
            #yield self.env.timeout(settings.timeout)

    def step(self, now):
        pass

    def a_json(self):
        final = {}
        for stamp, attrs in self._attrs.items():
            for a in attrs:
                if a not in final:
                   final[a] = {}
                final[a][stamp] = attrs[a]
        return final

class NuevoComportamiento(ComportamientoBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresas = settings["empresas"]

    def step(self, now):
        for i in self.empresas:
            self.attrs['sentimiento_empresa_%s' % i] = random.random()
