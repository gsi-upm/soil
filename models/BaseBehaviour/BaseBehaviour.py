import settings
from nxsim import BaseNetworkAgent
from .. import networkStatus


class BaseBehaviour(BaseNetworkAgent):

    def __init__(self, environment=None, agent_id=0, state=()):
        super().__init__(environment=environment, agent_id=agent_id, state=state)
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
            yield self.env.timeout(settings.network_params["timeout"])

    def step(self, now):
        networkStatus['agent_%s'% self.id] = self.to_json()

    def to_json(self):
        final = {}
        for stamp, attrs in self._attrs.items():
            for a in attrs:
                if a not in final:
                    final[a] = {}
                final[a][stamp] = attrs[a]
        return final
