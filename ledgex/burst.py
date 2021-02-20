import numpy as np
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar

from ledgex.atree import ATree
from ledgex.params import CONST
from ledgex.utils import LError, fonts, pretty_date

from typing import Dict, Tuple


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
        and 'total' for the final value for the node, including descendants.
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


def pretty_account_label(sel_accounts, desc_account_count, start, end, trans_count):
    """ Make label for sunburst """
    if desc_account_count > 0:
        desc_text = f"and {desc_account_count:,d} subaccounts"
    else:
        desc_text = ""
    date_range_content = f"between {pretty_date(start)} {pretty_date(end)}"
    result = f'{trans_count:,d} records in {", ".join(sel_accounts)} {desc_text} {date_range_content}'
    return result


class Burst:
    """Functions related to Plotly sunburst object """

    @classmethod
    def trans_to_burst(
        cls, account_tree, eras, figure, time_resolution, time_span, trans, unit
    ) -> tuple:
        """
        Accept an account tree and some parameters and return
        """
        min_period_start: np.datetime64 = None
        max_period_end: np.datetime64 = None
        sel_accounts = []
        filtered_trans = pd.DataFrame()
        desc_account_count = 0
        tr_label = CONST["time_res_lookup"].get(time_resolution)["label"]
        ts_label = CONST["time_span_lookup"].get(time_span)["label"]

        if len(trans) == 0:
            raise LError(
                "Tried to make burst figure from transactions, but no transactions provided."
            )

        colormap = {}
        if figure:
            for trace in figure.get("data"):
                account = trace.get("name")
                points = trace.get("selectedpoints")
                colormap[account] = trace.get("marker").get("color")
                if not points:
                    continue
                sel_accounts.append(account)
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
                    if len(filtered_trans) > 0:
                        filtered_trans = filtered_trans.append(new_trans)
                    else:
                        filtered_trans = new_trans
        filtered_count = len(filtered_trans)
        # If there are some transactions selected, show them
        if filtered_count > 0 and len(sel_accounts) > 0:
            # TODO: desc_account_count is still wrong.
            sel_accounts_content = pretty_account_label(
                sel_accounts,
                desc_account_count,
                min_period_start,
                max_period_end,
                filtered_count,
            )
        else:
            # If no trans are selected, show everything.  Note that we
            # could logically get here even if valid accounts are
            # seleceted, in which case it would be confusing to get back
            # all trans instead of none, but this should never happen haha
            # because any clickable bar must have $$, and so, trans
            sel_accounts_content = (
                f"Click a bar in the graph to filter from {len(trans):,d} records"
            )
            filtered_trans = trans
            min_period_start = trans["date"].min()
            max_period_end = trans["date"].max()

        time_series_selection_info = {
            "start": min_period_start,
            "end": max_period_end,
            "count": len(filtered_trans),
        }
        title = f"Average {ts_label} {unit} from {pretty_date(min_period_start)} to {pretty_date(max_period_end)}"
        sun_fig = make_sunburst(
            filtered_trans,
            time_span,
            min_period_start,
            max_period_end,
            CONST["subtotal_suffix"],
            colormap,
        )

        return (sel_accounts_content, time_series_selection_info, sun_fig, title)
