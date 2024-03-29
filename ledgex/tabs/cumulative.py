from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from app import app
from atree import ATree
from params import CONST, Params
from utils import layouts, make_cum_area, preventupdate_if_empty
from datastore import Datastore

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
                            id="cu_time_series_resolution",
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
    [Output("cu_time_series_resolution", "value")], [Input("param_store", "children")]
)
def load_cu_params(param_store: str):
    """Load time series resolution from the store; this also starts the
    callback cascade on this tab"""
    preventupdate_if_empty(param_store)
    params = Params.from_json(param_store)
    return [params.init_time_res]


@app.callback(
    [Output("time_serieses", "children")],
    Input("cu_time_series_resolution", "value"),
    State("data_store", "children"), State("param_store", "children"),
)
def cu_make_time_serieses(time_resolution, data_store, param_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    data_store: Datastore() = Datastore.from_json(data_store, params.cu_roots)
    trans: pd.DataFrame = data_store.trans
    account_tree: ATree = data_store.account_tree
    if len(params.cu_roots) > 0:
        account_list = params.cu_roots
    else:
        account_list = [account_tree.root]
    unit: str = params.unit
    data_title = params.ds_data_title
    result: list = []
    # make one chart for each item in the Cumulative account filter

    if not isinstance(account_list, list):
        app.logger.warning(f"Account list should be a list but isn't: {account_list}")
        raise PreventUpdate
    for account in account_list:
        fig: go.Figure = go.Figure(layout=layouts['base'])
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
        subaccounts: iter = account_tree.get_children_ids(account)
        for j, subaccount in enumerate(subaccounts):
            sub_desc = account_tree.get_descendent_ids(subaccount)
            sub_desc.append(subaccount)
            tba = trans[trans["account"].isin(sub_desc)]
            if len(tba) > 0:
                fig.add_trace(make_cum_area(tba, subaccount, j, time_resolution))
        output = dcc.Graph(id=f"{account}{j}", figure=fig)
        if len(result) > 0:
            result.append(output)
        else:
            result = [output]
    return [result]
