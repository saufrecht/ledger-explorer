import base64
import io
import json
from typing import Iterable, List
from urllib.parse import parse_qs
import urllib
from treelib import Tree

import numpy as np
import pandas as pd

import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from utils import load_eras, load_transactions, get_descendents, pretty_date, pretty_records
from utils import ROOT_ACCOUNTS
from utils import LError, ATree
from utils import PARENT_COL, ACCOUNT_COL, FAN_COL, DELIM, GC_COL_LABELS


from app import app


SAMPLE_TRANS_URL = 'https://ledge.uprightconsulting.com/s/sample_transaction_data.csv'


class LoadError(LError):
    """ Errors during data load """

    def __init__(self, message):
        self.message = message


def load_input_file(input_file, url: str, filename: str) -> Iterable:
    """ Load a tabular data file (CSV, maybe XLS) from URL or file upload."""

    data: pd.DataFrame() = pd.DataFrame()
    raw_text: str = None
    new_filename: str = None
    if input_file:
        try:
            data: pd.DataFrame = parse_base64_file(input_file, filename)
            raw_text: str = f'File {filename} loaded, {len(data)} records.'
            new_filename = filename
        except urllib.error.HTTPError as E:
            raw_text = f'Error loading {filename}: {E}'
    elif url:
        try:
            data: pd.DataFrame = pd.read_csv(url, thousands=',', low_memory=False)
            raw_text: str = f'{url} loaded, {len(data)} records.'
            new_filename = url
        except (urllib.error.URLError, FileNotFoundError) as E:
            raw_text = f'Error loading {url}: {E}'

    return [new_filename, data, raw_text]


def rename_columns(data: pd.DataFrame, col_labels: List):
    """ Make all column names lower-case. Renames any mapped columns."""
    # TODO: implement an actual mechanism for storing input filters
    # if not col_labels:
    # Gnucash-specific filter
    #    col_labels = [('amount num.', 'amount'), ('account name', ACCOUNT_COL)]

    data.columns = [x.lower() for x in data.columns]  # n.b. Changes in place
    for col_a, col_b in col_labels:
        lcol_a = col_a.lower()
        lcol_b = col_b.lower()
        if lcol_a and len(lcol_a) > 0 and lcol_a in data.columns:
            data[lcol_b] = data[lcol_a]
    return data


def convert_raw_data(raw_trans: pd.DataFrame, raw_tree: pd.DataFrame, raw_eras: pd.DataFrame, col_labels: List, delim: str) -> Iterable:  # NOQA
    """ Try and convert the provided data into usable transaction, tree,
    and era data.  Includes column renaming, and field-level business logic.
    Return dataframe of transactions, tree object of atree, and
    dataframe of eras.

    """
    if not isinstance(raw_trans, pd.DataFrame) or len(raw_trans) == 0:
        raise PreventUpdate

    try:
        raw_trans = rename_columns(raw_trans, col_labels)
        trans: pd.DataFrame = load_transactions(raw_trans)
    except Exception as E:
        raise LoadError(f'Could not import the transactions because: {type(E)}, {E}')

    atree: Tree = ATree()
    # look for account tree in separate tree file.  Apply renaming, if any.
    if len(raw_tree) > 0:
        raw_tree = rename_columns(raw_tree, col_labels)
        if FAN_COL in raw_tree.columns:
            atree = ATree.from_names(raw_tree[FAN_COL], delim)
        elif set([PARENT_COL, ACCOUNT_COL]).issubset(raw_tree.columns):
            atree = ATree.from_parents(raw_tree[[ACCOUNT_COL, PARENT_COL]])

    # if we don't have a viable atree from an external file,
    # try to get it from the trans file.
    if len(atree) == 0:
        if 'full account name' in trans.columns:
            atree = ATree.from_names(trans[FAN_COL], delim)
        elif set([PARENT_COL, 'account name']).issubset(trans.columns):
            atree = ATree.from_parents(trans[[ACCOUNT_COL, PARENT_COL]])

    # Because treelib can't be restored from JSON, store it denormalized in
    # trans[FAN_COL] (for simplicity, overwrite if it's already there)
    if len(atree) > 0:
        trans = ATree.stuff_tree_into_trans(trans, atree)

    # Special case for Gnucash and other ledger data.  TODO: generalize
    # mangle amounts signs for known account types, to make graphs least surprising
    for account in [ra for ra in ROOT_ACCOUNTS if ra['flip_negative'] is True]:
        if atree.get_node(account['id']):
            trans['amount'] = np.where(trans[ACCOUNT_COL].isin(get_descendents(account['id'], atree)),
                                       trans['amount'] * -1,
                                       trans['amount'])

    earliest_trans: np.datetime64 = trans['date'].min()
    latest_trans: np.datetime64 = trans['date'].max()

    if len(raw_eras) > 0:
        eras: pd.DataFrame = load_eras(raw_eras, earliest_trans, latest_trans)
    else:
        eras = pd.DataFrame()

    return (trans, atree, eras)


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
                html.H3('Transactions', className='col_heading', id='trans_heading'),
                html.Div(id='trans_status',
                         children=['No transactions']),
                dcc.Upload(id='trans_file',
                           className='upload_target',
                           children=[
                               html.Div(id='trans_filename',
                                        className='filename',
                                        children='Drop here or'),
                               html.A(id='trans_select',
                                      children=' Select a file'),
                           ]),
                dcc.Input(className='url_input',
                          id='trans_url',
                          persistence=True,
                          persistence_type='memory',
                          type='url',
                          value='',
                          placeholder='URL for transaction csv file'),
                html.Div(id='trans_loaded_meta'),
                html.Div(id='trans_parsed_meta'),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H3('Accounts', className='col_heading', id='atree_heading'),
                html.Div(id='atree_status',
                         children=['No accounts']),
                dcc.Upload(id='atree_file',
                           className='upload_target',
                           children=[
                               html.Div(id='atree_filename',
                                        className='filename',
                                        children='Drop here or'),
                               html.A(id='atree_select',
                                      children=' Select a file'),
                           ]),
                dcc.Input(className='url_input',
                          id='atree_url',
                          persistence=True,
                          persistence_type='memory',
                          type='url',
                          placeholder='URL for account csv file'),
                html.Div(id='atree_loaded_meta'),
                html.Div(id='atree_parsed_meta'),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H3('Custom Reporting Periods', className='col_heading', id='eras_heading'),
                html.Div(id='eras_status',
                         children=['No reporting periods']),
                dcc.Upload(id='eras_file',
                           className='upload_target',
                           children=[
                               html.Div(id='eras_filename',
                                        className='filename',
                                        children='Drop here or'),
                               html.A(id='eras_select',
                                      children=' Select a file'),
                           ]),
                dcc.Input(className='url_input',
                          id='eras_url',
                          persistence=True,
                          persistence_type='memory',
                          type='url',
                          placeholder='URL for report era csv file'),
                html.Div(id='eras_loaded_meta'),
                html.Div(id='eras_parsed_meta'),
            ]),
    ])


@app.callback([Output('trans_url', 'value'),
               Output('trans_url', 'n_submit')],
              # Output('atree_url', 'value'),
              # Output('eras_url', 'value')],
              [Input('url_reader', 'search')])
def parse_url_search(search: str):
    if search and isinstance(search, str) and len(search) > 0:
        search = search.lstrip('?')
        inputs = parse_qs(search)
        transu = inputs.get('transu')[0]
        if isinstance(transu, str):
            return [transu, 1]

    raise PreventUpdate


@app.callback([Output('trans_filename', 'children'),
               Output('trans_file_store', 'children'),
               Output('trans_loaded_meta', 'children'),
               Output('trans_select', 'children')],
              [Input('trans_file', 'filename'),
               Input('trans_file', 'contents'),
               Input('trans_url', 'n_submit')],
              state=[State('trans_url', 'value')])
def upload_trans(filename: str, content, submit: int, url: str) -> Iterable:
    """ Whenever a new transaction source is provided (uploaded file, or new URL),
    upload it and provide visual feedback.
    Can't use time comparison to see which one is more recent (because dcc.Upload
    doesn't have an upload timestamp), so punt that for now; need to reload the page
    to control whether url or file takes precedence."""
    if ((not filename or len(filename) == 0) and (not url or len(url) == 0)):
        raise PreventUpdate

    new_filename, data, text = load_input_file(content, url, filename)
    if len(data) == 0:
        return [None, None, text, ' Select a file']
    else:
        return [new_filename, data.to_json(), text, ' Select a different file', ]


@app.callback(
    [Output('atree_filename', 'children'),
     Output('atree_file_store', 'children'),
     Output('atree_loaded_meta', 'children'),
     Output('atree_select', 'children')],
    [Input('atree_file', 'filename'),
     Input('atree_file', 'contents'),
     Input('atree_url', 'n_submit')],
    state=[State('atree_url', 'value')])
def upload_atree(filename: str, content, submit: int, url: str) -> Iterable:
    """ Whenever a new atree source is provided (uploaded file, or new URL),
    upload it and provide visual feedback. """
    if ((not filename or len(filename) == 0) and (not url or len(url) == 0)):
        raise PreventUpdate

    new_filename, data, text = load_input_file(content, url, filename)
    if len(data) == 0:
        return [None, None, text, ' Select a file']
    else:
        return [new_filename, data.to_json(), text, ' Select a different file', ]


@app.callback(
    [Output('eras_filename', 'children'),
     Output('eras_file_store', 'children'),
     Output('eras_loaded_meta', 'children'),
     Output('eras_select', 'children')],
    [Input('eras_file', 'filename'),
     Input('eras_file', 'contents'),
     Input('eras_url', 'n_submit')],
    state=[State('eras_url', 'value')])
def upload_eras(filename: str, content, submit: int, url: str) -> Iterable:
    """ Whenever a new transaction source is provided (uploaded file, or new URL),
    upload it and provide visual feedback.
    Can't use time comparison to see which one is more recent (because dcc.Upload
    doesn't have an upload timestamp), so punt that for now; need to reload the page
    to control whether url or file takes precedence."""
    if ((not filename or len(filename) == 0) and (not url or len(url) == 0)):
        raise PreventUpdate

    new_filename, data, text = load_input_file(content, url, filename)
    if len(data) == 0:
        return [None, None, text, ' Select a file']
    else:
        return [new_filename, data.to_json(), text, ' Select a different file', ]


@app.callback(
    [Output('data_store', 'children'),
     Output('trans_status', 'children'),
     Output('atree_status', 'children'),
     Output('eras_status', 'children'),
     Output('files_status', 'children'),
     Output('trans_parsed_meta', 'children'),
     Output('atree_parsed_meta', 'children'),
     Output('eras_parsed_meta', 'children')],
    [Input('trans_file_store', 'children'),
     Input('atree_file_store', 'children'),
     Input('eras_file_store', 'children')],
    state=[State('control_store', 'children'),
           State('trans_filename', 'children')])
def load_and_transform(trans_file_store: str, atree_file_store: str, eras_file_store: str, control_store: str, trans_filename: str):  # NOQA

    """ When any of the input files changes in interim storage, reload all the data. """

    if not trans_file_store or len(trans_file_store) == 0:
        raise PreventUpdate

    try:
        trans_data = pd.read_json(trans_file_store)
    except LoadError as LE:
        error = f'Error loading transaction data: {LE.message}'
        return [None, error, None, None, error, error, None, None]

    atree_data: pd.DataFrame = pd.DataFrame()
    if atree_file_store:
        atree_data = pd.read_json(atree_file_store)

    eras_data: pd.DataFrame = pd.DataFrame()
    if eras_file_store:
        eras_data = pd.read_json(atree_file_store)

    if control_store:
        controls = json.loads(control_store)
        col_labels = controls.get('col_labels', [])
        delim = controls.get('delimiter', DELIM)
    else:
        col_labels = GC_COL_LABELS
        delim = DELIM

    try:
        trans, atree, eras = convert_raw_data(trans_data, atree_data, eras_data, col_labels, delim)
    except LoadError as LE:
        error = f'Error parsing input data: {LE.message}'
        return [None, error, None, None, error, error, None, None]

    # Generate status info.  TODO: clean up this hack with a Jinja2 template, or at least another function

    earliest_trans: np.datetime64 = trans['date'].min()
    latest_trans: np.datetime64 = trans['date'].max()

    trans_summary: str = f'File: {trans_filename} loaded, with {len(trans)} transactions'
    files_status: str = f'{trans_filename}, {len(trans)} transactions'
    trans_status_list: list = [f'Data loaded: {len(trans)} between {pretty_date(earliest_trans)} and {pretty_date(latest_trans)}']  # NOQA
    first_rec = pretty_records(trans.head(3))
    last_rec = pretty_records(trans.tail(3))
    records: list = ['=================='] + ['first and last 3 records'] + first_rec + ['=================='] + last_rec  # NOQA
    trans_status_list = trans_status_list + records

    atree_summary: str = None
    atree_status_list: list = []
    if atree and len(atree) > 0:
        atree_summary: str = f'{len(atree)} accounts'
        atree_list: list = [f'Account Tree loaded: {atree_summary}, {atree.depth()} levels deep', atree.show_to_string()]  # NOQA
        files_status = f'{files_status}, {atree_summary}.'

    eras_summary: str = None
    eras_status_list: list = []
    if len(eras) > 0:
        eras_summary: str = f'{len(eras)} reporting eras'
        eras_status_list = [eras_summary]
        files_status = f'{files_status}, {eras_summary}.'

    trans_detail: list = [html.Div(children=x) for x in trans_status_list]
    atree_detail: list = [html.Div(children=x) for x in atree_status_list]
    eras_detail: list = [html.Div(children=x) for x in eras_status_list]

    data = json.dumps({'trans': trans.to_json(),
                       'eras': eras.to_json()})
    return [data, trans_summary, atree_summary, eras_summary, files_status, trans_detail, atree_detail, eras_detail]
