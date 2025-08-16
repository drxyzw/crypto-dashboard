import dash
from dash import html, dcc, callback, Input, Output, dash_table, State
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime as dt
import pandas as pd
import numpy as np
import ast
import scipy.spatial
from scipy.interpolate import interp1d

from utils.convention import *
from market.load_market import loadMarket

dash.register_page(__name__, path="/btc_qprobability/")

HEADER_STYLE = {
    "backgroundColor": "#f8f9fa",  # optional: light gray background
    # "padding": "2rem 1rem",
}

CONTENT_STYLE = {
    "padding": "2rem 1rem",
}

PROCESSED_DIR = "./data_processed"
df_market_object_list = pd.read_excel(PROCESSED_DIR + "/market_qprobability.xlsx")
df_market_object_list["MarketObjectsList"] = df_market_object_list["MarketObjects"].apply(ast.literal_eval)
dateList = df_market_object_list[df_market_object_list["MarketObjectsList"].apply(
        lambda x: all(target in x for target in ['BTCUSD.QPROBABILITY'])
    )]["Date"].values

layout = html.Div([
    html.H1("BTC/USD Risk-Neutral Probability", style=HEADER_STYLE),
    html.Div([
        dcc.Dropdown(id="date-selector", options = dateList, value = dateList[0]),
    ], style=CONTENT_STYLE),
    dcc.RangeSlider(id="strike_slider",
                    min=0,
                    max=400000,
                    step=50000,
                    value=[0, 400000]),
    dcc.RangeSlider(id="t_slider",
                    min=0.,
                    max=2.,
                    step=0.25,
                    value=[0., 2.]),
    dcc.Store(id="data-qprobability", data={
        "qprobability": None,
    }),
    dbc.Row([
        dbc.Col(dcc.Graph(id="qprobability-chart-container",
                          responsive=True,
                        ),
                # width=7,
                ),
    ]),
])

@callback(
    Output("qprobability-chart-container", "figure", allow_duplicate=True),
    Input("strike_slider", "value"),
    Input("t_slider", "value"),
    State("qprobability-chart-container", "figure"),
    State("data-qprobability", "data"),
    prevent_initial_call=True,
)
def update_chart_range(strike_slider_value, t_slider_value, fig, data):
    if not fig is None:
        fig['layout']['scene']['xaxis']['range'] = strike_slider_value
        fig['layout']['scene']['yaxis']['range'] = t_slider_value
        # find max and min aprobability within the range
        qprob_dict = data["qprobability"]
        qprob_selected_dict = list(filter(lambda x:
            (t_slider_value[0] <= x["TTM"]) & (x["TTM"] <= t_slider_value[1]) &
            (strike_slider_value[0] <= x["Strike"]) & (x["Strike"] <= strike_slider_value[1]),
            qprob_dict))
        qprob_selected = [d["Density"] for d in qprob_selected_dict]
        max_qprob = max(qprob_selected)
        min_qprob = min(qprob_selected)
        fig['layout']['scene']['zaxis']['range'] = [min_qprob, max_qprob]

        fig = go.Figure(fig)

        new_trace = go.Surface(
        x=fig.data[0].x,
        y=fig.data[0].y,
        z=fig.data[0].z,
        colorscale='Viridis',
        cmin=min_qprob,
        cmax=max_qprob,
        colorbar=dict(exponentformat="power"),
        name="qprobability")
        fig.update_traces(new_trace, selector=dict(name="qprobability"))

    return fig

def displayChart(qprobability, strike_sllider_value, t_sllider_value,
                 k_range = None, t_range = None):
    x = qprobability['Strike'].values
    y = qprobability['TTM'].values
    z = qprobability['Density'].values

    # tenors = [
    #     "1D", "1W", "2W", "1M", "2M", "3M", "6M", "9M",
    #     "1Y", "15M", "18M", "2Y", "3Y", "5Y",
    #     # "7Y", "10Y",
    #     # "12Y", "15Y", "20Y", "25Y", "30Y",
    #     ]

    z_list = []
    y_grid = []
    x_grid = np.unique(x)
    for t, group in sorted(qprobability.groupby('TTM')):
        group = group.sort_values('Strike')
        if len(group) >= 2:
            f = interp1d(group['Strike'], group['Density'], kind="linear", bounds_error=False, fill_value=np.nan)
            z_interp = f(x_grid)
            z_list.append(z_interp)
            y_grid.append(t)

    # make datapoints of (strike, TTM_i) for all strikes and certain i if adjacent (strike, TTM_i+1) and (strike, TTM_i-1) are nan
    # this is typically happens shortend monthly options where weekly options are available.
    i_y = 0
    for i_x in range(len(x_grid)):
        if (not pd.isna(z_list[i_y][i_x])) and pd.isna(z_list[i_y + 1][i_x]):
            z_list[i_y][i_x] = np.nan

    for i_y in range(1, len(y_grid) - 2):
        for i_x in range(len(x_grid)):
            if (not pd.isna(z_list[i_y][i_x])) and pd.isna(z_list[i_y - 1][i_x]) and pd.isna(z_list[i_y + 1][i_x]):
                z_list[i_y][i_x] = np.nan

    i_y = len(y_grid) - 1
    for i_x in range(len(x_grid)):
        if (not pd.isna(z_list[i_y][i_x])) and pd.isna(z_list[i_y - 1][i_x]):
            z_list[i_y][i_x] = np.nan

    Z_grid = np.vstack(z_list)
    X_grid = x_grid
    Y_grid = y_grid

    fig = go.Figure(data=go.Surface(
        x=X_grid,
        y=Y_grid,
        z=Z_grid,
        colorscale='Viridis',
        name="qprobability",
        colorbar=dict(exponentformat="power"),
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="Strike", range=strike_sllider_value),
            yaxis=dict(title="T (years)", range=t_sllider_value),
            zaxis=dict(title="Risk Neutral Probability", exponentformat="power"),
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        legend_orientation="h",
        )
    return fig

@callback(
    Output("qprobability-chart-container", "figure"),
    Output("data-qprobability", "data"),
    Input("date-selector", "value"),
    State("strike_slider", "value"),
    State("t_slider", "value"),
    State("data-qprobability", "data"),
)
def update_output(selected_date_str, strike_sllider_value, t_sllider_value, data):
    selected_date_py = dt.strptime(selected_date_str, "%Y-%m-%d")
    # selected_date_ql = YYYYMMDDHyphenToQlDate(selected_date_str)
    # market = loadMarket(selected_date_py, names=mkt_object_names)
    YYYYMMDD = selected_date_py.strftime("%Y%m%d")
    PROCESSED_DIR = "./data_processed"
    qprob_file = PROCESSED_DIR + "/" + YYYYMMDD + "/" + "BTCUSDQPROBABILITY_" + YYYYMMDD + ".xlsx"
    qprob = pd.read_excel(qprob_file)
    data["qprobability"] = qprob.to_dict("records")

    fig = displayChart(qprob, strike_sllider_value, t_sllider_value)
    return fig, data

