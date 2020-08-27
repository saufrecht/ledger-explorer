import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
from datetime import timedelta
import logging
import pandas as pd
import numpy as np

import plotly.graph_objects as go

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import TIME_RES_OPTIONS, TIME_RES_LOOKUP, TIME_SPAN_LOOKUP, LEAF_SUFFIX, SUBTOTAL_SUFFIX
from utils import chart_fig_layout, trans_table, data_from_json_store
from utils import get_children, get_descendents
from utils import make_bar, make_sunburst

from app import app


def _pretty_account_label(sel_accounts, desc_account_count, start, end, trans_count):
    if desc_account_count > 0:
        desc_text = f' and {desc_account_count:,d} subaccounts'
    else:
        desc_text = ''
    date_range_content = f' between {start.strftime("%Y-%m-%d")} and {end.strftime("%Y-%m-%d")}'
    result = f'{trans_count:,d} records in {", ".join(sel_accounts)} {desc_text} {date_range_content}'
    return result


ACCOUNTS = ['Income', 'Expenses']

layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id="time_series_box",
            children=[
                dcc.Graph(
                    id='master_time_series'),
                html.Div(
                    className="control_bar",
                    children=[
                        dcc.Store(id='time_series_selection_info',
                                  storage_type='memory'),
                        html.Div(
                            id='selected_trans_display',
                            children=None),
                        html.Fieldset(
                            className='control_bar',
                            children=[
                                html.Span(
                                    children='Group By ',
                                ),
                                dcc.Dropdown(
                                    id='time_series_resolution',
                                    options=TIME_RES_OPTIONS,
                                    clearable=False,
                                    value=1,
                                    style={'height': '1.2rem', 'width': '8rem',
                                           'color': 'var(--fg)',
                                           'backgroundColor': 'var(--bg-more)'}
                                ),
                            ]),
                        html.Fieldset(
                            className="control_bar",
                            children=[
                                html.Span(
                                    children='Monthly',
                                ),
                                daq.ToggleSwitch(
                                    id='time_series_span',
                                    value=False,
                                ),
                                html.Span(
                                    children='Annualized',
                                ),
                            ]),
                    ]),
            ]),
        html.Div(
            id="account_burst_box",
            children=[
                html.Div([
                    html.H3(
                        id='burst_title',
                        children=''),
                    html.Div(
                        id='selected_account_text',
                        children='Click a pie slice to filter records'),
                ]),
                dcc.Graph(
                    id='account_burst'),
            ]),
        html.Div(
            id='trans_table_box',
            children=[
                html.Div(
                    id='trans_table_text',
                    children=''
                ),
                trans_table
            ]),
    ])


@app.callback(
    [Output('master_time_series', 'figure')],
    [Input('time_series_resolution', 'value'),
     Input('time_series_span', 'value')],
    state=[State('data_store', 'children')])
def apply_time_series_resolution(time_resolution: int, time_span: bool, data_store: str):
    try:
        tr = TIME_RES_LOOKUP[time_resolution]
        ts = TIME_SPAN_LOOKUP[time_span]
        ts_label = ts.get('label')      # e.g., 'Annual' or 'Monthly'
        tr_label = tr.get('label')          # e.g., 'by Era'
    except KeyError:
        raise PreventUpdate
    except IndexError:
        logging.critical(f'Bad data from period selectors: time_resolution {time_resolution}, time_span {time_span}')
        raise PreventUpdate

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)
    chart_fig = go.Figure(layout=chart_fig_layout)
    root_account_id = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = get_children(root_account_id, account_tree)

    for i, account in enumerate(selected_accounts):
        chart_fig.add_trace(make_bar(trans, account_tree, eras, account, i, time_resolution, time_span, deep=True))

    ts_title = f'Average {ts_label} $, by {tr_label} '
    chart_fig.update_layout(
        title={'text': ts_title},
        xaxis={'showgrid': True, 'dtick': 'M3'},
        yaxis={'showgrid': True},
        barmode='relative')

    return [chart_fig]


@app.callback(
    [Output('selected_trans_display', 'children'),
     Output('time_series_selection_info', 'data'),
     Output('account_burst', 'figure'),
     Output('burst_title', 'children')],
    [Input('master_time_series', 'figure'),
     Input('master_time_series', 'selectedData'),
     Input('data_store', 'children')],
    state=[State('time_series_resolution', 'value'),
           State('time_series_span', 'value')])
def apply_selection_from_time_series(figure, selectedData, data_store, time_resolution, time_span):
    """
    Selecting specific points from the time series chart updates the
    account burst and the detail labels.

    Reminder to self: When you think selectedData input is broken, remember
    that unaltered default action in the graph is to zoom, not to select.

    Note: all of the necessary information is in figure but that doesn't seem
    to trigger reliably.  Adding selectedData as a second Input causes reliable
    triggering.

    TODO: maybe check for input safety?

    """

    if not figure or not data_store:  # prevent from crashing when triggered from other pages
        raise PreventUpdate

    sel_date_start: np.datetime64 = None
    sel_start_display_date: np.datetime64 = None  # Selection may be either > or ≥, so make the display consistent
    sel_date_end: np.datetime64 = None
    sel_accounts = []
    filtered_trans = pd.DataFrame()
    desc_account_count = 0
    time_series_selection_info = None
    tr_label = TIME_RES_LOOKUP[time_resolution]['label']
    ts_label = TIME_SPAN_LOOKUP[time_span]['label']

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)
    for trace in figure.get('data'):
        account = trace.get('name')
        points = trace.get('selectedpoints')
        if not points:
            continue
        sel_accounts.append(account)
        for point in points:
            if tr_label == 'Era':
                era = trace['text'][point]
                sel_date_start = eras[eras.index == era]['date_start'][0]
                sel_start_display_date = sel_date_start
                sel_date_end = eras[eras.index == era]['date_end'][0]
            else:
                sel_date_end = pd.to_datetime(trace['x'][point])
                # the first point in the time-series won't have a preceding point
                if point > 0:
                    sel_date_start = pd.to_datetime(trace['x'][point - 1])
                    sel_start_display_date = sel_date_start + timedelta(days=1)
                else:
                    sel_date_start = earliest_trans
                    sel_start_display_date = earliest_trans

            desc_accounts = get_descendents(account, account_tree)
            desc_account_count = desc_account_count + len(desc_accounts)
            subtree_accounts = [account] + desc_accounts
            new_trans = trans.loc[trans['account'].isin(subtree_accounts)].\
                loc[trans['date'] >= sel_date_start].\
                loc[trans['date'] <= sel_date_end]

            if len(filtered_trans) > 0:
                filtered_trans.append(new_trans)
            else:
                filtered_trans = new_trans

    # If no transactions are ultimately selected, show all accounts
    filtered_count = len(filtered_trans)

    if filtered_count > 0:
        sel_accounts_content = _pretty_account_label(sel_accounts, desc_account_count,
                                                     sel_start_display_date,
                                                     sel_date_end,
                                                     filtered_count)
    else:
        # If no trans are selected, show everything.  Note that we
        # could logically get here even if valid accounts are
        # seleceted, in which case it would be confusing to get back
        # all trans instead of none, but this should never happen haha
        # because any clickable bar must have $$, and so, trans
        sel_accounts_content = f'Click a bar in the graph to filter from {len(trans):,d} records'
        filtered_trans = trans
        sel_date_start = earliest_trans
        sel_date_end = latest_trans

    sun_fig = make_sunburst(filtered_trans, sel_date_start, sel_date_end,
                            SUBTOTAL_SUFFIX,
                            time_span)
    time_series_selection_info = {'start': sel_date_start, 'end': sel_date_end, 'count': len(filtered_trans)}

    title = f'Average {ts_label} $ from {sel_date_start.strftime("%Y-%m-%d")} to {sel_date_end.strftime("%Y-%m-%d")}'
    return [sel_accounts_content, time_series_selection_info, sun_fig, title]


@app.callback(
    [Output('trans_table', 'data'),
     Output('selected_account_text', 'children'),
     Output('trans_table_text', 'children')],
    [Input('account_burst', 'clickData'),
     Input('time_series_selection_info', 'data'),
     Input('data_store', 'children')])
def apply_burst_click(burst_clickData, time_series_info, data_store):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions

    TODO: maybe check for input safety?
    """

    if not burst_clickData:  # prevent from crashing when triggered from other pages
        raise PreventUpdate

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)

    date_start: np.datetime64 = pd.to_datetime(time_series_info.get('start', earliest_trans))
    date_end: np.datetime64 = pd.to_datetime(time_series_info.get('end', latest_trans))
    max_trans_count = time_series_info.get('count', 0)

    sub_accounts: list = []

    # Figure out which account(s) were selected in the sunburst click
    if burst_clickData:
        click_account = burst_clickData['points'][0]['id']
        # strip any SUFFFIXes from the label that were added in the sunburst hack
        if LEAF_SUFFIX in click_account:
            revised_id = click_account.replace(LEAF_SUFFIX, '')
        elif SUBTOTAL_SUFFIX in click_account:
            revised_id = click_account.replace(SUBTOTAL_SUFFIX, '')
        else:
            revised_id = click_account
    else:
        revised_id = []

    # if any accounts are selected, get those transactions.  Otherwise, get all transactions.
    if revised_id:
        # Add any sub-accounts
        sub_accounts = get_descendents(revised_id, account_tree)
        filter_accounts = [revised_id] + sub_accounts
        sel_trans = trans[trans['account'].isin(filter_accounts)]
        if (len_sub := len(sub_accounts)) > 0:
            account_text = f'{revised_id} and {len_sub} sub-accounts selected'
        else:
            account_text = f'{revised_id} selected'
    else:
        sel_trans = trans
        account_text = f'Click a pie slice to filter from {max_trans_count} records'

    try:
        sel_trans = sel_trans[(sel_trans['date'] >= date_start) & (sel_trans['date'] <= date_end)]
    except (KeyError, TypeError):
        pass
    sel_trans['date'] = pd.DatetimeIndex(sel_trans['date']).strftime("%Y-%m-%d")
    sel_trans = sel_trans.sort_values(['date'])

    trans_table_text: str = f'{len(sel_trans)} records'

    return [sel_trans.to_dict('records'), account_text, trans_table_text]
