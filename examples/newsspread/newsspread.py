from soil.agents import BaseAgent,FSM, state, default_state
import random
import logging


class DumbViewer(FSM):
    '''
    A viewer that gets infected via TV (if it has one) and tries to infect
    its neighbors once it's infected.
    '''
    defaults = {
        'prob_neighbor_spread': 0.5,
        'prob_neighbor_cure': 0.25,
    }

    @default_state
    @state
    def neutral(self):
        r = random.random()
        if self['has_tv'] and r < self.env['prob_tv_spread']:
            self.infect()
        return

    @state
    def infected(self):
        for neighbor in self.get_neighboring_agents(state_id=self.neutral.id):
            prob_infect = self.env['prob_neighbor_spread']
            r = random.random()
            if r < prob_infect:
                self.set_state(self.infected.id)
                neighbor.infect()
        return

    def infect(self):
        self.set_state(self.infected)

class HerdViewer(DumbViewer):
    '''
    A viewer whose probability of infection depends on the state of its neighbors.
    '''

    level = logging.DEBUG
 
    def infect(self):
        infected = self.count_neighboring_agents(state_id=self.infected.id)
        total = self.count_neighboring_agents()
        prob_infect = self.env['prob_neighbor_spread'] * infected/total
        self.debug('prob_infect', prob_infect)
        r = random.random()
        if r < prob_infect:
            self.set_state(self.infected.id)

class WiseViewer(HerdViewer):
    '''
    A viewer that can change its mind.
    '''
    @state
    def cured(self):
        prob_cure = self.env['prob_neighbor_cure']
        for neighbor in self.get_neighboring_agents(state_id=self.infected.id):
            r = random.random()
            if r < prob_cure:
                try:
                    neighbor.cure()
                except AttributeError:
                    self.debug('Viewer {} cannot be cured'.format(neighbor.id))
        return

    def cure(self):
        self.set_state(self.cured.id)

    @state
    def infected(self):
        prob_cure = self.env['prob_neighbor_cure']
        r = random.random()
        if r < prob_cure:
            self.cure()
            return
        return super().infected()
