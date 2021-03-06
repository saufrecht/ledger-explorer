import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import textwrap

from plotly.colors import colorbrewer as cb
import plotly.graph_objects as go
import plotly.express as px
from dash.dependencies import Input, Output, State, ALL
from params import Params
from dash.exceptions import PreventUpdate
from app import app
from atree import ATree
from utils import (
    layouts,
    traces,
    preventupdate_if_empty,
)

from datastore import Datastore

layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(id="ex_dummy", className="hidden", children="getstarted"),
        html.Div(id="ex_wrapper", children=[]),
    ],
)


@app.callback(
    [Output("ex_wrapper", "children")],
    [
        Input("ex_dummy", "children"),
        Input({"type": "ex_chart", "index": ALL}, "selectedData"),
        Input({"type": "ex_chart", "index": ALL}, "figure"),
    ],
    state=[
        State("data_store", "children"),
        State("param_store", "children"),
    ],
)
def ex_apply_selection(dummy, selectedData, figure, data_store, param_store):
    """Take the selected account from the main explorer chart
    and show it in a series of drill-down charts
    """
    preventupdate_if_empty(data_store)
    data_store: Datastore() = Datastore.from_json(data_store)
    tree: ATree = data_store.account_tree
    params: Params() = Params.from_json(param_store)
    unit: str = params.unit

    if not selectedData or len(selectedData) == 0:
        account = tree.root
    else:
        for i, indexed_fig in enumerate(figure):
            try:
                account = figure[i]["data"][0]["customdata"][
                    selectedData[i]["points"][0]["pointNumber"]
                ]
                if account and len(account) > 0:
                    break
            except TypeError:
                # happens when clicking on the second or later chart, because
                # the corresponding selectedData will be empty
                pass
    if not account:
        raise PreventUpdate
    lineage = tree.get_lineage_ids(account) + [account]
    charts: list = []
    trans: pd.DataFrame = data_store.trans
    tree: ATree = data_store.account_tree
    tree = tree.append_sums_from_trans(trans)
    tree.roll_up_subtotals()
    palette = cb.Set3
    selection_color = None
    color_data = pd.DataFrame(columns=["account", "color"])

    # iterate through the lineage and make a new stacked bar chart for each level.
    for i, node in enumerate(lineage):
        palette_mod = 12 - i  # compensate for shrinking palette
        drill_data = pd.DataFrame(
            columns=["account", "child_id", "child_tag", "color", "amount"]
        )
        children = tree.children(node)
        level_selection = []
        if len(children) > 0:
            try:
                level_selection = [
                    x.identifier for x in children if x.identifier == lineage[i + 1]
                ]
            except IndexError:
                pass
            for j, point in enumerate(children):
                point_id = point.identifier
                color = palette[j % palette_mod]
                color_data = color_data.append(
                    dict(account=point_id, color=color), ignore_index=True
                )
                if len(level_selection) > 0:  # If there is a selection …
                    if point_id == level_selection[0]:
                        selection_color = color
                    else:
                        color = "rgba(100, 100, 100, .5)"
                drill_data = drill_data.append(
                    dict(
                        account=node,
                        child_id=point.identifier,
                        child_tag=point.tag,
                        color=color,
                        amount=point.data["total"],
                    ),
                    ignore_index=True,
                )
        else:
            continue
        try:
            drill_data = drill_data.sort_values("amount")
            node_bar: go.Bar = go.Bar(
                y=drill_data["account"],
                x=drill_data["amount"],
                marker_color=drill_data["color"],
                textposition="inside",
                text=drill_data["child_tag"],
                texttemplate="%{text}<br>" + unit + "%{value:,.0f}",
                hovertemplate="%{text}<br>" + unit + "%{value:,.0f}<extra></extra>",
                customdata=drill_data["child_id"],
                orientation="h",
            )
            fig: go.Figure = go.Figure(data=node_bar)
            fig.update_layout(layouts["drill"])
            fig.update_traces(traces["drill"])
            if selection_color and len(selection_color) > 0:
                # Don't reuse selected colors in later bars.
                palette = list(set(cb.Set3) - set([selection_color]))
                if i > 0:
                    fig.update_layout(title_text=node, title_x=0, title_y=0.98)
            charts = charts + [
                dcc.Graph(figure=fig, id={"type": "ex_chart", "index": i})
            ]
        except Exception as E:
            charts = charts + [html.Div(f"Error making {node}: {E}")]

    if len(lineage) > 1:
        selected_accounts = tree.get_descendent_ids(lineage[-1]) + [lineage[i]]
        sel_trans = trans[trans["account"].isin(selected_accounts)]
        color_data = color_data.set_index("account")
        sel_trans["color"] = sel_trans.account.map(color_data.color)
        sel_trans["color"] = sel_trans["color"].fillna("darkslategray")
    else:
        sel_trans = trans
        sel_trans["color"] = "darkslategray"
    wrapper = textwrap.TextWrapper(width=40)

    def brfill(text, TW):
        return "<br>".join(TW.wrap(text))

    sel_trans["wrap"] = sel_trans["description"].apply(brfill, TW=wrapper)
    sel_trans["pretty_value"] = sel_trans["amount"].apply("{:,.0f}".format)

    sel_trans["customdata"] = (
        sel_trans["account"]
        + "<br>"
        + sel_trans["date"].astype(str)
        + "<br>"
        + sel_trans["pretty_value"]
        + "<br>"
        + sel_trans["wrap"]
    )
    dot_fig = px.scatter(
        sel_trans,
        x="date",
        y="amount",
        color="color",
        color_discrete_map="identity",
    )
    dot_fig.update_layout(layouts["dot_fig"])
    dot_fig.update_traces(traces["dot_fig"])
    dot_fig.update_traces(
        customdata=sel_trans["customdata"], hovertemplate="%{customdata}<extra></extra>"
    )
    charts = charts + [dcc.Graph(figure=dot_fig, id="ex_dot_chart")]
    return [charts]
