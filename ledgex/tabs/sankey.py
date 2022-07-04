from dash import dcc, html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from app import app

layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(id="sankey_data", className="hidden"),
        html.Div(
            children=[
                html.Div(id="flow_diagram"),
            ],
        ),
    ],
)
nodes = dict(
    label=[
        "Job",
        "Criminal Enterprise",
        "Gross Income $95k",
        "Bank A",
        "Bank B",
        "Bank C",
        "Cash under mattress 72",
        "Taxes 28",
    ],
    color=["gray", "yellow", "lightblue", "skyblue", "beige", "linen", "pink", "ivory"],
    x=[0, 0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.9],
    y=[0, 1, 0.3, 0.3, 0, 0, 0.2, 0.9],
)

flow_data = dict(
    source=[0, 1, 2, 2, 2, 3, 3, 4, 4, 5],
    target=[2, 2, 3, 6, 7, 4, 6, 5, 7, 6],
    value=[80, 15, 75, 14, 20, 54, 21, 46, 8, 46],
    color=[
        "gray",
        "yellow",
        "lightblue",
        "lightblue",
        "lightblue",
        "skyblue",
        "skyblue",
        "beige",
        "beige",
        "linen",
    ],
)


@app.callback(
    [Output("flow_diagram", "children")],
    [Input("sankey_data", "children")],
)
def fl_make_chart(data):
    """ Generate Sankey flow diagram """

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=300,
                    line=dict(color="black", width=0.5),
                    label=nodes["label"],
                    color=nodes["color"],
                    x=nodes["x"],
                    y=nodes["y"],
                ),
                link=dict(
                    source=flow_data["source"],
                    target=flow_data["target"],
                    value=flow_data["value"],
                    color=flow_data["color"],
                ),
            )
        ]
    )

    fig.update_layout(
        title_text="STUB for Sankey chart", font_size=20, height=1000, width=1000
    )
    return [dcc.Graph(figure=fig)]
