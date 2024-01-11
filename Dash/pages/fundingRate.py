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
        dcc.Graph(id=__app_id + 'funding_rate_chart'),
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
    fig = go.Figure([go.Scatter(x=df['TIMESTAMP'], y=df['CLOSE'], line=dict(color='firebrick', width=4), name='XBTUSD')])
    fig.update_layout(
        title=f'{market} {instrument} Fundung Rate over time',
        xaxis_title='Dates',
        yaxis_title='Funding Rate'
    )
    return fig

def plot_prices(spot_instru, future_instru):
    spot_v, spot_i = spot_instru.split('|')
    future_v, future_i = future_instru.split('|')
    df_spot = __dataAPI.load_annual_hourly_ohlc_data(mode='spot', instrument=spot_i, market=spot_v)
    df_future = __dataAPI.load_annual_hourly_ohlc_data(mode='futures', instrument=future_i, market=future_v)

    scatters = []
    scatters.append(go.Scatter(x=df_spot['TIMESTAMP'], y=df_spot['CLOSE'], name=spot_instru))
    scatters.append(go.Scatter(x=df_future['TIMESTAMP'], y=df_future['CLOSE'], name=df_future))

    fig = go.Figure(scatters)
    fig.update_layout(
        title=f'Spot vs Futures/Perp over time',
        xaxis_title='Dates',
        yaxis_title='Price'
    )
    return fig

@callback(
    [Output(component_id=__app_id + 'price_chart', component_property='figure'),
     Output(component_id=__app_id + 'funding_rate_chart', component_property='figure')],
    [Input(component_id=__app_id + 'funding_dropdown', component_property='value'),
    Input(component_id=__app_id + 'future_dropdown', component_property='value'),
    Input(component_id=__app_id + 'spot_dropdown', component_property='value')])
def graph_update(funding_dropdown, future_dropdown, spot_dropdown):
    if funding_dropdown is None or future_dropdown is None or spot_dropdown is None:
        raise PreventUpdate

    fig_price  = plot_prices(spot_dropdown, future_dropdown)
    fig_funding = plot_funding_rates(funding_dropdown)
    return fig_price, fig_funding
