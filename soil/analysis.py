import pandas as pd

import glob
import yaml
from os.path import join

from . import utils


def read_data(*args, group=False, **kwargs):
    iterable = _read_data(*args, **kwargs)
    if group:
        return group_trials(iterable)
    else:
        return list(iterable)


def _read_data(pattern, keys=None, convert_types=False,
               process=None, from_csv=False, **kwargs):
    for folder in glob.glob(pattern):
        config_file = glob.glob(join(folder, '*.yml'))[0]
        config = yaml.load(open(config_file))
        df = None
        if from_csv:
            for trial_data in sorted(glob.glob(join(folder,
                                                    '*.environment.csv'))):
                df = read_csv(trial_data, convert_types=convert_types)
                if process:
                    df = process(df, **kwargs)
                yield config_file, df, config
        else:
            for trial_data in sorted(glob.glob(join(folder, '*.db.sqlite'))):
                df = read_sql(trial_data, convert_types=convert_types,
                              keys=keys)
                if process:
                    df = process(df, **kwargs)
                yield config_file, df, config


def read_csv(filename, keys=None, convert_types=False, **kwargs):
    '''
    Read a CSV in canonical form: ::

        <agent_id, t_step, key, value, value_type>

    '''
    df = pd.read_csv(filename)
    if convert_types:
        df = convert_types_slow(df)
    if keys:
        df = df[df['key'].isin(keys)]
    return df


def read_sql(filename, keys=None, convert_types=False, limit=-1):
    condition = ''
    if keys:
        k = map(lambda x: "\'{}\'".format(x), keys)
        condition = 'where key in ({})'.format(','.join(k))
    query = 'select * from history {} limit {}'.format(condition, limit)
    df = pd.read_sql_query(query, 'sqlite:///{}'.format(filename))
    if convert_types:
        df = convert_types_slow(df)
    return df


def convert_row(row):
    row['value'] = utils.convert(row['value'], row['value_type'])
    return row


def convert_types_slow(df):
    '''This is a slow operation.'''
    dtypes = get_types(df)
    for k, v in dtypes.items():
        t = df[df['key']==k]
        t['value'] = t['value'].astype(v)
    df = df.apply(convert_row, axis=1)
    return df

def split_df(df):
    '''
    Split a dataframe in two dataframes: one with the history of agents,
    and one with the environment history
    '''
    envmask = (df['agent_id'] == 'env')
    n_env = envmask.sum()
    if n_env == len(df):
        return df, None
    elif n_env == 0:
        return None, df
    agents, env = [x for _, x in df.groupby(envmask)]
    return env, agents


def process(df, **kwargs):
    '''
    Process a dataframe in canonical form ``(t_step, agent_id, key, value, value_type)`` into
    two dataframes with a column per key: one with the history of the agents, and one for the
    history of the environment.
    '''
    env, agents = split_df(df)
    return process_one(env, **kwargs), process_one(agents, **kwargs)


def get_types(df):
    dtypes = df.groupby(by=['key'])['value_type'].unique()
    return {k:v[0] for k,v in dtypes.iteritems()}


def process_one(df, *keys, columns=['key'], values='value',
                index=['t_step', 'agent_id'], aggfunc='first', **kwargs):
    '''
    Process a dataframe in canonical form ``(t_step, agent_id, key, value, value_type)`` into
    a dataframe with a column per key
    '''
    if df is None:
        return df
    if keys:
        df = df[df['key'].isin(keys)]

    dtypes = get_types(df)

    df = df.pivot_table(values=values, index=index, columns=columns,
                        aggfunc=aggfunc, **kwargs)
    df = df.fillna(0).astype(dtypes)
    return df


def get_count_processed(df, *keys):
    if keys:
        df = df[list(keys)]
    # p = df.groupby(level=0).apply(pd.Series.value_counts)
    p = df.unstack().apply(pd.Series.value_counts, axis=1)
    return p


def get_count(df, *keys):
    if keys:
        df = df[df['key'].isin(keys)]
    p = df.groupby(by=['t_step', 'key', 'value']).size().unstack(level=[1,2]).fillna(0)
    return p


def get_value(df, *keys, aggfunc='sum'):
    if keys:
        df = df[df['key'].isin(keys)]
    p = process_one(df, *keys)
    p = p.groupby(level='t_step').agg(aggfunc)
    return p


def plot_all(*args, **kwargs):
    '''
    Read all the trial data and plot the result of applying a function on them.
    '''
    dfs = do_all(*args, **kwargs)
    ps = []
    for line in dfs:
        f, df, config = line
        df.plot(title=config['name'])
        ps.append(df)
    return ps

def do_all(pattern, func, *keys, include_env=False, **kwargs):
    for config_file, df, config in read_data(pattern, keys=keys):
        p = func(df, *keys, **kwargs)
        p.plot(title=config['name'])
        yield config_file, p, config


def group_trials(trials, aggfunc=['mean', 'min', 'max', 'std']):
    trials = list(trials)
    trials = list(map(lambda x: x[1] if isinstance(x, tuple) else x, trials))
    return pd.concat(trials).groupby(level=0).agg(aggfunc).reorder_levels([2, 0,1] ,axis=1)



