import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html, callback
import dash

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP])

SIDEBAT_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa"
}

CONTENT_STYLE = {
    "margin-left": "16rem",
    "margin-right" :"2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div([
    html.H3("Cryptoboard", className="display-6"),
    html.Hr(),
    dbc.Nav([
        dbc.NavLink("Home", href="/", active="exact"),
        dbc.NavLink("USD SOFR Yield Curve", href="/sofr_curve", active="exact"),
        dbc.NavLink("BTC/USD Future Curve", href="/btc_forward", active="exact"),
        dbc.NavLink("BTC/USD Volatility Surface ", href="/btc_volsurface", active="exact"),
    ],
    vertical=True,
    pills=True)
],
style=SIDEBAT_STYLE)
app.layout = html.Div([dcc.Location(id="url"), sidebar, 
                       html.Div(dash.page_container, style=CONTENT_STYLE)])

if __name__ == "__main__":
    app.run(debug=True)
