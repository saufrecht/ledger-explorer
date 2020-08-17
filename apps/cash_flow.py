import dash_core_components as dcc
import dash_html_components as html
import logging
import pandas as pd
import treelib

import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import TIME_RES_OPTIONS, TIME_RES_LOOKUP, TIME_SPAN_OPTIONS, TIME_SPAN_LOOKUP, LEAF_SUFFIX, SUBTOTAL_SUFFIX
from utils import chart_fig_layout, trans_table, data_from_json_store
from utils import get_children, get_descendents
from utils import make_bar, make_scatter, make_sunburst

from app import app


ACCOUNTS = ['Income', 'Expenses']

layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='time_series_control_bar',
            className="control_bar dashbox",
            children=[
                dcc.Slider(
                    className='resolution-slider',
                    id='time_series_resolution',
                    min=0,
                    max=4,
                    step=1,
                    marks=TIME_RES_OPTIONS,
                    value=1
                ),
                dcc.Slider(
                    className='span-slider',
                    id='time_series_span',
                    min=0,
                    max=1,
                    step=1,
                    marks=TIME_SPAN_OPTIONS,
                    value=1
                )
            ]),
        html.Div(
            id='detail_control_bar',
            className="control_bar dashbox",
            children=[
                html.H2(
                    id='selected_account_display',
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
            className='account_burst dashbox',
            children=[
                dcc.Graph(
                    id='account_burst')
            ]),
        html.Div(
            className='master_time_series dashbox',
            children=[
                dcc.Graph(
                    id='master_time_series')
            ]),
        html.Div(
            className="trans_table dashbox",
            children=[
                trans_table
            ]),
        html.Div(
            className='transaction_time_series dashbox',
            children=[
                dcc.Graph(
                    id='transaction_time_series')
            ]),
    ])


@app.callback(
    [Output('master_time_series', 'figure')],
    [Input('time_series_resolution', 'value'),
     Input('time_series_span', 'value')],
    state=[State('data_store', 'children')])
def apply_time_series_resolution(time_resolution, time_span, data_store):
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

    chart_fig.update_layout(
        title={'text': f'Average {ts_label} $, by {tr_label} '},
        xaxis={'showgrid': True, 'dtick': 'M3'},
        barmode='relative')

    return [chart_fig]


@app.callback(
    [Output('selected_account_display', 'children'),
     Output('selected_date_range_display', 'children'),
     Output('detail_store', 'data'),
     Output('account_burst', 'figure')],
    [Input('master_time_series', 'figure'),
     Input('master_time_series', 'selectedData'),
     Input('data_store', 'children')])
def apply_selection_from_time_series(figure, selectedData, data_store):
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
    selection_start_date = None
    selection_end_date = None
    date_range_content = None
    filtered_trans = None
    selected_accounts = []
    detail_store = None

    if not figure:
        raise PreventUpdate

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)
    for trace in figure.get('data'):
        account = trace.get('name')
        points = trace.get('selectedpoints')
        if not points:
            continue
        selected_accounts.append(account)
        for point in points:
            # back out the selection parameters (account and start/end dates)
            # from the trace
            # TODO: for All, x is end date
            #       for By Era, x is start date
            #       for A/Q/M, x is end date
            # so fix that.
            selection_start_date = pd.to_datetime(trace['x'][point])
            # the last point in the time-series won't have a following point
            try:
                selection_end_date = pd.to_datetime(trace['x'][point + 1])
            except IndexError:
                selection_end_date = latest_trans

            logging.debug(f'point: start {selection_start_date}, end {selection_end_date}')
            point_accounts = get_descendents(account, account_tree)

            new_trans = trans.loc[trans['account'].isin(point_accounts)].\
                loc[trans['date'] >= selection_start_date].\
                loc[trans['date'] <= selection_end_date]

            try:
                filtered_trans.append(new_trans)
            except AttributeError:
                filtered_trans = new_trans

    # If no transactions are ultimately selected, show all transactions
    try:
        data_count = len(filtered_trans)
    except TypeError:
        data_count = 0
    if data_count == 0:
        filtered_trans = trans
        selected_accounts = ['All']

    sun_fig = make_sunburst(trans, selection_start_date, selection_end_date, SUBTOTAL_SUFFIX=SUBTOTAL_SUFFIX)
    account_children = ', '.join(selected_accounts)
    if selection_start_date and selection_end_date:
        date_range_content = ['Between ',
                              selection_start_date.strftime("%Y-%m-%d"),
                              ' and ',
                              selection_end_date.strftime("%Y-%m-%d")]
        detail_store = {'start': selection_start_date, 'end': selection_end_date}
    return [account_children, date_range_content, detail_store, sun_fig]


@app.callback(
    [Output('trans_table', 'data'),
     Output('transaction_time_series', 'figure'),
     Output('burst_selected_account_display', 'children')],
    [Input('account_burst', 'clickData'),
     Input('detail_store', 'data'),
     Input('data_store', 'children')])
def apply_burst_click(burst_clickData, detail_data, data_store):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions

    TODO: maybe check for input safety?
    """

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)

    selected_accounts = []
    tts_fig = go.Figure(layout=chart_fig_layout)

    if burst_clickData:
        click_account = burst_clickData['points'][0]['id']
    else:
        click_account = []

    if click_account:
        try:
            selected_accounts = [click_account] + get_children(click_account, account_tree)
        except treelib.exceptions.NodeIDAbsentError:
            # This is a hack.  If the account isn't there, assume that the reason
            # is that it was reidentified to 'X Leaf', and back that out.
            try:
                if LEAF_SUFFIX in click_account:
                    revised_id = click_account.replace(LEAF_SUFFIX, '')
                    selected_accounts = [revised_id]
            except treelib.exceptions.NodeIDAbsentError:
                pass
    else:
        title = 'All'
        pass

    if selected_accounts:
        title = click_account
        sel_trans = trans[trans['account'].isin(selected_accounts)]
    else:
        sel_trans = trans

    try:
        start_date = detail_data['start']
        end_date = detail_data['end']
        sel_trans = sel_trans[(sel_trans['date'] >= start_date) & (sel_trans['date'] <= end_date)]
        tts_fig.add_shape(
            type="rect",
            x0=earliest_trans,
            x1=start_date,
            yref='paper',
            ysizemode='scaled',
            y0=0,
            y1=1,
            line=dict(width=0),
            fillcolor='#e1e1e1',
            opacity=0.6
        )
        tts_fig.add_shape(
            type="rect",
            x0=end_date,
            x1=latest_trans,
            yref='paper',
            ysizemode='scaled',
            y0=0,
            y1=1,
            line=dict(width=0),
            fillcolor='#e1e1e1',
            opacity=0.6
        )

    except (KeyError, TypeError):
        pass

    if len(selected_accounts) == 1:
        try:
            account = selected_accounts[0]
            tts_fig.add_trace(make_scatter(account, sel_trans))
        except TypeError:
            pass
    elif len(selected_accounts) > 1:
        # TODO: design bug: certain leaves (maybe with ¿hidden children?)
        # appear as leaves in the sunburst and show only one
        # account in the trans table, but have multiple selected_accounts
        # and so render as bars when they should be scatter
        for i, account in enumerate(selected_accounts):
            tts_fig.add_trace(make_bar(trans, account_tree, eras, account, i, 4, 1, deep=True))
            tts_fig.update_layout(
                barmode='stack',
                showlegend=True)
    return [sel_trans.to_dict('records'), tts_fig, title]
