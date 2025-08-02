import dash
from dash import html, dcc, callback, Input, Output, dash_table
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

dash.register_page(__name__, path="/btc_volsurface/")

HEADER_STYLE = {
    "backgroundColor": "#f8f9fa",  # optional: light gray background
    # "padding": "2rem 1rem",
}

CONTENT_STYLE = {
    "padding": "2rem 1rem",
}

PROCESSED_DIR = "./data_processed"
df_market_object_list = pd.read_excel(PROCESSED_DIR + "/market_objects.xlsx")
df_market_object_list["MarketObjectsList"] = df_market_object_list["MarketObjects"].apply(ast.literal_eval)
dateList = df_market_object_list[df_market_object_list["MarketObjectsList"].apply(
        lambda x: all(target in x for target in ['BTCUSD.VOLSURFACE'])
    )]["Date"].values

layout = html.Div([
    html.H1("BTC/USD Volatility Surface", style=HEADER_STYLE),
    html.Div([
        dcc.Dropdown(id="date-selector", options = dateList, value = dateList[0]),
    ], style=CONTENT_STYLE),
    dcc.Checklist(id="arbitrage-checklist",
                  options=["Show arbitrage point"],
                  value=[]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="volsurface-chart-container",
                          responsive=True,
                        ),
                # width=7,
                ),
    ]),
])
@callback(
    Output("volsurface-chart-container", "figure"),
    Input("date-selector", "value"),
    Input("arbitrage-checklist", "value"),
)
def update_output(selected_date_str, arbitrage_checklist_value):
    show_arbitrage_point = len(arbitrage_checklist_value) > 0
    selected_date_py = dt.strptime(selected_date_str, "%Y-%m-%d")
    selected_date_ql = YYYYMMDDHyphenToQlDate(selected_date_str)
    mkt_object_names = ['BTCUSD.VOLSURFACE']
    # market = loadMarket(selected_date_py, names=mkt_object_names)
    # volsurface = market[mkt_object_names[0]]
    YYYYMMDD = selected_date_py.strftime("%Y%m%d")
    PROCESSED_DIR = "./data_processed"
    volsurface_file = PROCESSED_DIR + "/" + YYYYMMDD + "/" + "BTCUSDVOLSURFACE_" + YYYYMMDD + ".xlsx"
    volsurface = pd.read_excel(volsurface_file)
    x = volsurface['Strike'].values
    y = volsurface['TTM'].values
    z = volsurface['Vol'].values

    # tenors = [
    #     "1D", "1W", "2W", "1M", "2M", "3M", "6M", "9M",
    #     "1Y", "15M", "18M", "2Y", "3Y", "5Y",
    #     # "7Y", "10Y",
    #     # "12Y", "15Y", "20Y", "25Y", "30Y",
    #     ]

    z_list = []
    y_grid = []
    x_grid = np.unique(x)
    for t, group in sorted(volsurface.groupby('TTM')):
        group = group.sort_values('Strike')
        if len(group) >= 2:
            f = interp1d(group['Strike'], group['Vol'], kind="linear", bounds_error=False, fill_value=np.nan)
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
    ))

    if show_arbitrage_point:
        arb_points = volsurface.dropna(subset=["Arbitrage"])
        # call spread arbitrage
        df_cs_arb = arb_points[arb_points["Arbitrage"].str.contains("CS", na=False)]
        x_cs = df_cs_arb['Strike'].values
        y_cs = df_cs_arb['TTM'].values
        z_cs = df_cs_arb['Vol'].values
        fig.add_trace(go.Scatter3d(
            x=x_cs,
            y=y_cs,
            z=z_cs,
            mode='markers+text',
            marker=dict(size=2, color='yellow', symbol='circle', opacity=0.6),
            textposition="top center",
            name="Call spread arbitrage"
        ))
        # butterfly arbitrage
        df_bf_arb = arb_points[arb_points["Arbitrage"].str.contains("BF", na=False)]
        x_bf = df_bf_arb['Strike'].values
        y_bf = df_bf_arb['TTM'].values
        z_bf = df_bf_arb['Vol'].values
        fig.add_trace(go.Scatter3d(
            x=x_bf,
            y=y_bf,
            z=z_bf,
            mode='markers+text',
            marker=dict(size=1, color='cyan', symbol='square', opacity=0.6),
            textposition="top center",
            name="Butterfly arbitrage"
        ))
        # calendar arbitrage
        df_cal_arb = arb_points[arb_points["Arbitrage"].str.contains("CA", na=False)]
        x_ca = df_cal_arb['Strike'].values
        y_ca = df_cal_arb['TTM'].values
        z_ca = df_cal_arb['Vol'].values
        fig.add_trace(go.Scatter3d(
            x=x_ca,
            y=y_ca,
            z=z_ca,
            mode='markers+text',
            marker=dict(size=3, color='red', symbol='circle', opacity=0.6),
            textposition="top center",
            name="Calendar arbitrage"
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="Strike"),
            yaxis=dict(title="T (years)"),
            zaxis=dict(title="Vol", tickformat=".0%", range=[z.min(), z.max()]),
        ),
        margin=dict(l=20, r=20, t=50, b=20)
        )
    return fig #, funding_table, funding_fig

