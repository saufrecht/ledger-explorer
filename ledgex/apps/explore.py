import json

import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.atree import ATree
from ledgex.params import CONST, Params
from ledgex.utils import (
    chart_fig_layout,
    make_bar,
    preventupdate_if_empty,
    LError,
)
from ledgex.data_store import Datastore


layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                html.Div(id="ex_dummy", className="hidden"),
                html.Div(id="explore_chart", className="flex_down"),
            ],
        ),
    ],
)


@app.callback(
    [Output("explore_chart", "children")],
    [Input("ex_dummy", "children")],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def ex_make_charts(ex_dummy, data_store, param_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    trans: pd.DataFrame = data_store.trans
    account_tree: ATree = data_store.account_tree
    account_list = [account_tree.get_children(account_tree.root)]
    unit: str = params.unit
    data_title = params.ex_data_title
    result: list = []
    # make one chart for each item in the account filter

    if not isinstance(account_list, list):
        app.logger.warning(f"Account list should be a list but isn't: {account_list}")
        raise PreventUpdate
    for account in account_list:
        try:
            return trans_to_burst(
                account_tree, eras, figure, time_resolution, time_span, trans, unit
            )
        except LError as E:
            app.logger.warning(f"Failed to generate sunburst.  Error: {E}")

        output: go.Figure = trans_to_burst(
            account_tree, eras, figure, time_resolution, time_span, trans, unit
        )

        if len(result) > 0:
            result.append(output)
        else:
            result = [output]
    return [result]
