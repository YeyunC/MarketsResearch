import datetime as dt
from typing import Callable

import pandas as pd
import requests


class cryptoCompareApi():
    def __init__(self):
        self.api_key = "bd7e829531032b62e5042190f9508096366df339e576b8469469ea1f4ddcd6d9"

    def make_request(self, url, params):
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()["Data"]
            data_df = pd.DataFrame(data)
            return data_df
        else:
            return pd.DataFrame()

    def load_date_range_data(self, start_date, end_date, freq, load_func: Callable, market, instrument):
        to_ts = end_date.timestamp()
        if freq == 'days':
            limit = (end_date - start_date).days
        elif freq == 'hours':
            limit = (end_date - start_date).days * 24
        elif freq == 'minutes':
            limit = (end_date - start_date).days * 24 * 60
        else:
            limit = 0
        return load_func(freq, market, instrument, to_ts, limit)

    def load_funding_rate_historical_ohlcv(self, freq, market, instrument, to_ts, limit):
        if not freq in ['days', 'hours', 'minutes']:
            return

        url = f'https://data-api.cryptocompare.com/futures/v1/historical/funding-rate/{freq}?'
        params = {
            'market': market,
            'instrument': instrument,
            'to_ts': to_ts,
            'limit': limit
        }
        data = self.make_request(url, params)
        return data

    def proc_funding_rate_historical_ohlcv(self, data):
        data.index = [dt.datetime.fromtimestamp(x) for x in data['TIMESTAMP']]
        return data[['MARKET', 'INSTRUMENT', 'MAPPED_INSTRUMENT', 'CLOSE']]


if __name__ == '__main__':
    dataAPI = cryptoCompareApi()
    # data = dataAPI.load_funding_rate_historical_ohlcv('hours', 'bitmex', 'XBTUSD', '1702857416', 1000)

    data = dataAPI.load_date_range_data(
        start_date=dt.datetime(2023, 1, 1),
        end_date=dt.datetime(2024, 1, 1),
        freq = 'hours',
        load_func=dataAPI.load_funding_rate_historical_ohlcv,
        market='bitmex',
        instrument='XBTUSD')
    data = dataAPI.proc_funding_rate_historical_ohlcv(data)
    print(data)
