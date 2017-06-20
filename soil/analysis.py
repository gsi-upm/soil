import pandas as pd

import glob
import yaml
from os.path import join


def get_data(pattern, process=True, attributes=None):
    for folder in glob.glob(pattern):
        config_file = glob.glob(join(folder, '*.yml'))[0]
        config = yaml.load(open(config_file))
        for trial_data in sorted(glob.glob(join(folder, '*.environment.csv'))):
            df = pd.read_csv(trial_data)
            if process:
                if attributes is not None:
                    df = df[df['attribute'].isin(attributes)]
                df = df.pivot_table(values='attribute', index='tstep', columns=['value'], aggfunc='count').fillna(0)
            yield config_file, df, config


def plot_all(*args, **kwargs):
    for config_file, df, config in sorted(get_data(*args, **kwargs)):
        df.plot(title=config['name'])
