import dash
from dash import dcc, html, callback, Output, Input
import plotly.express as px
import dash_bootstrap_components as dbc

dash.register_page(__name__, path='/', name='Home') # '/' is home page

layout = dbc.Row([
    dbc.Col(
        html.Div(
            children="Home Sweet Home",
            style={'fontSize':50, 'textAlign':'center'}
        )
    )
])