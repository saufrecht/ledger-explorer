import base64
import io
import json
import inspect  # DEBUG
from typing import Iterable, List, Dict
import urllib
from treelib import Tree

import numpy as np
import pandas as pd

import dash_core_components as dcc
import dash_html_components as html

from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import load_eras, load_transactions, get_descendents, pretty_date
from utils import data_from_json_store
from utils import ROOT_ACCOUNTS
from utils import LError, ATree
from utils import PARENT_COL, ACCOUNT_COL, FAN_COL, DELIM, LABELS


from app import app


class LoadError(LError):
    """ Errors during data load """

    def __init__(self, message):
        self.message = message


def rename_columns(data: pd.DataFrame, labels: List):
    """ Make all column names lower-case. Renames any mapped columns."""
    # TODO: implement an actual mechanism for storing input filters
    # if not labels:
    # Gnucash-specific filter
    #    labels = [('amount num.', 'amount'), ('account name', ACCOUNT_COL)]

    data.columns = [x.lower() for x in data.columns]  # n.b. Changes in place
    for col_a, col_b in labels:
        lcol_a = col_a.lower()
        lcol_b = col_b.lower()
        if lcol_a and len(lcol_a) > 0 and lcol_a in data.columns:
            data[lcol_b] = data[lcol_a]
    return data


def convert_raw_info(raw_trans: pd.DataFrame, raw_tree: pd.DataFrame, raw_eras: pd.DataFrame, labels: List = LABELS, delim: str = DELIM) -> Dict:  # NOQA
    """ Try and convert the provided data into usable transaction, tree,
    and era data.  Includes column renaming, and field-level business logic.
    Return a dict of trans and account_tree and eras.

    """
    try:
        raw_trans = rename_columns(raw_trans, labels)
        trans: pd.DataFrame = load_transactions(raw_trans)
    except Exception as E:
        raise LoadError(f'Could not import the transactions because: {type(E)}, {E}')

    account_tree: Tree = ATree()
    # look for account tree in separate tree file
    if len(raw_tree) > 0:
        raw_tree = rename_columns(raw_tree, labels)
        if FAN_COL in raw_tree.columns:
            account_tree = ATree.from_names(raw_tree[FAN_COL], delim)
        elif set([PARENT_COL, ACCOUNT_COL]).issubset(raw_tree.columns):
            account_tree = ATree.from_parents(raw_tree[[ACCOUNT_COL, PARENT_COL]])

    # look for account tree in trans parent column
    if len(account_tree) == 0\
       and 'full_account name' not in trans.columns\
       and set([PARENT_COL, 'account name']).issubset(trans.columns):
        account_tree = ATree.from_parents(trans[ACCOUNT_COL, PARENT_COL])

    # Because treelib can't be restored from JSON, store it denormalized in
    # trans[FAN_COL] if it isn't already there.
    if len(account_tree) > 0 and 'full_account name' not in trans.columns:
        trans = ATree.stuff_tree_into_trans(trans, account_tree)

    # Special case for Gnucash and other ledger data.  TODO: generalize
    # mangle amounts signs for known account types, to make graphs least surprising
    for account in [ra for ra in ROOT_ACCOUNTS if ra['flip_negative'] is True]:
        if account_tree.get_node(account['id']):
            trans['amount'] = np.where(trans[ACCOUNT_COL].isin(get_descendents(account['id'], account_tree)),
                                       trans['amount'] * -1,
                                       trans['amount'])

    earliest_trans: np.datetime64 = trans['date'].min()
    latest_trans: np.datetime64 = trans['date'].max()

    if len(raw_eras) > 0:
        eras: pd.DataFrame = load_eras(raw_eras, earliest_trans, latest_trans)
    else:
        eras = pd.DataFrame()

    data = {'trans': trans.to_json(orient='split', date_format='%Y%m%d'),
            'eras': eras.to_json(orient='split', date_format='%Y%m%d')}
    return data


def parse_base64_file(content: str, filename: str) -> pd.DataFrame:
    """ Take the input to the upload control and return a dataframe"""
    content_type, content_string = content.split(',')

    decoded = base64.b64decode(content_string + '===')  # prevent padding errors
    data: pd.DataFrame = pd.DataFrame()
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            data = pd.read_csv(io.StringIO(decoded.decode('utf-8')),
                               thousands=',', low_memory=False)
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            data = pd.read_excel(io.BytesIO(decoded))
    except Exception as E:
        raise LoadError(f'Unable to load file {filename} because {E}')

    return data


layout = html.Div(
    className="layout_box col3",
    children=[
        html.Div(
            id='trans_file_store',
            className='hidden'),
        html.Div(
            id='eras_file_store',
            className='hidden'),
        html.Div(
            id='tree_file_store',
            className='hidden'),
        html.Div(
            id='url_store',
            className='hidden'),
        html.Div(
            className='ds_column',
            children=[
                html.H3('Data Source'),
                dcc.Upload(
                    id='transactions_file',
                    className='upload_target',
                    children=html.Div([
                        'Drop here, or ',
                        html.A('Select File')])),
                dcc.Input(
                    id='transactions_url',
                    type='url',
                    # value="https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/CO2%20emissions%20(Aggregate%20dataset%20(2020))/CO2%20emissions%20(Aggregate%20dataset%20(2020)).csv",  # NOQA
                    value='https://ledge.uprightconsulting.com/s/sample_transaction_data.csv',
                    placeholder='URL for transaction csv file'),
                html.Label(
                    id='trans_url_label',
                    htmlFor='transactions_url',
                    children='Transaction Source URL'),
                html.Div(
                    id='trans_meta',
                    className='code',
                    children=['Loaded: none']),
            ]),
        html.Div(
            className="ds_column",
            children=[
                html.H3('Account Tree'),
                dcc.Upload(
                    id='tree_file',
                    className='upload_target',
                    children=html.Div([
                        'Drop or ',
                        html.A('Select')])),
                dcc.Input(
                    id='tree_url',
                    type='url',
                    value='http://localhost/le_account_tree.csv',
                    placeholder='https://your/custom/account_tree.csv'),
                html.Label(
                    id='tree_url_label',
                    htmlFor='tree_url',
                    children='Account Tree source URL (optional)'),
                html.Pre(
                    id='atree_meta',
                    className='code',
                    children=['Loaded: none']),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H3('Custom Reporting Periods'),
                dcc.Upload(
                    id='eras_file',
                    className='upload_target',
                    children=html.Div([
                        'Drop or ',
                        html.A('Select')])),
                dcc.Input(
                    id='eras_url',
                    type='url',
                    value='http://localhost/le_eras.csv',
                    placeholder='URL for eras csv file'),
                html.Label(
                    id='eras_url_label',
                    htmlFor='eras_url',
                    children='Eras source URL (optional)'),
                html.Div(
                    id='eras_meta',
                    className='code',
                    children=['Loaded: none']),
            ]),
        html.Div(
            className='three_col',
            children=[
                html.Button('Reload URLs', id='url_load_button'),
                html.Button('Reload Data', id='data_load_button'),
            ]),
    ])


@app.callback(
    [Output('url_store', 'children'),
     Output('trans_url_label', 'children'),
     Output('tree_url_label', 'children'),
     Output('eras_url_label', 'children')],
    [Input('url_load_button', 'n_clicks')],
    state=[State('transactions_url', 'value'),
           State('tree_url', 'value'),
           State('eras_url', 'value')])
def load_urls(n_clicks: int, transactions_url: str, tree_url: str, eras_url: str) -> Iterable:
    """ When the Load from URL button is clicked, load the designated files
    and update the data store"""
    app.logger.info(f'DEBUG CALLBACK {inspect.currentframe().f_code.co_name}')
    if not transactions_url:
        raise PreventUpdate

    try:
        trans_data: pd.DataFrame = pd.read_csv(transactions_url, thousands=',', low_memory=False)
        trans_text: str = f'{transactions_url} loaded, {len(trans_data)} records.'
    except urllib.error.HTTPError:
        # except error.URLError as E:
        #    return [None, f'Error loading transactions: {E}', None, None]
        raise PreventUpdate

    try:
        tree_data: pd.DataFrame = pd.read_csv(tree_url)
        tree_text: str = f'{tree_url} loaded, {len(tree_data)} records.'
    except urllib.error.HTTPError:
        tree_data = pd.DataFrame()
        tree_text = None

    try:
        eras_data: pd.DataFrame = pd.read_csv(eras_url, thousands=',', low_memory=False)
        eras_text: str = f'File {eras_url} loaded, {len(eras_data)} records.'
    except urllib.error.HTTPError:
        eras_data: pd.DataFrame = pd.DataFrame()
        eras_text = None

    data = dict(trans=trans_data.to_json(orient='split', date_format='%Y%m%d'),
                tree=tree_data.to_json(orient='split'),
                eras=eras_data.to_json(orient='split', date_format='%Y%m%d'))

    return [json.dumps(data), trans_text, tree_text, eras_text]


@app.callback(
    [Output('trans_file_store', 'children')],
    [Input('transactions_file', 'contents')],
    state=[State('transactions_file', 'filename')])
def load_trans_files(trans_file, filename: str) -> Iterable:
    """ When the contents of the load box for transactions changes, reload transactions
    and update the data store"""
    app.logger.info(f'DEBUG CALLBACK {inspect.currentframe().f_code.co_name}')
    if not trans_file:
        raise PreventUpdate

    try:
        trans_data: pd.DataFrame = parse_base64_file(trans_file, filename)
    except urllib.error.HTTPError:
        raise PreventUpdate

    data = trans_data.to_json(orient='split', date_format='%Y%m%d')

    return data


@app.callback(
    [Output('tree_file_store', 'children')],
    [Input('tree_file', 'contents')],
    state=[State('tree_file', 'filename')])
def load_tree_files(tree_file, filename: str) -> Iterable:
    """ When the contents of the load box for tree changes, reload tree
    and update the data store"""
    app.logger.info(f'DEBUG CALLBACK {inspect.currentframe().f_code.co_name}')
    if not tree_file:
        raise PreventUpdate

    tree_data: pd.DataFrame = pd.DataFrame()
    try:
        tree_data: pd.DataFrame = parse_base64_file(tree_file, filename)
    except FileNotFoundError:
        pass

    data = tree_data.to_json(orient='split')

    return data


@app.callback(
    [Output('eras_file_store', 'children')],
    [Input('eras_file', 'contents')],
    state=[State('eras_file', 'filename')])
def load_era_files(eras_file, filename: str) -> Iterable:
    """ When the contents of the load box for eras changes, reload eras
    and update the data store"""
    app.logger.info(f'DEBUG CALLBACK {inspect.currentframe().f_code.co_name}')
    if not eras_file:
        raise PreventUpdate

    eras_data: pd.DataFrame = pd.DataFrame()
    try:
        eras_data: pd.DataFrame = parse_base64_file(eras_file, filename)
    except FileNotFoundError as E:
        return no_update, f'Could not import the eras because: {E}'

    data = eras_data.to_json(orient='split', date_format='%Y%m%d')

    return data


@app.callback(
    [Output('data_store', 'children')],
    [Input('data_load_button', 'n_clicks'),
     Input('url_store', 'children'),
     Input('trans_file_store', 'children'),
     Input('tree_file_store', 'children'),
     Input('eras_file_store', 'children'),
     Input('control_store', 'children')])
def transform_load(n_clicks: int, url_store: str, trans_file_store, tree_file_store, eras_file_store, control_store):  # NOQA
    """ Go through all of the data input controls (uploads and URLs),
    clean up all the raw data, and put it into the data_store for the
    tab pages to use.  Business logic in this function is only at the
    file level; subfunctions can work at the field level.

    """
    app.logger.info(f'DEBUG CALLBACK {inspect.currentframe().f_code.co_name}')
    if not url_store and not trans_file_store:
        raise PreventUpdate

    try:
        if trans_file_store:
            raw_trans = json.loads(trans_file_store)
        elif url_store:
            trans_from_url = json.loads(url_store).get('trans', None)
            if trans_from_url:
                raw_trans = pd.read_json(trans_from_url, orient='split')
    except LoadError as LE:
        data = {'error': LE.message}
        return [json.dumps(data)]

    raw_tree = pd.DataFrame()
    if tree_file_store:
        raw_tree = json.loads(tree_file_store)
    elif url_store:
        tree_from_url = json.loads(url_store).get('tree', None)
        if tree_from_url:
            raw_tree = pd.read_json(tree_from_url, orient='split')

    raw_eras = pd.DataFrame()
    if eras_file_store:
        raw_eras = json.loads(eras_file_store)
    elif url_store:
        eras_from_url = json.loads(url_store).get('eras', None)
        if eras_from_url:
            raw_eras = pd.read_json(eras_from_url, orient='split')

    if control_store:
        controls = json.loads(control_store)
        labels = controls.get('labels', [])
        delim = controls.get('delimiter', DELIM)
    else:
        labels = LABELS
        delim = DELIM

    try:
        data = convert_raw_info(raw_trans, raw_tree, raw_eras, labels, delim)
    except LoadError as LE:
        data = {'error': LE.message}

    return [json.dumps(data)]


@app.callback(
    [Output('trans_meta', 'children'),
     Output('atree_meta', 'children'),
     Output('eras_meta', 'children')],
    [Input('data_store', 'children')],
    state=[State('control_store', 'children')])
def update_metadata(data_store, control_store) -> Iterable:
    """ When data store changes, refresh all of the data meta-information
    and display """
    app.logger.info(f'DEBUG CALLBACK {inspect.currentframe().f_code.co_name}')
    if not data_store or data_store == '':
        raise PreventUpdate

    data_error: str = json.loads(data_store).get('error', None)
    if data_error:
        return [data_error, data_error, data_error]

    dd = data_from_json_store(data_store)
    trans = dd.get('trans')
    eras = dd.get('eras')
    account_tree = dd.get('account_tree')
    earliest_trans = dd.get('earliest_trans')
    latest_trans = dd.get('latest_trans')

    trans_list: list = [f'Data loaded: {len(trans)} records between {pretty_date(earliest_trans)} and {pretty_date(latest_trans)}']  # NOQA

    atree_list = [f'Account Tree loaded: {len(account_tree)}, {account_tree.depth()} levels deep']
    eras_list: list = [f'Eras loaded: {len(eras)}']

    records: list = ['first 5 records'] + trans.head(n=5).values.tolist() + \
        [''] + ['last 5 records'] + trans.tail(n=5).values.tolist()
    trans_list = trans_list + records

    trans_html: list = [html.Div(children=x) for x in trans_list]
    atree_html: list = [html.Div(children=x) for x in atree_list]
    eras_html: list = [html.Div(children=x) for x in eras_list]

    return [trans_html, atree_html, eras_html]
