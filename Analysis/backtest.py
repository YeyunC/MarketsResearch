import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

import Analysis.funding_trades as fr
from DataAPI.cryptoCompare import cryptoCompareApi

__dataAPI = cryptoCompareApi()


def get_all_future_basis(instrument, market):
    def get_fut_col_name(fut):
        return f"basis_{fut['tenor']}|{fut['market']}"

    def get_funding_col_name():
        return f"funding_{fut['tenor']}|{fut['market']}"

    spot_markets = list(fr.get_all_spots(instrument)['market'])

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
    df = df[df['spot'] > 1]

    pnl_series = {}
    for idx, fut in all_futures.iterrows():
        try:
            tmp_name = get_fut_col_name(fut)
            if tmp_name in df.columns:
                if ('basis_' in tmp_name) and ('PERP' in tmp_name):
                    funding_column = tmp_name.replace('basis', 'funding')
                    df_tmp = df[['spot', tmp_name, funding_column]]
                    index_series = df_tmp['spot'] - df[tmp_name]
                    start_price = df_tmp['spot'].dropna()[0]
                    start_index = index_series.dropna()[0]
                    index_pnl = (index_series - start_index) / start_price
                    df_tmp[tmp_name.replace('basis_', 'pnl_market')] = index_pnl

                    funding_pnl = df_tmp[funding_column] * df_tmp['spot'] / 8
                    funding_pnl = funding_pnl.shift(1).fillna(0)
                    funding_pnl = funding_pnl.cumsum() / start_price
                    df_tmp[tmp_name.replace('basis_', 'pnl_funding_')] = funding_pnl
                    df_tmp[tmp_name.replace('basis_', 'pnl_total_')] = funding_pnl + index_pnl
                    pnl_series[tmp_name.replace('basis_', '')] = df_tmp
                else:
                    df_tmp = df[['spot', tmp_name]].dropna()
                    index_series = df['spot'] - df[tmp_name]
                    start_price = df['spot'].dropna()[0]
                    start_index = index_series.dropna()[0]
                    index_pnl = (index_series - start_index) / start_price
                    df_tmp[tmp_name.replace('basis_', 'pnl_total_')] = index_pnl
                    pnl_series[tmp_name.replace('basis_', '')] = df_tmp
        except:
            print(fut)

    return pnl_series


def plot_pnl(df, title):
    fig, ax = plt.subplots(figsize=(12, 6))

    # ax.yaxis.set_major_formatter(FormatStrFormatter('.2%'))
    fmt = '%.1f%%'  # Format you want the ticks, e.g. '40%'
    yticks = mtick.FormatStrFormatter(fmt)
    ax.yaxis.set_major_formatter(yticks)

    for i in df.columns:
        if 'pnl' in i:
            if 'total' in i:
                label = 'Total PnL'
            elif 'funding' in i:
                label = 'Funding PnL'
            else:
                label = 'Position PnL'
            ax.plot(df.index, df[i] * 100, label=label)

    plt.title(title)
    plt.legend()
    plt.ylabel('Cummulative PnL in %')
    plt.show()


if __name__ == '__main__':
    df_list = get_all_future_basis('BTC-USDT', 'binance')
    # plot_pnl(df_list['PERPETUAL|binance'], 'Long Binance BTC-USDT Spot, Short Binance BTC-USDT Perpetual')
    # plot_pnl(df_list['20240329|binance'], 'Long Binance BTC-USDT Spot, Short Binance 3M Future')
    plot_pnl(df_list['20240628|binance'], 'Long Binance BTC-USDT Spot, Short Binance 6M Future')
