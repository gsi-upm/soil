from soil.agents import FSM, state, default_state
from soil.time import Delta


class Fibonacci(FSM):
    """Agent that only executes in t_steps that are Fibonacci numbers"""

    defaults = {"prev": 1}

    @default_state
    @state
    def counting(self):
        self.log("Stopping at {}".format(self.now))
        prev, self["prev"] = self["prev"], max([self.now, self["prev"]])
        return None, Delta(prev)


class Odds(FSM):
    """Agent that only executes in odd t_steps"""

    @default_state
    @state
    def odds(self):
        self.log("Stopping at {}".format(self.now))
        return None, Delta(1 + self.now % 2)


from soil import Simulation

simulation = Simulation(
    model_params={
        'agents':[
            {'agent_class': Fibonacci, 'node_id': 0},
            {'agent_class': Odds, 'node_id': 1}
        ],
        'topology': {
            'params': {
                'generator': 'complete_graph',
                'n': 2
            }
        },
    },
    max_time=100,
)

if __name__ == "__main__":
    simulation.run(dry_run=True)
