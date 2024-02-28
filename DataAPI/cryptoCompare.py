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
        if len(data) == 0:
            return pd.DataFrame()
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
        params = {}
        if mode == 'futures':
            params = {'instrument_status': 'ACTIVE,EXPIRED'}
        data = self.request_to_dict(url, params)
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

    def load_all_futures_markets_instrument_df(self):
        all_futures = self.load_all_futures_markets_instruments()
        df = pd.DataFrame(all_futures, columns=['market', 'instrument'])
        df['underlying'] = ['-'.join(x.split('-')[:2]) for x in df['instrument']]
        df['style'] = [x.split('-')[-2] for x in df['instrument']]
        df['tenor'] = [x.split('-')[-1] for x in df['instrument']]
        return df

    def load_futures_instruments(self, market='', underlying='', mode='', style=''):
        df = self.load_all_futures_markets_instrument_df()
        df_tmp = df.copy()

        if market != '':
            df_tmp = df_tmp[df_tmp['market'] == market]
        if underlying != '':
            df_tmp = df_tmp[df_tmp['underlying'] == underlying]
        if mode == 'PERP_ONLY':
            df_tmp = df_tmp[df_tmp['tenor'] == 'PERPETUAL']
        elif mode == 'FUTURE_ONLY':
            df_tmp = df_tmp[df_tmp['tenor'] != 'PERPETUAL']
        if style != '':
            df_tmp = df_tmp[df_tmp['style'] == style]
        return df_tmp

    def load_all_spot_markets_instrument_df(self):
        all_spots = self.load_all_spots_markets_instruments()
        df = pd.DataFrame(all_spots, columns=['market', 'instrument'])
        return df

    def load_spot_instruments(self, market='', instrument=''):
        df = self.load_all_spot_markets_instrument_df()
        df_tmp = df.copy()

        if market != '':
            df_tmp = df_tmp[df_tmp['market'] == market]
        if instrument != '':
            df_tmp = df_tmp[df_tmp['instrument'] == instrument]
        return df_tmp

    def load_all_futures_ohlc_data(self, market, underlying, iyear=2023):
        year_start = pd.Timestamp(iyear, 1, 1)
        year_end = min(pd.Timestamp(iyear + 1, 1, 1), pd.Timestamp.now())

        data_list = []
        metadata = dataAPI.load_all_meta_data('futures')
        for key, val in metadata[market]['instruments'].items():
            if underlying in key:
                if not 'PERPETUAL' in key:
                    try:
                        if not 'FIRST_TRADE_FUTURES_TIMESTAMP' in val.keys():
                            continue
                        first_ts = pd.to_datetime(val['FIRST_TRADE_FUTURES_TIMESTAMP'], unit='s')
                        last_ts = pd.to_datetime(val['LAST_TRADE_FUTURES_TIMESTAMP'], unit='s')
                        if first_ts > year_end:
                            continue
                        if last_ts < year_start:
                            continue

                        start_ts = max(first_ts, year_start)
                        end_ts = min(last_ts, year_end)

                        expiry_ts = pd.to_datetime(val['CONTRACT_EXPIRATION_TS'], unit='s')

                        data = self.load_date_range_data(
                            start_date=start_ts,
                            end_date=end_ts,
                            freq='hours',
                            load_func=self.load_historical_ohlcv,
                            mode='futures',
                            market=market,
                            instrument=key)
                        data = self.proc_historical_ohlcv(data)
                        data['EXPIRY_TS'] = expiry_ts
                        data['CONTRACT'] = key

                        data_list.append(data)

                    except:
                        print(key)

        rlt = pd.concat(data_list)
        return rlt

    def load_rolling_futures_ohlc_data(self, market, instrument, start_year=2023, end_year=2024):
        data = self.load_annual_hourly_ohlc_data('allfutures', market, instrument, start_year, end_year)
        data['EXPIRY_TS'] = pd.to_datetime(data['EXPIRY_TS'])
        # data = data[(data['EXPIRY_TS'] - data['TIMESTAMP']) > pd.Timedelta(days=2)]
        data.sort_values(['TIMESTAMP', 'EXPIRY_TS'], inplace=True)
        # data.drop_duplicates(subset='TIMESTAMP', keep='last', inplace=True)
        data = data[['TIMESTAMP', 'CLOSE', 'CONTRACT', 'EXPIRY_TS']].copy()
        return data

    def load_annual_hourly_ohlc_data(self, mode, market, instrument, start_year=2023, end_year=2024):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path_to_cache = os.path.join(project_root, 'Data', 'ohlc_annual_hourly')

        for x in [mode, instrument, market]:
            path_to_cache = os.path.join(path_to_cache, x)
            if not os.path.exists(path_to_cache):
                os.mkdir(path_to_cache)

        iyear = start_year
        while iyear <= end_year:
            file_path = os.path.join(path_to_cache, f'{iyear}.csv')
            if not os.path.exists(file_path):
                if mode == 'allfutures':
                    data = self.load_all_futures_ohlc_data(
                        market=market,
                        underlying=instrument,
                        iyear=iyear)
                else:
                    data = self.load_date_range_data(
                        start_date=dt.datetime(iyear, 1, 1),
                        end_date=min(dt.datetime(iyear + 1, 1, 1), dt.datetime.now()),
                        freq='hours',
                        load_func=self.load_historical_ohlcv,
                        mode=mode,
                        market=market,
                        instrument=instrument)
                    data = self.proc_historical_ohlcv(data)
                if len(data) == 0:
                    pd.DataFrame({'EMPTY': []}).to_csv(file_path, index_label=False)
                else:
                    data.to_csv(file_path, index_label=False)
            iyear = iyear + 1

        data_list = []
        iyear = start_year
        while iyear <= end_year:
            file_path = os.path.join(path_to_cache, f'{iyear}.csv')
            data = pd.read_csv(file_path)
            if len(data) > 0:
                data['TIMESTAMP'] = pd.to_datetime(data['TIMESTAMP'])
                data_list.append(data)
            iyear = iyear + 1

        if len(data_list) > 0:
            data = pd.concat(data_list)
            print(f'{path_to_cache} loaded {len(data)} rows')
            return data
        else:
            return pd.DataFrame()


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

    data = dataAPI.load_rolling_futures_ohlc_data('binance', 'BTC-USDT')
    print(data)
    # data = dataAPI.load_annual_hourly_ohlc_data(
    #     mode='spot',
    #     instrument='BTC-USDT',
    #     market='bitstamp'
    # )
    # print(len(data))
