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
    def test_die_raises_exception(self):
        d = Dead(unique_id=0, model=environment.Environment())
        d.step()
        with pytest.raises(agents.DeadAgent):
            d.step()

    def test_die_returns_infinity(self):
        d = Dead(unique_id=0, model=environment.Environment())
        ret = d.step().abs(0)
        print(ret, 'next')
        assert ret == stime.INFINITY
