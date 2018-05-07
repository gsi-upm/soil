import time
import os
import pandas as pd
import sqlite3
import copy
from collections import UserDict, Iterable, namedtuple

from . import utils


class History:
    """
    Store and retrieve values from a sqlite database.
    """

    def __init__(self, db_path=None, name=None, dir_path=None, backup=True):
        if db_path is None and name:
            db_path = os.path.join(dir_path or os.getcwd(),
                                   '{}.db.sqlite'.format(name))
        if db_path is None:
            db_path = ":memory:"
        else:
            if backup and os.path.exists(db_path):
                newname = db_path + '.backup{}.sqlite'.format(time.time())
                os.rename(db_path, newname)
        self._db_path = db_path
        if isinstance(db_path, str):
            self._db = sqlite3.connect(db_path)
        else:
            self._db = db_path

        with self._db:
            self._db.execute('''CREATE TABLE IF NOT EXISTS history (agent_id text, t_step int, key text, value text text)''')
            self._db.execute('''CREATE TABLE IF NOT EXISTS value_types (key text, value_type text)''')
            self._db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_history ON history (agent_id, t_step, key);''')
        self._dtypes = {}
        self._tups = []

    def conversors(self, key):
        """Get the serializer and deserializer for a given key."""
        if key not in self._dtypes:
            self.read_types()
        return self._dtypes[key]

    @property
    def dtypes(self):
        return {k:v[0] for k, v in self._dtypes.items()}

    def save_tuples(self, tuples):
        self.save_records(Record(*tup) for tup in tuples)

    def save_records(self, records):
        with self._db:
            for rec in records:
                if not isinstance(rec, Record):
                    rec = Record(*rec)
                if rec.key not in self._dtypes:
                    name = utils.name(rec.value)
                    serializer = utils.serializer(name)
                    deserializer = utils.deserializer(name)
                    self._dtypes[rec.key] = (name, serializer, deserializer)
                    self._db.execute("replace into value_types (key, value_type) values (?, ?)", (rec.key, name))
                self._db.execute("replace into history(agent_id, t_step, key, value) values (?, ?, ?, ?)", (rec.agent_id, rec.t_step, rec.key, rec.value))

    def save_record(self, *args, **kwargs):
        self._tups.append(Record(*args, **kwargs))
        if len(self._tups) > 100:
            self.flush_cache()

    def flush_cache(self):
        '''
        Use a cache to save state changes to avoid opening a session for every change.
        The cache will be flushed at the end of the simulation, and when history is accessed.
        '''
        self.save_records(self._tups)
        self._tups = list()

    def to_tuples(self):
            self.flush_cache()
            with self._db:
                res = self._db.execute("select agent_id, t_step, key, value from history ").fetchall()
            for r in res:
                agent_id, t_step, key, value = r
                _, _ , des = self.conversors(key)
                yield agent_id, t_step, key, des(value)

    def read_types(self):
            with self._db:
                res = self._db.execute("select key, value_type from value_types ").fetchall()
            for k, v in res:
                serializer = utils.serializer(v)
                deserializer = utils.deserializer(v)
                self._dtypes[k] = (v, serializer, deserializer)

    def __getitem__(self, key):
        key = Key(*key)
        agent_ids = [key.agent_id] if key.agent_id is not None else []
        t_steps = [key.t_step] if key.t_step is not None else []
        keys = [key.key] if key.key is not None else []

        df = self.read_sql(agent_ids=agent_ids,
                           t_steps=t_steps,
                           keys=keys)
        r = Records(df, filter=key, dtypes=self._dtypes)
        if r.resolved:
            return r.value()
        return r



    def read_sql(self, keys=None, agent_ids=None, t_steps=None, convert_types=False, limit=-1):

        self.read_types()

        def escape_and_join(v):
            if v is None:
                return
            return ",".join(map(lambda x: "\'{}\'".format(x), v))

        filters = [("key in ({})".format(escape_and_join(keys)), keys),
                   ("agent_id in ({})".format(escape_and_join(agent_ids)), agent_ids)
        ]
        filters = list(k[0] for k in filters if k[1])

        last_df = None
        if t_steps:
            # Look for the last value before the minimum step in the query
            min_step = min(t_steps)
            last_filters = ['t_step < {}'.format(min_step),]
            last_filters = last_filters + filters
            condition = ' and '.join(last_filters)

            last_query = '''
            select h1.*
            from history h1
            inner join (
            select agent_id, key, max(t_step) as t_step
            from history
            where {condition}
            group by agent_id, key
            ) h2
            on h1.agent_id = h2.agent_id  and
               h1.key      = h2.key       and
               h1.t_step   = h2.t_step
            '''.format(condition=condition)
            last_df = pd.read_sql_query(last_query, self._db)

            filters.append("t_step >= '{}' and t_step <= '{}'".format(min_step, max(t_steps)))

        condition = ''
        if filters:
            condition = 'where {} '.format(' and '.join(filters))
        query = 'select * from history {} limit {}'.format(condition, limit)
        df = pd.read_sql_query(query, self._db)
        if last_df is not None:
            df = pd.concat([df, last_df])

        df_p = df.pivot_table(values='value', index=['t_step'],
                              columns=['key', 'agent_id'],
                              aggfunc='first')

        for k, v in self._dtypes.items():
            if k in df_p:
                dtype, _, deserial = v
                df_p[k] = df_p[k].fillna(method='ffill').fillna(deserial()).astype(dtype)
        if t_steps:
            df_p = df_p.reindex(t_steps, method='ffill')
        return df_p.ffill()


class Records():

    def __init__(self, df, filter=None, dtypes=None):
        if not filter:
            filter = Key(agent_id=None,
                         t_step=None,
                         key=None)
        self._df = df
        self._filter = filter
        self.dtypes = dtypes or {}
        super().__init__()

    def mask(self, tup):
        res = ()
        for i, k in zip(tup[:-1], self._filter):
            if k is None:
                res = res + (i,)
        res = res + (tup[-1],)
        return res

    def filter(self, newKey):
        f = list(self._filter)
        for ix, i in enumerate(f):
            if i is None:
                f[ix] = newKey
        self._filter = Key(*f)

    @property
    def resolved(self):
        return sum(1 for i in self._filter if i is not None) == 3

    def __iter__(self):
        for column, series in self._df.iteritems():
            key, agent_id = column
            for t_step, value in series.iteritems():
                r = Record(t_step=t_step,
                           agent_id=agent_id,
                           key=key,
                           value=value)
                yield self.mask(r)

    def value(self):
        if self.resolved:
            f = self._filter
            try:
                i = self._df[f.key][str(f.agent_id)]
                ix = i.index.get_loc(f.t_step, method='ffill')
                return i.iloc[ix]
            except KeyError:
                return self.dtypes[f.key][2]()
        return list(self)

    def __getitem__(self, k):
        n = copy.copy(self)
        n.filter(k)
        if n.resolved:
            return n.value()
        return n

    def __len__(self):
        return len(self._df)

    def __str__(self):
        if self.resolved:
            return str(self.value())
        return '<Records for [{}]>'.format(self._filter)


Key = namedtuple('Key', ['agent_id', 't_step', 'key'])
Record = namedtuple('Record', 'agent_id t_step key value')
