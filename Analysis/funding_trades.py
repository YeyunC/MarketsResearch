import datetime as dt
import os

import matplotlib.pyplot as plt
import pandas as pd

from DataAPI import cme
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
                                                      market=perp['market'], end_year=2024)
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
        return f"basis_{fut['tenor']}|{fut['market']}"

    def get_funding_col_name():
        return f"funding_{fut['tenor']}|{fut['market']}"

    spot_markets = list(get_all_spots(instrument)['market'])

    spot_market = market
    if not market in spot_markets:
        spot_market = 'coinbase'
        print(f'spot market {market} does not exist, using {spot_market} instead')

    try:
        df_spot = __dataAPI.load_annual_hourly_ohlc_data(
            mode='spot', instrument=instrument, market=spot_market, start_year=2023)
        df_spot = df_spot[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'spot'}, axis=1)
        df_spot = df_spot.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
    except:
        print(market)

    data_list = [df_spot]

    if market == 'CME':
        data = cme.load_file(token=instrument.split('-')[0].lower())
        data_list.append(data)
        df = pd.concat(data_list, axis=1).sort_index()
        tmp_name = data.columns[0]
        df[tmp_name] = df[tmp_name] / df['spot']
        df.drop('spot', axis=1, inplace=True)
        return df

    all_futures = __dataAPI.load_futures_instruments(underlying=instrument, market=market, style='VANILLA')
    for idx, fut in all_futures.iterrows():
        try:
            data = __dataAPI.load_annual_hourly_ohlc_data(
                mode='futures', instrument=fut['instrument'], market=fut['market'], start_year=2023)

            if len(data) > 0:
                tmp_name = get_fut_col_name(fut)
                data = data[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': tmp_name}, axis=1)
                data = data.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
                data_list.append(data)

            if 'PERP' in fut['instrument']:
                funding_rate = __dataAPI.load_annual_hourly_ohlc_data(
                    mode='fundingrate', instrument=fut['instrument'], market=fut['market'], start_year=2023)
                if len(funding_rate) > 0:
                    tmp_name = get_funding_col_name()
                    funding_rate = funding_rate[funding_rate['CLOSE'] < 10000]
                    funding_rate = funding_rate[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': tmp_name}, axis=1)
                    funding_rate = funding_rate.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
                    data_list.append(funding_rate)

        except:
            print(fut)

    df = pd.concat(data_list, axis=1).sort_index()
    for idx, fut in all_futures.iterrows():
        try:
            tmp_name = get_fut_col_name(fut)
            if tmp_name in df.columns:
                if 'basis_' in tmp_name:
                    df[tmp_name] = df[tmp_name] / df['spot'] - 1

                # df[tmp_name] = df[tmp_name] / df['spot'] - 1
                # df['basis'] = df[tmp_name] / df['spot'] - 1

                # tenor = fut['tenor']
                # if tenor == 'PERPETUAL':
                #
                #     df = pd.concat([df, funding_rate], axis=1)
                #
                #     # if basis
                #
                #     df[tmp_name] = np.power((1 + df[tmp_name] * 3), 365) - 1

                # if funding
                # df[tmp_name] = np.power((1 + df['FUNDING'] * 3), 365) - 1

                # df[tmp_name] = np.power((1 + (df[tmp_name] - df['FUNDING']) * 3), 365) - 1

                # df['basis_annulized'] = np.power((1 + df['basis'] * 3), 365) - 1
                # df['funding_annulized'] = np.power((1 + df['FUNDING'] * 3), 365) - 1
                # df.to_csv('tmp.csv')
                # df.drop('FUNDING', axis=1, inplace=True)
                # else:
                #     expiry = dt.datetime.strptime(tenor, '%Y%m%d')
                #     today = dt.datetime.now()
                #     annulized_factor = 365 / (expiry - today).days
                #     df[tmp_name] = np.power(1 + df[tmp_name], annulized_factor) - 1
        except:
            print(fut)

    df = df[df['spot'] > 1]
    df.drop('spot', axis=1, inplace=True)
    return df


def calc_stats(df):
    quantiles = df.quantile([0.05, 0.95])
    quantiles.index = [f'percentile_{x:0.0%}' for x in quantiles.index]

    # stats = pd.DataFrame([df.count(), df.mean(), df.std()], index=['n_datapoints', 'mean', 'std_dev'])
    stats = pd.DataFrame([df.mean(), df.std()], index=['mean', 'std_dev'])
    df = pd.concat([stats, quantiles])

    return df


def calc_stats_to_df(df, lookback):
    filter_day = df.index.max() - dt.timedelta(days=lookback)
    df_calc = df[df.index >= filter_day].copy()
    rlt = calc_stats(df_calc)
    rlt = annualize_df(rlt)
    rlt = rlt.T.sort_index()
    rlt['lookback'] = lookback
    return rlt


def plot_charts_look_back(df, lookback):
    filter_day = df.index.max() - dt.timedelta(days=lookback)
    df_calc = df[df.index >= filter_day].copy()
    for col in df.columns:
        plot_column(df_calc, col, instrument, lookback)
        if 'PERP' in col:
            market = col.split('|')[-1]
            if market in ['binance', 'bitfinex', 'okex']:
                plot_column_hist(df_calc, col, instrument, lookback)


def calc_all_stats(instrument):
    # df_funding = get_all_funding_rates(instrument)
    #
    # data_list = [df_funding]
    data_list = []
    all_future_markets = get_all_futures(instrument=instrument).sort_values('market')['market'].unique()
    if instrument in ('BTC-USD', 'ETH-USD'):
        all_future_markets = ['CME'] + list(all_future_markets)

    for mkt in all_future_markets:
        df_basis = get_all_future_basis(instrument, market=mkt)
        data_list.append(df_basis)

    df = pd.concat(data_list, axis=1)

    rlt_list = []
    for x in [90, 180, 365]:
        rlt = calc_stats_to_df(df, lookback=x)
        rlt_list.append(rlt)
    df_rlt = pd.concat(rlt_list)
    df_rlt = df_rlt.sort_index()

    df = annualize_df(df)
    for x in [90, 180, 365]:
        plot_charts_look_back(df, x)
    return df_rlt


def annualize_df(rlt):
    for col in rlt.columns:
        if 'funding_' in col:
            rlt[col] = rlt[col] * 3 * 365
        elif 'basis_' in col:
            if 'PERPETUAL' in col:
                rlt[col] = rlt[col] * 3 * 365
            elif 'cme' in col:
                rlt[col] = rlt[col] * 12
            else:
                tenor = col.split('_')[-1].split('|')[0]
                expiry = dt.datetime.strptime(tenor, '%Y%m%d')
                today = dt.datetime.now()
                annulized_factor = 365 / (expiry - today).days
                rlt[col] = rlt[col] * annulized_factor

    return rlt


def plot_column(df, col, instrument, lookback):
    plt.figure(figsize=(30, 10))
    plt.axhline(y=0, color='lightgray', linestyle='-')
    plt.plot(df.index, df[col])
    plt.title(col)
    if 'PERP' in col:
        lb = df[col].quantile(0.01)
        ub = df[col].quantile(0.99)
        maxb = df[col].max()
        minb = df[col].min()
        ub = max(min(maxb, 10), ub)
        lb = min(max(minb, -10), lb)
        plt.ylim(lb, ub)
    # plt.legend()
    plt.tight_layout()

    # write image to bytes
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_to_fig = os.path.join(project_root, 'Data', 'funding_basis_stats')
    file_path = os.path.join(path_to_fig, f'fig_{instrument}_{col}_{lookback}.png')

    plt.savefig(file_path, format='PNG')


def plot_column_hist(df, col, instrument, lookback):
    plt.figure(figsize=(12, 4))
    plt.hist(df[col], bins=50)
    plt.axvline(x=0, color='green', linestyle='--')
    plt.title(col)
    plt.tight_layout()

    # write image to bytes
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_to_fig = os.path.join(project_root, 'Data', 'funding_basis_stats')
    file_path = os.path.join(path_to_fig, f'hist_{instrument}_{col}_{lookback}.png')

    plt.savefig(file_path, format='PNG')


if __name__ == '__main__':
    instrument = 'BTC-USDT'

    spot_market = get_all_spots(instrument=instrument)
    # print(spot_market)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_to_cache = os.path.join(project_root, 'Data', 'funding_basis_stats')
    file_path = os.path.join(path_to_cache, f'{instrument}_1Y.csv')

    data = calc_all_stats(instrument=instrument)
    data.to_csv(file_path)

    # get_all_future_basis(instrument, market='binance')
