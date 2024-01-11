import datetime as dt
import os
from typing import Callable

import pandas as pd
import requests


class cryptoCompareApi():
    def __init__(self):
        self.api_key = "bd7e829531032b62e5042190f9508096366df339e576b8469469ea1f4ddcd6d9"
        self.meta_data_futures = {}
        self.meta_data_spots = {}

    def request_to_df(self, url, params={}):
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()["Data"]
            data_df = pd.DataFrame(data)
            return data_df
        else:
            print(response.json()['Err']['message'])
            return pd.DataFrame()

    def request_to_dict(self, url, params={}):
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()["Data"]
            return data
        else:
            print(response.json()['Err']['message'])
            return {}

    def calc_n_period(self, start_date, end_date, freq):
        limit = (end_date - start_date).total_seconds()
        if freq == 'hours':
            limit = limit / 60 / 60
        elif freq == 'minutes':
            limit = limit / 60
        elif freq == 'days':
            limit = limit / 60 / 60 / 24
        return limit

    def offset_period(self, time_ref, n, freq):
        if freq == 'hours':
            return time_ref - dt.timedelta(hours=n)
        elif freq == 'minutes':
            return time_ref - dt.timedelta(minutes=n)
        else:
            return time_ref - dt.timedelta(days=n)

    def load_date_range_data(self, start_date, end_date, freq, load_func: Callable, mode, market, instrument):

        max_limit = 2000
        data_list = []
        new_end_date = end_date
        n_period = self.calc_n_period(start_date, new_end_date, freq)

        while n_period > max_limit:
            tmp_data = load_func(mode, freq, market, instrument, new_end_date.timestamp() - 1, max_limit)
            data_list.append(tmp_data)

            new_end_date = self.offset_period(new_end_date, max_limit, freq)
            n_period = self.calc_n_period(start_date, new_end_date, freq)

        tmp_data = load_func(mode, freq, market, instrument, new_end_date.timestamp() - 1, n_period)
        data_list.append(tmp_data)
        return pd.concat(reversed(data_list))

    def load_historical_ohlcv(self, mode, freq, market, instrument, to_ts, limit):
        if not freq in ['days', 'hours', 'minutes']:
            return

        if not mode in ['spot', 'futures', 'fundingrate']:
            return

        if mode == 'futures':
            end_point = 'futures/v1/historical'
        elif mode == 'fundingrate':
            end_point = 'futures/v1/historical/funding-rate'
        else:
            end_point = 'spot/v1/historical'

        print(f'{end_point} {market} {instrument} {freq} {int(to_ts)} {limit}')
        url = f'https://data-api.cryptocompare.com/{end_point}/{freq}?'
        params = {
            'market': market,
            'instrument': instrument,
            'to_ts': to_ts,
            'limit': limit
        }
        data = self.request_to_df(url, params)
        return data

    def proc_historical_ohlcv(self, data):
        data['TIMESTAMP'] = [dt.datetime.fromtimestamp(x) for x in data['TIMESTAMP']]
        desired_column = [
            'TIMESTAMP', 'CLOSE', 'TOTAL_TRADES', 'VOLUME',
            'TOTAL_TRADES_BUY', 'TOTAL_TRADES_SELL',
            'VOLUME_BUY', 'VOLUME_SELL'
        ]

        columns = pd.Series(list(set(desired_column).intersection(set(data.columns))))
        return data[columns]

    def load_all_meta_data(self, mode='spot'):
        if not mode in ['futures', 'spot', 'index']:
            return

        url = f'https://data-api.cryptocompare.com/{mode}/v1/markets/instruments'
        data = self.request_to_dict(url, {})
        return data

    def load_all_futures_markets_instruments(self):
        if len(self.meta_data_futures) == 0:
            self.meta_data_futures = self.load_all_meta_data(mode='futures')

        market_instru_list = []
        for market, market_meta in self.meta_data_futures.items():
            for instru, instru_meta in market_meta['instruments'].items():
                # mapped_instru = instru_meta['INSTRUMENT_MAPPING']['MAPPED_INSTRUMENT']
                market_instru_list.append((market, instru))
        return market_instru_list

    def load_all_spots_markets_instruments(self):
        if len(self.meta_data_spots) == 0:
            self.meta_data_spots = self.load_all_meta_data(mode='spot')

        market_instru_list = []
        for market, market_meta in self.meta_data_spots.items():
            for instru, instru_meta in market_meta['instruments'].items():
                # mapped_instru = instru_meta['INSTRUMENT_MAPPING']['MAPPED_INSTRUMENT']
                market_instru_list.append((market, instru))
        return market_instru_list

    def load_annual_hourly_ohlc_data(self, mode, market, instrument):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path_to_cache = os.path.join(project_root, 'Data', 'ohlc_annual_hourly')

        for x in [mode, instrument, market]:
            path_to_cache = os.path.join(path_to_cache, x)
            if not os.path.exists(path_to_cache):
                os.mkdir(path_to_cache)

        file_path = os.path.join(path_to_cache, '2014.csv')
        if not os.path.exists(file_path):
            data = self.load_date_range_data(
                start_date=dt.datetime(2023, 1, 1),
                end_date=dt.datetime(2024, 1, 1),
                freq='hours',
                load_func=self.load_historical_ohlcv,
                mode=mode,
                market=market,
                instrument=instrument)
            data = self.proc_historical_ohlcv(data)
            data.to_csv(file_path, index_label=False)

        data = pd.read_csv(file_path)
        data['TIMESTAMP'] = pd.to_datetime(data['TIMESTAMP'])
        return data


if __name__ == '__main__':
    dataAPI = cryptoCompareApi()

    # data = dataAPI.load_date_range_data(
    #     start_date=dt.datetime(2023, 1, 1),
    #     end_date=dt.datetime(2024, 1, 1),
    #     freq='hours',
    #     load_func=dataAPI.load_funding_rate_historical_ohlcv,
    #     market='bitmex',
    #     instrument='XBTUSD')
    # data = dataAPI.proc_funding_rate_historical_ohlcv(data)

    data = dataAPI.load_annual_hourly_ohlc_data(
        mode='spot',
        instrument='BTC-USDT',
        market='bitstamp'
    )
    print(len(data))
