import json
from typing import Iterable, List
from urllib import error
from treelib import Tree

import numpy as np
import pandas as pd

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import load_eras, load_transactions, make_account_tree_from_trans, get_descendents, pretty_date
from utils import data_from_json_store
from utils import ROOT_ACCOUNTS


from app import app


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='data_tab_body',
            className="control_bar dashbox",
            children=[
                html.Fieldset([
                    html.Div([
                        html.Label(
                            htmlFor='transactions_url',
                            children='Transaction Source URL'),
                        dcc.Input(
                            id='transactions_url',
                            type='url',
                            value='http://localhost/transactions.csv',
                            placeholder='URL for transaction csv file'
                        )]),
                    html.Div([
                        html.Label(
                            htmlFor='eras_url',
                            children='Eras source URL (optional)'),
                        dcc.Input(
                            id='eras_url',
                            type='url',
                            value='http://localhost/eras.csv',
                            placeholder='URL for eras csv file'
                        )]),
                    html.Div([
                        html.Button('Reload', id='data_load_button')
                    ]),
                ]),
            ]),
        html.Div(id='meta_data_box',
                 children=[
                     html.H4("Files"),
                     html.Div(
                         id='meta_data',
                         children=['none']),
                 ]),
        html.Div(id='account_tree_box',
                 children=[
                     html.H4("Account Tree"),
                     html.Div(
                         id='account_tree',
                         className='code',
                         children=['none'])
                 ]),
        html.Div(id='records_box',
                 children=[
                     html.H4("Transactions"),
                     html.Div(
                         id='records',
                         className='code',
                         children=['none']),
                 ]),
    ])


@app.callback(
    [Output('data_store', 'children')],
    [Input('data_load_button', 'n_clicks')],
    state=[State('transactions_url', 'value'),
           State('eras_url', 'value')])
def load_url(n_clicks: int, transactions_url: str, eras_url: str) -> Iterable:
    """ When the Load from URL button is clicked, load the designated files
    and update the data store"""

    if not n_clicks or n_clicks == 0:
        raise PreventUpdate

    try:
        trans: pd.DataFrame = load_transactions(transactions_url)
    except error.URLError as E:
        return [None, f'Error loading transactions: {E}', None, None]

    account_tree: Tree = make_account_tree_from_trans(trans)
    for account in [ra for ra in ROOT_ACCOUNTS if ra['flip_negative'] is True]:
        trans['amount'] = np.where(trans['account'].isin(get_descendents(account['id'], account_tree)),
                                   trans['amount'] * -1,
                                   trans['amount'])

    earliest_trans: np.datetime64 = trans['date'].min()
    latest_trans: np.datetime64 = trans['date'].max()

    try:
        eras: pd.DataFrame = load_eras(eras_url, earliest_trans, latest_trans)
    except error.URLError:
        eras = pd.DataFrame()

    data = dict(trans=trans.to_json(orient='split', date_format='%Y%m%d'),
                eras=eras.to_json(orient='split', date_format='%Y%m%d'))

    return [json.dumps(data)]


@app.callback(
    [Output('meta_data', 'children'),
     Output('account_tree', 'children'),
     Output('records', 'children')],
    [Input('data_store', 'children')])
def load_data(data_store) -> Iterable:
    """ When data store changes, refresh all of the data meta-information
    and display """

    trans, eras, account_tree, earliest_trans, latest_trans = data_from_json_store(data_store)

    meta_info: list = [f'Data loaded: {len(trans)} records',
                       f'Earliest record: {pretty_date(earliest_trans)}',
                       f'Latest record: {pretty_date(latest_trans)}',
                       f'Eras loaded: {len(eras)}']
    meta_html: list = [html.Div(children=x) for x in meta_info]

    records: list = ['first 5 records'] + trans.head(n=5).values.tolist() + \
        [''] + ['last 5 records'] + trans.tail(n=5).values.tolist()
    records_html: List[str] = [html.Div(children=x, className='code_row') for x in records]

    tree_records: List[str] = [f'Tree nodes: {len(account_tree)}'] + [x.tag for x in account_tree.all_nodes()]

    account_tree_html: List[str] = [html.Div(children=x, className='code_row') for x in tree_records]

    return [meta_html, account_tree_html, records_html]
