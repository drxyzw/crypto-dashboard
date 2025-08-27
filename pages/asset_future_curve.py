import dash
from dash import html, dcc, callback, Input, Output, dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
from datetime import datetime as dt
import pandas as pd
import ast

from utils.convention import *
from market.load_market import loadMarket

dash.register_page(__name__, path="/btc_future/")

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
        lambda x: all(target in x for target in ['USD.SOFR.CSA_USD', 'BTC.FUNDING.CSA_USD', 'BTCUSD.SPOT'])
    )]["Date"].values

layout = html.Div([
    html.H1("BTC/USD Future Curve", style=HEADER_STYLE),
    html.Div([
        dcc.Dropdown(id="date-selector", options = dateList, value = dateList[0]),
    ], style=CONTENT_STYLE),
    dbc.Row([
        dbc.Col(html.Div(id="future-table-container"), width=5),
        dbc.Col(dcc.Graph(id="future-chart-container",
                          responsive=True,
                        ),
                width=7,
                ),
    ]),
    html.Br(),
    html.H1("BTC Implied Yield Curve", style=HEADER_STYLE),
    html.H5("Noise on future price may disturb implied rate"),
    html.H5("This is NOT a funding rate of perpetual future"),
    dbc.Row([
        dbc.Col(html.Div(id="funding-table-container"), width=5),
        dbc.Col(dcc.Graph(id="funding-chart-container",
                          responsive=True,
                        ),
                width=7,
                ),
    ])
])

@callback(
    Output("future-table-container", "children"),
    Output("future-chart-container", "figure"),
    Output("funding-table-container", "children"),
    Output("funding-chart-container", "figure"),
    Input("date-selector", "value"),
)
def update_output(selected_date_str):
    selected_date_py = dt.strptime(selected_date_str, "%Y-%m-%d")
    selected_date_ql = YYYYMMDDHyphenToQlDate(selected_date_str)
    mkt_object_names = ['USD.SOFR.CSA_USD', 'BTC.FUNDING.CSA_USD', 'BTCUSD.SPOT']
    market = loadMarket(selected_date_py, names=mkt_object_names)
    sofr_curve = market['USD.SOFR.CSA_USD']
    funding_curve = market['BTC.FUNDING.CSA_USD']
    spot_object = market['BTCUSD.SPOT']
    spot = spot_object.spotRate
    tenors = [
        "1D", "1W", "2W", "1M", "2M", "3M", "6M", "9M",
        "1Y", "15M", "18M", "2Y", "3Y", "5Y",
        # "7Y", "10Y",
        # "12Y", "15Y", "20Y", "25Y", "30Y",
        ]
    cal = UKorUSCalendar()
    tenor_dates = [cal.advance(selected_date_ql, ql.Period(tenor)) for tenor in tenors]
    tenor_dates_str = [d.to_date().strftime("%Y-%m-%d") for d in tenor_dates]

    # future curve
    future_values = [spot * funding_curve.discount(d) / sofr_curve.discount(d) for d in tenor_dates]
    df_future_table = pd.DataFrame({"Tenor": tenors, "Date": tenor_dates_str, "Future Value": future_values})
    df_spot_table = pd.DataFrame({"Tenor": ["Spot"], "Date": [selected_date_str], "Future Value": [spot]})
    df_future_table = pd.concat([df_spot_table, df_future_table])
    future_table = dash_table.DataTable(
        data = df_future_table.to_dict("records"),
        columns = [
                    {"name": c, "id": c, "type": "numeric",
                     "format": Format(precision=2, scheme=Scheme.fixed)}
                    if df_future_table[c].dtype.kind in "fc" else
                    {"name": c, "id": c}
                   for c in df_future_table.columns],
        style_header = {"textAlign": "center"},
        style_table = {"overflowX": "auto"},
        fill_width=False,
    )
    future_fig = {
        "data": [
            {
                "x": tenors,
                "y": future_values,
                "type": "line",
                "name": "Future Curve",
            }
        ],
        "layout": {
            "title": f"SOFR Curve on {selected_date_str}",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Future Value"},
            "margin": {"l": 50, "r": 20, "t": 20, "b": 20}
        },
    }

    # funding curve
    funding_zrates = [-funding_curve.zeroRate(d, ql.Actual365Fixed(), ql.Compounded, ql.Continuous).rate() * 100. for d in tenor_dates]
    df_funding_table = pd.DataFrame({"Tenor": tenors, "Date": tenor_dates_str, "Zero Rate (%)": funding_zrates})
    funding_table = dash_table.DataTable(
        data = df_funding_table.to_dict("records"),
        columns = [
                    {"name": c, "id": c, "type": "numeric",
                     "format": Format(precision=5, scheme=Scheme.fixed)}
                    if df_funding_table[c].dtype.kind in "fc" else
                    {"name": c, "id": c}
                   for c in df_funding_table.columns],
        style_header = {"textAlign": "center"},
        style_table = {"overflowX": "auto"},
        fill_width=False,
    )
    funding_fig = {
        "data": [
            {
                "x": tenors,
                "y": funding_zrates * 100,
                "type": "line",
                "name": "Implied Funding Spread Curve",
            }
        ],
        "layout": {
            "title": f"Implied Funding Spread Curve on {selected_date_str}",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Rate (%)"},
            "margin": {"l": 50, "r": 20, "t": 20, "b": 20}
        },
    }
    return future_table, future_fig, funding_table, funding_fig

