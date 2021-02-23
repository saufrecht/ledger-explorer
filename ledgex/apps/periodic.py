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
from ledgex.burst import Burst
from ledgex.params import CONST, Params
from ledgex.utils import (
    chart_fig_layout,
    pe_trans_table,
    make_bar,
    period_to_date_range,
    pretty_date,
    preventupdate_if_empty,
    LError,
)
from ledgex.datastore import Datastore


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                dcc.Graph(id="pe_master_time_series"),
                html.Div(
                    className="control_bar",
                    children=[
                        dcc.Store(
                            id="pe_time_series_selection_info", storage_type="memory"
                        ),
                        html.Div(id="pe_selected_trans_display", children=None),
                        html.Fieldset(
                            className="flpe_forward radio",
                            children=[
                                html.Span(children="Group By "),
                                dcc.RadioItems(
                                    id="pe_time_series_resolution",
                                    options=CONST["time_res_options"],
                                ),
                            ],
                        ),
                        html.Fieldset(
                            className="flpe_forward radio",
                            children=[
                                dcc.RadioItems(
                                    id="pe_time_series_span",
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
                        html.H3(id="pe_burst_title", children=""),
                        html.Div(
                            id="pe_selected_account_text",
                            children="Click a pie slice to filter records",
                        ),
                    ]
                ),
                dcc.Graph(id="pe_account_burst"),
            ],
        ),
        html.Div(
            className="detail_time_series_box",
            children=[
                dcc.Graph(id="pe_detail_time_series"),
            ],
        ),
        html.Div(
            className="trans_table_box",
            children=[
                html.Div(id="pe_trans_table_text", children=""),
                pe_trans_table,
            ],
        ),
    ],
)


@app.callback(
    [
        Output("pe_time_series_resolution", "value"),
        Output("pe_time_series_resolution", "options"),
        Output("pe_time_series_span", "value"),
    ],
    [Input("pe_tab_trigger", "children")],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def load_pe_params(trigger: str, data_store: str, param_store: str):
    """ When the param store changes and this tab is visible, update the top params"""
    preventupdate_if_empty(param_store)
    params = Params(**json.loads(param_store))
    options = CONST["time_res_options"]
    if data_store:
        data: Datastore() = Datastore.from_json(data_store)
        eras = data.eras
        if len(eras) > 0:
            options = [CONST["time_res_era_option"]] + options

    return [params.init_time_res, options, params.init_time_span]


@app.callback(
    [Output("pe_master_time_series", "figure")],
    [
        Input("pe_time_series_resolution", "value"),
        Input("pe_time_series_span", "value"),
    ],
    state=[State("data_store", "children"), State("param_store", "children")],
)
def pe_make_time_series(
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
        ts_label = CONST["time_span_lookup"][time_span][
            "label"
        ]  # e.g., 'Annual' or 'Monthly'
    except KeyError as E:
        app.logger.warning(
            f"Bad data from selectors: time_resolution {time_resolution}, time_span {time_span}. {E}"
        )
        raise PreventUpdate

    data_store: Datastore() = Datastore.from_json(data_store, params.pe_roots)
    trans: pd.DataFrame = data_store.trans
    eras: pd.DataFrame = data_store.eras
    if time_resolution == "era" and len(eras) == 0:
        raise PreventUpdate  # TODO: better solution is, if eras isn't loaded, remove ERAS from the choices
    account_tree: ATree = data_store.account_tree
    unit = params.unit

    chart_fig: go.Figure = go.Figure(layout=chart_fig_layout)
    root_account_id: str = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = account_tree.get_children_ids(root_account_id)

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
        Output("pe_account_burst", "figure"),
        Output("pe_burst_title", "children"),
        Output("pe_selected_trans_display", "children"),
        Output("pe_time_series_selection_info", "data"),
    ],
    [
        Input("pe_master_time_series", "figure"),
        Input("pe_master_time_series", "selectedData"),
    ],
    state=[
        State("pe_time_series_resolution", "value"),
        State("pe_time_series_span", "value"),
        State("data_store", "children"),
        State("param_store", "children"),
    ],
)
def pe_time_series_selection_to_sunburst_and_transaction_table(
    figure, selectedData, time_resolution, time_span, data_store, param_store
):
    """Selecting specific points from the time series chart updates the
    account burst and the detail labels.  Reminder to self: When you
    think selectedData input is broken, remember that unaltered
    default action in the graph is to zoom, not to select.

    Note: all of the necessary information is in figure but that
    doesn't seem to trigger reliably.  Adding selectedData as a second
    Input causes reliable triggering.

    TODO: BUG: The starting point of an Era- or Decade-wide object is
    not applied when clicked on

    TODO: UX BUG: By default, the sunburst has little to no Expenses,
    because Expenses is by default negative value.  The only way to
    see negative expenses in the sunburst is to select a net-negative
    set of data, in which case (the Ledger Explorer implementation of)
    sunburst flips sign.  I.e., the user must first click on an
    Expenses column in the time series, which will cause the burst to
    be net-negative, which will flip it to positive, which will cause
    it to display as expected.  Possible solution: limit the burst to
    a single parent account (not root)?

    """
    params: Params() = Params.from_json(param_store)
    data_store: Datastore() = Datastore.from_json(data_store, params.pe_roots)
    preventupdate_if_empty(data_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    if not time_span:
        time_span = params.init_time_span
    trans = data_store.trans
    if len(trans) == 0:
        app.logger.error(
            "Tried to make burst figure from transactions, but no transactions provided."
        )
        raise PreventUpdate()
    eras = data_store.eras
    account_tree = data_store.account_tree
    unit = params.unit

    tr_label = CONST["time_res_lookup"].get(time_resolution)["label"]
    ts_label = CONST["time_span_lookup"].get(time_span)["label"]
    min_period_start: np.datetime64 = None
    max_period_end: np.datetime64 = None
    selected_accounts = []
    selected_trans = pd.DataFrame()
    desc_account_count = 0
    colormap = {}

    # Get the names and colors of all accounts in the Input figure.
    # If anything is clicked, set the selection dates, accounts, and transactions.
    if figure:
        for trace in figure.get("data"):
            account = trace.get("name")
            points = trace.get("selectedpoints")
            colormap[account] = trace.get("marker").get("color")
            if not points:
                continue
            selected_accounts.append(account)
            for point in points:
                point_x = trace["x"][point]
                period_start, period_end = period_to_date_range(
                    tr_label, ts_label, point_x, eras
                )
                if min_period_start is None:
                    min_period_start = period_start
                else:
                    min_period_start = min(min_period_start, period_start)
                if max_period_end is None:
                    max_period_end = period_end
                else:
                    max_period_end = max(max_period_end, period_end)
                desc_accounts = account_tree.get_descendents(account)
                desc_account_count = desc_account_count + len(desc_accounts)
                subtree_accounts = [account] + desc_accounts
                new_trans = (
                    trans.loc[trans["account"].isin(subtree_accounts)]
                    .loc[trans["date"] >= period_start]
                    .loc[trans["date"] <= period_end]
                )
                if len(selected_trans) > 0:
                    selected_trans = selected_trans.append(new_trans)
                else:
                    selected_trans = new_trans
    selected_count = len(selected_trans)

    if selected_count > 0 and len(selected_accounts) > 0:
        # If there are selected data, describe the contents of the sunburst
        # TODO: desc_account_count is still wrong.
        description = Burst.pretty_account_label(
            selected_accounts,
            desc_account_count,
            min_period_start,
            max_period_end,
            selected_count,
        )
    else:
        # If no trans are selected, show everything.  Note that we
        # could logically get here even if valid accounts are
        # seleceted, in which case it would be confusing to get back
        # all trans instead of none, but this should never happen haha
        # because any clickable bar must have $$, and so, trans
        description = f"Click a bar in the graph to filter from {len(trans):,d} records"
        selected_trans = trans
        min_period_start = trans["date"].min()
        max_period_end = trans["date"].max()

    title = f"Average {ts_label} {unit} from {pretty_date(min_period_start)} to {pretty_date(max_period_end)}"
    time_series_selection_info = {
        "start": min_period_start,
        "end": max_period_end,
        "count": len(selected_trans),
    }

    try:
        sun_fig = Burst.from_trans(account_tree, selected_trans, time_span, colormap)
    except LError as E:
        app.logger.warning(f"Failed to generate sunburst.  Error: {E}")
        raise PreventUpdate

    return (sun_fig, title, description, time_series_selection_info)


@app.callback(
    [
        Output("pe_trans_table", "data"),
        Output("pe_selected_account_text", "children"),
        Output("pe_trans_table_text", "children"),
        Output("pe_detail_time_series", "figure"),
    ],
    [
        Input("pe_account_burst", "clickData"),
        Input("pe_account_burst", "figure"),
    ],
    state=[
        State("pe_time_series_selection_info", "data"),
        State("data_store", "children"),
        State("param_store", "children"),
        State("pe_time_series_resolution", "value"),
        State("pe_time_series_span", "value"),
    ],
)
def apply_burst_click(
    burst_clickData,
    burst_figure,
    time_series_info,
    data_store: str,
    param_store: str,
    time_resolution: int,
    time_span: str,
):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions
    burst_figure Input is used only to guarantee a trigger on initial page load.
    """
    data_store: Datastore() = Datastore.from_json(data_store)
    preventupdate_if_empty(data_store)
    preventupdate_if_empty(time_series_info)
    trans = data_store.trans
    preventupdate_if_empty(trans)
    account_tree = data_store.account_tree
    earliest_trans = data_store.earliest_trans
    latest_trans = data_store.latest_trans

    date_start: np.datetime64 = pd.to_datetime(
        time_series_info.get("start", earliest_trans)
    )
    date_end: np.datetime64 = pd.to_datetime(time_series_info.get("end", latest_trans))
    max_trans_count = time_series_info.get("count", 0)

    sub_accounts: list = []

    # Figure out which account(s) were selected in the sunburst click
    if burst_clickData:
        raw_click_account = burst_clickData["points"][0]["id"]
        # strip any SUFFFIXes from the label that were added in the sunburst hack
        if CONST["leaf_suffix"] in raw_click_account:
            click_account = raw_click_account.replace(CONST["leaf_suffix"], "")
        elif CONST["subtotal_suffix"] in raw_click_account:
            click_account = raw_click_account.replace(CONST["subtotal_suffix"], "")
        else:
            click_account = raw_click_account
    else:
        click_account = []

    # if an accounts was clicked, get a ledger of those transactions, and a detailed time series
    # chart of the clicked account.  Otherwise, get all transactions, and an empty chart.
    detail_fig: go.Figure = go.Figure(layout=chart_fig_layout)
    if click_account:
        # Add any sub-accounts
        sub_accounts = account_tree.get_descendents(click_account)
        filter_accounts = [click_account] + sub_accounts
        sel_trans = trans[trans["account"].isin(filter_accounts)]
        if (len_sub := len(sub_accounts)) > 0:
            account_text = f"{click_account} and {len_sub} sub-accounts selected"
        else:
            account_text = f"{click_account} selected"

        # also, build the detail chart for the primarily selected account
        params: Params() = Params.from_json(param_store)
        if not time_resolution:
            time_resolution = params.init_time_res
        if not time_span:
            time_span = params.init_time_span
        unit = params.unit
        eras: pd.DataFrame = data_store.eras
        try:
            tr_label = CONST["time_res_lookup"][time_resolution][
                "label"
            ]  # e.g., 'by Era'
            ts_label = CONST["time_span_lookup"][time_span][
                "label"
            ]  # e.g., 'Annual' or 'Monthly'
        except KeyError as E:
            app.logger.warning(
                f"Bad data from selectors: time_resolution {time_resolution}, time_span {time_span}. {E}"
            )
            raise PreventUpdate
        bar = make_bar(
            trans,
            account_tree,
            click_account,
            time_resolution,
            time_span,
            eras,
            0,
            deep=True,
            unit=unit,
        )
        if bar:
            detail_fig.add_trace(bar)
            ts_title = f"Average {ts_label} {click_account} {unit}, by {tr_label} "
            detail_fig.update_layout(
                title={"text": ts_title},
                xaxis={"showgrid": True, "nticks": 20},
                yaxis={"showgrid": True},
                barmode="relative",
            )
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

    pe_trans_table_text: str = f"{len(sel_trans)} records"

    return [sel_trans.to_dict("records"), account_text, pe_trans_table_text, detail_fig]
