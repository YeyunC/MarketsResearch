import datetime as dt

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html, callback, Output, Input
from dash.exceptions import PreventUpdate

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
    funding_instrument_list = __dataAPI.load_all_futures_markets_instruments()
    funding_instrument_list = [x for x in funding_instrument_list if filter_instrument(x[1])]

    target_funding_list = [x for x in funding_instrument_list if ('VANILLA-PERPETUAL' in x[1])]
    target_futures_list = [x for x in funding_instrument_list if ('VANILLA' in x[1])]

    spot_instrument_list = __dataAPI.load_all_spots_markets_instruments()
    target_spots_list = [x for x in spot_instrument_list if filter_instrument(x[1])]

    layout = html.Div(id='parent', children=[
        html.H1(
            id='H1',
            children='Funding Rate',
            style={'textAlign': 'center', 'marginTop': 40, 'marginBottom': 40}),
        dbc.Row([
            dbc.Col([
                dcc.Markdown("Funding Rate Instrument"),
                dcc.Dropdown(
                    id=__app_id + 'funding_dropdown',
                    options=[{'label': '|'.join(x), 'value': '|'.join(x)} for x in target_funding_list])
            ]),
            dbc.Col([
                dcc.Markdown("Futures Instrument"),
                dcc.Dropdown(
                    id=__app_id + 'future_dropdown',
                    options=[{'label': '|'.join(x), 'value': '|'.join(x)} for x in target_futures_list])
            ]),
            dbc.Col([
                dcc.Markdown("Spot Instrument"),
                dcc.Dropdown(
                    id=__app_id + 'spot_dropdown',
                    options=[{'label': '|'.join(x), 'value': '|'.join(x)} for x in target_spots_list])
            ]),
        ]),
        dcc.Graph(id=__app_id + 'funding_rate_chart')
    ])
    return layout


layout = get_layout()


def load_future_data(market, instrument):
    data = __dataAPI.load_date_range_data(
        start_date=dt.datetime(2023, 1, 1),
        end_date=dt.datetime(2024, 1, 1),
        freq='hours',
        load_func=__dataAPI.load_funding_rate_historical_ohlcv,
        market=market,
        instrument=instrument)
    data = __dataAPI.proc_funding_rate_historical_ohlcv(data)
    return data


def plot_funding_rates(market, instrument):
    df = load_future_data(market, instrument)
    fig = go.Figure([go.Scatter(x=df.index, y=df['CLOSE'], line=dict(color='firebrick', width=4), name='XBTUSD')])
    fig.update_layout(
        title=f'{market} {instrument} Fundung Rate over time',
        xaxis_title='Dates',
        yaxis_title='Funding Rate'
    )
    return fig


@callback(
    Output(component_id=__app_id + 'funding_rate_chart', component_property='figure'),
    [Input(component_id=__app_id + 'funding_dropdown', component_property='value')])
def graph_update(dropdown_value):
    if dropdown_value is None:
        raise PreventUpdate
    print(dropdown_value)
    market, instrument = dropdown_value.split('|')
    fig = plot_funding_rates(market, instrument)
    return fig
