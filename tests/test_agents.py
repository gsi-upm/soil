from unittest import TestCase
import pytest

from soil import agents, environment
from soil import time as stime


class Dead(agents.FSM):
    @agents.default_state
    @agents.state
    def only(self):
        return self.die()


class TestAgents(TestCase):
    def test_die_returns_infinity(self):
        '''The last step of a dead agent should return time.INFINITY'''
        d = Dead(unique_id=0, model=environment.Environment())
        ret = d.step()
        assert ret == stime.NEVER

    def test_die_raises_exception(self):
        '''A dead agent should raise an exception if it is stepped after death'''
        d = Dead(unique_id=0, model=environment.Environment())
        d.step()
        with pytest.raises(stime.DeadAgent):
            d.step()


    def test_agent_generator(self):
        '''
        The step function of an agent could be a generator. In that case, the state of the
        agent will be resumed after every call to step.
        '''
        a = 0
        class Gen(agents.BaseAgent):
            def step(self):
                nonlocal a
                for i in range(5):
                    yield
                    a += 1
        e = environment.Environment()
        g = Gen(model=e, unique_id=e.next_id())
        e.schedule.add(g)

        for i in range(5):
            e.step()
            assert a == i

    def test_state_decorator(self):
        class MyAgent(agents.FSM):
            run = 0
            @agents.default_state
            @agents.state('original')
            def root(self):
                self.run += 1
                return self.other

            @agents.state
            def other(self):
                self.run += 1

        e = environment.Environment()
        a = MyAgent(model=e, unique_id=e.next_id())
        a.step()
        assert a.run == 1
        a.step()


    def test_broadcast(self):
        '''
        An agent should be able to broadcast messages to every other agent, AND each receiver should be able
        to process it
        '''
        class BCast(agents.Evented):
            pings_received = 0

            def step(self):
                print(self.model.broadcast)
                try:
                    self.model.broadcast('PING')
                except Exception as ex:
                    print(ex)
                while True:
                    self.check_messages()
                    yield

            def on_receive(self, msg, sender=None):
                self.pings_received += 1
        
        e = environment.EventedEnvironment()

        for i in range(10):
            e.add_agent(agent_class=BCast)
        e.step()
        pings_received = lambda: [a.pings_received for a in e.agents]
        assert sorted(pings_received()) == list(range(1, 11))
        e.step()
        assert all(x==10 for x in pings_received())

    def test_ask_messages(self):
        '''
        An agent should be able to ask another agent, and wait for a response.
        '''

        # #Results depend on ordering (agents are shuffled), so force the first agent
        pings = []
        pongs = []
        responses = []

        class Ping(agents.EventedAgent):
            def step(self):
                target_id = (self.unique_id + 1) % self.count_agents()
                target = self.model.agents[target_id]
                print('starting')
                while True:
                    print('Pings: ', pings, responses or not pings, self.model.schedule._queue)
                    if pongs or not pings:
                        pings.append(self.now)
                        response = yield target.ask('PING')
                        responses.append(response)
                    else:
                        print('NOT sending ping')
                    print('Checking msgs')
                    # Do not advance until we have received a message.
                    # warning: it will wait at least until the next time in the simulation
                    yield self.received(check=True)
                print('done')

            def on_receive(self, msg, sender=None):
                if msg == 'PING':
                    pongs.append(self.now)
                    return 'PONG'

        e = environment.EventedEnvironment()
        for i in range(2):
            e.add_agent(agent_class=Ping)
        assert e.now == 0

        # There should be a delay of one step between agent 0 and 1
        # On the first step:
        #   Agent 0 sends a PING, but blocks before a PONG
        #   Agent 1 sends a PONG, and blocks after its PING
        # After that step, every agent can both receive (there are pending messages) and then send.

        e.step()
        assert e.now == 1
        assert pings == [0]
        assert pongs == []

        e.step()
        assert e.now == 2
        assert pings == [0, 1]
        assert pongs == [1]

        e.step()
        assert e.now == 3
        assert pings == [0, 1, 2]
        assert pongs == [1, 2]
