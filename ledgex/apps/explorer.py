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
    ex_trans_table,
    make_bar,
    trans_to_burst,
    preventupdate_if_empty,
    LError
)
from ledgex.data_store import Datastore


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                dcc.Graph(id="ex_master_time_series"),
                html.Div(
                    className="control_bar",
                    children=[
                        dcc.Store(
                            id="ex_time_series_selection_info", storage_type="memory"
                        ),
                        html.Div(id="ex_selected_trans_display", children=None),
                        html.Fieldset(
                            className="flex_forward radio",
                            children=[
                                html.Span(children="Group By "),
                                dcc.RadioItems(
                                    id="ex_time_series_resolution",
                                    options=CONST["time_res_options"],
                                ),
                            ],
                        ),
                        html.Fieldset(
                            className="flex_forward radio",
                            children=[
                                dcc.RadioItems(
                                    id="ex_time_series_span",
                                    options=CONST["time_span_options"],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            className="account_burst_box",
            children=[
                html.Div(
                    [
                        html.H3(id="ex_burst_title", children=""),
                        html.Div(
                            id="ex_selected_account_text",
                            children="Click a pie slice to filter records",
                        ),
                    ]
                ),
                dcc.Graph(id="ex_account_burst"),
            ],
        ),
        html.Div(
            className="trans_table_box",
            children=[
                html.Div(id="ex_trans_table_text", children=""),
                ex_trans_table,
            ],
        ),
    ],
)


@app.callback(
    [
        Output("ex_time_series_resolution", "value"),
        Output("ex_time_series_resolution", "options"),
        Output("ex_time_series_span", "value"),
    ],
    [Input("ex_tab_trigger", "children")],
    state=[State("data_store", "children"),
           State("param_store", "children")]
)
def load_ex_params(trigger: str, data_store: str, param_store: str):
    """ When the param store changes and this tab is visible, update the top params"""
    preventupdate_if_empty(param_store)
    params = Params(**json.loads(param_store))
    options = CONST["time_res_options"]
    datastore: Datastore() = Datastore.from_json(data_store)
    eras = datastore.eras
    if len(eras) > 0:
        options = [CONST["time_res_era_option"]] + options

    return [params.init_time_res, options, params.init_time_span]


@app.callback(
    [Output("ex_master_time_series", "figure")],
    [
        Input("ex_time_series_resolution", "value"),
        Input("ex_time_series_span", "value"),
    ],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def ex_make_time_series(
    time_resolution: int, time_span: str, data_store: str, param_store: str
):
    """ Generate a Dash bar chart figure from transactional data """
    preventupdate_if_empty(data_store)
    params: Params() = Params.from_json(param_store)
    if not time_resolution:
        time_resolution = params.init_time_res

    if not time_span:
        time_span = params.init_time_span

    try:
        tr_label = CONST["time_res_lookup"][time_resolution]["label"]  # e.g., 'by Era'
        ts_label = CONST["time_span_lookup"][time_span]["label"]  # e.g., 'Annual' or 'Monthly'
    except KeyError as E:
        app.logger.warning(
            f"Bad data from selectors: time_resolution {time_resolution}, time_span {time_span}. {E}"
        )
        raise PreventUpdate

    datastore: Datastore() = Datastore.from_json(data_store, params.ex_roots)
    trans: pd.DataFrame = datastore.trans
    eras: pd.DataFrame = datastore.eras
    if time_resolution == "era" and len(eras) == 0:
        raise PreventUpdate  # TODO: better solution is, if eras isn't loaded, remove ERAS from the choices
    account_tree: ATree = datastore.account_tree
    unit = params.unit

    chart_fig: go.Figure = go.Figure(layout=chart_fig_layout)
    root_account_id: str = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = account_tree.get_children(root_account_id)

    for i, account in enumerate(selected_accounts):
        bar = make_bar(
                trans,
                account_tree,
                account,
                time_resolution,
                time_span,
                eras,
                i,
                deep=True,
                unit=unit,
            )
        if bar:
            chart_fig.add_trace(bar)

    ts_title = f"Average {ts_label} {unit}, by {tr_label} "
    chart_fig.update_layout(
        title={"text": ts_title},
        xaxis={"showgrid": True, "nticks": 20},
        yaxis={"showgrid": True},
        barmode="relative",
    )
    return [chart_fig]


@app.callback(
    [
        Output("ex_selected_trans_display", "children"),
        Output("ex_time_series_selection_info", "data"),
        Output("ex_account_burst", "figure"),
        Output("ex_burst_title", "children"),
    ],
    [
        Input("ex_master_time_series", "figure"),
        Input("ex_master_time_series", "selectedData"),
    ],
    state=[
        State("ex_time_series_resolution", "value"),
        State("ex_time_series_span", "value"),
        State("data_store", "children"),
        State("param_store", "children"),
    ],
)
def apply_selection_from_time_series(
    figure, selectedData, time_resolution, time_span, data_store, param_store
):
    """
    Selecting specific points from the time series chart updates the
    account burst and the detail labels.
    Reminder to self: When you think selectedData input is broken, remember
    that unaltered default action in the graph is to zoom, not to select.
    Note: all of the necessary information is in figure but that doesn't seem
    to trigger reliably.  Adding selectedData as a second Input causes reliable
    triggering.
    """
    datastore: Datastore() = Datastore.from_json(data_store)
    preventupdate_if_empty(datastore)
    params: Params() = Params.from_json(param_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    if not time_span:
        time_span = params.init_time_span
    trans = datastore.trans
    eras = datastore.eras
    account_tree = datastore.account_tree
    unit = params.unit

    try:
        return trans_to_burst(
            account_tree, eras, figure, time_resolution, time_span, trans, unit
        )
    except LError as E:
        app.logger.warning(f'Failed to generate sunburst.  Error: {E}')
        raise PreventUpdate


@app.callback(
    [
        Output("ex_trans_table", "data"),
        Output("ex_selected_account_text", "children"),
        Output("ex_trans_table_text", "children"),
    ],
    [
        Input("ex_account_burst", "clickData"),
        Input("ex_account_burst", "figure"),

    ],
    state=[State("ex_time_series_selection_info", "data"),
           State("data_store", "children")]
)
def apply_burst_click(burst_clickData, burst_figure, time_series_info, data_store):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions
    Burst_figure is not used for anything but is present to guarantee a trigger on initial page load.
    """
    datastore: Datastore() = Datastore.from_json(data_store)
    preventupdate_if_empty(datastore)
    trans = datastore.trans
    preventupdate_if_empty(trans)
    account_tree = datastore.account_tree
    earliest_trans = datastore.earliest_trans
    latest_trans = datastore.latest_trans

    date_start: np.datetime64 = pd.to_datetime(
        time_series_info.get("start", earliest_trans)
    )
    date_end: np.datetime64 = pd.to_datetime(time_series_info.get("end", latest_trans))
    max_trans_count = time_series_info.get("count", 0)

    sub_accounts: list = []

    # Figure out which account(s) were selected in the sunburst click
    if burst_clickData:
        click_account = burst_clickData["points"][0]["id"]
        # strip any SUFFFIXes from the label that were added in the sunburst hack
        if CONST["leaf_suffix"] in click_account:
            revised_id = click_account.replace(CONST["leaf_suffix"], "")
        elif CONST["subtotal_suffix"] in click_account:
            revised_id = click_account.replace(CONST["subtotal_suffix"], "")
        else:
            revised_id = click_account
    else:
        revised_id = []

    # if any accounts are selected, get those transactions.  Otherwise, get all transactions.

    if revised_id:
        # Add any sub-accounts
        sub_accounts = account_tree.get_descendents(revised_id)
        filter_accounts = [revised_id] + sub_accounts
        sel_trans = trans[trans["account"].isin(filter_accounts)]
        if (len_sub := len(sub_accounts)) > 0:
            account_text = f"{revised_id} and {len_sub} sub-accounts selected"
        else:
            account_text = f"{revised_id} selected"
    else:

        sel_trans = trans
        account_text = f"Click a pie slice to filter from {max_trans_count} records"

    try:
        sel_trans = sel_trans[
            (sel_trans["date"] >= date_start) & (sel_trans["date"] <= date_end)
        ]
    except (KeyError, TypeError):
        pass
    sel_trans["date"] = pd.DatetimeIndex(sel_trans["date"]).strftime("%Y-%m-%d")
    sel_trans = sel_trans.sort_values(["date"])

    ex_trans_table_text: str = f"{len(sel_trans)} records"
    return [sel_trans.to_dict("records"), account_text, ex_trans_table_text]
