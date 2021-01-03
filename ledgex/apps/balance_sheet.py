import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from ledgex.app import app
from ledgex.atree import ATree
from ledgex.params import CONST, Params
from ledgex.utils import chart_fig_layout, make_cum_area, preventupdate_if_empty
from ledgex.data_store import Datastore

layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                html.Fieldset(
                    className="flex_forward radio",
                    children=[
                        html.Span(children="Group By "),
                        dcc.RadioItems(
                            id="bs_time_series_resolution",
                            options=CONST["time_res_options"],
                        ),
                    ],
                ),
                html.Div(id="time_serieses", className="flex_down"),
            ],
        ),
    ],
)


@app.callback(
    [Output("bs_time_series_resolution", "value")], [Input("param_store", "children")]
)
def load_bs_params(param_store: str):
    """Load time series resolution from the store; this also starts the
    callback cascade on this tab"""
    preventupdate_if_empty(param_store)
    params = Params.from_json(param_store)
    return [params.init_time_res]


@app.callback(
    [Output("time_serieses", "children")],
    [Input("bs_time_series_resolution", "value")],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def bs_make_time_series(time_resolution, data_store, param_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    datastore: Datastore() = Datastore.from_json(data_store, params.bs_roots)
    trans: pd.DataFrame = datastore.trans
    account_tree: ATree = datastore.account_tree
    if len(params.bs_roots) > 0:
        account_list = params.bs_roots
    else:
        account_list = [account_tree.root]
    unit: str = params.unit
    data_title = params.ds_data_title
    result: list = []
    # make one chart for each item in the Balance Sheet account filter
    for i, account in enumerate(account_list):
        fig: go.Figure = go.Figure(layout=chart_fig_layout)
        fig.update_layout(
            title={"text": f"{data_title} {account}: Cumulative {unit}"},
            xaxis={"showgrid": True, "nticks": 20},
            yaxis={"showgrid": True},
            legend={
                "xanchor": "left",
                "x": 0,
                "yanchor": "bottom",
                "y": 0,
                "bgcolor": "rgba(0, 0, 0, 0)",
            },
            barmode="relative",
        )
        subaccounts: iter = account_tree.get_children(account)
        for j, subaccount in enumerate(subaccounts):
            sub_desc = account_tree.get_descendents(subaccount)
            tba = trans[trans["account"].isin(sub_desc)]
            if len(tba) > 0:
                fig.add_trace(make_cum_area(tba, subaccount, j, time_resolution))
        output = dcc.Graph(id=f"{account}{j}", figure=fig)
        if len(result) > 0:
            result.append(output)
        else:
            result = [output]
    return [result]
