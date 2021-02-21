import numpy as np
import pandas as pd
import plotly.express as px

from ledgex.atree import ATree
from ledgex.params import CONST
from ledgex.utils import fonts, pretty_date

from typing import Dict


class Burst:
    """Functions related to Plotly sunburst object """

    @staticmethod
    def pretty_account_label(sel_accounts, desc_account_count, start, end, trans_count):
        """ Make label for sunburst """
        if desc_account_count > 0:
            desc_text = f"and {desc_account_count:,d} subaccounts"
        else:
            desc_text = ""
        date_range_content = f"between {pretty_date(start)} {pretty_date(end)}"
        return f'{trans_count:,d} records in {", ".join(sel_accounts)} {desc_text} {date_range_content}'

    @staticmethod
    def positize(trans):
        """Negative values can't be plotted in sunbursts.  This can't be fixed with absolute value
        because that would erase the distinction between debits and credits within an account.
        Simply reversing sign could result in a net-negative sum, which also breaks sunbursts.
        This function always returns a net-positive sum DataFrame of transactions, suitable for
        a sunburst."""
        if trans.sum(numeric_only=True)["amount"] < 0:
            trans["amount"] = trans["amount"] * -1
        return trans

    @classmethod
    def from_trans(
        cls,
        trans: pd.DataFrame,
        time_span: str,
        colormap: Dict = {},
    ):
        """
        Using a tree of accounts and a DataFrame of transactions,
        generate a figure for a sunburst, where each node is an account
        in the tree, and the value of each node is the subtotal of all
        transactions for that node and any subtree, filtered by date.
        """
        date_start = trans["date"].min()
        date_end = pd.Timestamp.now()
        prorate_factor: float = 1
        if time_span != "total":
            ts = CONST["time_span_lookup"][time_span]
            ts_months = ts.get("months")  # e.g., 12
            duration_m = pd.to_timedelta(
                (date_end - date_start), unit="ms"
            ) / np.timedelta64(1, "M")
            # prorate: e.g., annual average over 18 months would be 12 / 18 = .667
            prorate_factor = ts_months / duration_m
        trans = Burst.positize(trans)

        sun_tree = ATree.from_trans_and_make_subtotals(trans, prorate_factor)
        sun_tree.set_subtotals()

        #######################################################################
        # Make the figure
        #######################################################################

        sun_frame = pd.DataFrame(
            [
                (x.identifier, x.tag, x.bpointer, x.data["total"])
                for x in sun_tree.all_nodes()
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
