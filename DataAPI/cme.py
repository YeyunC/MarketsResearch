import datetime as dt
import os

import pandas as pd

import DataAPI.util as dutil


def load_file(token='btc'):
    fn = f'cme_{token}_future_continous_2023.csv'
    root_dir = dutil.get_project_root()
    file_path = os.path.join(root_dir, 'Data', 'cme_ohlc', fn)
    data = pd.read_csv(file_path)
    data['date_time'] = data['Local Date'] + ' ' + data['Local Time']
    data['TIMESTAMP'] = [dt.datetime.strptime(x, "%d-%b-%Y %H:%M") for x in data['date_time']]
    data['Close'] = [float(str(x).replace(',', '')) for x in data['Close']]
    data = data[['TIMESTAMP', 'Close']].rename({'Close': 'basis_cme|FRONT_MONTH_FUTURE'}, axis=1)
    data = data.set_index('TIMESTAMP').resample('1H').last()
    return data


if __name__ == '__main__':
    data = load_file()
