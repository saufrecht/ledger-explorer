import dash_core_components as dcc
import dash_html_components as html
import logging

import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from utils import TIME_RES_LOOKUP, TIME_RES_OPTIONS
from utils import chart_fig_layout, data_from_json_store
from utils import get_children
from utils import make_cum_bar

from app import app


ACCOUNTS: list = ['Assets', 'Liabilities']

layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='bs_time_series_control_bar',
            className="control_bar dashbox",
            children=[
                dcc.Dropdown(
                    className='resolution-dropdown',
                    id='bs_period',
                    options=TIME_RES_OPTIONS,
                    value=2
                ),
                html.H2(
                    id='selected_account_text',
                    children=['Account']),
                html.H2(
                    id='burst_selected_account_display',
                    children=[]),
                html.H2(
                    id='selected_date_range_display',
                    children=['All Dates']),
                dcc.Store(id='detail_store',
                          storage_type='memory')
            ]),
        html.Div(
            className='master_time_series dashbox',
            id='time_series_box',
            children=[
                dcc.Graph(
                    id='bs_master_time_series')
            ]),
        html.Div(
            id='kludge to eliminate "nonexistent object" errors',
            style={'display': 'none'},
            children=[
                html.Div(
                    id='account_burst'),
                html.Div(
                    id='burst_title'),
                html.Div(
                    id='master_time_series'),
                html.Div(
                    id='selected_trans_display'),
                html.Div(
                    id='time_series_resolution'),
                html.Div(
                    id='time_series_selection_info'),
                html.Div(
                    id='time_series_span'),
                html.Div(
                    id='trans_table'),
                html.Div(
                    id='trans_table_text'),
                html.Div(
                    id='transaction_time_series'),
            ]),
    ])


@app.callback(
    [Output('bs_master_time_series', 'figure')],
    [Input('bs_period', 'value')],
    state=[State('data_store', 'children')])
def bs_set_period(period_value, data_store):
    try:
        period = TIME_RES_LOOKUP[period_value]
    except IndexError:
        logging.critical(f'Bad data from period selectors: time_resolution {period}')
        return

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)

    chart_fig = go.Figure(layout=chart_fig_layout)
    root_account_id = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = get_children(root_account_id, account_tree)

    for i, account in enumerate(selected_accounts):
        chart_fig.add_trace(make_cum_bar(trans, account_tree, eras, account, i, period_value, deep=True))

    chart_fig.update_layout(
        title={'text': '$'},
        xaxis={'showgrid': True, 'dtick': 'M3'},
        barmode='relative')

    return [chart_fig]
