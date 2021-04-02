import pandas as pd
import plotly.express as px

from typing import Dict

from atree import ATree
from utils import fonts
from ledger import Ledger
from params import CONST


class Burst:
    """Functions related to Plotly sunburst object """

    @staticmethod
    def pretty_account_label(sel_accounts, desc_account_count, trans_count):
        """ Make label for sunburst """
        if desc_account_count > 0:
            desc_text = f"and {desc_account_count:,d} subaccounts"
        else:
            desc_text = ""
        return f'{trans_count:,d} records in {", ".join(sel_accounts)} {desc_text}'

    @classmethod
    def from_trans(
        cls,
        tree: ATree,
        trans: pd.DataFrame,
        time_span: str,
        unit: str = CONST["unit"],
        factor: float = 1,
        colormap: Dict = {},
        span_label: str = "",
    ):
        """
        Using a tree of accounts and a DataFrame of transactions,
        generate a figure for a sunburst, where each node is an account
        in the tree, and the value of each node is the subtotal of all
        transactions for that node and any subtree, filtered by date.
        """
        trans = Ledger.positize(trans)
        tree = tree.append_sums_from_trans(trans, factor)
        tree.roll_up_subtotals(prevent_negatives=True)
        tree = tree.trim_excess_root()
        abbrev = CONST["time_span_lookup"][time_span]["abbrev"]

        #######################################################################
        # Make the figure
        #######################################################################

        sun_frame = pd.DataFrame(
            [
                (x.identifier, x.tag, x.bpointer, x.data["total"])
                for x in tree.all_nodes()
            ],
            columns=["id", "name", "parent", "value"],
        )
        sun_frame["color"] = sun_frame["id"].map(colormap)
        sun_frame["unit"] = unit
        sun_frame["abbrev"] = abbrev
        sun_frame["span_label"] = span_label
        sun_frame["label_pre"] = (
            sun_frame["id"]
            + "<br>"
            + sun_frame["unit"]
            + sun_frame["value"].astype(str)
            + sun_frame["abbrev"]
        )
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

        figure.update_traces(
            text=sun_frame["label_pre"],
            customdata=sun_frame["span_label"],
            insidetextorientation="horizontal",
            maxdepth=3,
            texttemplate="%{text}",
            hovertemplate="%{text}<extra>%{customdata}</extra>",
        )

        figure.update_layout(
            font=fonts["big"],
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, l=5, r=5, b=5),  # NOQA
        )
        return figure
