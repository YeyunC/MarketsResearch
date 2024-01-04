import datetime as dt

import dash
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from DataAPI.cryptoCompare import cryptoCompareApi

app = dash.Dash()  # initialising dash app
df = px.data.stocks()  # reading stock price dataset

__app_id = 'funding_rate_'
__dataAPI = cryptoCompareApi()


def get_layout():
    funding_instrument_list = __dataAPI.instrument_search('BTC')

    layout = html.Div(id='parent', children=[
        html.H1(
            id='H1',
            children='Funding Rate',
            style={'textAlign': 'center', 'marginTop': 40, 'marginBottom': 40}),
        dcc.Dropdown(
            id=__app_id + 'mkt_instru_dropdown',
            options=[{'label': '|'.join(x), 'value': x} for x in funding_instrument_list]),
        dcc.Graph(
            id=__app_id + 'funding_rate_chart')])
    return layout


def load_future_data(market, instrument):
    dataAPI = cryptoCompareApi()

    data = dataAPI.load_date_range_data(
        start_date=dt.datetime(2023, 1, 1),
        end_date=dt.datetime(2024, 1, 1),
        freq='hours',
        load_func=dataAPI.load_funding_rate_historical_ohlcv,
        market=market,
        instrument=instrument)
    data = dataAPI.proc_funding_rate_historical_ohlcv(data)
    return data


def plot_funding_rates(market, instrument):
    df = load_future_data(market, instrument)
    fig = go.Figure([go.Scatter(x=df.index, y=df['CLOSE'], line=dict(color='firebrick', width=4), name='XBTUSD')])
    fig.update_layout(
        title='Fundung Rate over time',
        xaxis_title='Dates',
        yaxis_title='Prices'
    )
    return fig


app.layout = get_layout()


@app.callback(
    Output(component_id=__app_id + 'funding_rate_chart', component_property='figure'),
    [Input(component_id=__app_id + 'mkt_instru_dropdown', component_property='value')])
def graph_update(dropdown_value):
    if dropdown_value is None:
        raise PreventUpdate
    print(dropdown_value)
    market, instrument = dropdown_value
    fig = plot_funding_rates(market, instrument)
    return fig


if __name__ == '__main__':
    app.run_server()
