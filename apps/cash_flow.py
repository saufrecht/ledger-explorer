import dash_core_components as dcc
import dash_html_components as html
from datetime import timedelta
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
            className='account_burst dashbox',
            children=[
                html.Div([
                    html.H3(children='Average Monthly $'),
                    html.Div(
                        id='selected_account_display',
                        children=None),
                ]),
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
                html.Div(
                    id='selected_trans_display',
                    children=''),
                dcc.Store(id='time_series_selection_info',
                          storage_type='memory'),
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
        title={'text': f'Average {ts_label} $, by {tr_label} ',
               'font': {'color': '#eee8d5'}},
        xaxis={'showgrid': True, 'dtick': 'M3',
               'linecolor': '#657b83',
               'color': '#657b83',
               'gridcolor': '#657b83'},
        yaxis={'showgrid': True,
               'linecolor': '#657b83',
               'color': '#657b83',
               'gridcolor': '#657b83'},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#586e75',
        font={'color': '#657b83'},
        barmode='relative')

    return [chart_fig]


@app.callback(
    [Output('selected_account_display', 'children'),
     Output('time_series_selection_info', 'data'),
     Output('account_burst', 'figure')],
    [Input('master_time_series', 'figure'),
     Input('master_time_series', 'selectedData'),
     Input('data_store', 'children')],
    state=[State('time_series_resolution', 'value')])
def apply_selection_from_time_series(figure, selectedData, data_store, time_resolution):
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

    sel_start_date = None
    sel_start_display_date = None  # Selection may be either > or ≥, so make the display consistent
    sel_end_date = None
    sel_accounts = []
    filtered_trans = pd.DataFrame()
    desc_account_count = 0
    time_series_selection_info = None
    tr_label = TIME_RES_LOOKUP[time_resolution]['label']

    if not figure:
        raise PreventUpdate

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
                sel_start_date = eras[eras.index == era]['start_date'][0]
                sel_start_display_date = sel_start_date
                sel_end_date = eras[eras.index == era]['end_date'][0]
            else:
                sel_end_date = pd.to_datetime(trace['x'][point])
                # the first point in the time-series won't have a preceding point
                if point > 0:
                    sel_start_date = pd.to_datetime(trace['x'][point - 1])
                    sel_start_display_date = sel_start_date + timedelta(days=1)
                else:
                    sel_start_date = earliest_trans
                    sel_start_display_date = sel_start_date

            logging.debug(f'Trace {account}, point {point}: start {sel_start_date}, end {sel_end_date}')
            desc_accounts = get_descendents(account, account_tree)
            desc_account_count = desc_account_count + len(desc_accounts)
            subtree_accounts = [account] + desc_accounts
            new_trans = trans.loc[trans['account'].isin(subtree_accounts)].\
                loc[trans['date'] >= sel_start_date].\
                loc[trans['date'] <= sel_end_date]

            if len(filtered_trans) > 0:
                filtered_trans.append(new_trans)
            else:
                filtered_trans = new_trans

    # If no transactions are ultimately selected, show all accounts
    filtered_count = len(filtered_trans)

    if filtered_count > 0:
        sel_accounts_content = _pretty_account_label(sel_accounts, desc_account_count,
                                                     sel_start_display_date,
                                                     sel_end_date,
                                                     filtered_count)
    else:
        # If no trans are selected, show everything.  Note that we
        # could logically get here even if valid accounts are
        # seleceted, in which case it would be confusing to get back
        # all trans instead of none, but this should never happen haha
        # because any clickable bar must have $$, and so, trans
        sel_accounts_content = f'All records ({len(trans):,d})'
        filtered_trans = trans
        sel_start_date = earliest_trans
        sel_end_date = latest_trans

    sun_fig = make_sunburst(filtered_trans, sel_start_date, sel_end_date,
                            SUBTOTAL_SUFFIX=SUBTOTAL_SUFFIX)
    time_series_selection_info = {'start': sel_start_date, 'end': sel_end_date, 'count': len(filtered_trans)}

    return [sel_accounts_content, time_series_selection_info, sun_fig]


@app.callback(
    [Output('trans_table', 'data'),
     Output('transaction_time_series', 'figure'),
     Output('selected_trans_display', 'children')],
    [Input('account_burst', 'clickData'),
     Input('time_series_selection_info', 'data'),
     Input('data_store', 'children')])
def apply_burst_click(burst_clickData, time_series_info, data_store):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions

    TODO: maybe check for input safety?
    """

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)

    start_date = time_series_info.get('start', earliest_trans)
    end_date = time_series_info.get('end', latest_trans)
    max_trans_count = time_series_info.get('count', 0)

    sel_accounts = []
    tts_fig = go.Figure(layout=chart_fig_layout)

    # Figure out which account(s) were selected in the sunburst click
    if burst_clickData:
        click_account = burst_clickData['points'][0]['id']
    else:
        click_account = []

    if click_account:
        try:
            sel_accounts = [click_account] + get_children(click_account, account_tree)
        except treelib.exceptions.NodeIDAbsentError:
            # This is a hack.  If the account isn't there, assume that the reason
            # is that it was reidentified to 'X Leaf', and back that out.
            try:
                if LEAF_SUFFIX in click_account:
                    revised_id = click_account.replace(LEAF_SUFFIX, '')
                    sel_accounts = [revised_id]
            except treelib.exceptions.NodeIDAbsentError:
                pass

    if sel_accounts:
        sel_trans = trans[trans['account'].isin(sel_accounts)]
        title = click_account + f': {len(sel_trans)} records'
    else:
        sel_trans = trans

    try:
        sel_trans = sel_trans[(sel_trans['date'] >= start_date) & (sel_trans['date'] <= end_date)]

        # Populate the drilldown chart below.
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

    if max_trans_count > (sel_count := len(sel_trans)):
        title = f'Showing {sel_count:,d} records out of {max_trans_count:,d}.  Only: {", ".join(sel_accounts)}'
    else:
        title = f'{max_trans_count:,d} records'

    if len(sel_accounts) == 1:
        try:
            account = sel_accounts[0]
            tts_fig.add_trace(make_scatter(account, sel_trans))
        except TypeError:
            pass
    elif len(sel_accounts) > 1:
        # TODO: design bug: certain leaves (maybe with ¿hidden children?)
        # appear as leaves in the sunburst and show only one
        # account in the trans table, but have multiple sel_accounts
        # and so render as bars when they should be scatter
        for i, account in enumerate(sel_accounts):
            tts_fig.add_trace(make_bar(trans, account_tree, eras, account, i, 4, 1, deep=True))
            tts_fig.update_layout(
                barmode='stack',
                showlegend=True)

    return [sel_trans.to_dict('records'), tts_fig, title]
