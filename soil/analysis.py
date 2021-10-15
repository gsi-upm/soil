import pandas as pd

import glob
import yaml
from os.path import join

from . import serialization
from tsih import History


def read_data(*args, group=False, **kwargs):
    iterable = _read_data(*args, **kwargs)
    if group:
        return group_trials(iterable)
    else:
        return list(iterable)


def _read_data(pattern, *args, from_csv=False, process_args=None, **kwargs):
    if not process_args:
        process_args = {}
    for folder in glob.glob(pattern):
        config_file = glob.glob(join(folder, '*.yml'))[0]
        config = yaml.load(open(config_file), Loader=yaml.SafeLoader)
        df = None
        if from_csv:
            for trial_data in sorted(glob.glob(join(folder,
                                                    '*.environment.csv'))):
                df = read_csv(trial_data, **kwargs)
                yield config_file, df, config
        else:
            for trial_data in sorted(glob.glob(join(folder, '*.sqlite'))):
                df = read_sql(trial_data, **kwargs)
                yield config_file, df, config


def read_sql(db, *args, **kwargs):
    h = History(db_path=db, backup=False, readonly=True)
    df = h.read_sql(*args, **kwargs)
    return df


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
    df = process_one(df)
    return df


def convert_row(row):
    row['value'] = serialization.deserialize(row['value_type'], row['value'])
    return row


def convert_types_slow(df):
    '''
    Go over every column in a dataframe and convert it to the type determined by the `get_types`
    function.

    This is a slow operation.
    '''
    dtypes = get_types(df)
    for k, v in dtypes.items():
        t = df[df['key']==k]
        t['value'] = t['value'].astype(v)
    df = df.apply(convert_row, axis=1)
    return df


def split_processed(df):
    env = df.loc[:, df.columns.get_level_values(1).isin(['env', 'stats'])]
    agents = df.loc[:, ~df.columns.get_level_values(1).isin(['env', 'stats'])]
    return env, agents


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
    '''
    Get the value type for every key stored in a raw history dataframe.
    '''
    dtypes = df.groupby(by=['key'])['value_type'].unique()
    return {k:v[0] for k,v in dtypes.iteritems()}


def process_one(df, *keys, columns=['key', 'agent_id'], values='value',
                fill=True, index=['t_step',],
                aggfunc='first', **kwargs):
    '''
    Process a dataframe in canonical form ``(t_step, agent_id, key, value, value_type)`` into
    a dataframe with a column per key
    '''
    if df is None:
        return df
    if keys:
        df = df[df['key'].isin(keys)]

    df = df.pivot_table(values=values, index=index, columns=columns,
                        aggfunc=aggfunc, **kwargs)
    if fill:
        df = fillna(df)
    return df


def get_count(df, *keys):
    '''
    For every t_step and key, get the value count.

    The result is a dataframe with `t_step` as index, an a multiindex column based on `key` and the values found for each `key`.
    '''
    if keys:
        df = df[list(keys)]
        df.columns = df.columns.remove_unused_levels()
    counts = pd.DataFrame()
    for key in df.columns.levels[0]:
        g = df[[key]].apply(pd.Series.value_counts, axis=1).fillna(0)
        for value, series in g.iteritems():
            counts[key, value] = series
    counts.columns = pd.MultiIndex.from_tuples(counts.columns)
    return counts


def get_majority(df, *keys):
    '''
    For every t_step and key, get the value of the majority of agents

    The result is a dataframe with `t_step` as index, and columns based on `key`.
    '''
    df = get_count(df, *keys)
    return df.stack(level=0).idxmax(axis=1).unstack()


def get_value(df, *keys, aggfunc='sum'):
    '''
    For every t_step and key, get the value of *numeric columns*, aggregated using a specific function.
    '''
    if keys:
        df = df[list(keys)]
        df.columns = df.columns.remove_unused_levels()
    df = df.select_dtypes('number')
    return df.groupby(level='key', axis=1).agg(aggfunc)


def plot_all(*args, plot_args={}, **kwargs):
    '''
    Read all the trial data and plot the result of applying a function on them.
    '''
    dfs = do_all(*args, **kwargs)
    ps = []
    for line in dfs:
        f, df, config = line
        if len(df) < 1:
            continue
        df.plot(title=config['name'], **plot_args)
        ps.append(df)
    return ps

def do_all(pattern, func, *keys, include_env=False, **kwargs):
    for config_file, df, config in read_data(pattern, keys=keys):
        if len(df) < 1:
            continue
        p = func(df, *keys, **kwargs)
        yield config_file, p, config


def group_trials(trials, aggfunc=['mean', 'min', 'max', 'std']):
    trials = list(trials)
    trials = list(map(lambda x: x[1] if isinstance(x, tuple) else x, trials))
    return pd.concat(trials).groupby(level=0).agg(aggfunc).reorder_levels([2, 0,1] ,axis=1)


def fillna(df):
    new_df = df.ffill(axis=0)
    return new_df
