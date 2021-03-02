import dash_core_components as dcc
import dash_html_components as html
import pandas as pd

from plotly.colors import colorbrewer as cb
import plotly.graph_objects as go
import plotly.express as px
from dash.dependencies import Input, Output, State, ALL
from ledgex.params import Params
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.atree import ATree
from ledgex.utils import (
    dot_fig_layout,
    drill_layout,
    preventupdate_if_empty,
)

from ledgex.datastore import Datastore


layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(id="ex_dummy", className="hidden", children="getstarted"),
        html.Div(id="ex_wrapper", children=[]),
    ],
)


@app.callback(
    [Output("ex_wrapper", "children")],
    [Input("ex_dummy", "children"),
     Input({"type": "ex_chart", "index": ALL}, "selectedData"),
     Input({"type": "ex_chart", "index": ALL}, "figure")],
    state=[
        State("data_store", "children"),
        State("param_store", "children"),
    ],
)
def ex_apply_selection(dummy, selectedData, figure, data_store, param_store):
    """Take the selected account from the main explorer chart
    and show it in a series of drill-down charts
    """
    data_store: Datastore() = Datastore.from_json(data_store)
    tree: ATree = data_store.account_tree
    params: Params() = Params.from_json(param_store)
    unit: str = params.unit
    preventupdate_if_empty(data_store)
    if not selectedData or len(selectedData) == 0:
        account = tree.root
    else:
        for i, indexed_fig in enumerate(figure):
            try:
                account = figure[i]['data'][0]['customdata'][selectedData[i]['points'][0]['pointNumber']]
                if account and len(account) > 0:
                    break
            except Exception as E:
                app.logger.debug(f'Error parsing pattern-matching callback: {E}')
    if not account:
        raise PreventUpdate
    lineage = tree.get_lineage_ids(account) + [account]
    charts: list = []
    trans: pd.DataFrame = data_store.trans
    tree: ATree = data_store.account_tree
    tree = tree.append_sums_from_trans(trans)
    tree.roll_up_subtotals()
    palette = cb.Set3
    bg_color = 'rgba(100, 100, 100, 0.1)'
    selection_color = None
    for i, node in enumerate(lineage):
        palette_mod = 12 - i  # compensate for shrinking palette
        drill_data = pd.DataFrame(columns=["account", "child_id", "child_tag", "color", "amount"])
        children = tree.children(node)
        level_selection = []
        if len(children) > 0:
            try:
                level_selection = [x.identifier for x in children if x.identifier == lineage[i + 1]]
            except IndexError:
                pass
            for j, point in enumerate(children):
                point_id = point.identifier
                color = palette[j % palette_mod]
                if len(level_selection) > 0:  # If there is a selection …
                    if point_id == level_selection[0]:
                        selection_color = color
                    else:
                        color = 'rgba(100, 100, 100, .5)'
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
            node_bar: go.Bar = go.Bar(
                y=drill_data["account"],
                x=drill_data["amount"],
                marker_color=drill_data["color"],
                textposition="inside",
                text=drill_data["child_tag"],
                texttemplate="%{text}<br>" + unit + "%{value:,.0f}",
                hovertemplate="%{text}<br>amount:" + unit + "%{value:.0f}<extra></extra>",
                customdata=drill_data["child_id"],
                orientation="h",
            )
            fig: go.Figure = go.Figure(data=node_bar)
            fig.update_layout(drill_layout)
            fig.update_layout(plot_bgcolor=bg_color)
            if selection_color and len(selection_color) > 0:
                # Once a color is used for a background, remove it from the palette
                palette = list(set(cb.Set3) - set([selection_color]))
                # and set it as the background for the next graph
                bg_color = selection_color
                if i > 0:
                    fig.update_layout(title_text=node, title_x=0, title_y=0.98)
            charts = charts + [dcc.Graph(figure=fig, id={"type": "ex_chart", "index": i})]
        except Exception as E:
            charts = charts + [html.Div(f"Error making {node}: {E}")]

    if len(lineage) > 1:
        selected_accounts = tree.get_descendent_ids(lineage[-1]) + [lineage[i]]
        selected_trans = trans[trans["account"].isin(selected_accounts)]
    else:
        selected_trans = trans
    dot_fig = px.scatter(selected_trans, x="date", y="amount", labels="account")
    dot_fig.update_layout(dot_fig_layout)
    if selection_color:
        dot_fig.update_traces(marker_color=selection_color)
    charts = charts + [dcc.Graph(figure=dot_fig, id="ex_dot_chart")]
    return [charts]
