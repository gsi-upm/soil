from soil.agents import FSM, state, default_state


class Fibonacci(FSM):
    '''Agent that only executes in t_steps that are Fibonacci numbers'''

    defaults = {
        'prev': 1
    }

    @default_state
    @state
    def counting(self):
        self.log('Stopping at {}'.format(self.now))
        prev, self['prev'] = self['prev'], max([self.now, self['prev']])
        return None, self.env.timeout(prev)

class Odds(FSM):
    '''Agent that only executes in odd t_steps'''
    @default_state
    @state
    def odds(self):
        self.log('Stopping at {}'.format(self.now))
        return None, self.env.timeout(1+self.now%2)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    from soil import Simulation
    s = Simulation(network_agents=[{'ids': [0], 'agent_type': Fibonacci},
                                   {'ids': [1], 'agent_type': Odds}],
                   dry_run=True,
                   network_params={"generator": "complete_graph", "n": 2},
                   max_time=100,
                   )
    s.run()