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
    html.H3("Math quiz", className="display-6"),
    html.Hr(),
    dbc.Nav([
        dbc.NavLink("Home", href="/", active="exact"),
        dbc.NavLink("Addition", href="/addition", active="exact"),
        dbc.NavLink("Subtraction", href="/subtraction", active="exact"),
        dbc.NavLink("Multiplication", href="/multiplication", active="exact"),
        dbc.NavLink("Division", href="/division", active="exact"),
    ],
    vertical=True,
    pills=True)
],
style=SIDEBAT_STYLE)
# content = html.Div(id="page-content", style=CONTENT_STYLE)
# app.layout = html.Div([dcc.Location(id="url"), sidebar, content])
app.layout = html.Div([dcc.Location(id="url"), sidebar, 
                       html.Div(dash.page_container, style=CONTENT_STYLE)])

# @callback(
#     Output("page-content", "children"),
#     [Input("url", "pathname")]
# )
# def render_page_content(pathname):
#     if pathname == "/":
#         return html.P("Home") 
#     return html.P("else")

if __name__ == "__main__":
    app.run(debug=True)
