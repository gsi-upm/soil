from unittest import TestCase

from soil import time, agents, environment


class TestMain(TestCase):

    def test_cond_env(self):
        """ """

        times_started = []
        times_awakened = []
        times_asleep = []
        times = []
        done = []

        class CondAgent(agents.BaseAgent):
            def step(self):
                nonlocal done, times_started, times_asleep, times_awakened
                times_started.append(self.now)
                while True:
                    times_asleep.append(self.now)
                    while self.now < 10:
                        yield self.delay(2)
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
        assert env.schedule.steps == 6
        assert len(times) == 6

        while env.schedule.time < 13:
            times.append(env.now)
            env.step()

        assert times == [0, 2, 4, 6, 8, 10, 11, 12]
        assert env.schedule.time == 13
        assert times_started == [0, 11, 12]
        assert times_awakened == [10, 11, 12]
        assert done == [10, 11, 12]
        assert env.schedule.steps == 8
        assert len(times) == 8
