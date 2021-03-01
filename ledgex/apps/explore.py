import dash_core_components as dcc
import dash_html_components as html
import pandas as pd

import plotly.express as px
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.atree import ATree
from ledgex.params import Params
from ledgex.utils import (
    chart_fig_layout,
    preventupdate_if_empty,
)

from ledgex.datastore import Datastore


layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(id="ex_dummy", className="hidden"),
        html.Div(
            className="time_series_box",
            children=[
                dcc.Graph(id="ex_chart", className="flex_down"),
            ],
        ),
        html.Div(
            id="ex_drilldown_div",
            className="time_series_box",
        ),
    ],
)


# @app.callback(
#     [Output("ex_drill_figures", "children")],
#     [Input("ex_chart", "seleffctedData")],
#     state=[
#         State("data_store", "children"),
#         State("param_store", "children"),
#     ],
# )
# def ex_apply_selection(selectedData, data_store, param_store):
#     """Take the selected account from the main explorer chart
#     and show it in a series of drill-down charts
#     """
#     breakpoint()
#     params: Params() = Params.from_json(param_store)
#     data_store: Datastore() = Datastore.from_json(data_store, params.pe_roots)
#     # preventupdate_if_empty(data_store)
#     app.logger.debug(data_store.trans)

#     foo = html.Div("Foobar")
#     return [foo]


@app.callback(
    [Output("exo_chart", "figure")],
    [Input("ex_dummy", "children"), Input("pe_tab_trigger", "children")],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def ex_make_charts(ex_dummy, trigger, data_store, param_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    data_store: Datastore() = Datastore.from_json(data_store, params.ex_roots)
    trans: pd.DataFrame = data_store.trans
    tree: ATree = data_store.account_tree
    tree = tree.append_sums_from_trans(trans)
    tree.roll_up_subtotals()
    bar_data = pd.DataFrame(columns=["Account", "SubAccount", "Amount"])
    account_list = tree.get_children_ids(tree.root)
    if not isinstance(account_list, list):
        app.logger.warning(f"Account list should be a list but isn't: {account_list}")
        raise PreventUpdate
    for account in account_list:
        sub_tree = tree.subtree(account)
        for point in sub_tree.children(account):
            bar_data = bar_data.append(
                dict(
                    Account=account,
                    SubAccount=point.tag,
                    Amount=point.data["total"],
                    Color=point.tag,
                ),
                ignore_index=True,
            )
    bar_data = bar_data.sort_values(["Account", "Amount"])
    chart_fig: px.Figure = px.bar(
        bar_data,
        y="Account",
        x="Amount",
        color="SubAccount",
        text="SubAccount",
        orientation="h",
    )
    chart_fig.update_layout(chart_fig_layout)
    chart_fig.layout.update(showlegend=False)

    return [chart_fig]

