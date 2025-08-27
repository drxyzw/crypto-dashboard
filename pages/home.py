import dash
from dash import html, dcc
dash.register_page(__name__, path="/")

github_url = "https://github.com/drxyzw/crypto-dashboard"
layout = html.Div([
    html.H1("Home"),
    html.H5("GitHub:"),
    html.A(github_url, href=github_url),
])
