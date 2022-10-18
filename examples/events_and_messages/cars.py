from __future__ import annotations
from soil import *
from soil import events
from mesa.space import MultiGrid
from enum import Enum


@dataclass
class Journey:
    origin: (int, int)
    destination: (int, int)
    tip: float

    passenger: Passenger = None
    driver: Driver = None


class City(EventedEnvironment):
    def __init__(self, *args, n_cars=1, height=100, width=100,  n_passengers=10, agents=None, **kwargs):
        self.grid = MultiGrid(width=width, height=height, torus=False)
        if agents is None:
            agents = []
            for i in range(n_cars):
                agents.append({'agent_class': Driver})
            for i in range(n_passengers):
                agents.append({'agent_class': Passenger})
        super().__init__(*args, agents=agents, **kwargs)
        for agent in self.agents:
            self.grid.place_agent(agent, (0, 0))
            self.grid.move_to_empty(agent)

class Driver(Evented, FSM):
    pos = None
    journey = None
    earnings = 0

    def on_receive(self, msg, sender):
        if self.journey is None and isinstance(msg, Journey) and msg.driver is None:
            msg.driver = self
            self.journey = msg

    @default_state
    @state
    def wandering(self):
        target = None
        self.check_passengers()
        self.journey = None
        while self.journey is None:
            if target is None or not self.move_towards(target):
                target = self.random.choice(self.model.grid.get_neighborhood(self.pos, moore=False))
            self.check_passengers()
            self.check_messages() # This will call on_receive behind the scenes
            yield Delta(30)
        try:
            self.journey = yield self.journey.passenger.ask(self.journey, timeout=60)
        except events.TimedOut:
            self.journey = None
            return
        return self.driving

    def check_passengers(self):
        c = self.count_agents(agent_class=Passenger)
        self.info(f"Passengers left {c}")
        if not c:
            self.die()

    @state
    def driving(self):
        #Approaching
        while self.move_towards(self.journey.origin):
            yield
        while self.move_towards(self.journey.destination, with_passenger=True):
            yield
        self.check_passengers()
        return self.wandering

    def move_towards(self, target, with_passenger=False):
        '''Move one cell at a time towards a target'''
        self.info(f"Moving { self.pos } -> { target }")
        if target[0] == self.pos[0] and target[1] == self.pos[1]:
            return False

        next_pos = [self.pos[0], self.pos[1]]
        for idx in [0, 1]:
            if self.pos[idx] < target[idx]:
                next_pos[idx] += 1
                break
            if self.pos[idx] > target[idx]:
                next_pos[idx] -= 1
                break
        self.model.grid.move_agent(self, tuple(next_pos))
        if with_passenger:
            self.journey.passenger.pos = self.pos  # This could be communicated through messages
        return True
            

class Passenger(Evented, FSM):
    pos = None

    @default_state
    @state
    def asking(self):
        destination = (self.random.randint(0, self.model.grid.height), self.random.randint(0, self.model.grid.width))
        self.journey = None
        journey = Journey(origin=self.pos,
                          destination=destination,
                          tip=self.random.randint(10, 100),
                          passenger=self)

        timeout = 60
        expiration = self.now + timeout
        self.model.broadcast(journey, ttl=timeout, sender=self, agent_class=Driver)
        while not self.journey:
            self.info(f"Passenger at: { self.pos }. Checking for responses.")
            try:
                yield self.received(expiration=expiration)
            except events.TimedOut:
                self.info(f"Passenger at: { self.pos }. Asking for journey.")
                self.model.broadcast(journey, ttl=timeout, sender=self, agent_class=Driver)
                expiration = self.now + timeout
            self.check_messages()
        return self.driving_home

    def on_receive(self, msg, sender):
        if isinstance(msg, Journey):
            self.journey = msg
            return msg

    @state
    def driving_home(self):
        while self.pos[0] != self.journey.destination[0] or self.pos[1] != self.journey.destination[1]:
            yield self.received(timeout=60)
        self.info("Got home safe!")
        self.die()


simulation = Simulation(model_class=City, model_params={'n_passengers': 2})

if __name__ == "__main__":
    with easy(simulation) as s:
        s.run()
