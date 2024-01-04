import datetime as dt
from typing import Callable

import pandas as pd
import requests


class cryptoCompareApi():
    def __init__(self):
        self.api_key = "bd7e829531032b62e5042190f9508096366df339e576b8469469ea1f4ddcd6d9"
        self.meta_data_futures = {}

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

    def load_date_range_data(self, start_date, end_date, freq, load_func: Callable, market, instrument):

        max_limit = 2000
        data_list = []
        new_end_date = end_date
        n_period = self.calc_n_period(start_date, new_end_date, freq)

        while n_period > max_limit:
            tmp_data = load_func(freq, market, instrument, new_end_date.timestamp() - 1, max_limit)
            data_list.append(tmp_data)

            new_end_date = self.offset_period(new_end_date, max_limit, freq)
            n_period = self.calc_n_period(start_date, new_end_date, freq)

        tmp_data = load_func(freq, market, instrument, new_end_date.timestamp() - 1, n_period)
        data_list.append(tmp_data)
        return pd.concat(reversed(data_list))

    def load_funding_rate_historical_ohlcv(self, freq, market, instrument, to_ts, limit):
        if not freq in ['days', 'hours', 'minutes']:
            return

        print(f'futures/v1/historical/funding-rate {market} {instrument} {freq} {int(to_ts)} {limit}')
        url = f'https://data-api.cryptocompare.com/futures/v1/historical/funding-rate/{freq}?'
        params = {
            'market': market,
            'instrument': instrument,
            'to_ts': to_ts,
            'limit': limit
        }
        data = self.request_to_df(url, params)
        return data

    def proc_funding_rate_historical_ohlcv(self, data):
        data.index = [dt.datetime.fromtimestamp(x) for x in data['TIMESTAMP']]
        return data[['MARKET', 'INSTRUMENT', 'MAPPED_INSTRUMENT', 'CLOSE']]

    def load_all_futures_meta_data(self):
        url = 'https://data-api.cryptocompare.com/futures/v1/markets/instruments'
        data = self.request_to_dict(url, {})
        return data

    def load_all_futures_markets_instruments(self):
        if len(self.meta_data_futures) == 0:
            self.meta_data_futures = self.load_all_futures_meta_data()

        market_instru_list = []
        for market, market_meta in self.meta_data_futures.items():
            for instru, instru_meta in market_meta['instruments'].items():
                market_instru_list.append((market, instru))
        return market_instru_list


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

    data = dataAPI.load_all_futures_markets_instruments()
    dataAPI.instrument_search('btc')

    # data = dataAPI.load_all_futures_instruments(market='binance')
    print(data)
