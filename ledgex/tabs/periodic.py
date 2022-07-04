import json

from dash import dcc, html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from app import app
from burst import Burst
from params import CONST, Params
from ledger import Ledger
from errors import LError
from utils import (
    layouts,
    pe_trans_table,
    periodic_bar,
    period_to_date_range,
    pretty_date,
    preventupdate_if_empty,
)
from datastore import Datastore


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                html.Div(
                    className="control_bar",
                    children=[
                        dcc.Store(id="pe_selection_store", storage_type="memory"),
                        html.Div(
                            className="control_group",
                            children=[
                                dcc.Dropdown(
                                    id="pe_time_series_span",
                                    options=CONST["time_span_options"],
                                    searchable=False,
                                ),
                                html.Span(id="pe_intra_text", children=" by "),
                                dcc.Dropdown(
                                    id="pe_time_series_resolution",
                                    options=CONST["time_res_options"],
                                    searchable=False,
                                ),
                            ]),
                        dcc.DatePickerRange(
                            id="pe_date_range",
                            display_format='YYYY-MM-DD',
                        ),
                    ],
                ),
                dcc.Graph(id="pe_master_time_series"),
            ],
        ),
        html.Div(
            className="account_burst_box",
            children=[
                html.H3(id="pe_burst_title", children=""),
                html.Div(
                    id="pe_burst_text",
                    children="Click a pie slice to filter records",
                ),
                dcc.Graph(id="pe_account_burst"),
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
        Output("pe_date_range", "start_date"),
        Output("pe_date_range", "end_date"),
    ],
    Input("pe_tab_trigger", "children"),
    State("data_store", "children"),
    State("param_store", "children"),
)
def pe_load_params(trigger: str, data_store: str, param_store: str):
    """ When the param store changes and this tab is visible, update the top params"""
    preventupdate_if_empty(param_store)
    params = Params(**json.loads(param_store))
    tr_options = CONST["time_res_options"]
    if data_store and len(Datastore.from_json(data_store).eras) > 0:
        tr_options = [CONST["time_res_era_option"]] + tr_options
    return [params.init_time_res, tr_options, params.init_time_span, params.start_date, params.end_date]


@app.callback(
    [Output("pe_master_time_series", "figure")],
    [
        Input("pe_time_series_resolution", "value"),
        Input("pe_time_series_span", "value"),
        Input("pe_date_range", "start_date"),
        Input("pe_date_range", "end_date"),
    ],
    State("data_store", "children"),
    State("param_store", "children"),
)
def pe_make_master_time_series(
    time_resolution: int, time_span: str, start_date: str, end_date: str, data_store: str, param_store: str
):
    """ Generate a Dash bar chart figure from transactional data """
    preventupdate_if_empty(data_store)
    params: Params = Params.from_json(param_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    if not time_span:
        time_span = params.init_time_span
    trans, atree, eras, dstore = Datastore.get_parts(data_store, params.pe_roots)
    unit = params.unit
    chart_fig: go.Figure = go.Figure(layout=layouts["periodic"])
    # get everything, remembering that it's already been pre-filtered by pe_roots
    root_account_id: str = atree.root
    selected_accounts = atree.get_children_ids(root_account_id)
    factor = Ledger.prorate_factor(time_span, ts_resolution=time_resolution)
    for i, account in enumerate(selected_accounts):
        try:
            bar = periodic_bar(
                trans,
                atree,
                account,
                time_resolution,
                time_span,
                factor,
                eras,
                i,
                deep=True,
                positize=True,
                unit=unit,
                sel_start_date=start_date,
                sel_end_date=end_date
            )
            if bar:
                chart_fig.add_trace(bar)
        except LError:
            pass
    return [chart_fig]


@app.callback(
    Output("pe_account_burst", "figure"),
    Output("pe_burst_title", "children"),
    Output("pe_burst_text", "children"),
    Output("pe_selection_store", "data"),
    Input("pe_master_time_series", "figure"),
    Input("pe_master_time_series", "selectedData"),
    State("pe_time_series_resolution", "value"),
    State("pe_time_series_span", "value"),
    State("data_store", "children"),
    State("param_store", "children"),
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

    """
    params: Params() = Params.from_json(param_store)
    preventupdate_if_empty(data_store)
    trans, atree, eras, dstore = Datastore.get_parts(data_store, params.pe_roots)
    if not time_resolution:
        time_resolution = params.init_time_res
    if not time_span:
        time_span = params.init_time_span
    if len(trans) == 0:
        app.logger.error(
            "Tried to make burst figure from transactions, but no transactions provided."
        )
        raise PreventUpdate()
    unit = params.unit

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
                    time_resolution, point_x, eras
                )
                if min_period_start is None:
                    min_period_start = period_start
                else:
                    min_period_start = min(min_period_start, period_start)
                if max_period_end is None:
                    max_period_end = period_end
                else:
                    max_period_end = max(max_period_end, period_end)
                desc_accounts = atree.get_descendent_ids(account)
                desc_account_count = desc_account_count + len(desc_accounts)
                subtree_accounts = [account] + desc_accounts
                new_trans = (
                    trans.loc[trans["account"].isin(subtree_accounts)]
                    .loc[trans["date"] >= period_start]
                    .loc[trans["date"] <= period_end]
                )
                new_trans = Ledger.positize(new_trans)  # each top-level account should net positive
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
            selected_count,
        )
    else:
        # If no trans are selected, show everything.  Note that we
        # could logically get here even if valid accounts are
        # selected, in which case it would be confusing to get back
        # all trans instead of none, but this should never happen haha
        # because any clickable bar must have $$, and so, trans
        description = f"Click a bar in the graph to filter from {len(trans):,d} records"
        selected_trans = trans
        min_period_start = trans["date"].min()
        max_period_end = trans["date"].max()

    title = f"{ts_label} {unit} from {pretty_date(min_period_start)} to {pretty_date(max_period_end)}"
    pe_selection_store = {
        "start": min_period_start,
        "end": max_period_end,
        "count": len(selected_trans),
        "accounts": selected_accounts,
    }

    duration = round(
        pd.to_timedelta((max_period_end - min_period_start), unit="ms")
        / np.timedelta64(1, "M")
    )
    factor = Ledger.prorate_factor(time_span, duration=duration)
    try:
        sun_fig = Burst.from_trans(
            atree, selected_trans, time_span, unit, factor, colormap, title
        )
    except LError as E:
        text = f"Failed to generate sunburst.  Error: {E}"
        app.logger.warning(text)
        description = text

    return (sun_fig, title, description, pe_selection_store)


@app.callback(
        Output("pe_trans_table", "data"),
        Output("pe_trans_table_text", "children"),
        Input("pe_account_burst", "clickData"),
        Input("pe_account_burst", "figure"),
        State("pe_selection_store", "data"),
        State("data_store", "children"),
        State("param_store", "children"),
        State("pe_time_series_resolution", "value"),
        State("pe_time_series_span", "value"),
)
def apply_burst_click(
    burst_clickData,
    burst_figure,
    pe_selection_store,
    data_store: str,
    param_store: str,
    time_resolution: int,
    time_span: str,
):
    """Clicking on a slice in the Sunburst updates the transaction list
    with matching transactions burst_figure Input is used only to
    guarantee a trigger on initial page load.

    """
    preventupdate_if_empty(data_store)
    preventupdate_if_empty(pe_selection_store)
    trans, atree, eras, dstore = Datastore.get_parts(data_store)
    preventupdate_if_empty(trans)
    earliest_trans = dstore.earliest_trans
    latest_trans = dstore.latest_trans

    # get the selection parameters from the master time series, via an intermediary store.
    date_start: np.datetime64 = pd.to_datetime(
        pe_selection_store.get("start", earliest_trans)
    )
    date_end: np.datetime64 = pd.to_datetime(
        pe_selection_store.get("end", latest_trans)
    )
    max_trans_count: int = pe_selection_store.get("count", 0)
    click_accounts: list = pe_selection_store.get("accounts", [])

    # Figure out which accounts to use to filter transactions.  If any
    # account(s) were selected in the sunburst click, they override
    # the selection passed through from master_time_series
    if burst_clickData:
        raw_click_account = burst_clickData["points"][0]["id"]
        # strip any SUFFFIXes from the label that were added in the sunburst hack
        if CONST["leaf_suffix"] in raw_click_account:
            click_accounts = [raw_click_account.replace(CONST["leaf_suffix"], "")]
        elif CONST["subtotal_suffix"] in raw_click_account:
            click_accounts = [raw_click_account.replace(CONST["subtotal_suffix"], "")]
        else:
            click_accounts = [raw_click_account]

    if len(click_accounts) > 0:
        sub_accounts: list = []
        for account in click_accounts:
            sub_accounts = atree.get_descendent_ids(account)
        sel_accounts = click_accounts + sub_accounts
        sel_trans = trans[
            trans["account"].isin(sel_accounts)
            & (trans["date"] >= date_start)
            & (trans["date"] <= date_end)
        ]
        num_trans = len(sel_trans)
        account_text = f"{num_trans} selected for {', '.join(click_accounts)}"
        if (len_sub := len(sub_accounts)) > 0:
            account_text = account_text + f" and {len_sub} sub-accounts"
    else:
        sel_trans = trans
        num_trans = len(sel_trans)
        account_text = f"All accounts selected. Click a pie slice to filter from {max_trans_count} records"

    sel_trans["date"] = pd.DatetimeIndex(sel_trans["date"]).strftime("%Y-%m-%d")
    sel_trans = sel_trans.sort_values(["date"])

    return [sel_trans.to_dict("records"), account_text]
