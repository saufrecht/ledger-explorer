import base64
import io
import json
from typing import Iterable, List, Dict
import urllib
from treelib import Tree

import numpy as np
import pandas as pd

import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import load_eras, load_transactions, get_descendents, data_from_json_store, pretty_date, pretty_records
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
    """ Take the input to the upload control, assuming it's a csv,
    and return a dataframe"""
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
            className='ds_column',
            children=[
                html.H3('Transactions', id='trans_heading'),
                html.Div(
                    id='trans_meta'),
                dcc.Upload(
                    id='trans_file',
                    className='upload_target',
                    children=html.Div([
                        'Drop here, or ',
                        html.A('Select File')])),
                html.Div(
                    className='flex_forward',
                    children=[
                        dcc.Input(
                            className='url_input',
                            id='trans_url',
                            persistence=True,
                            persistence_type='memory',
                            type='url',
                            # value="https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/CO2%20emissions%20(Aggregate%20dataset%20(2020))/CO2%20emissions%20(Aggregate%20dataset%20(2020)).csv",  # NOQA
                            value='https://ledge.uprightconsulting.com/s/sample_transaction_data.csv',
                            placeholder='URL for transaction csv file'),
                        html.Button('Load URL', id='trans_url_load_button'),
                    ]),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H4('Custom Account Tree', id='atree_heading'),
                html.Div(
                    id='atree_meta',
                    children=['None Loaded']),
                dcc.Upload(
                    id='atree_file',
                    className='upload_target',
                    children=html.Div([
                        'Drop here, or ',
                        html.A('Select File')])),
                html.Div(
                    className='flex_forward',
                    children=[
                        dcc.Input(
                            className='url_input',
                            id='atree_url',
                            persistence=True,
                            persistence_type='memory',
                            type='url',
                            value='',
                            placeholder='URL for atreeaction csv file'),
                        html.Button('Load URL', id='atree_url_load_button'),
                    ]),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H4('Custom Reporting Periods', id='eras_heading'),
                html.Div(
                    id='eras_meta',
                    children=['None Loaded']),
                dcc.Upload(
                    id='eras_file',
                    className='upload_target',
                    children=html.Div([
                        'Drop here, or ',
                        html.A('Select File')])),
                html.Div(
                    className='flex_forward',
                    children=[
                        dcc.Input(
                            className='url_input',
                            id='eras_url',
                            type='url',
                            persistence=True,
                            persistence_type='memory',
                            value='',
                            placeholder='URL for custom reporting eras csv file'),
                        html.Button('Load URL', id='eras_url_load_button'),
                    ]),
            ]),
        html.Div(
            className='three_col',
            children=[

                html.Button('Reload Data', id='data_load_button'),
            ]),
    ])


@app.callback(
    [Output('trans_raw_store', 'children'),
     Output('trans_meta', 'children')],
    [Input('trans_url_load_button', 'n_clicks'),
     Input('trans_file', 'contents')],
    state=[State('trans_url', 'value'),
           State('trans_file', 'filename')])
def get_raw_trans(n_clicks: int, input_file, url: str, filename: str) -> Iterable:
    """ When a file is loaded, or the Load URL button is clicked, populate the raw data store for this file."""
    app.logger.info(f'get_raw_trans fired with url {url} and filename {filename} and n_clicks {n_clicks}.')
    raw_data: pd.DataFrame() = pd.DataFrame()
    if n_clicks:
        if url:
            try:
                raw_data: pd.DataFrame = pd.read_csv(url, thousands=',', low_memory=False)
                raw_text: str = f'{url} loaded, {len(raw_data)} records.'
            except urllib.error.URLError as E:
                raw_text = f'Error loading {url}: {E}'
        else:
            raise PreventUpdate
    else:
        if input_file:
            try:
                raw_data: pd.DataFrame = parse_base64_file(input_file, filename)
                raw_text: str = f'File {filename} loaded, {len(raw_data)} records.'
            except urllib.error.HTTPError as E:
                raw_text = f'Error loading {filename}: {E}'
        else:
            raise PreventUpdate

    data = raw_data.to_json()
    app.logger.info(f'  Meanwhile, trans_raw_store is {len(data)} big')
    return [data, raw_text]


@app.callback(
    [Output('atree_raw_store', 'children'),
     Output('atree_meta', 'children')],
    [Input('atree_url_load_button', 'n_clicks'),
     Input('atree_file', 'contents')],
    state=[State('atree_url', 'value'),
           State('atree_file', 'filename')])
def get_raw_atree(n_clicks: int, input_file, url: str, filename: str) -> Iterable:
    """ When a file is loaded, or the Load URL button is clicked, populate the raw data store for this file."""

    if n_clicks:
        if url:
            try:
                raw_data: pd.DataFrame = pd.read_csv(url, thousands=',', low_memory=False)
                raw_text: str = f'{url} loaded, {len(raw_data)} records.'
            except urllib.error.URLError as E:
                return [None, f'Error loading {url}: {E}']
        else:
            raise PreventUpdate
    else:
        if input_file:
            try:
                raw_data: pd.DataFrame = parse_base64_file(input_file, filename)
                raw_text: str = f'File {filename} loaded, {len(raw_data)} records.'
            except urllib.error.HTTPError:
                raise PreventUpdate

        else:
            raise PreventUpdate

    data = raw_data.to_json()
    return [data, raw_text]


@app.callback(
    [Output('eras_raw_store', 'children'),
     Output('eras_meta', 'children')],
    [Input('eras_url_load_button', 'n_clicks'),
     Input('eras_file', 'contents')],
    state=[State('eras_url', 'value'),
           State('eras_file', 'filename')])
def get_raw_eras(n_clicks: int, input_file, url: str, filename: str) -> Iterable:
    """ When a file is loaded, or the Load URL button is clicked, populate the raw data store for this file."""

    if n_clicks:
        if url:
            try:
                raw_data: pd.DataFrame = pd.read_csv(url, thousands=',', low_memory=False)
                raw_text: str = f'{url} loaded, {len(raw_data)} records.'
            except urllib.error.URLError as E:
                return [None, f'Error loading {url}: {E}']
        else:
            raise PreventUpdate
    else:
        if input_file:
            try:
                raw_data: pd.DataFrame = parse_base64_file(input_file, filename)
                raw_text: str = f'File {filename} loaded, {len(raw_data)} records.'
            except urllib.error.HTTPError:
                raise PreventUpdate

        else:
            raise PreventUpdate

    data = raw_data.to_json()
    return [data, raw_text]


@app.callback(
    [Output('data_store', 'children')],
    [Input('data_load_button', 'n_clicks')],
    state=[State('trans_raw_store', 'children'),
           State('atree_raw_store', 'children'),
           State('eras_raw_store', 'children'),
           State('control_store', 'children')])
def load_and_transform(n_clicks: int, trans_raw_store: str, atree_raw_store: str, eras_raw_store: str, control_store: str):  # NOQA
    if trans_raw_store:
        app.logger.info(f'load_and_transform fired with trans_raw_store {len(trans_raw_store)}')
    else:
        app.logger.info(f'load_and_transform fired with 0 trans_raw_store')
    """ Go through all of the data input controls (uploads and URLs),
    clean up all the raw data, and put it into the data_store for the
    tab pages to use.  Business logic in this function is only at the
    file level; subfunctions can work at the field level.

    """
    if not n_clicks or n_clicks == 0 or not trans_raw_store:
        raise PreventUpdate

    try:
        raw_trans = pd.read_json(trans_raw_store)

        raw_tree = pd.DataFrame()
        if atree_raw_store:
            raw_tree = pd.read_json(atree_raw_store)

        raw_eras = pd.DataFrame()
        if eras_raw_store:
            raw_eras = pd.read_json(eras_raw_store)

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

    except LoadError as LE:
        data = {'error': LE.message}

    return [json.dumps(data)]


@app.callback(
    [Output('trans_parsed_meta', 'children'),
     Output('atree_parsed_meta', 'children'),
     Output('eras_parsed_meta', 'children')],
    [Input('data_store', 'children')],
    state=[State('control_store', 'children')])
def update_metadata(data_store, control_store) -> Iterable:
    """ When data store changes, refresh all of the data meta-information
    and display """
    app.logger.info(f'update_metadata fired')

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

    first_rec = pretty_records(trans.head(3))
    last_rec = pretty_records(trans.tail(3))

    records: list = ['==================='] + ['first and last 3 records'] + first_rec + ['==================='] + last_rec  # NOQA
    trans_list = trans_list + records

    trans_html: list = [html.Div(children=x) for x in trans_list]
    atree_html: list = [html.Div(children=x) for x in atree_list]
    eras_html: list = [html.Div(children=x) for x in eras_list]

    return [trans_html, atree_html, eras_html]
