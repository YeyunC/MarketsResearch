import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

import Analysis.funding_trades as fr
import Analysis.risk_free_rate as rfr
from DataAPI.cryptoCompare import cryptoCompareApi

__dataAPI = cryptoCompareApi()


def get_perp_basis_pnl(instrument, market):
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

    perp = f'{instrument}-VANILLA-PERPETUAL'

    perp_data = __dataAPI.load_annual_hourly_ohlc_data(
        mode='futures', instrument=perp, market=market, start_year=2023)
    perp_data = perp_data[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'PERP'}, axis=1)
    perp_data = perp_data.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')

    funding_rate = __dataAPI.load_annual_hourly_ohlc_data(
        mode='fundingrate', instrument=perp, market=market, start_year=2023)

    if len(funding_rate) > 0:
        funding_rate = funding_rate[funding_rate['CLOSE'] < 10000]
        funding_rate = funding_rate[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'FUNDING'}, axis=1)
        funding_rate = funding_rate.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')

    df = pd.concat([df_spot, perp_data, funding_rate], axis=1).sort_index()
    df = df[df['spot'] > 1]

    index_series = df['spot'] - df['PERP']
    start_price = df['spot'].dropna()[0]
    start_index = index_series.dropna()[0]
    df['position_pnl'] = (index_series - start_index) / start_price

    funding_pnl = df['FUNDING'] * df['spot'] / 8
    funding_pnl = funding_pnl.shift(1).fillna(0)
    df['funding_pnl'] = funding_pnl.cumsum() / start_price
    df['total_pnl'] = df['position_pnl'] + df['funding_pnl']

    df.to_csv('PNL_LongSpotShortPerp.csv')
    return df


def get_term_future_basis_pnl(instrument, market):
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

    rolling_futures = __dataAPI.load_rolling_futures_ohlc_data(
        instrument=instrument, market=spot_market, start_year=2023)

    near_futures = rolling_futures.sort_values('EXPIRY_TS').drop_duplicates(subset='TIMESTAMP',
                                                                            keep='first').sort_values('TIMESTAMP')
    far_futures = rolling_futures.sort_values('EXPIRY_TS').drop_duplicates(subset='TIMESTAMP', keep='last').sort_values(
        'TIMESTAMP')

    futures = pd.merge_asof(near_futures, far_futures, on='TIMESTAMP', suffixes=('_near', '_far'))
    futures['roll'] = (futures['EXPIRY_TS_near'] == (futures['TIMESTAMP'] + pd.Timedelta(days=2)))
    futures['use_far'] = (futures['EXPIRY_TS_near'] <= (futures['TIMESTAMP'] + pd.Timedelta(days=2)))

    futures.loc[futures['use_far'], 'index'] = futures['CLOSE_far']
    futures.loc[~futures['use_far'], 'index'] = futures['CLOSE_near']
    futures = futures.set_index('TIMESTAMP')

    df = pd.concat([df_spot, futures], axis=1).sort_index()
    df = df[df['spot'] > 1]

    index_series = df['spot'] - df['index']
    start_price = df['spot'].dropna()[0]
    start_index = index_series.dropna()[0]
    df['unrealized_pnl'] = index_series - start_index
    df['roll'] = df['roll'].fillna(False)
    df.loc[df['roll'], 'realized_pnl'] = df['CLOSE_far'] - df['CLOSE_near']
    df['realized_pnl'] = df['realized_pnl'].fillna(0).cumsum()
    df['total_pnl'] = df['unrealized_pnl'] + df['realized_pnl']
    df['total_pnl'] = df['total_pnl'] / start_price
    df['unrealized_pnl'] = df['unrealized_pnl'] / start_price
    df['realized_pnl'] = df['realized_pnl'] / start_price

    df.to_csv('PNL_LongSpotShortFuture.csv')
    return df


def plot_pnl(df, title, cols):
    fig, ax = plt.subplots(figsize=(12, 6))

    # ax.yaxis.set_major_formatter(FormatStrFormatter('.2%'))
    fmt = '%.1f%%'  # Format you want the ticks, e.g. '40%'
    yticks = mtick.FormatStrFormatter(fmt)
    ax.yaxis.set_major_formatter(yticks)

    # for i in ['total_pnl', 'unrealized_pnl', 'realized_pnl']:
    for i in cols:
        ax.plot(df.index, df[i] * 100, label=i)

    ax.axhline(0, color='black', linestyle='--')

    plt.title(title)
    plt.legend()
    plt.ylabel('Cummulative PnL in %')
    plt.tight_layout()
    plt.show()


def calc_stats(df):
    # n_days = (df.index.max() - df.index.min()).days
    # final_return = df.iloc[-1]['total_pnl']
    # annualized_return = final_return / n_days * 365

    daily_return = pd.DataFrame(df['total_pnl'].resample('1D').last())
    risk_free_return = rfr.read_risk_free_return()
    daily_return = daily_return.join(risk_free_return)
    daily_return['return_1'] = daily_return['total_pnl'].shift().fillna(0)
    daily_return['daily_strategy_return'] = daily_return['total_pnl'] - daily_return['return_1']
    daily_return['daily_excess_return'] = daily_return['daily_strategy_return'] - daily_return['daily_risk_free_return']

    annualized_return = daily_return['daily_strategy_return'].mean() * 365
    annualized_risk_free_return = daily_return['daily_risk_free_return'].mean() * 365

    annualized_return_vol = daily_return['daily_strategy_return'].std() * np.sqrt(365)
    annualized_excess_return_vol = daily_return['daily_excess_return'].std() * np.sqrt(365)

    sharpe_ratio = (annualized_return - annualized_risk_free_return) / annualized_excess_return_vol

    start_price = df.iloc[0]['spot']
    df['price_index'] = start_price * (1 + df['total_pnl'])
    df['cummax'] = df['price_index'].cummax()
    df['drawdown'] = df['price_index'] / df['cummax'] - 1
    max_draw_down = df['drawdown'].min()
    df['drawdown'].plot()
    plt.show()

    return {
        'Annualized Return': annualized_return,
        'Annualized Risk Free Return': annualized_risk_free_return,
        'Max Draw Down': max_draw_down,
        'Vol of Return': annualized_return_vol,
        'Vol of Excess Return': annualized_excess_return_vol,
        'Sharpe Ratio': sharpe_ratio,
    }


if __name__ == '__main__':
    df_perp = get_perp_basis_pnl('BTC-USDT', 'binance')
    # plot_pnl(
    #     df_perp,
    #     'Binance BTC-USDT | Long Spot, Short Perpetual',
    #     ['position_pnl', 'funding_pnl', 'total_pnl']
    # )
    print('perp')
    print(calc_stats(df_perp))

    df_term_future = get_term_future_basis_pnl('BTC-USDT', 'binance')
    plot_pnl(
        df_term_future,
        'Binance BTC-USDT | Long Spot, Short Front Month Futures Rolling Every 3M',
        ['unrealized_pnl', 'realized_pnl', 'total_pnl']
    )

    print('term future')
    print(calc_stats(df_term_future))
