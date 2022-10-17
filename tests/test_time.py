from unittest import TestCase

from soil import time, agents, environment

class TestMain(TestCase):
    def test_cond(self):
        '''
        A condition should match a When if the concition is True
        '''

        t = time.Cond(lambda t: True)
        f = time.Cond(lambda t: False)
        for i in range(10):
            w = time.When(i)
            assert w == t
            assert w is not f

    def test_cond(self):
        '''
        Comparing a Cond to a Delta should always return False
        '''

        c = time.Cond(lambda t: False)
        d = time.Delta(1)
        assert c is not d

    def test_cond_env(self):
        '''
        '''

        times_started = []
        times_awakened = []
        times = []
        done = 0

        class CondAgent(agents.BaseAgent):

            def step(self):
                nonlocal done
                times_started.append(self.now)
                while True:
                    yield time.Cond(lambda agent: agent.model.schedule.time >= 10)
                    times_awakened.append(self.now)
                    if self.now >= 10:
                        break
                done += 1

        env = environment.Environment(agents=[{'agent_class': CondAgent}])


        while env.schedule.time < 11:
            env.step()
            times.append(env.now)
        assert env.schedule.time == 11
        assert times_started == [0]
        assert times_awakened == [10]
        assert done == 1
        # The first time will produce the Cond.
        # Since there are no other agents, time will not advance, but the number
        # of steps will.
        assert env.schedule.steps == 12
        assert len(times) == 12

        while env.schedule.time < 12:
            env.step()
            times.append(env.now)

        assert env.schedule.time == 12
        assert times_started == [0, 11]
        assert times_awakened == [10, 11]
        assert done == 2
        # Once more to yield the cond, another one to continue
        assert env.schedule.steps == 14
        assert len(times) == 14
