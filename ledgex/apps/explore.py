import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.atree import ATree
from ledgex.burst import Burst
from ledgex.params import Params
from ledgex.utils import (
    preventupdate_if_empty,
    LError,
)
from ledgex.datastore import Datastore


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
    [Input("ex_dummy", "children"),
     Input("pe_tab_trigger", "children")],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def ex_make_charts(ex_dummy, trigger, data_store, param_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    breakpoint()
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    data_store: Datastore() = Datastore.from_json(data_store, params.cu_roots)
    trans: pd.DataFrame = data_store.trans
    tree: ATree = data_store.account_tree
    account_list = tree.get_children(tree.root)
    result: list = []
    # make one chart for each item in the account filter

    if not isinstance(account_list, list):
        app.logger.warning(f"Account list should be a list but isn't: {account_list}")
        raise PreventUpdate
    for account in account_list:
        try:
            selected_accounts = tree.get_descendents(account)
            selected_trans = trans[trans["account"].isin(selected_accounts)]
            output = dcc.Graph(figure=Burst.from_trans(selected_trans, "total"))
        except LError as E:
            app.logger.warning(f"Failed to generate sunburst.  Error: {E}")

        if len(result) > 0:
            result.append(output)
        else:
            result = [output]
    return [result]
