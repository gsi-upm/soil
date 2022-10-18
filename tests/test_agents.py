from unittest import TestCase
import pytest

from soil import agents, environment
from soil import time as stime


class Dead(agents.FSM):
    @agents.default_state
    @agents.state
    def only(self):
        return self.die()


class TestMain(TestCase):
    def test_die_returns_infinity(self):
        '''The last step of a dead agent should return time.INFINITY'''
        d = Dead(unique_id=0, model=environment.Environment())
        ret = d.step().abs(0)
        print(ret, "next")
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
        assert a.run == 2
