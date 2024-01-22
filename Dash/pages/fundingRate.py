import datetime as dt

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import dash_table
from dash import dcc, html, callback, Output, Input
from dash.exceptions import PreventUpdate

from Analysis import funding_trades
from DataAPI.cryptoCompare import cryptoCompareApi

__app_id = 'funding_rate_'
dash.register_page(__name__, path=f'/{__app_id[:-1]}', name=__app_id.replace('_', ' ').title())

__dataAPI = cryptoCompareApi()


def filter_instrument(x):
    target_tokens = ['BTC', 'ETH', 'USD', 'USDT', 'USDC', 'EUR', 'BUSD', 'XBT']
    if not '-' in x:
        return False
    sl = x.split('-')
    ccy1 = sl[0]
    ccy2 = sl[1]
    return (ccy1 in target_tokens) and (ccy2 in target_tokens)


def get_layout():
    all_future = __dataAPI.load_futures_instruments()
    all_future_underlying = all_future['underlying'].unique()

    layout = html.Div(id='parent', children=[
        html.H1(
            id='H1',
            children='Funding Rate',
            style={'textAlign': 'center', 'marginTop': 40, 'marginBottom': 40}),
        dbc.Row([
            dbc.Col([
                dcc.Markdown("Underlying"),
                dcc.Dropdown(
                    id=__app_id + 'underlying_dropdown',
                    value='BTC-USDT',
                    options=[{'label': x, 'value': x} for x in all_future_underlying]),
            ]),
            dbc.Col([
                dcc.Markdown("Markets"),
                dcc.Dropdown(
                    id=__app_id + 'market_dropdown')

            ]),
            # dbc.Col([
            #     dcc.Markdown("Spot Instrument"),
            #     dcc.Dropdown(
            #         id=__app_id + 'spot_dropdown',
            #         value='binanceusa|BTC-USDT',
            #         options=[{'label': '|'.join(x), 'value': '|'.join(x)} for x in target_spots_list])
            # ]),
        ]),
        dcc.Graph(id=__app_id + 'basis_chart'),
        dbc.Col(id=__app_id + 'quantile_table', xs=4, sm=4, md=3, lg=3, xl=3, xxl=3),
        dcc.Graph(id=__app_id + 'distribution_chart'),
        dcc.Graph(id=__app_id + 'price_chart')
    ])
    return layout


layout = get_layout()


def plot_funding_rates(funding_instru):
    market, instrument = funding_instru.split('|')
    df = __dataAPI.load_annual_hourly_ohlc_data(
        mode='fundingrate',
        instrument=instrument,
        market=market
    )
    fig = go.Figure(
        [go.Scatter(x=df['TIMESTAMP'], y=df['CLOSE'], line=dict(color='firebrick', width=4), name='XBTUSD')])
    fig.update_layout(
        title=f'{market} {instrument} Fundung Rate over time',
        xaxis_title='Dates',
        yaxis_title='Funding Rate'
    )
    return fig


def plot_basis(instrument, market):
    df = funding_trades.get_all_future_basis(instrument, market)
    data = []
    for col in df.columns:
        data.append(go.Scatter(x=df.index, y=df[col], name=col))
    fig = go.Figure(data)
    fig.update_layout(
        title=f'{market} {instrument} basis over time',
        xaxis_title='Dates',
        yaxis_title='basis',
        showlegend=True
    )
    return fig


def plot_prices(spot_instru, future_instru, funding_instru):
    spot_v, spot_i = spot_instru.split('|')
    df_spot = __dataAPI.load_annual_hourly_ohlc_data(mode='spot', instrument=spot_i, market=spot_v)
    df_spot = df_spot[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'spot'}, axis=1).set_index('TIMESTAMP')
    funding_v, funding_i = funding_instru.split('|')
    df_funding = __dataAPI.load_annual_hourly_ohlc_data(mode='fundingrate', instrument=funding_i, market=funding_v)
    df_funding = df_funding[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': 'funding'}, axis=1).set_index('TIMESTAMP')
    df = pd.concat([df_spot, df_funding], axis=1)

    future_list = __dataAPI.load_futures_instruments(underlying='BTC-USDT', style='VANILLA')
    for tmp_idx, tmp in future_list.iterrows():
        # future_v, future_i = tmp_futures.split('|')
        df_future = __dataAPI.load_annual_hourly_ohlc_data(mode='futures', instrument=tmp['instrument'],
                                                           market=tmp['market'])
        tmp_name = f"{tmp['market']}|{tmp['instrument']}"
        df_future = df_future[['TIMESTAMP', 'CLOSE']].rename({'CLOSE': tmp_name}, axis=1)
        df_future = df_future.drop_duplicates(subset='TIMESTAMP', keep='last').set_index('TIMESTAMP')
        df = pd.concat([df, df_future], axis=1)

    df = df.sort_index().reset_index()

    # annualized the basis
    df['annual_funding'] = df['funding'] * 3 * 365
    for tmp_futures in future_list:
        df[tmp_futures] = df[tmp_futures] / df['spot'] - 1
        tenor = tmp_futures.split('-')[-1]
        if tenor == 'PERPETUAL':
            df[tmp_futures] = df[tmp_futures] * 3 * 365
        else:
            expiry = dt.datetime.strptime(tenor, '%Y%m%d')
            today = dt.datetime.now()
            annulized_factor = (expiry - today).days / 365
            df[tmp_futures] = df[tmp_futures] / annulized_factor

    quantiles = df.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    quantiles['stats'] = [f'{x:0.0%} percentile' for x in quantiles.index]
    stats = pd.DataFrame([df.mean(), df.std()], index=['mean', 'std dev'])
    stats['stats'] = stats.index
    quantiles = pd.concat([stats, quantiles])

    quantiles['annual_funding'] = [f'{x:.2%}' for x in quantiles['annual_funding']]
    for tmp_futures in future_list:
        quantiles[tmp_futures] = [f'{x:.2%}' for x in quantiles[tmp_futures]]

    stats = pd.DataFrame([df.count()], index=['n_datapoints'])
    for tmp_futures in future_list:
        stats[tmp_futures] = [f'{x:,.0f}' for x in stats[tmp_futures]]
    stats['stats'] = stats.index
    quantiles = pd.concat([stats, quantiles])

    quantiles = quantiles[['stats', 'annual_funding'] + future_list]
    quantile_table = dash_table.DataTable(quantiles.to_dict('records'),
                                          [{"name": i, "id": i} for i in quantiles.columns])

    fig_price = go.Figure([
        go.Scatter(x=df['TIMESTAMP'], y=df['spot'], name=spot_instru)])
    fig_price.update_layout(
        title=f'Spot vs Futures/Perp over time',
        xaxis_title='Dates',
        yaxis_title='Price in $'
    )

    fig_funding = go.Figure([
                                go.Scatter(x=df['TIMESTAMP'], y=df['annual_funding'], name='funding rates')] + [
                                go.Scatter(x=df['TIMESTAMP'], y=df[tmp_futures], name=f'basis for {tmp_futures}')
                                for tmp_futures in future_list])

    fig_funding.update_layout(
        title=f'Fundung Rate vs Future-Spot over time',
        xaxis_title='Dates',
        yaxis_title='Funding Rates in bps'
    )

    fig_histogram = go.Figure()
    fig_histogram.add_trace(go.Histogram(x=df['annual_funding'], name='annual_funding', histnorm='probability density'))
    for tmp_futures in future_list:
        fig_histogram.add_trace(go.Histogram(x=df[tmp_futures], name=tmp_futures, histnorm='probability density'))
    fig_histogram.update_layout(barmode='overlay')
    # Reduce opacity to see both histograms
    fig_histogram.update_traces(opacity=0.75)
    fig_histogram.update_layout(title='Basis and funding distribution')

    return fig_price, fig_funding, fig_histogram, quantile_table


@callback(
    Output(component_id=__app_id + 'market_dropdown', component_property='options'),
    [Input(component_id=__app_id + 'underlying_dropdown', component_property='value')])
def load_markets(underlying_dropdown):
    if underlying_dropdown is None:
        raise PreventUpdate

    all_future = __dataAPI.load_futures_instruments(underlying=underlying_dropdown, style='VANILLA')
    all_future_markets = all_future['market'].unique()
    if underlying_dropdown == 'BTC-USDT':
        all_future_markets = ['CME'] + list(all_future_markets)
    return [{'label': x, 'value': x} for x in all_future_markets]


@callback(
    Output(component_id=__app_id + 'basis_chart', component_property='figure'),
    [Input(component_id=__app_id + 'underlying_dropdown', component_property='value'),
     Input(component_id=__app_id + 'market_dropdown', component_property='value')])
def basis_plot_update(underlying, market):
    if underlying is None or market is None:
        raise PreventUpdate

    fig = plot_basis(instrument=underlying, market=market)
    return fig
