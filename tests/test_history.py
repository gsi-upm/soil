from unittest import TestCase

import os
import pandas as pd

from soil import history, analysis


ROOT = os.path.abspath(os.path.dirname(__file__))


class TestHistory(TestCase):

    def test_history(self):
        """
        """
        tuples = (
            ('a_0', 0, 'id', 'h',  ),
            ('a_0', 1, 'id', 'e',  ),
            ('a_0', 2, 'id', 'l',  ),
            ('a_0', 3, 'id', 'l',  ),
            ('a_0', 4, 'id', 'o',  ),
            ('a_1', 0, 'id', 'v',  ),
            ('a_1', 1, 'id', 'a',  ),
            ('a_1', 2, 'id', 'l',  ),
            ('a_1', 3, 'id', 'u',  ),
            ('a_1', 4, 'id', 'e',  ),
            ('env', 1, 'prob', 1),
            ('env', 3, 'prob', 2),
            ('env', 5, 'prob', 3),
            ('a_2', 7, 'finished', True),
        )
        h = history.History()
        h.save_tuples(tuples)
        # assert h['env', 0, 'prob'] == 0
        for i in range(1, 7):
            assert h['env', i, 'prob'] == ((i-1)//2)+1


        for i, k in zip(range(5), 'hello'):
            assert h['a_0', i, 'id'] == k
        for record, value in zip(h['a_0', None, 'id'], 'hello'):
            t_step, val = record
            assert val == value

        for i, k in zip(range(5), 'value'):
            assert h['a_1', i, 'id'] == k
        for i in range(5, 8):
            assert h['a_1', i, 'id'] == 'e'
        for i in range(7):
            assert h['a_2', i, 'finished'] == False
        assert h['a_2', 7, 'finished']

    def test_history_gen(self):
        """
        """
        tuples = (
            ('a_1', 0, 'id', 'v',  ),
            ('a_1', 1, 'id', 'a',  ),
            ('a_1', 2, 'id', 'l',  ),
            ('a_1', 3, 'id', 'u',  ),
            ('a_1', 4, 'id', 'e',  ),
            ('env', 1, 'prob', 1),
            ('env', 2, 'prob', 2),
            ('env', 3, 'prob', 3),
            ('a_2', 7, 'finished', True),
        )
        h = history.History()
        h.save_tuples(tuples)
        for t_step, key, value in h['env', None, None]:
            assert t_step == value
            assert key == 'prob'

        records = list(h[None, 7, None])
        assert len(records) == 3
        for i in records:
            agent_id, key, value = i
            if agent_id == 'a_1':
                assert key == 'id'
                assert value == 'e'
            elif agent_id == 'a_2':
                assert key == 'finished'
                assert value == True
            else:
                assert key == 'prob'
                assert value == 3


        records = h['a_1', 7, None]
        assert records['id'] == 'e'
