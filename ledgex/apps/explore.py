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
    preventupdate_if_empty,
)

from ledgex.datastore import Datastore


layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                html.Div(id="ex_dummy", className="hidden"),
                dcc.Graph(id="explore_chart", className="flex_down"),
            ],
        ),
    ],
)


@app.callback(
    [Output("explore_chart", "figure")],
    [Input("ex_dummy", "children"), Input("pe_tab_trigger", "children")],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def ex_make_charts(ex_dummy, trigger, data_store, param_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    data_store: Datastore() = Datastore.from_json(data_store, params.cu_roots)
    trans: pd.DataFrame = data_store.trans
    tree: ATree = data_store.account_tree
    tree = tree.append_sums_from_trans(trans)
    tree.roll_up_subtotals()
    account_list = tree.get_children_ids(tree.root)
    bar_data = pd.DataFrame(columns=["Account", "SubAccount", "Amount"])
    # make one chart for each item in the account filter
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
    chart_fig: px.Figure = px.bar(
        bar_data,
        y="Account",
        x="Amount",
        color="SubAccount",
        text="SubAccount",
        orientation="h",
    )
    chart_fig.layout.update(showlegend=False)

    return [chart_fig]

    # params: Params() = Params.from_json(param_store)
    # if not time_resolution:
    #     time_resolution = params.init_time_res
    # if not time_span:
    #     time_span = params.init_time_span
    # unit = params.unit
    # eras: pd.DataFrame = data_store.eras
    # try:
    #     tr_label = CONST["time_res_lookup"][time_resolution][
    #         "label"
    #     ]  # e.g., 'by Era'
    #     ts_label = CONST["time_span_lookup"][time_span][
    #         "label"
    #     ]  # e.g., 'Annual' or 'Monthly'
    # except KeyError as E:
    #     app.logger.warning(
    #         f"Bad data from selectors: time_resolution {time_resolution}, time_span {time_span}. {E}"
    #     )
    #     raise PreventUpdate
    # bar = make_bar(
    #     trans,
    #     account_tree,
    #     click_account,
    #     time_resolution,
    #     time_span,
    #     eras,
    #     0,
    #     deep=True,
    #     unit=unit,
    # )
    # detail_fig: go.Figure = go.Figure(layout=chart_fig_layout)
    # if bar:
    #     detail_fig.add_trace(bar)
    #     ts_title = f"Average {ts_label} {click_account} {unit}, by {tr_label} "
    #     detail_fig.update_layout(
    #         title={"text": ts_title},
    #         xaxis={"showgrid": True, "nticks": 20},
    #         yaxis={"showgrid": True},
    #         barmode="relative",
    #     )
    # elseif len(sel_accounts) > 0:
    #     sel_trans = trans[trans["account"]
    #     account_text = f"Click a pie slice to filter from {max_trans_count} records"

    # try:
    #     sel_trans = sel_trans[
    #         (sel_trans["date"] >= date_start) & (sel_trans["date"] <= date_end)
    #     ]
    # except (KeyError, TypeError):
    #     pass
    # sel_trans["date"] = pd.DatetimeIndex(sel_trans["date"]).strftime("%Y-%m-%d")
    # sel_trans = sel_trans.sort_values(["date"])

    # pe_trans_table_text: str = f"{len(sel_trans)} records"
