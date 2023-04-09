from unittest import TestCase

from soil import time, agents, environment


class TestMain(TestCase):
    def test_cond(self):
        """
        A condition should match a When if the concition is True
        """

        t = time.Cond(lambda t: True)
        f = time.Cond(lambda t: False)
        for i in range(10):
            w = time.When(i)
            assert w == t
            assert w is not f

    def test_cond(self):
        """
        Comparing a Cond to a Delta should always return False
        """

        c = time.Cond(lambda t: False)
        d = time.Delta(1)
        assert c is not d

    def test_cond_env(self):
        """ """

        times_started = []
        times_awakened = []
        times_asleep = []
        times = []
        done = []

        class CondAgent(agents.BaseAgent):
            def step(self):
                nonlocal done
                times_started.append(self.now)
                while True:
                    times_asleep.append(self.now)
                    yield time.Cond(lambda agent: agent.now >= 10, delta=2)
                    times_awakened.append(self.now)
                    if self.now >= 10:
                        break
                done.append(self.now)

        env = environment.Environment()
        env.add_agent(CondAgent)

        while env.schedule.time < 11:
            times.append(env.now)
            env.step()

        assert env.schedule.time == 11
        assert times_started == [0]
        assert times_awakened == [10]
        assert done == [10]
        # The first time will produce the Cond.
        assert env.schedule.steps == 6
        assert len(times) == 6

        while env.schedule.time < 13:
            times.append(env.now)
            env.step()

        assert times == [0, 2, 4, 6, 8, 10, 11]
        assert env.schedule.time == 13
        assert times_started == [0, 11]
        assert times_awakened == [10]
        assert done == [10]
        # Once more to yield the cond, another one to continue
        assert env.schedule.steps == 7
        assert len(times) == 7
