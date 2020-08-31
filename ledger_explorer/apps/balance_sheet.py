import dash_core_components as dcc
import dash_html_components as html
from more_itertools import intersperse
import logging
import pandas as pd


import plotly.graph_objects as go
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import TIME_RES_LOOKUP, TIME_RES_OPTIONS
from utils import chart_fig_layout, data_from_json_store, bs_trans_table
from utils import get_descendents, pretty_date
from utils import make_cum_area

from app import app


ACCOUNTS: list = ['Assets', 'Liabilities', 'Equity']

layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className='master_time_series dashbox',
            id='bs_time_series_box',
            children=[
                html.Fieldset(
                    className='control_bar',
                    children=[
                        html.Span(
                            children='Group By ',
                        ),
                        dcc.RadioItems(
                            id='bs_period',
                            options=[x for x in TIME_RES_OPTIONS if x['label'] != 'Era'],
                            value=3,
                            style={'height': '1.2rem',
                                   'color': 'var(--fg)',
                                   'backgroundColor': 'var(--bg-more)'}
                        ),
                    ]),
                dcc.Graph(
                    id='bsa_master_time_series'),
                dcc.Graph(
                    id='bsl_master_time_series'),
                dcc.Graph(
                    id='bse_master_time_series'),
            ]),
        html.Div(
            id='bs_trans_table_box',
            children=[
                html.Div(
                    id='bs_trans_table_text',
                    children=''
                ),
                bs_trans_table
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
                    id='selected_account_text'),
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
    [Output('bsa_master_time_series', 'figure'),
     Output('bsl_master_time_series', 'figure'),
     Output('bse_master_time_series', 'figure')],
    [Input('bs_period', 'value')],
    state=[State('data_store', 'children')])
def bs_set_period(period_value, data_store):
    try:
        period = TIME_RES_LOOKUP[period_value]
    except IndexError:
        logging.critical(f'Bad data from period selectors: time_resolution {period}')
        return
    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)
    result = []
    for account in ACCOUNTS:
        chart_fig = go.Figure(layout=chart_fig_layout)
        subaccounts = get_descendents(account, account_tree)
        for i, subaccount in enumerate(subaccounts):
            tba = trans[trans['account'].isin([subaccount])]
            if len(tba) > 0:
                chart_fig.add_trace(make_cum_area(tba, subaccount, i, period_value))
        chart_fig.update_layout(
            title={'text': account},
            xaxis={'showgrid': True, 'dtick': 'M3'},
            showlegend=True,
            legend={'xanchor': 'left', 'x': 0, 'yanchor': 'bottom', 'y': 0, 'bgcolor': 'rgba(0, 0, 0, 0)'},
            barmode='relative')
        if len(result) > 0:
            result.append(chart_fig)
        else:
            result = [chart_fig]
    return result


@app.callback(
    [Output('bs_trans_table', 'data'),
     Output('bs_trans_table_text', 'children')],
    [Input('bsa_master_time_series', 'selectedData'),
     Input('bsl_master_time_series', 'selectedData'),
     Input('bse_master_time_series', 'selectedData'),
     Input('data_store', 'children')])
def apply_selection_from_bs_time_series(bsa_master_time_series,
                                        bsl_master_time_series,
                                        bse_master_time_series, data_store):
    """
    selecting a point or points in the time series updates the transaction table to show
    all transactions up to that point
    """
    ctx = dash.callback_context
    click = ctx.triggered[0]['prop_id'].split('.')[0]
    if not data_store or len(click) == 0:
        raise PreventUpdate
    inputs = {'bsa_master_time_series': bsa_master_time_series, 'bsl_master_time_series': bsl_master_time_series,
              'bse_master_time_series': bse_master_time_series}
    selection = inputs[click]
    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store, ACCOUNTS)
    trans_filter: dict = {}
    sel_trans: pd.DataFrame = pd.DataFrame()
    sel_text: list = []
    for point in selection['points']:
        account = point['customdata']
        end_date = point['x']
        try:
            trans_filter[account].append(end_date)
        except (KeyError, AttributeError):
            trans_filter[account] = [end_date]

    for account in trans_filter.keys():
        if not trans_filter[account]:
            continue
        end_date = max(trans_filter[account])
        new_trans = trans.loc[(trans['account'] == account) & (trans['date'] <= end_date)]
        sel_trans = sel_trans.append(new_trans)
        new_text = f'{account}: {len(sel_trans)} records through {pretty_date(end_date)}'
        sel_text = sel_text + [new_text]

    sel_trans = sel_trans.set_index('date').sort_index()
    sel_trans['total'] = sel_trans['amount'].cumsum()
    sel_trans['date'] = pd.DatetimeIndex(sel_trans.index).strftime("%Y-%m-%d")

    sel_output = [html.Span(children=x) for x in sel_text]
    final_label = list(intersperse(html.Br(), sel_output))
    return [sel_trans.to_dict('records'), final_label]
