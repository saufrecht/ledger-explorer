import base64
from dataclasses import dataclass
import io
import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
from treelib import Tree
from typing import Iterable
import urllib


from app import app

from utils import ATree, CONSTANTS, LError, get_descendents


class LoadError(LError):
    """ Errors during transaction, Account Tree, and Eras data load """
    def __init__(self, message):
        self.message = message


@dataclass
class Controls():
    """ Class to hold everything to do with settings & controls """
    # Default to the column headings of Gnucash exports
    account_label: str = 'Account Name'
    amount_label: str = 'Amount Num.'
    date_label: str = 'Date'
    desc_label: str = 'Description'
    fullname_label: str = 'Full Account Name'
    init_time_span: str = True
    init_time_res: int = 3
    ds_data_title: str = 'Ledger'
    ds_delimiter: str = CONSTANTS['delim']
    ds_unit: str = CONSTANTS['unit']
    ds_label: str = CONSTANTS['ds_label']
    bs_label: str = CONSTANTS['bs_label']
    ex_label: str = CONSTANTS['ex_label']
    ex_account_filter: list = ('Income', 'Expenses')
    bs_account_filter: list = ('Debt', 'Equity', 'Liabilities')

    def to_json(self):
        """ Convert controls to JSON via dict structure """
        return json.dumps(self, default=lambda x: x.__dict__)

    @classmethod
    def from_json(cls, json_data: str):
        """ Convert controls to JSON via dict structure """
        if json_data and isinstance(json_data, str) and len(json_data) > 0:
            body = json.loads(json_data, object_hook=lambda d: SimpleNamespace(**d))
            return body
        else:
            return Controls()


def load_eras(data, earliest_date, latest_date):
    """
    If era data file is available, use it to construct
    arbitrary bins
    """
    try:
        data = data.replace(r'^\s*$', np.nan, regex=True)
        data['date_start'] = data['date_start'].astype({'date_start': 'datetime64'})
        data['date_end'] = data['date_end'].astype({'date_end': 'datetime64'})
        # TODO: filter out out-of-order rows
    except Exception as E:
        app.logger.critical(f'Error parsing eras file: {E}')
        return pd.DataFrame()

    data = data.sort_values(by=['date_start'], ascending=True)
    data = data.reset_index(drop=True).set_index('name')

    # if the first start or last end is missing, substitute earliest/lastest possible date
    if pd.isnull(data.iloc[0].date_end):
        data.iloc[0].date_end = latest_date
    if pd.isnull(data.iloc[-1].date_start):
        data.iloc[-1].date_start = earliest_date

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


def rename_columns(data: pd.DataFrame, parameters: Controls) -> pd.DataFrame:
    """ Make all column names lower-case. Renames any mapped columns. """
    data.columns = [x.lower() for x in data.columns]  # n.b. Changes in place

    # TODO: once trans is a class, then just iterate with vars(Trans()).items()

    # take all of the input column names and rename them to the standard internal names
    cols = [(parameters.account_label, 'account'), (parameters.amount_label, 'amount'), (parameters.desc_label, 'description'), (parameters.fullname_label, 'full account name'), (parameters.date_label, 'date')]  # NOQA

    for col_a, col_b in cols:
        lcol_a = col_a.lower()
        if lcol_a and len(lcol_a) > 0 and lcol_a in data.columns:
            data[col_b] = data[lcol_a]
    return data


def load_input_file(input_file, url: str, filename: str) -> Iterable:
    """ Load a tabular data file (CSV, maybe XLS) from URL or file upload."""

    data: pd.DataFrame() = pd.DataFrame()
    result_meta: str = None
    new_filename: str = None
    if input_file:
        try:
            data: pd.DataFrame = parse_base64_file(input_file, filename)
            result_meta: str = f'File {filename} loaded, {len(data)} records.'
            new_filename = filename
        except urllib.error.HTTPError as E:
            result_meta = f'Error loading {filename}: {E}'
    elif url:
        try:
            data: pd.DataFrame = pd.read_csv(url, thousands=',', low_memory=False)
            result_meta: str = f'{url} loaded, {len(data)} records.'
            new_filename = url
        except (urllib.error.URLError, FileNotFoundError) as E:
            result_meta = f'Error loading {url}: {E}'

    return [new_filename, data, result_meta]


def load_transactions(data: pd.DataFrame):
    """
    Load a json_encoded dataframe matching the transaction export format from Gnucash.
    Uses column names CONSTANTS['account_col'], 'Description', 'Memo', Notes',
    CONSTANTS['fan_col'], 'Date', 'Amount Num.'
    """
    if len(data) == 0:
        raise LError('No data in file')

    # try to parse date.  TODO: Maybe move this to a function so it can be re-used in era parsing
    try:
        data['date'] = data['date'].astype({'date': 'datetime64'})
    except ValueError:
        # try to parse date a different way: accept YYYY
        data['date'] = pd.to_datetime(data['date'], format='%Y').astype({'date': 'datetime64[ms]'})

    data['amount'] = data['amount'].replace(to_replace=',', value='')
    data['amount'] = data['amount'].fillna(value=0)
    data['amount'] = data['amount'].astype(float, errors='ignore').round(decimals=0).astype(int, errors='ignore')

    #######################################################################
    # Gnucash-specific filter:
    # Gnucash doesn't include the date, description, or notes for transaction splits.  Fill them in.
    try:
        data['date'] = data['date'].fillna(method='ffill')
        data['description'] = data['description'].fillna(method='ffill').astype(str)
        data['notes'] = data['notes'].fillna(method='ffill').astype(str)
        data['notes'] = data['notes']
        data['description'] = (data['description'] + ' ' + data['memo'] + ' ' + data['notes']).str.strip()
    except Exception as E:  # NOQA
        # TODO: handle this better, so it runs only when gnucash is indicated
        pass

    #######################################################################

    data.fillna('', inplace=True)  # Any remaining fields with invalid numerical data should be text fields
    data.where(data.notnull(), None)

    trans = data[['date', 'description', 'amount', CONSTANTS['account_col'], CONSTANTS['fan_col']]]
    return trans


def convert_raw_data(raw_trans: pd.DataFrame, raw_tree: pd.DataFrame, raw_eras: pd.DataFrame, parameters: Controls) -> Iterable:  # NOQA
    """ Try and convert the provided data into usable transaction, tree,
    and era data.  Includes column renaming, and field-level business logic.
    Return dataframe of transactions, tree object of atree, and
    dataframe of eras.

    """
    if not isinstance(raw_trans, pd.DataFrame) or len(raw_trans) == 0:
        raise LoadError('Tried to load transaction data and failed')
    try:
        raw_trans = rename_columns(raw_trans, parameters)
        trans: pd.DataFrame = load_transactions(raw_trans)
    except Exception as E:
        raise LoadError(f'Could not import the transactions because: {type(E)}, {E}')

    atree: Tree = ATree()
    # look for account tree in separate tree file.  Apply renaming, if any.
    if len(raw_tree) > 0:
        raw_tree = rename_columns(raw_tree, parameters)
        if CONSTANTS['fan_col'] in raw_tree.columns:
            atree = ATree.from_names(raw_tree[CONSTANTS['fan_col']], parameters.ds_delimiter)
        elif set([CONSTANTS['parent_col'], CONSTANTS['account_col']]).issubset(raw_tree.columns):
            atree = ATree.from_parents(raw_tree[[CONSTANTS['account_col'], CONSTANTS['parent_col']]])

    # if we don't have a viable atree from an external file,
    # try to get it from the trans file.
    if len(atree) == 0:
        if 'full account name' in trans.columns:
            atree = ATree.from_names(trans[CONSTANTS['fan_col']], parameters.ds_delimiter)
        elif set([CONSTANTS['parent_col'], 'account name']).issubset(trans.columns):
            atree = ATree.from_parents(trans[[CONSTANTS['account_col'], CONSTANTS['parent_col']]])

    # Because treelib can't be restored from JSON, store it denormalized in
    # trans[CONSTANTS['fan_col']] (for simplicity, overwrite if it's already there)
    if len(atree) > 0:
        trans = ATree.stuff_tree_into_trans(trans, atree)

    # Special case for Gnucash and other ledger data.  TODO: generalize
    # mangle amounts signs for known account types, to make graphs least surprising
    for account in [ra for ra in CONSTANTS['root_accounts'] if ra['flip_negative'] is True]:
        if atree.get_node(account['id']):
            trans['amount'] = np.where(trans[CONSTANTS['account_col']].isin(get_descendents(account['id'], atree)),
                                       trans['amount'] * -1,
                                       trans['amount'])

    earliest_trans: np.datetime64 = trans['date'].min()
    latest_trans: np.datetime64 = trans['date'].max()

    if len(raw_eras) > 0:
        eras: pd.DataFrame = load_eras(raw_eras, earliest_trans, latest_trans)
    else:
        eras = pd.DataFrame()

    return (trans, atree, eras)
