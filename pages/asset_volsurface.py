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
)
def update_output(selected_date_str):
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

    # volsurface_pivot = volsurface.pivot(index='TTM', columns='Strike', values='Vol')
    # z = volsurface_pivot.values
    # x = volsurface_pivot.columns.values
    # y = volsurface_pivot.index.values

    # X, Y = np.meshgrid(x, y)
    # # tenors = [
    # #     "1D", "1W", "2W", "1M", "2M", "3M", "6M", "9M",
    # #     "1Y", "15M", "18M", "2Y", "3Y", "5Y",
    # #     # "7Y", "10Y",
    # #     # "12Y", "15Y", "20Y", "25Y", "30Y",
    # #     ]
    # # cal = UKorUSCalendar()
    # # tenor_dates = [cal.advance(selected_date_ql, ql.Period(tenor)) for tenor in tenors]
    # # tenor_dates_str = [d.to_date().strftime("%Y-%m-%d") for d in tenor_dates]
    # fig = go.Figure(data=[go.Surface(z=z, x=X, y=Y)])
    # fig.update_layout(title = dict(text="BTC/USD Volatility Surface"),
    #                   margin=dict(l=20, r=20, t=50, b=20))
    # fig.update_layout(
    #     scene=dict(
    #         xaxis=dict(title="Strike", range=[x.min(), x.max()]),
    #         yaxis=dict(title="T", range=[y.min(), y.max()]),
    #         zaxis=dict(title="Vol"),
    #     )
    # )
    points2D = np.column_stack((x, y))
    tri = scipy.spatial.Delaunay(points2D)

    fig = go.Figure(data=[go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=tri.simplices[:, 0],
        j=tri.simplices[:, 1],
        k=tri.simplices[:, 2],
        colorscale='Viridis',
        intensity=z,
        colorbar=dict(
            title="Vol",
            tickformat=".0%", # Format as percentage
        ),
        opacity=0.9,
        flatshading=True
    )])
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="Strike"),
            yaxis=dict(title="T (years)"),
            zaxis=dict(title="Vol", tickformat=".0%"),
        ),
        margin=dict(l=20, r=20, t=50, b=20)
        )
    return fig #, funding_table, funding_fig

