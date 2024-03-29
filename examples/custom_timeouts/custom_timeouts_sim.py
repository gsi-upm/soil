from soil.agents import FSM, state, default_state


class Fibonacci(FSM):
    """Agent that only executes in t_steps that are Fibonacci numbers"""
    prev = 1

    @default_state
    @state
    def counting(self):
        self.log("Stopping at {}".format(self.now))
        prev, self["prev"] = self["prev"], max([self.now, self["prev"]])
        return self.delay(prev)
    


class Odds(FSM):
    """Agent that only executes in odd t_steps"""

    @state(default=True)
    def odds(self):
        self.log("Stopping at {}".format(self.now))
        return self.delay(1 + (self.now % 2))


from soil import Environment, Simulation
from networkx import complete_graph


class TimeoutsEnv(Environment):
    def init(self):
        self.create_network(generator=complete_graph, n=2)
        self.add_agent(agent_class=Fibonacci, node_id=0)
        self.add_agent(agent_class=Odds, node_id=1)


sim = Simulation(model=TimeoutsEnv, max_steps=10)

if __name__ == "__main__":
    sim.run(dump=False)
