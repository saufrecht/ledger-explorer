import json
import pandas as pd
import numpy as np

import plotly.graph_objects as go

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import chart_fig_layout, data_from_json_store
from utils import get_children, get_descendents
from utils import make_bar
from utils import ex_trans_table, ATree
from utils import trans_to_burst
from params import Params, CONST
from app import app


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(className="time_series_box",
                 children=[
                     dcc.Graph(id='ex_master_time_series'),
                     html.Div(className="control_bar",
                              children=[
                                  dcc.Store(id='ex_time_series_selection_info',
                                            storage_type='memory'),
                                  html.Div(id='ex_selected_trans_display',
                                           children=None),
                                  html.Fieldset(className='flex_forward radio',
                                                children=[
                                                    html.Span(children='Group By '),
                                                    dcc.RadioItems(id='ex_time_series_resolution',
                                                                   options=CONST['time_res_options'])
                                                ]),
                                  html.Fieldset(className='flex_forward radio',
                                                children=[
                                                    dcc.RadioItems(id='ex_time_series_span',
                                                                   options=CONST['time_span_options']),
                                                ]),
                              ]),
                 ]),
        html.Div(
            className="account_burst_box",
            children=[
                html.Div([
                    html.H3(id='ex_burst_title',
                            children=''),
                    html.Div(id='ex_selected_account_text',
                             children='Click a pie slice to filter records')
                ]),
                dcc.Graph(id='ex_account_burst')
            ]),
        html.Div(
            className='trans_table_box',
            children=[
                html.Div(id='ex_trans_table_text',
                         children=''),
                ex_trans_table,
            ]),
    ])


@app.callback([Output('ex_time_series_resolution', 'value'),
               Output('ex_time_series_resolution', 'options'),
               Output('ex_time_series_span', 'value')],
              [Input('control_store', 'children')],
              state=[State('data_store', 'children')])
def load_ex_controls(control_store: str, data_store: str):
    """ When the control store changes and this tab is visible, update the top controls"""
    if control_store and len(control_store) > 0:
        params = Params(**json.loads(control_store))
    else:
        raise PreventUpdate
    options = CONST['time_res_options']
    dd = data_from_json_store(data_store)
    eras = dd.get('eras')
    if len(eras) > 0:
        options = [CONST['time_res_era_option']] + options

    return [params.init_time_res, options, params.init_time_span]


@app.callback([Output('ex_master_time_series', 'figure')],
              [Input('ex_time_series_resolution', 'value'),
               Input('ex_time_series_span', 'value')],
              state=[State('data_store', 'children'),
                     State('control_store', 'children')])
def ex_make_time_series(time_resolution: int, time_span: str, data_store: str, control_store: str):
    """ Generate a Dash bar chart figure from transactional data """
    if not data_store:
        raise PreventUpdate
    params = Params.from_json(control_store)
    if not time_resolution:
        time_resolution = params.init_time_res

    if not time_span:
        time_span = params.init_time_span

    try:
        tr_label = CONST['time_res_lookup'][time_resolution]['label']  # e.g., 'by Era'
        ts_label = CONST['time_span_lookup'][time_span]['label']       # e.g., 'Annual' or 'Monthly'
    except KeyError as E:
        app.logger.warning(f'Bad data from selectors: time_resolution {time_resolution}, time_span {time_span}. {E}')
        raise PreventUpdate

    dd: dict = data_from_json_store(data_store, params.ex_account_filter)
    trans: pd.DataFrame = dd.get('trans')
    eras: pd.DataFrame = dd.get('eras')
    if time_resolution == 'era' and len(eras) == 0:
        raise PreventUpdate  # TODO: better solution is, if eras isn't loaded, remove ERAS from the choices
    account_tree: ATree = dd.get('account_tree')
    unit = dd.get('unit')

    chart_fig: go.Figure = go.Figure(layout=chart_fig_layout)
    root_account_id: str = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = get_children(root_account_id, account_tree)

    for i, account in enumerate(selected_accounts):
        chart_fig.add_trace(make_bar(trans, account_tree, account, time_resolution, time_span, eras, i, deep=True))

    ts_title = f'Average {ts_label} {unit}, by {tr_label} '
    chart_fig.update_layout(title={'text': ts_title},
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
    params = Params.from_json(control_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    if not time_span:
        time_span = params.init_time_span

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
        if CONST['leaf_suffix'] in click_account:
            revised_id = click_account.replace(CONST['leaf_suffix'], '')
        elif CONST['subtotal_suffix'] in click_account:
            revised_id = click_account.replace(CONST['subtotal_suffix'], '')
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
