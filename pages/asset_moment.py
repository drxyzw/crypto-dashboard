import dash
from dash import html, dcc, callback, Input, Output, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime as dt
import pandas as pd
import numpy as np
import ast
from scipy.interpolate import interp1d

from utils.convention import *
from market.load_market import loadMarket

dash.register_page(__name__, path="/btc_moment/")

HEADER_STYLE = {
    "backgroundColor": "#f8f9fa",  # optional: light gray background
    # "padding": "2rem 1rem",
}

CONTENT_STYLE = {
    "padding": "2rem 1rem",
}

ANALYSIS_DIR = "./data_analyzed"
df_regression = pd.read_excel(ANALYSIS_DIR + "/regression.xlsx")
moments = {"M1": "1st moment",
           "CM2": "2nd central moment",
           "CMN3": "3rd normalized central moment",
           "CMN4": "4th normalized central moment"}
moment_keys = list(moments.keys())
moment_values = list(moments.values())
df_vs_prediction = pd.read_excel(ANALYSIS_DIR + "/vsPrediction.xlsx")
dfs_vs_prediction = [
    df_vs_prediction[[m + "_PH_pred", m + "_PH", "Date", "ExpiryDate", "FutureExpiryDate", "TTM"]]
    for m in moment_keys]

layout = html.Div([
    html.H1("BTC/USD Moment Analysis", style=HEADER_STYLE),
    html.H3("Prediction of Physical Measure from Risk-Neutral Measure "),
    dash_table.DataTable(id="table_regression",
                         columns=[
                             dict(name=i, id=i) if i == "Target" else
                             dict(name=i, id=i, type="numeric", format=dict(specifier=".5f"))
                             for i in df_regression.columns],
                         data=df_regression.to_dict("records"),
                         style_cell=dict(textAlign="left")),
    dbc.Row([
        dbc.Col(dcc.Graph(id="1st-moment-chart-container",
                          responsive=True,
                          figure=px.scatter(dfs_vs_prediction[0],
                                            x = moment_keys[0] + "_PH_pred",
                                            y = moment_keys[0] + "_PH", title=moment_values[0])
                        ), width=6,
        ),
        dbc.Col(dcc.Graph(id="2nd-moment-chart-container",
                          responsive=True,
                          figure=px.scatter(dfs_vs_prediction[1],
                                            x = moment_keys[1] + "_PH_pred",
                                            y = moment_keys[1] + "_PH", title=moment_values[1])
                        ), width=6,
        ),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="3rd-moment-chart-container",
                          responsive=True,
                          figure=px.scatter(dfs_vs_prediction[2],
                                            x = moment_keys[2] + "_PH_pred",
                                            y = moment_keys[2] + "_PH", title=moment_values[2])
                        ), width=6,
        ),
        dbc.Col(dcc.Graph(id="4th-moment-chart-container",
                          responsive=True,
                          figure=px.scatter(dfs_vs_prediction[3],
                                            x = moment_keys[3] + "_PH_pred",
                                            y = moment_keys[3] + "_PH", title=moment_values[3])
                        ), width=6,
        ),
    ]),
])

