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
        """The last step of a dead agent should return time.INFINITY"""
        d = Dead(unique_id=0, model=environment.Environment())
        ret = d.step()
        assert ret == stime.INFINITY

    def test_die_raises_exception(self):
        """A dead agent should raise an exception if it is stepped after death"""
        d = Dead(unique_id=0, model=environment.Environment())
        assert d.alive
        d.step()
        assert not d.alive
        with pytest.raises(stime.DeadAgent):
            d.step()

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

        e = environment.Environment()
        a = e.add_agent(MyAgent)
        e.step()
        assert a.times_run == 0
        a.step()
        assert a.times_run == 1
        assert a.state_id == MyAgent.other.id
        a.step()
        assert a.times_run == 2

    def test_broadcast(self):
        """
        An agent should be able to broadcast messages to every other agent, AND each receiver should be able
        to process it
        """

        class BCast(agents.Evented):
            pings_received = 0

            def step(self):
                print(self.model.broadcast)
                try:
                    self.model.broadcast("PING")
                except Exception as ex:
                    print(ex)
                while True:
                    self.process_messages()
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
        assert all(x == 10 for x in pings_received())

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
                    if not self.process_messages():
                        yield from self.received()
                print("done")

            def on_receive(self, msg, sender=None):
                if msg == "PING":
                    pongs.append(self.now)
                    return "PONG"
                raise Exception("This should never happen")

        e = environment.EventedEnvironment(schedule_class=stime.OrderedTimedActivation)
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