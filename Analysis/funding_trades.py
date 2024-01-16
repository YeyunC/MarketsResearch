import datetime as dt
import os

import pandas as pd

from DataAPI.cryptoCompare import cryptoCompareApi

__dataAPI = cryptoCompareApi()


def get_all_futures(instrument='BTC-USDT'):
    data = __dataAPI.load_futures_instruments(underlying=instrument)
    return data


def get_all_spots(instrument='BTC-USDT'):
    data = __dataAPI.load_spot_instruments(instrument=instrument)
    return data


def get_all_funding_rates(instrument):
    all_perps = __dataAPI.load_futures_instruments(underlying=instrument, style='VANILLA', mode='PERP_ONLY')

    data_list = []
    for idx, perp in all_perps.iterrows():
        data = __dataAPI.load_annual_hourly_ohlc_data(mode='fundingrate', instrument=perp['instrument'],
                                                      market=perp['market'])
        tmp_name = f"funding_{perp['market']}"
        data['CLOSE'] = data['CLOSE'] * 3 * 365
        data = data[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': tmp_name}, axis=1)
        data = data.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
        data_list.append(data)

    df = pd.concat(data_list, axis=1)
    df = df.sort_index()
    return df


def get_all_future_basis(instrument, market):
    def get_fut_col_name(fut):
        return f"basis_{fut['market']}|{fut['tenor']}"

    spot_markets = list(get_all_spots(instrument)['market'])

    spot_market = market
    if not market in spot_markets:
        print(f'spot market {market} does not exist, using binance instead')
        spot_market = 'binance'

    df_spot = __dataAPI.load_annual_hourly_ohlc_data(mode='spot', instrument=instrument, market=spot_market)
    df_spot = df_spot[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'spot'}, axis=1)
    df_spot = df_spot.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')

    data_list = [df_spot]

    all_futures = __dataAPI.load_futures_instruments(underlying=instrument, market=market, style='VANILLA')
    for idx, fut in all_futures.iterrows():
        data = __dataAPI.load_annual_hourly_ohlc_data(mode='futures', instrument=fut['instrument'],
                                                      market=fut['market'])
        if len(data) > 0:
            tmp_name = get_fut_col_name(fut)
            data = data[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': tmp_name}, axis=1)
            data = data.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
            data_list.append(data)

    df = pd.concat(data_list, axis=1).sort_index()
    for idx, fut in all_futures.iterrows():
        tmp_name = get_fut_col_name(fut)
        if tmp_name in df.columns:
            df[tmp_name] = df[tmp_name] / df['spot'] - 1

            tenor = fut['tenor']
            if tenor == 'PERPETUAL':
                df[tmp_name] = df[tmp_name] * 3 * 365
            else:
                expiry = dt.datetime.strptime(tenor, '%Y%m%d')
                today = dt.datetime.now()
                annulized_factor = (expiry - today).days / 365
                df[tmp_name] = df[tmp_name] / annulized_factor

    df.drop('spot', axis=1, inplace=True)
    return df


def calc_stats(df):
    quantiles = df.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    quantiles.index = [f'percentile_{x:0.0%}' for x in quantiles.index]

    stats = pd.DataFrame([df.count(), df.mean(), df.std()], index=['n_datapoints', 'mean', 'std_dev'])
    df = pd.concat([stats, quantiles])

    return df


def calc_all_stats(instrument):
    df_funding = get_all_funding_rates(instrument)

    data_list = [df_funding]
    all_future_markets = get_all_futures(instrument=instrument)['market'].unique()
    for mkt in all_future_markets:
        df_basis = get_all_future_basis(instrument, market=mkt)
        data_list.append(df_basis)

    df = pd.concat(data_list, axis=1)
    rlt = calc_stats(df)
    rlt = rlt.T
    return rlt


if __name__ == '__main__':
    instrument = 'BTC-USDT'

    spot_market = get_all_spots(instrument='BTC-USDT')

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_to_cache = os.path.join(project_root, 'Data', 'funding_basis_stats')
    file_path = os.path.join(path_to_cache, f'{instrument}.csv')

    data = calc_all_stats(instrument='BTC-USDT')
    data.to_csv(file_path)
