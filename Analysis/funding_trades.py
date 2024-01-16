from DataAPI.cryptoCompare import cryptoCompareApi
import pandas as pd
__dataAPI = cryptoCompareApi()


def get_all_futures(instrument = 'BTC-USDT'):
    data = __dataAPI.load_futures_instruments(underlying=instrument)
    return data

def get_all_spots(instrument = 'BTC-USDT'):
    data = __dataAPI.load_spot_instruments(instrument=instrument)
    return data


if __name__ == '__main__':
    data = get_all_spots()
    data = get_all_futures()

# def plot_prices(spot_instru, future_instru, funding_instru):
#     spot_v, spot_i = spot_instru.split('|')
#     df_spot = __dataAPI.load_annual_hourly_ohlc_data(mode='spot', instrument=spot_i, market=spot_v)
#     df_spot = df_spot[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'spot'}, axis=1).set_index('TIMESTAMP')
#     funding_v, funding_i = funding_instru.split('|')
#     df_funding = __dataAPI.load_annual_hourly_ohlc_data(mode='fundingrate', instrument=funding_i, market=funding_v)
#     df_funding = df_funding[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'funding'}, axis=1).set_index('TIMESTAMP')
#     df = pd.concat([df_spot, df_funding], axis=1)
#
#     future_list = __dataAPI.load_futures_instruments(market='binance', underlying='BTC-USDT')
#     for tmp_futures in future_list:
#         # future_v, future_i = tmp_futures.split('|')
#         df_future = __dataAPI.load_annual_hourly_ohlc_data(mode='futures', instrument=tmp_futures, market='binance')
#         df_future = df_future[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': tmp_futures}, axis=1)
#         df_future = df_future.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
#         df = pd.concat([df, df_future], axis=1)
#
#     df = df.sort_index().reset_index()
#
#     # annualized the basis
#     df['annual_funding'] = df['funding'] * 3 * 365
#     for tmp_futures in future_list:
#         df[tmp_futures] = df[tmp_futures] / df['spot'] - 1
#         tenor = tmp_futures.split('-')[-1]
#         if tenor == 'PERPETUAL':
#             df[tmp_futures] = df[tmp_futures] * 3 * 365
#         else:
#             expiry = dt.datetime.strptime(tenor, '%Y%m%d')
#             today = dt.datetime.now()
#             annulized_factor = (expiry - today).days / 365
#             df[tmp_futures] = df[tmp_futures] / annulized_factor
#
#     quantiles = df.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
#     quantiles['stats'] = [f'{x:0.0%} percentile' for x in quantiles.index]
#     stats = pd.DataFrame([df.mean(), df.std()], index=['mean', 'std dev'])
#     stats['stats'] = stats.index
#     quantiles = pd.concat([stats, quantiles])
#
#     quantiles['annual_funding'] = [f'{x:.2%}' for x in quantiles['annual_funding']]
#     for tmp_futures in future_list:
#         quantiles[tmp_futures] = [f'{x:.2%}' for x in quantiles[tmp_futures]]
#
#     stats = pd.DataFrame([df.count()], index=['n_datapoints'])
#     for tmp_futures in future_list:
#         stats[tmp_futures] = [f'{x:,.0f}' for x in stats[tmp_futures]]
#     stats['stats'] = stats.index
#     quantiles = pd.concat([stats, quantiles])
#
#     quantiles = quantiles[['stats', 'annual_funding'] + future_list]
#     quantile_table = dash_table.DataTable(quantiles.to_dict('records'),
#                                           [{"name": i, "id": i} for i in quantiles.columns])