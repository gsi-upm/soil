from soil.agents import FSM, state, default_state, prob
import logging


class DumbViewer(FSM):
    '''
    A viewer that gets infected via TV (if it has one) and tries to infect
    its neighbors once it's infected.
    '''
    defaults = {
        'prob_neighbor_spread': 0.5,
        'prob_tv_spread': 0.1,
    }

    @default_state
    @state
    def neutral(self):
        if self['has_tv']:
            if prob(self.env['prob_tv_spread']):
                return self.infected

    @state
    def infected(self):
        for neighbor in self.get_neighboring_agents(state_id=self.neutral.id):
            if prob(self.env['prob_neighbor_spread']):
                neighbor.infect()

    def infect(self):
        '''
        This is not a state. It is a function that other agents can use to try to
        infect this agent. DumbViewer always gets infected, but other agents like
        HerdViewer might not become infected right away
        '''

        self.set_state(self.infected)


class HerdViewer(DumbViewer):
    '''
    A viewer whose probability of infection depends on the state of its neighbors.
    '''

    def infect(self):
        '''Notice again that this is NOT a state. See DumbViewer.infect for reference'''
        infected = self.count_neighboring_agents(state_id=self.infected.id)
        total = self.count_neighboring_agents()
        prob_infect = self.env['prob_neighbor_spread'] * infected/total
        self.debug('prob_infect', prob_infect)
        if prob(prob_infect):
            self.set_state(self.infected)


class WiseViewer(HerdViewer):
    '''
    A viewer that can change its mind.
    '''

    defaults = {
        'prob_neighbor_spread': 0.5,
        'prob_neighbor_cure': 0.25,
        'prob_tv_spread': 0.1,
    }

    @state
    def cured(self):
        prob_cure = self.env['prob_neighbor_cure']
        for neighbor in self.get_neighboring_agents(state_id=self.infected.id):
            if prob(prob_cure):
                try:
                    neighbor.cure()
                except AttributeError:
                    self.debug('Viewer {} cannot be cured'.format(neighbor.id))

    def cure(self):
        self.set_state(self.cured.id)

    @state
    def infected(self):
        cured = max(self.count_neighboring_agents(self.cured.id),
                    1.0)
        infected = max(self.count_neighboring_agents(self.infected.id),
                       1.0)
        prob_cure = self.env['prob_neighbor_cure'] * (cured/infected)
        if prob(prob_cure):
            return self.cured
        return self.set_state(super().infected)
