import time
import os
import pandas as pd
import sqlite3
import copy
import logging
import tempfile

logger = logging.getLogger(__name__)

from collections import UserDict, namedtuple

from . import serialization
from .utils import open_or_reuse, unflatten_dict


class History:
    """
    Store and retrieve values from a sqlite database.
    """

    def __init__(self, name=None, db_path=None, backup=False, readonly=False):
        if readonly and (not os.path.exists(db_path)):
            raise Exception('The DB file does not exist. Cannot open in read-only mode')

        self._db = None
        self._temp = db_path is None
        self._stats_columns = None
        self.readonly = readonly

        if self._temp:
            if not name:
                name = time.time()
            # The file will be deleted as soon as it's closed
            # Normally, that will be on destruction
            db_path = tempfile.NamedTemporaryFile(suffix='{}.sqlite'.format(name)).name


        if backup and os.path.exists(db_path):
                newname = db_path + '.backup{}.sqlite'.format(time.time())
                os.rename(db_path, newname)

        self.db_path = db_path

        self.db = db_path
        self._dtypes = {}
        self._tups = []


        if self.readonly:
            return

        with self.db:
            logger.debug('Creating database {}'.format(self.db_path))
            self.db.execute('''CREATE TABLE IF NOT EXISTS history (agent_id text, t_step int, key text, value text)''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS value_types (key text, value_type text)''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS stats (trial_id text)''')
            self.db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_history ON history (agent_id, t_step, key);''')

    @property
    def db(self):
        try:
            self._db.cursor()
        except (sqlite3.ProgrammingError, AttributeError):
            self.db = None  # Reset the database
        return self._db

    @db.setter
    def db(self, db_path=None):
        self._close()
        db_path = db_path or self.db_path
        if isinstance(db_path, str):
            logger.debug('Connecting to database {}'.format(db_path))
            self._db = sqlite3.connect(db_path)
            self._db.row_factory = sqlite3.Row
        else:
            self._db = db_path

    def _close(self):
        if self._db is None:
            return
        self.flush_cache()
        self._db.close()
        self._db = None

    def save_stats(self, stat):
        if self.readonly:
            print('DB in readonly mode')
            return
        if not stat:
            return
        with self.db:
            if not self._stats_columns:
                self._stats_columns = list(c['name'] for c in self.db.execute('PRAGMA table_info(stats)'))

            for column, value in stat.items():
                if column in self._stats_columns:
                    continue
                dtype = 'text'
                if not isinstance(value, str):
                    try:
                        float(value)
                        dtype = 'real'
                        int(value)
                        dtype = 'int'
                    except ValueError:
                        pass
                self.db.execute('ALTER TABLE stats ADD "{}" "{}"'.format(column, dtype))
                self._stats_columns.append(column)

            columns = ", ".join(map(lambda x: '"{}"'.format(x), stat.keys()))
            values = ", ".join(['"{0}"'.format(col) for col in stat.values()])
            query = "INSERT INTO stats ({columns}) VALUES ({values})".format(
                columns=columns,
                values=values
            )
            self.db.execute(query)

    def get_stats(self, unflatten=True):
        rows = self.db.execute("select * from stats").fetchall()
        res = []
        for row in rows:
            d = {}
            for k in row.keys():
                if row[k] is None:
                    continue
                d[k] = row[k]
            if unflatten:
                d = unflatten_dict(d)
            res.append(d)
        return res

    @property
    def dtypes(self):
        self._read_types()
        return {k:v[0] for k, v in self._dtypes.items()}

    def save_tuples(self, tuples):
        '''
        Save a series of tuples, converting them to records if necessary
        '''
        self.save_records(Record(*tup) for tup in tuples)

    def save_records(self, records):
        '''
        Save a collection of records
        '''
        for record in records:
            if not isinstance(record, Record):
                record = Record(*record)
            self.save_record(*record)

    def save_record(self, agent_id, t_step, key, value):
        '''
        Save a collection of records to the database.
        Database writes are cached.
        '''
        if self.readonly:
            raise Exception('DB in readonly mode')
        if key not in self._dtypes:
            self._read_types()
            if key not in self._dtypes:
                name = serialization.name(value)
                serializer = serialization.serializer(name)
                deserializer = serialization.deserializer(name)
                self._dtypes[key] = (name, serializer, deserializer)
                with self.db:
                    self.db.execute("replace into value_types (key, value_type) values (?, ?)", (key, name))
        value = self._dtypes[key][1](value)
        self._tups.append(Record(agent_id=agent_id,
                                 t_step=t_step,
                                 key=key,
                                 value=value))
        if len(self._tups) > 100:
            self.flush_cache()

    def flush_cache(self):
        '''
        Use a cache to save state changes to avoid opening a session for every change.
        The cache will be flushed at the end of the simulation, and when history is accessed.
        '''
        if self.readonly:
            raise Exception('DB in readonly mode')
        logger.debug('Flushing cache {}'.format(self.db_path))
        with self.db:
            for rec in self._tups:
                self.db.execute("replace into history(agent_id, t_step, key, value) values (?, ?, ?, ?)", (rec.agent_id, rec.t_step, rec.key, rec.value))
        self._tups = list()

    def to_tuples(self):
        self.flush_cache()
        with self.db:
            res = self.db.execute("select agent_id, t_step, key, value from history ").fetchall()
        for r in res:
            agent_id, t_step, key, value = r
            if key not in self._dtypes:
                self._read_types()
            if key not in self._dtypes:
                raise ValueError("Unknown datatype for {} and {}".format(key, value))
            value = self._dtypes[key][2](value)
            yield agent_id, t_step, key, value

    def _read_types(self):
        with self.db:
            res = self.db.execute("select key, value_type from value_types ").fetchall()
        for k, v in res:
            serializer = serialization.serializer(v)
            deserializer = serialization.deserializer(v)
            self._dtypes[k] = (v, serializer, deserializer)

    def __getitem__(self, key):
        self.flush_cache()
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

        self._read_types()

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
            # Convert negative indices into positive
            if any(x<0 for x in t_steps):
                max_t = int(self.db.execute("select max(t_step) from history").fetchone()[0])
                t_steps = [t if t>0 else max_t+1+t for t in t_steps]

            # We will be doing ffill interpolation, so we need to look for
            # the last value before the minimum step in the query
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
            last_df = pd.read_sql_query(last_query, self.db)

            filters.append("t_step >= '{}' and t_step <= '{}'".format(min_step, max(t_steps)))

        condition = ''
        if filters:
            condition = 'where {} '.format(' and '.join(filters))
        query = 'select * from history {} limit {}'.format(condition, limit)
        df = pd.read_sql_query(query, self.db)
        if last_df is not None:
            df = pd.concat([df, last_df])

        df_p = df.pivot_table(values='value', index=['t_step'],
                              columns=['key', 'agent_id'],
                              aggfunc='first')

        for k, v in self._dtypes.items():
            if k in df_p:
                dtype, _, deserial = v
                try:
                    df_p[k] = df_p[k].fillna(method='ffill').astype(dtype)
                except (TypeError, ValueError):
                    # Avoid forward-filling unknown/incompatible types
                    continue
        if t_steps:
            df_p = df_p.reindex(t_steps, method='ffill')
        return df_p.ffill()

    def __getstate__(self):
        state = dict(**self.__dict__)
        del state['_db']
        del state['_dtypes']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self._dtypes = {}
        self._db = None

    def dump(self, f):
        self._close()
        for line in open_or_reuse(self.db_path, 'rb'):
            f.write(line)


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
            except KeyError as ex:
                return self.dtypes[f.key][2]()
        return list(self)

    def df(self):
        return self._df

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

Stat = namedtuple('Stat', 'trial_id')
