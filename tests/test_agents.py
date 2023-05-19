from unittest import TestCase
import pytest

from soil import agents, events, environment
from soil import time as stime


class Dead(agents.FSM):
    @agents.default_state
    @agents.state
    def only(self):
        return self.die()


class TestAgents(TestCase):
    def test_die_returns_infinity(self):
        """The last step of a dead agent should return time.INFINITY"""
        d = Dead(unique_id=0, model=environment.Environment())
        ret = d.step()
        assert ret == stime.INFINITY

    def test_die_raises_exception(self):
        """A dead agent should continue returning INFINITY after death"""
        d = Dead(unique_id=0, model=environment.Environment())
        assert d.alive
        d.step()
        assert not d.alive
        when = float(d.step())
        assert not d.alive
        assert when == stime.INFINITY

    def test_agent_generator(self):
        """
        The step function of an agent could be a generator. In that case, the state of the
        agent will be resumed after every call to step.
        """
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
            times_run = 0

            @agents.state("original", default=True)
            def root(self):
                return self.other

            @agents.state
            def other(self):
                self.times_run += 1

        assert MyAgent.other.id == "other"
        e = environment.Environment()
        a = e.add_agent(MyAgent)
        e.step()
        assert a.times_run == 0
        a.step()
        assert a.times_run == 1
        assert a.state_id == MyAgent.other.id
        a.step()
        assert a.times_run == 2

    def test_state_decorator_multiple(self):
        class MyAgent(agents.FSM):
            times_run = 0

            @agents.state(default=True)
            def one(self):
                return self.two

            @agents.state
            def two(self):
                return self.one

        e = environment.Environment()
        first = e.add_agent(MyAgent, state_id=MyAgent.one)
        second = e.add_agent(MyAgent, state_id=MyAgent.two)
        assert first.state_id == MyAgent.one.id
        assert second.state_id == MyAgent.two.id
        e.step()
        assert first.state_id == MyAgent.two.id
        assert second.state_id == MyAgent.one.id

    def test_state_decorator_multiple_async(self):
        class MyAgent(agents.FSM):
            times_run = 0

            @agents.state(default=True)
            def one(self):
                yield self.delay(1)
                return self.two

            @agents.state
            def two(self):
                yield self.delay(1)
                return self.one

        e = environment.Environment()
        first = e.add_agent(MyAgent, state_id=MyAgent.one)
        second = e.add_agent(MyAgent, state_id=MyAgent.two)
        for i in range(2):
            assert first.state_id == MyAgent.one.id
            assert second.state_id == MyAgent.two.id
            e.step()
        for i in range(2):
            assert first.state_id == MyAgent.two.id
            assert second.state_id == MyAgent.one.id
            e.step()

    def test_broadcast(self):
        """
        An agent should be able to broadcast messages to every other agent, AND each receiver should be able
        to process it
        """

        class BCast(agents.Evented):
            pings_received = []

            async def step(self):
                self.broadcast("PING")
                print("PING sent")
                while True:
                    msgs = await self.received()
                    self.pings_received += msgs

        e = environment.Environment()

        num_agents = 10
        for i in range(num_agents):
            e.add_agent(agent_class=BCast)
        e.step()
        # Agents are executed in order, so the first agent should have not received any messages
        pings_received = lambda: [len(a.pings_received) for a in e.agents]
        assert sorted(pings_received()) == list(range(0, num_agents))
        e.step()
        # After the second step, every agent should have received a broadcast from every other agent
        received = pings_received()
        assert all(x == (num_agents - 1) for x in received)

    def test_ask_messages(self):
        """
        An agent should be able to ask another agent, and wait for a response.
        """

        # There are two agents, they try to send pings
        # This is arguably a very contrived example.
        # There should be a delay of one step between agent 0 and 1
        # On the first step:
        #   Agent 0 sends a PING, but blocks before a PONG
        #   Agent 1 detects the PING, responds with a PONG, and blocks after its own PING
        # After that step, every agent can both receive (there are pending messages) and send.
        # In each step, for each agent, one message is sent, and another one is received
        # (although not necessarily in that order).

        # Results depend on ordering (agents are normally shuffled)
        # so we force the timedactivation not to be shuffled

        pings = []
        pongs = []
        responses = []

        class Ping(agents.EventedAgent):
            def step(self):
                target_id = (self.unique_id + 1) % self.count_agents()
                target = self.model.agents[target_id]
                print("starting")
                while True:
                    if pongs or not pings:  # First agent, or anyone after that
                        pings.append(self.now)
                        response = yield from target.ask("PING")
                        responses.append(response)
                    else:
                        print("NOT sending ping")
                    print("Checking msgs")
                    # Do not block if we have already received a PING
                    msgs = yield from self.received()
                    for ping in msgs:
                        if ping.payload == "PING":
                            ping.reply = "PONG"
                            pongs.append(self.now)
                        else:
                            raise Exception("This should never happen")


        e = environment.Environment(schedule_class=stime.OrderedTimedActivation)
        for i in range(2):
            e.add_agent(agent_class=Ping)
        assert e.now == 0

        for i in range(5):
            e.step()
            time = i + 1
            assert e.now == time
            assert len(pings) == 2 * time
            assert len(pongs) == (2 * time) - 1
            # Every step between 0 and t appears twice
            assert sum(pings) == sum(range(time)) * 2
            # It is the same as pings, without the leading 0
            assert sum(pongs) == sum(range(time)) * 2

    def test_agent_filter(self):
        e = environment.Environment()
        e.add_agent(agent_class=agents.BaseAgent)
        e.add_agent(agent_class=agents.Evented)
        base = list(e.agents(agent_class=agents.BaseAgent))
        assert len(base) == 2
        ev = list(e.agents(agent_class=agents.Evented))
        assert len(ev) == 1
        assert ev[0].unique_id == 1
        null = list(e.agents(unique_ids=[0, 1], agent_class=agents.NetworkAgent))
        assert not null

    def test_agent_return(self):
        '''
        An agent should be able to cycle through different states and control when it
        should be awaken.
        '''
        class TestAgent(agents.Agent):
            @agents.state(default=True)
            def one(self):
                return self.two
            
            @agents.state
            def two(self):
                return self.three.at(10)
            
            @agents.state
            def three(self):
                return self.four.delay(1)

            @agents.state
            def four(self):
                yield self.delay(2)
                return self.five.delay(3)
            
            @agents.state
            def five(self):
                return self.delay(1)

        model = environment.Environment()
        a = model.add_agent(TestAgent)
        assert a.state_id == TestAgent.one.id
        assert a.now == 0
        model.step()
        assert a.state_id == TestAgent.two.id
        assert a.now == 1
        model.step()
        assert a.state_id == TestAgent.three.id
        assert a.now == 10
        model.step()
        assert a.state_id == TestAgent.four.id
        assert a.now == 11
        model.step()
        assert a.state_id == TestAgent.four.id
        assert a.now == 13
        model.step()
        assert a.state_id == TestAgent.five.id
        assert a.now == 16
        model.step()
        assert a.state_id == TestAgent.five.id
        assert a.now == 17

    def test_agent_async(self):
        '''
        Async functions should also be valid states.
        '''

        class TestAgent(agents.Agent):
            @agents.state(default=True)
            def one(self):
                return self.two
            
            @agents.state
            def two(self):
                return self.three.at(10)
            
            @agents.state
            def three(self):
                return self.four.delay(1)

            @agents.state
            async def four(self):
                await self.delay(2)
                return self.five.delay(3)
            
            @agents.state
            def five(self):
                return self.delay(1)
            
        model = environment.Environment()
        a = model.add_agent(TestAgent)
        assert a.now == 0
        assert a.state_id == TestAgent.one.id
        model.step()
        assert a.now == 1
        assert a.state_id == TestAgent.two.id
        model.step()
        assert a.now == 10
        assert a.state_id == TestAgent.three.id
        model.step()
        assert a.state_id == TestAgent.four.id
        assert a.now == 11
        model.step()
        assert a.state_id == TestAgent.four.id
        assert a.now == 13
        model.step()
        assert a.state_id == TestAgent.five.id
        assert a.now == 16
        model.step()
        assert a.state_id == TestAgent.five.id
        assert a.now == 17

    def test_agent_return_step(self):
        '''
        The same result as the previous test should be achievable by manually
        handling the agent state.
        '''
        class TestAgent(agents.Agent):
            my_state = 1
            my_count = 0

            def step(self):
                if self.my_state == 1:
                    self.my_state = 2
                    return None
                elif self.my_state == 2:
                    self.my_state = 3
                    return self.at(10)
                elif self.my_state == 3:
                    self.my_state = 4
                    self.my_count = 0
                    return self.delay(1)
                elif self.my_state == 4:
                    self.my_count += 1
                    if self.my_count == 1:
                        return self.delay(2)
                    self.my_state = 5
                    return self.delay(3)
                elif self.my_state == 5:
                    return self.delay(1)

        model = environment.Environment()
        a = model.add_agent(TestAgent)
        assert a.my_state == 1
        assert a.now == 0
        model.step()
        assert a.now == 1
        assert a.my_state == 2
        model.step()
        assert a.now == 10
        assert a.my_state == 3
        model.step()
        assert a.now == 11
        assert a.my_state == 4
        model.step()
        assert a.now == 13
        assert a.my_state == 4
        model.step()
        assert a.now == 16
        assert a.my_state == 5
        model.step()
        assert a.now == 17
        assert a.my_state == 5

    def test_agent_return_step_async(self):
        '''
        The same result as the previous test should be achievable by manually
        handling the agent state.
        '''
        class TestAgent(agents.Agent):
            my_state = 1

            async def step(self):
                self.my_state = 2
                await self.delay()
                self.my_state = 3
                await self.at(10)
                self.my_state = 4
                await self.delay(1)
                await self.delay(2)
                self.my_state = 5
                await self.delay(3)
                while True:
                    await self.delay(1)

        model = environment.Environment()
        a = model.add_agent(TestAgent)
        assert a.my_state == 1
        assert a.now == 0
        model.step()
        assert a.now == 1
        assert a.my_state == 2
        model.step()
        assert a.now == 10
        assert a.my_state == 3
        model.step()
        assert a.now == 11
        assert a.my_state == 4
        model.step()
        assert a.now == 13
        assert a.my_state == 4
        model.step()
        assert a.now == 16
        assert a.my_state == 5
        model.step()
        assert a.now == 17
        assert a.my_state == 5
    
    def test_receive(self):
        '''
        An agent should be able to receive a message after waiting
        '''
        model = environment.Environment()
        class TestAgent(agents.Agent):
            sent = False
            woken = 0
            def step(self):
                self.woken += 1
                return super().step()

            @agents.state(default=True)
            async def one(self):
                try:
                    self.sent = await self.received(timeout=15)
                    return self.two.at(20)
                except events.TimedOut:
                    pass
            @agents.state
            def two(self):
                return self.die()

        a = model.add_agent(TestAgent)

        class Sender(agents.Agent):
            async def step(self):
                await self.delay(10)
                a.tell(1)
                return stime.INFINITY

        b = model.add_agent(Sender)

        # Start and wait
        model.step()
        assert model.now == 10
        assert a.woken == 1
        assert not a.sent

        # Sending the message
        model.step()
        assert model.now == 10
        assert a.woken == 1
        assert not a.sent

        # The receiver callback
        model.step()
        assert model.now == 15
        assert a.woken == 2
        assert a.sent[0].payload == 1

        # The timeout
        model.step()
        assert model.now == 20
        assert a.woken == 2

        # The last state of the agent
        model.step()
        assert a.woken == 3
        assert model.now == float('inf')

    def test_receive_timeout(self):
        '''
        A timeout should be raised if no messages are received after an expiration time
        '''
        model = environment.Environment()
        timedout = False
        class TestAgent(agents.Agent):
            @agents.state(default=True)
            def one(self):
                try:
                    yield from self.received(timeout=10)
                    raise AssertionError('Should have raised an error.')
                except events.TimedOut:
                    nonlocal timedout
                    timedout = True

        a = model.add_agent(TestAgent)

        model.step()
        assert model.now == 10
        model.step()
        # Wake up the callback
        assert model.now == 10
        assert not timedout
        # The actual timeout
        model.step()
        assert model.now == 11
        assert timedout

    def test_attributes(self):
        """Attributes should be individual per agent"""

        class MyAgent(agents.Agent):
            my_attribute = 0
        
        model = environment.Environment()
        a = MyAgent(model=model)
        assert a.my_attribute == 0
        b = MyAgent(model=model, my_attribute=1)
        assert b.my_attribute == 1
        assert a.my_attribute == 0
