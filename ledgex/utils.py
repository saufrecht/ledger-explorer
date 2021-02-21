from typing import Dict, List, Tuple

from datetime import datetime, timedelta
import calendar

import dash_table
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate

from ledgex.app import app
from ledgex.atree import ATree
from ledgex.params import CONST

pd.options.mode.chained_assignment = (
    None  # default='warn'  This suppresses the invalid warning for the .map function
)


class LError(Exception):
    """ Base class for package errors"""


class LoadError(LError):
    """ Errors during transaction, Account Tree, and Eras data load """

    def __init__(self, message):
        self.message = message


disc_colors = px.colors.qualitative.D3

fonts = dict(
    big=dict(family="IBM Plex Sans Medium", size=24),
    medium=dict(family="IBM Plex Sans Light", size=20),
    small=dict(family="IBM Plex Light", size=12),
)

time_series_layout = dict(
    legend={"x": 0, "y": 1}, font=fonts["small"], titlefont=fonts["medium"]
)

chart_fig_layout = dict(
    clickmode="event+select",
    dragmode="select",
    margin=dict(l=10, r=10, t=10, b=10),  # NOQA
    height=350,
    showlegend=False,
    title=dict(font=fonts["big"], x=0.1, y=0.9),
    hoverlabel=dict(bgcolor="var(--bg)", font_color="var(--fg)", font=fonts["medium"]),
)


trans_table = dash_table.DataTable(
    id="trans_table",
    columns=[
        dict(id="date", name="Date", type="datetime"),
        dict(id=CONST["account_col"], name="Account"),
        dict(id="description", name="Description"),
        dict(id="amount", name="Amount", type="numeric"),
    ],
    style_header={
        "font-family": "IBM Plex Sans, Verdana, sans",
        "font-weight": "600",
        "text-align": "center",
    },
    style_cell={
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "backgroundColor": "var(--bg)",
        "border": "none",
        "maxWidth": 0,
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "var(--bg-more)"},
    ],
    style_cell_conditional=[
        {
            "if": {"column_id": "date"},
            "textAlign": "left",
            "padding": "0px 10px",
            "width": "20%",
        },
        {
            "if": {"column_id": CONST["account_col"]},
            "textAlign": "left",
            "padding": "0px px",
            "width": "18%",
        },
        {
            "if": {"column_id": "description"},
            "textAlign": "left",
            "padding": "px 2px 0px 3px",
        },
        {"if": {"column_id": "amount"}, "padding": "0px 12px 0px 0px", "width": "13%"},
    ],
    data=[],
    sort_action="native",
    page_action="native",
    filter_action="native",
    style_as_list_view=True,
    page_size=20,
)


# TODO: replace with class or something; I guess put all this in __init__?
bs_trans_table = dash_table.DataTable(
    id="bs_trans_table",
    columns=[
        dict(id="date", name="Date", type="datetime"),
        dict(id=CONST["account_col"], name="Account"),
        dict(id="description", name="Description"),
        dict(id="amount", name="Amount", type="numeric"),
        dict(id="total", name="Total", type="numeric"),
    ],
    style_header={
        "font-family": "IBM Plex Sans, Verdana, sans",
        "font-weight": "600",
        "text-align": "center",
    },
    style_cell={
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "backgroundColor": "var(--bg)",
        "border": "none",
        "maxWidth": 0,
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "var(--bg-more)"},
    ],
    style_cell_conditional=[
        {
            "if": {"column_id": "date"},
            "textAlign": "left",
            "padding": "0px 10px",
            "width": "20%",
        },
        {
            "if": {"column_id": CONST["account_col"]},
            "textAlign": "left",
            "padding": "0px px",
            "width": "18%",
        },
        {
            "if": {"column_id": "description"},
            "textAlign": "left",
            "padding": "px 2px 0px 3px",
        },
        {"if": {"column_id": "amount"}, "padding": "0px 12px 0px 0px", "width": "11%"},
        {"if": {"column_id": "total"}, "padding": "0px 12px 0px 0px", "width": "11%"},
    ],
    data=[],
    sort_action="native",
    page_action="native",
    filter_action="native",
    style_as_list_view=True,
    page_size=20,
)


pe_trans_table = dash_table.DataTable(
    id="pe_trans_table",
    columns=[
        dict(id="date", name="Date", type="datetime"),
        dict(id=CONST["account_col"], name="Account"),
        dict(id="description", name="Description"),
        dict(id="amount", name="Amount", type="numeric"),
    ],
    style_header={
        "font-family": "IBM Plex Sans, Verdana, sans",
        "font-weight": "600",
        "text-align": "center",
    },
    style_cell={
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "backgroundColor": "var(--bg)",
        "border": "none",
        "maxWidth": 0,
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "var(--bg-more)"},
    ],
    style_cell_conditional=[
        {
            "if": {"column_id": "date"},
            "textAlign": "left",
            "padding": "0px 10px",
            "width": "20%",
        },
        {
            "if": {"column_id": CONST["account_col"]},
            "textAlign": "left",
            "padding": "0px px",
            "width": "18%",
        },
        {
            "if": {"column_id": "description"},
            "textAlign": "left",
            "padding": "px 2px 0px 3px",
        },
        {"if": {"column_id": "amount"}, "padding": "0px 12px 0px 0px", "width": "13%"},
    ],
    data=[],
    sort_action="native",
    page_action="native",
    filter_action="native",
    style_as_list_view=True,
    page_size=20,
)


trans_table_format = dict(
    columns=[
        dict(id="date", name="Date", type="datetime"),
        dict(id=CONST["account_col"], name="Account"),
        dict(id="description", name="Description"),
        dict(id="amount", name="Amount", type="numeric"),
        dict(id="total", name="Total", type="numeric"),
    ],
    style_header={
        "font-family": "IBM Plex Sans, Verdana, sans",
        "font-weight": "600",
        "text-align": "center",
    },
    style_cell={
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "backgroundColor": "var(--bg)",
        "border": "none",
        "maxWidth": 0,
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "var(--bg-more)"},
    ],
    style_cell_conditional=[
        {
            "if": {"column_id": "date"},
            "textAlign": "left",
            "padding": "0px 10px",
            "width": "20%",
        },
        {
            "if": {"column_id": CONST["account_col"]},
            "textAlign": "left",
            "padding": "0px px",
            "width": "18%",
        },
        {
            "if": {"column_id": "description"},
            "textAlign": "left",
            "padding": "px 2px 0px 3px",
        },
        {"if": {"column_id": "amount"}, "padding": "0px 12px 0px 0px", "width": "11%"},
        {"if": {"column_id": "total"}, "padding": "0px 12px 0px 0px", "width": "11%"},
    ],
    data=[],
    sort_action="native",
    page_action="native",
    filter_action="native",
    style_as_list_view=True,
    page_size=20,
)


def period_to_date_range(
    tr_label: str, ts_label: str, period: str, eras: pd.DataFrame
) -> Tuple[np.datetime64, np.datetime64]:

    # Convert period label to tuple of start and end dates, based on tr_label

    def _month_end(date: np.datetime64) -> np.datetime64:
        # return the date of the last day of the month of the input date
        year = date.year
        month = date.month
        last_day = calendar.monthrange(year, month)[1]
        end_date = np.datetime64(datetime(year=year, month=month, day=last_day))
        return end_date

    if tr_label == "Era":
        era = eras.loc[(eras["date_start"] < period) & (eras["date_end"] > period)]
        period_start = era["date_start"][0]
        period_end = era["date_end"][0]
    if tr_label == "Decade":
        period_start = datetime(int(period.year / 10) * 10, 1, 1)
        period_end = datetime(int(((period.year / 10) + 1) * 10) - 1, 12, 31)
    elif tr_label == "Year":
        period_start = datetime(int(period), 1, 1)
        period_end = datetime(int(period), 12, 31)
    elif tr_label == "Quarter":
        try:
            year: int = int(period[0:4])
        except ValueError:
            raise LError("Internal error while trying to convert year to date.")
        try:
            Q: int = int(period[6:7])
        except ValueError:
            raise LError("Internal error while trying to convert quarter to date.")
        start_month: int = (Q * 3) - 2
        period_start = datetime(year, start_month, 1)
        period_end = _month_end(period_start + timedelta(days=63))
    elif tr_label == "Month":
        period_start = datetime.strptime(period + "-01", "%Y-%b-%d")
        period_end = _month_end(period_start)
    else:
        raise LError(
            "Internal error: {tr_label} is not Era, Decade, Year, Quarter, or Month"
        )
    return (np.datetime64(period_start), np.datetime64(period_end))


def pretty_date(date: np.datetime64) -> str:
    """ convert Numpy datetime64 to 'YYYY-MMM-DD' """
    return pd.to_datetime(str(date)).strftime("%Y-%m-%d")


def preventupdate_if_empty(field: object):
    """ Shorthand to halt callbacks if data missing"""
    if isinstance(field, pd.DataFrame):
        if len(field) == 0:
            raise PreventUpdate
    elif not field:
        raise PreventUpdate
    elif len(field) == 0:
        raise PreventUpdate
    else:
        return


def make_bar(
    trans: pd.DataFrame,
    account_tree: ATree,
    account_id: str,
    time_resolution: str,
    time_span: str,
    eras: pd.DataFrame,
    color_num: int = 0,
    deep: bool = False,
    unit: str = CONST["unit"],
) -> go.Bar:
    """returns a go.Bar object with total by time_resolution period for
    the selected account.  If deep, include total for all descendent accounts."""
    if deep:
        tba = trans[
            trans[CONST["account_col"]].isin(
                [account_id] + account_tree.get_descendents(account_id)
            )
        ]
    else:
        tba = trans[trans[CONST["account_col"]] == account_id]
    tba = tba.set_index("date")
    tr: dict = CONST["time_res_lookup"][time_resolution]
    tr_hover: str = tr.get("abbrev", None)  # e.g., "Q"
    tr_label: str = tr.get("label", None)  # e.g., "Quarter"
    tr_months: int = tr.get("months", None)  # e.g., 3
    tr_format: str = tr.get("format", None)  # e.g., %Y-%m

    ts = CONST["time_span_lookup"][time_span]
    ts_hover = ts.get("abbrev")  # NOQA  e.g., "y"
    ts_months = ts.get("months")  # e.g., 12

    trace_type: str = "periodic"
    if tr_label == "Era":
        if len(eras) > 0:
            trace_type = "era"
        else:
            trace_type = "total"
    elif tr_label in ["Decade", "Year", "Quarter", "Month"]:
        format = tr_format
    else:
        raise PreventUpdate  # ibid

    try:
        marker_color = disc_colors[color_num]
    except IndexError:
        # don't ever run out of colors
        marker_color = "var(--Cyan)"
    if trace_type == "periodic":
        resample_keyword = tr["resample_keyword"]
        bin_amounts = (
            tba.resample(resample_keyword).sum()["amount"].to_frame(name="value")
        )
        factor = ts_months / tr_months
        bin_amounts["x"] = bin_amounts.index.to_period().strftime(format)
        bin_amounts["y"] = bin_amounts["value"] * factor
        bin_amounts["text"] = f"{tr_hover}"
        bin_amounts["customdata"] = account_id
        bin_amounts[
            "texttemplate"
        ] = "%{customdata}"  # workaround for passing variables through layers of plotly
        trace = go.Bar(
            name=account_id,
            x=bin_amounts.x,
            y=bin_amounts.y,
            customdata=bin_amounts.customdata,
            text=bin_amounts.text,
            texttemplate=bin_amounts.texttemplate,
            textposition="auto",
            opacity=0.9,
            hovertemplate="%{x}<br>%{customdata}:<br>%{y:$,.0f}<br>",  # TODO: pass in unit for $
            marker_color=marker_color,
        )
    elif trace_type == "era":
        latest_tba = tba.index.max()
        # convert the era dates to a series that can be used for grouping
        bins = eras.date_start.sort_values()
        bin_boundary_dates = bins.tolist()
        bin_labels = bins.index.tolist()
        # there must be one more bin boundary than label, so:
        if bin_boundary_dates[-1] <= latest_tba:
            # if there's going to be any data in the last bin, add a final boundary
            bin_boundary_dates = bin_boundary_dates + [latest_tba]
        else:
            # otherwise, lose its label, leaving its start as the final boundary of the previous
            bin_labels = bin_labels[0:-1]
        try:
            tba["bin"] = pd.cut(
                x=tba.index,
                bins=bin_boundary_dates,
                labels=bin_labels,
                duplicates="drop",
            )
        except ValueError as E:
            app.logger.warning(
                "An error making the bins for eras.  Probably because of design errors"
                + f" in how eras are parsed and loaded: {E}"
            )
            return None
        bin_amounts = pd.DataFrame(
            {
                "date": bin_boundary_dates[0:-1],
                "value": tba.groupby("bin")["amount"].sum(),
            }
        )
        bin_amounts["date_start"] = bin_boundary_dates[0:-1]
        bin_amounts["date_end"] = bin_boundary_dates[1:]
        # Plotly bars want the midpoint and width:
        bin_amounts["delta"] = bin_amounts["date_end"] - bin_amounts["date_start"]
        bin_amounts["width"] = bin_amounts["delta"] / np.timedelta64(1, "ms")
        bin_amounts["midpoint"] = bin_amounts["date_start"] + bin_amounts["delta"] / 2
        bin_amounts["months"] = bin_amounts["delta"] / np.timedelta64(1, "M")
        bin_amounts["value"] = bin_amounts["value"] * (
            ts_months / bin_amounts["months"]
        )
        bin_amounts["text"] = account_id
        bin_amounts["customdata"] = (
            bin_amounts["text"]
            + "<br>"
            + bin_amounts.index.astype(str)
            + "<br>("
            + bin_amounts["date_start"].astype(str)
            + " to "
            + bin_amounts["date_end"].astype(str)
            + ")"
        )
        trace = go.Bar(
            name=account_id,
            x=bin_amounts.midpoint,
            width=bin_amounts.width,
            y=bin_amounts.value,
            customdata=bin_amounts.customdata,
            text=bin_amounts.text,
            textposition="auto",
            opacity=0.9,
            texttemplate="%{text}<br>%{value:$,.0f}",  # TODO: pass in unit for $
            hovertemplate="%{customdata}<br>%{value:$,.0f}",  # TODO: pass in unit for $
            marker_color=marker_color,
        )
    else:
        return None
    return trace


def make_cum_area(
    trans: pd.DataFrame, account_id: str, color_num: int = 0, time_resolution: int = 0
) -> go.Scatter:
    """returns an object with cumulative total by time_resolution period for
    the selected account."""

    tr = CONST["time_res_lookup"][time_resolution]
    resample_keyword = tr["resample_keyword"]
    trans = trans.set_index("date")

    bin_amounts = trans.resample(resample_keyword).sum().cumsum()
    bin_amounts["date"] = bin_amounts.index
    bin_amounts["value"] = bin_amounts["amount"]
    bin_amounts["label"] = account_id
    try:
        marker_color = disc_colors[color_num]
    except IndexError:
        # don't ever run out of colors
        marker_color = "var(--Cyan)"
    bin_amounts[
        "texttemplate"
    ] = "%{customdata}"  # workaround for passing variables through layers of plotly
    scatter = go.Scatter(
        x=bin_amounts["date"],
        y=bin_amounts["value"],
        name=account_id,
        mode="lines+markers",
        marker={"symbol": "circle", "opacity": 1, "color": marker_color},
        customdata=bin_amounts["label"],
        hovertemplate="%{customdata}<br>%{y:$,.0f}<br>%{x}<extra></extra>",  # TODO: pass in unit for $
        line={"width": 0.5, "color": marker_color},
        hoverlabel={"namelength": 15},
        stackgroup="one",
    )

    return scatter


def make_scatter(account_id: str, trans: pd.DataFrame, color_num: int = 0):
    """returns scatter trace of input transactions"""

    trace = go.Scatter(
        name=account_id,
        x=trans["date"],
        y=trans["amount"],
        text=trans[CONST["account_col"]],
        ids=trans.index,
        mode="markers",
        marker=dict(symbol="circle"),
    )
    return trace


def make_sunburst(
    trans: pd.DataFrame,
    time_span: str,
    date_start: np.datetime64 = None,
    date_end: np.datetime64 = None,
    subtotal_suffix: str = CONST["subtotal_suffix"],
    colormap: Dict = {},
):
    """
    Using a tree of accounts and a DataFrame of transactions,
    generate a figure for a sunburst, where each node is an account
    in the tree, and the value of each node is the subtotal of all
    transactions for that node and any subtree, filtered by date.
    """

    #######################################################################
    # Set up a new tree with totals based on date-filtered transactions
    #######################################################################
    if not date_start:
        date_start = trans["date"].min()
    if not date_end:
        date_end = pd.Timestamp.now()

    ts = CONST["time_span_lookup"][time_span]
    ts_months = ts.get("months")  # e.g., 12

    duration_m = pd.to_timedelta((date_end - date_start), unit="ms") / np.timedelta64(
        1, "M"
    )
    sel_trans = trans[(trans["date"] >= date_start) & (trans["date"] <= date_end)]
    # TODO: if the time series has, e.g., income and expenses,
    # positizing this way effectively removes the expenses, because
    # they are negative.  Might be better to show both in the
    # sunburst, even though this puts positive values next to reversed
    # negative values (e.g., earn 20, spend 10, net is 10, but
    # sunburst shows (10 + -(-20) = 30?!), because more data would be browsable that
    # way.  Could reverse with flip_negative CONST, and color coding
    # the reversed negatives to reduce confusion ??
    sel_trans = positize(sel_trans)

    def make_subtotal_tree(trans, prorate_months):
        """
        Calculate the subtotal for each node (direct subtotal only, no children) in
        the provided transaction tree and store it in the tree.
        """
        trans = trans.reset_index(drop=True).set_index(CONST["account_col"])
        sel_tree = ATree.from_names(trans[CONST["fan_col"]])
        subtotals = trans.groupby(CONST["account_col"]).sum()["amount"]
        for node in sel_tree.all_nodes():
            try:
                subtotal = subtotals.loc[node.tag]
            except KeyError:
                # These should be nodes without leaf_totals, and therefore
                # not present in the subtotals DataFrame
                continue

            try:
                norm_subtotal = round(subtotal * ts_months / duration_m)
            except OverflowError:
                norm_subtotal = 0
            if norm_subtotal < 0:
                norm_subtotal = 0
            node.data = {"leaf_total": norm_subtotal}

        return sel_tree

    _sun_tree = make_subtotal_tree(sel_trans, ts_months)

    #######################################################################
    # Total up all the nodes.
    #######################################################################
    # sunburst is very very finicky and wants the subtotals to be
    # exactly correct and never missing, so build them directly from
    # the leaf totals to avoid floats, rounding, and other fatal problems.
    #
    # If a leaf_total is moved out of a subtotal, there
    # has to be a way to differentiate between clicking
    # on the sub-total and clicking on the leaf.  Do this by
    # appending a magic string to the id of the leaf.
    # Then, use the tag as the key to transaction.account.
    # This will cause the parent tag, 'XX Subtotal', to fail matches, and
    # the child, which is labeled 'XX Leaf' but tagged 'XX' to match.

    # BEFORE                          | AFTER
    # id   parent   tag  leaf_total   | id       parent   tag          leaf_total    total
    # A             A            50   | A                 A Subtotal                    72
    # B    A        B            22   | A Leaf   A        A                    50       50
    #                                 | B        A        B                    22       22

    def set_node_total(node):
        """
        Set the total value of the node as a property of the node.  Assumes
        a _sun_tree Tree in surrounding scope, and modifies that
        treelib as a side effect.

        Assumption: No negative leaf values

        Uses 'leaf_total' for all transactions that belong to this node's account,
        and 'total' for the final value for the node, including descendents.
        """
        nonlocal _sun_tree
        node_id = node.identifier
        tag = node.tag
        try:
            leaf_total = node.data.get("leaf_total", 0)
        except AttributeError:
            # in case it doesn't even have a data node
            leaf_total = 0
        running_subtotal = leaf_total

        children = _sun_tree.children(node_id)

        if children:
            # if it has children, rename it to subtotal, but
            # don't change the identity.  Don't do this for
            # the root node, which doesn't need a rename
            # and will look worse if it gets one
            if node_id != _sun_tree.ROOT_ID:
                subtotal_tag = tag + CONST["subtotal_suffix"]
                _sun_tree.update_node(node_id, tag=subtotal_tag)

            # If it has its own leaf_total, move that amount
            # to a new leaf node
            if leaf_total > 0:

                new_leaf_id = node_id + CONST["leaf_suffix"]
                node.data["leaf_total"] = 0
                _sun_tree.create_node(
                    identifier=new_leaf_id,
                    tag=tag,
                    parent=node_id,
                    data=dict(leaf_total=leaf_total, total=leaf_total),
                )

            for child in children:
                # recurse to get subtotals.  This won't double-count
                # the leaf_total from the node because children
                # was set before the new synthetic node
                child_total = set_node_total(child)
                running_subtotal += child_total

        # Remove zeros, because they look terrible in sunburst.
        if running_subtotal == 0:
            _sun_tree.remove_node(node_id)
        else:
            if node.data:
                node.data["total"] = running_subtotal
            else:
                node.data = {"total": running_subtotal}

        return running_subtotal

    root = _sun_tree.get_node(_sun_tree.root)

    set_node_total(root)

    def summarize_to_other(node):
        """
        If there are more than (MAX_SLICES - 2) children in this node,
        group the excess children into a new 'other' node.
        Recurse to do this for all children, including any 'other' nodes
        that get created.

        The "-2" accounts for the Other node to be created, and for
        one-based vs zero-based counting.
        """
        nonlocal _sun_tree
        node_id = node.identifier
        children = _sun_tree.children(node_id)
        if len(children) > (CONST["max_slices"] - 2):
            other_id = CONST["other_prefix"] + node_id
            other_subtotal = 0
            _sun_tree.create_node(
                identifier=other_id,
                tag=other_id,
                parent=node_id,
                data=dict(total=other_subtotal),
            )
            total_list = [
                (dict(identifier=x.identifier, total=x.data["total"])) for x in children
            ]
            sorted_list = sorted(total_list, key=lambda k: k["total"], reverse=True)
            for i, child in enumerate(sorted_list):
                if i > (CONST["max_slices"] - 2):
                    other_subtotal += child["total"]
                    _sun_tree.move_node(child["identifier"], other_id)
            _sun_tree.update_node(other_id, data=dict(total=other_subtotal))

        children = _sun_tree.children(node_id)

        for child in children:
            summarize_to_other(child)

    # summarize_to_other(root)

    #######################################################################
    # Make the figure
    #######################################################################

    sun_frame = pd.DataFrame(
        [
            (x.identifier, x.tag, x.bpointer, x.data["total"])
            for x in _sun_tree.all_nodes()
        ],
        columns=["id", "name", "parent", "value"],
    )

    sun_frame["color"] = sun_frame["id"].map(colormap)

    figure = px.sunburst(
        sun_frame,
        ids="id",
        names="name",
        parents="parent",
        values="value",
        height=600,
        color="id",
        branchvalues="total",
        color_discrete_map=colormap,
    )

    #        go.Sunburst({'marker': {'colorscale': 'Aggrnyl'}}),
    figure.update_traces(
        insidetextorientation="horizontal",
        maxdepth=3,
        hovertemplate="%{label}<br>%{value}",
        texttemplate="%{label}<br>%{value}",
    )

    figure.update_layout(
        font=fonts["big"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, l=5, r=5, b=5),  # NOQA
    )
    return figure


def positize(trans):
    """Negative values can't be plotted in sunbursts.  This can't be fixed with absolute value
    because that would erase the distinction between debits and credits within an account.
    Simply reversing sign could result in a net-negative sum, which also breaks sunbursts.
    This function always returns a net-positive sum DataFrame of transactions, suitable for
    a sunburst."""

    if trans.sum(numeric_only=True)["amount"] < 0:
        trans["amount"] = trans["amount"] * -1

    return trans


def pretty_records(trans: pd.DataFrame) -> list:
    """ Make a nice list of records """
    output: List = []
    if len(trans) > 0:
        list = trans.to_dict(orient="records")
        for row in list:
            output = output + ["————————————"]
            for key in row.keys():
                output = output + [f"{key}={row[key]}"]
    return output
