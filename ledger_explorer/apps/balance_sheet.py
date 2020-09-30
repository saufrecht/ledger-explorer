import dash_core_components as dcc
import dash_html_components as html
from more_itertools import intersperse
import pandas as pd

import plotly.graph_objects as go
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import chart_fig_layout, data_from_json_store, bs_trans_table, ATree
from utils import get_children, get_descendents, pretty_date
from utils import make_cum_area
from params import Params, CONST
from app import app


layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(className='time_series_box',
                 children=[
                     html.Fieldset(
                         className='flex_forward radio',
                         children=[
                             html.Span(children='Group By '),
                             dcc.RadioItems(id='bs_time_series_resolution',
                                            options=CONST['time_res_options']),
                         ]),
                     html.Div(id='time_serieses',
                              className='flex_down')
                 ]),
        html.Div(
            id='bs_trans_table_box',
            children=[
                html.Div(id='bs_trans_table_text',
                         children=''),
                bs_trans_table
            ]),
    ])


@app.callback([Output('bs_time_series_resolution', 'value')],
              [Input('control_store', 'children')])
def load_bs_controls(control_store: str):
    if control_store and len(control_store) > 0:
        params = Params.from_json(control_store)
    else:
        raise PreventUpdate

    return [params.init_time_res]


@app.callback([Output('time_serieses', 'children')],
              [Input('bs_time_series_resolution', 'value')],
              state=[State('data_store', 'children'),
                     State('control_store', 'children')])
def bs_make_time_series(time_resolution, data_store, control_store):
    """ Generate cumulative Dash bar charts for all root accounts """
    if not data_store:
        raise PreventUpdate
    params = Params.from_json(control_store)
    if not time_resolution:
        time_resolution = params.init_time_res
    dd: dict = data_from_json_store(data_store, params.bs_account_filter)
    trans: pd.DataFrame = dd.get('trans')
    account_tree: ATree = dd.get('account_tree')
    unit: str = params.ds_unit
    data_title = params.ds_data_title
    result: list = []
    # make one chart for each item in the Balance Sheet account filter
    for i, account in enumerate(params.bs_account_filter):
        fig: go.Figure = go.Figure(layout=chart_fig_layout)
        fig.update_layout(title={'text': f'{data_title} {account}: Cumulative {unit}'},
                          xaxis={'showgrid': True, 'nticks': 20},
                          yaxis={'showgrid': True},
                          legend={'xanchor': 'left', 'x': 0,
                                  'yanchor': 'bottom', 'y': 0,
                                  'bgcolor': 'rgba(0, 0, 0, 0)'},
                          barmode='relative')
        subaccounts: iter = get_children(account, account_tree)
        for j, subaccount in enumerate(subaccounts):
            sub_desc = get_descendents(subaccount, account_tree)
            tba = trans[trans['account'].isin(sub_desc)]
            if len(tba) > 0:
                fig.add_trace(make_cum_area(tba, subaccount, j, time_resolution))

        output = dcc.Graph(id=f'{account}{j}',
                           figure=fig)
        if len(result) > 0:
            result.append(output)
        else:
            result = [output]

    return [result]


@app.callback(
    [Output('bs_trans_table', 'data'),
     Output('bs_trans_table_text', 'children')],
    [Input('bsa_master_time_series', 'selectedData'),
     Input('bsl_master_time_series', 'selectedData'),
     Input('bse_master_time_series', 'selectedData')],
    state=[State('data_store', 'children'),
           State('control_store', 'children')])
def apply_selection_from_bs_time_series(bsa_master_time_series,
                                        bsl_master_time_series,
                                        bse_master_time_series, data_store, control_store):
    """
    selecting a point or points in the time series updates the transaction table to show
    all transactions up to that point
    TODO: this is temporarily disabled now that the time serieses are dynamically generated.
    Should be replaced with dynamically generated callbacks?
    """

    if control_store and len(control_store) > 0:
        params = Params.from_json(control_store)
    else:
        raise PreventUpdate

    ctx = dash.callback_context
    click = ctx.triggered[0]['prop_id'].split('.')[0]
    if not data_store or len(click) == 0:
        raise PreventUpdate
    inputs = {'bsa_master_time_series': bsa_master_time_series, 'bsl_master_time_series': bsl_master_time_series,
              'bse_master_time_series': bse_master_time_series}
    selection = inputs[click]
    dd = data_from_json_store(data_store, params.bs_account_filter)
    trans = dd.get('trans')

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

    if len(sel_trans) == 0:
        raise PreventUpdate

    sel_trans = sel_trans.set_index('date').sort_index()
    sel_trans['total'] = sel_trans['amount'].cumsum()
    sel_trans['date'] = pd.DatetimeIndex(sel_trans.index).strftime("%Y-%m-%d")

    sel_output = [html.Span(children=x) for x in sel_text]
    final_label = list(intersperse(html.Br(), sel_output))
    return [sel_trans.to_dict('records'), final_label]
