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
        assert ret == stime.NEVER

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
            run = 0

            @agents.state("original", default=True)
            def root(self):
                self.run += 1
                return self.other

            @agents.state
            def other(self):
                self.run += 1

        e = environment.Environment()
        a = e.add_agent(MyAgent)
        e.step()
        assert a.run == 1
        a.step()
        print("DONE")

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
                        response = yield target.ask("PING")
                        responses.append(response)
                    else:
                        print("NOT sending ping")
                    print("Checking msgs")
                    # Do not block if we have already received a PING
                    if not self.check_messages():
                        yield self.received()
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