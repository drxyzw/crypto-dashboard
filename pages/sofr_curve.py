import dash
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
import random
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import pandas as pd

from utils.convention import *
from market.load_market import loadMarket

dash.register_page(__name__, path="/sofr_curve/")

HEADER_STYLE = {
    "backgroundColor": "#f8f9fa",  # optional: light gray background
    # "padding": "2rem 1rem",
}

CONTENT_STYLE = {
    "padding": "2rem 1rem",
}

levels = ["Elemtary (1-digit and no regrouping)",
                    "Easy (1-digit and regrouping)",
                    "Intermediate (2-digit)",
                    ]

PROCESSED_DIR = "./data_processed"
df_market_object_list = pd.read_excel(PROCESSED_DIR + "/market_objects.xlsx")
dateList = df_market_object_list[df_market_object_list["MarketObjects"].str.contains('USD.SOFR.CSA_USD')]["Date"]

layout = html.Div([
    html.H1("USD SOFR Curve", style=HEADER_STYLE),
    html.Div([
        dcc.Dropdown(id="date-selector", options = dateList, value = dateList[0]),
    ], style=CONTENT_STYLE),
    dbc.Row([
        dbc.Col(html.Div(id="table-container"), width=5),
        dbc.Col(dcc.Graph(id="chart-container",
                          responsive=True,
                        ),
                width=7,
                ),
    ])
])

@callback(
    Output("table-container", "children"),
    Output("chart-container", "figure"),
    Input("date-selector", "value"),
)
def update_output(selected_date_str):
    selected_date_py = dt.strptime(selected_date_str, "%Y-%m-%d")
    selected_date_ql = YYYYMMDDHyphenToQlDate(selected_date_str)
    mkt_object_name = 'USD.SOFR.CSA_USD'
    market = loadMarket(selected_date_py, names=[mkt_object_name])
    sofr_curve = market[mkt_object_name]
    tenors = [
        "1D", "1W", "2W", "1M", "2M", "3M", "6M", "9M",
        "1Y", "15M", "18M", "2Y", "3Y", "5Y",
        # "7Y", "10Y",
        # "12Y", "15Y", "20Y", "25Y", "30Y",
        ]
    cal = UKorUSCalendar()
    tenor_dates = [cal.advance(selected_date_ql, ql.Period(tenor)) for tenor in tenors]
    tenor_dates_str = [d.to_date().strftime("%Y-%m-%d") for d in tenor_dates]
    discounts = [sofr_curve.discount(d) for d in tenor_dates]
    zrates = [sofr_curve.zeroRate(d, ql.Actual365Fixed(), ql.Compounded, ql.Continuous).rate() * 100. for d in tenor_dates]
    df_table = pd.DataFrame({"Tenor": tenors, "Date": tenor_dates_str, "DF": discounts, "Zero Rate (%)": zrates})
    table = dash_table.DataTable(
        data = df_table.to_dict("records"),
        columns = [
                    {"name": c, "id": c, "type": "numeric",
                     "format": Format(precision=5, scheme=Scheme.fixed)}
                    if df_table[c].dtype.kind in "fc" else
                    {"name": c, "id": c}
                   for c in df_table.columns],
        style_header = {"textAlign": "center"},
        style_table = {"overflowX": "auto"},
        fill_width=False,
    )

    fig = {
        "data": [
            {
                "x": tenors,
                "y": zrates * 100,
                "type": "line",
                "name": "SOFR Curve",
            }
        ],
        "layout": {
            "title": f"SOFR Curve on {selected_date_str}",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Rate (%)"},
            "margin": {"l": 20, "r": 20, "t": 20, "b": 20}
        },
    }
    return table, fig

