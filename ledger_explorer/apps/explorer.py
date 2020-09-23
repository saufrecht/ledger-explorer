import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
import pandas as pd
import numpy as np

import plotly.graph_objects as go

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import TIME_RES_OPTIONS, TIME_RES_LOOKUP, TIME_SPAN_LOOKUP, LEAF_SUFFIX, SUBTOTAL_SUFFIX
from utils import chart_fig_layout, data_from_json_store
from utils import get_children, get_descendents
from utils import make_bar
from utils import ex_trans_table
from utils import trans_to_burst
from loading import Controls
from app import app


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                dcc.Graph(
                    id='ex_master_time_series'),
                html.Div(
                    className="control_bar",
                    children=[
                        dcc.Store(id='ex_time_series_selection_info',
                                  storage_type='memory'),
                        html.Div(
                            id='ex_selected_trans_display',
                            children=None),
                        html.Fieldset(
                            className='control_bar',
                            children=[
                                html.Span(
                                    children='Group By ',
                                ),
                                dcc.RadioItems(
                                    id='ex_time_series_resolution',
                                    options=TIME_RES_OPTIONS,
                                    style={'height': '1.2rem',
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
                                    id='ex_time_series_span',
                                ),
                                html.Span(
                                    children='Annualized',
                                ),
                            ]),
                    ]),
            ]),
        html.Div(
            className="account_burst_box",
            children=[
                html.Div([
                    html.H3(
                        id='ex_burst_title',
                        children=''),
                    html.Div(
                        id='ex_selected_account_text',
                        children='Click a pie slice to filter records'),
                ]),
                dcc.Graph(
                    id='ex_account_burst'),
            ]),
        html.Div(
            className='trans_table_box',
            children=[
                html.Div(
                    id='ex_trans_table_text',
                    children=''
                ),
                ex_trans_table,
            ]),
    ])


@app.callback(
    [Output('ex_master_time_series', 'figure')],
    [Input('ex_time_series_resolution', 'value'),
     Input('ex_time_series_span', 'value'),
     Input('tab_draw_trigger', 'children')],
    state=[State('data_store', 'children'),
           State('control_store', 'children')])
def make_time_series(time_resolution: int, time_span: bool, trigger, data_store: str, control_store: str):
    if not data_store:
        raise PreventUpdate
    controls = Controls.from_json(control_store)

    if not time_resolution:
        time_resolution = controls.init_time_res

    if not time_span:
        time_span = controls.init_time_span

    try:
        tr = TIME_RES_LOOKUP[time_resolution]
        ts = TIME_SPAN_LOOKUP[time_span]
        ts_label = ts.get('label')      # e.g., 'Annual' or 'Monthly'
        tr_label = tr.get('label')          # e.g., 'by Era'
    except KeyError as E:
        app.logger.info(f'Bad data from period selectors: time_resolution {time_resolution}, time_span {time_span}. {E}')
        raise PreventUpdate

    dd = data_from_json_store(data_store, controls.ex_account_filter)

    trans = dd.get('trans')
    eras = dd.get('eras')
    if time_resolution == 1 and len(eras) == 0:
        raise PreventUpdate  # TODO: better solution is, if eras isn't loaded, remove ERAS from the choices
    account_tree = dd.get('account_tree')
    unit = dd.get('unit')

    chart_fig = go.Figure(layout=chart_fig_layout)
    root_account_id = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = get_children(root_account_id, account_tree)

    for i, account in enumerate(selected_accounts):
        chart_fig.add_trace(make_bar(trans, account_tree, eras, account, i, time_resolution, time_span, deep=True))

    ts_title = f'Average {ts_label} {unit}, by {tr_label} '
    chart_fig.update_layout(
        title={'text': ts_title},
        xaxis={'showgrid': True, 'nticks': 20},
        yaxis={'showgrid': True},
        barmode='relative')

    return [chart_fig]


@app.callback(
    [Output('ex_selected_trans_display', 'children'),
     Output('ex_time_series_selection_info', 'data'),
     Output('ex_account_burst', 'figure'),
     Output('ex_burst_title', 'children')],
    [Input('ex_master_time_series', 'figure'),
     Input('ex_master_time_series', 'selectedData'),
     Input('data_store', 'children')],
    state=[State('ex_time_series_resolution', 'value'),
           State('ex_time_series_span', 'value'),
           State('control_store', 'value')])
def apply_selection_from_time_series(figure, selectedData, data_store, time_resolution, time_span, control_store):
    """
    Selecting specific points from the time series chart updates the
    account burst and the detail labels.

    Reminder to self: When you think selectedData input is broken, remember
    that unaltered default action in the graph is to zoom, not to select.

    Note: all of the necessary information is in figure but that doesn't seem
    to trigger reliably.  Adding selectedData as a second Input causes reliable
    triggering.

    """
    controls = Controls.from_json(control_store)
    if not time_resolution:
        time_resolution = controls.init_time_res
    if not time_span:
        time_span = controls.init_time_span

    dd = data_from_json_store(data_store)
    if not dd:
        raise PreventUpdate

    trans = dd.get('trans')
    eras = dd.get('eras')
    account_tree = dd.get('account_tree')
    unit = dd.get('unit')

    return trans_to_burst(account_tree, eras, figure, time_resolution, time_span, trans, unit)


@app.callback(
    [Output('ex_trans_table', 'data'),
     Output('ex_selected_account_text', 'children'),
     Output('ex_trans_table_text', 'children')],
    [Input('ex_account_burst', 'clickData'),
     Input('ex_time_series_selection_info', 'data'),
     Input('data_store', 'children')])
def apply_burst_click(burst_clickData, time_series_info, data_store):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions

    TODO: maybe check for input safety?
    """
    dd = data_from_json_store(data_store)
    trans = dd.get('trans')
    if not isinstance(trans, pd.DataFrame) or len(trans) == 0:
        raise PreventUpdate
    account_tree = dd.get('account_tree')
    earliest_trans = dd.get('earliest_trans')
    latest_trans = dd.get('latest_trans')

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

    ex_trans_table_text: str = f'{len(sel_trans)} records'
    return [sel_trans.to_dict('records'), account_text, ex_trans_table_text]
