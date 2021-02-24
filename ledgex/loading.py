import base64
import io
import urllib
from typing import Iterable

import numpy as np
import pandas as pd
from treelib import Tree

from ledgex.app import app
from ledgex.atree import ATree
from ledgex.params import CONST, Params
from ledgex.errors import LoadError


def load_eras(data, earliest_date, latest_date):
    """
    If era data file is available, use it to construct
    arbitrary bins
    """
    try:
        data = data.replace(r"^\s*$", np.nan, regex=True)
        data["date_start"] = data["date_start"].astype({"date_start": "datetime64"})
        data["date_end"] = data["date_end"].astype({"date_end": "datetime64"})
        # TODO: filter out out-of-order rows
    except Exception as E:
        app.logger.warning(f"Error parsing eras file: {E}")
        return pd.DataFrame()

    data = data.sort_values(by=["date_start"], ascending=True)
    data = data.reset_index(drop=True).set_index("name")

    # if the first start or last end is missing, substitute earliest/lastest possible date
    # TODO: this is broken because sorting is not reliable, because data containing NaN is not sorted
    # to the right place for this logic to work
    if pd.isnull(data.iloc[0].date_start):
        data.iloc[-1].date_start = earliest_date
    if pd.isnull(data.iloc[-1].date_end):
        data.iloc[0].date_end = latest_date
    return data


def parse_base64_file(content: str, filename: str) -> pd.DataFrame:
    """Take the input to the upload control, assuming it's a csv,
    and return a dataframe"""
    content_type, content_string = content.split(",")
    decoded = base64.b64decode(content_string + "===")  # prevent padding errors
    data: pd.DataFrame = pd.DataFrame()
    try:
        if "csv" in filename:
            # Assume that the user uploaded a CSV file
            data = pd.read_csv(
                io.StringIO(decoded.decode("utf-8")), thousands=",", low_memory=False
            )
        elif "xls" in filename:
            # Assume that the user uploaded an excel file
            data = pd.read_excel(io.BytesIO(decoded))
    except Exception as E:
        raise LoadError(f"Unable to load file {filename} because {E}")

    return data


def rename_columns(data: pd.DataFrame, parameters: Params) -> pd.DataFrame:
    """ Make all column names lower-case. Renames any mapped columns. """
    data.columns = [x.lower() for x in data.columns]  # n.b. Changes in place

    # TODO: once trans is a class, then just iterate with vars(Trans()).items()

    # take all of the input column names and rename them to the standard internal names
    cols = [
        (parameters.account_label, "account"),
        (parameters.amount_label, "amount"),
        (parameters.desc_label, "description"),
        (parameters.fan_label, "full account name"),
        (parameters.date_label, "date"),
    ]  # NOQA

    for col_a, col_b in cols:
        lcol_a = col_a.lower()
        if lcol_a and len(lcol_a) > 0 and lcol_a in data.columns:
            data[col_b] = data[lcol_a]
    return data


def load_input_file(input_file=None, url=None, filename=None) -> Iterable:
    """ Load a tabular data file (CSV, maybe XLS) from URL or file upload."""
    data: pd.DataFrame() = pd.DataFrame()
    result_meta: str = ''
    new_filename: str = ''
    # TODO: trim whitespace from column titles
    if input_file:
        try:
            data = parse_base64_file(input_file, filename)
            result_meta = f"File {filename} loaded, {len(data)} records."
            new_filename = filename
        except urllib.error.HTTPError as E:
            result_meta = f"Error loading file {filename}: {E}"
        except pd.errors.ParserError as E:
            result_meta = f"Error parsing file {filename}: {E}"
    elif isinstance(url, str):
        try:
            data = pd.read_csv(url, thousands=",", low_memory=False)
            result_meta = f"{url} loaded, {len(data)} records."
            new_filename = url
        except (urllib.error.URLError, FileNotFoundError) as E:
            result_meta = f"Error loading URL {url}: {E}"
        except (pd.errors.ParserError, ImportError) as E:
            result_meta = f"Error parsing file {filename}: {E}"

    return [new_filename, data, result_meta]


def load_transactions(data: pd.DataFrame):
    """
    Load a json_encoded dataframe matching the transaction export format from Gnucash.
    Uses column names CONST['account_col'], 'Description', 'Memo', Notes',
    CONST['fan_col'], 'Date', 'Amount Num.'
    """
    if len(data) == 0:
        raise LoadError("No data in file")

    # try to parse date.  TODO: Maybe move this to a function so it can be re-used in era parsing
    try:
        data["date"] = data["date"].astype({"date": "datetime64"})
    except ValueError:
        # try to parse date a different way: accept YYYY
        data["date"] = pd.to_datetime(data["date"], format="%Y").astype(
            {"date": "datetime64[ms]"}
        )

    data["amount"] = data["amount"].replace(to_replace=",", value="")
    data["amount"] = data["amount"].fillna(value=0)
    data["amount"] = (
        data["amount"]
        .astype(float, errors="ignore")
        .round(decimals=0)
        .astype(int, errors="ignore")
    )

    #######################################################################
    # Gnucash-specific filter:
    # Gnucash doesn't include the date, description, or notes for transaction splits.  Fill them in.
    try:
        data["date"] = data["date"].fillna(method="ffill")
        data["description"] = (
            data["description"].fillna(method="ffill", limit=1).fillna("").astype(str)
        )
        data["notes"] = (
            data["notes"].fillna(method="ffill", limit=1).fillna("").astype(str)
        )
        data["memo"] = (
            data["memo"].fillna(method="ffill", limit=1).fillna("").astype(str)
        )
        data["description"] = data[["description", "notes", "memo"]].agg(
            " ".join, axis=1
        )

    except Exception as E:  # NOQA
        # TODO: handle this better, so it runs only when gnucash is indicated
        pass

    #######################################################################

    data.fillna(
        "", inplace=True
    )  # Any remaining fields with invalid numerical data should be text fields
    data.where(data.notnull(), None)

    trans = data[
        ["date", "description", "amount", CONST["account_col"], CONST["fan_col"]]
    ]
    return trans


def convert_raw_data(
    raw_trans: pd.DataFrame,
    raw_tree: pd.DataFrame,
    raw_eras: pd.DataFrame,
    parameters: Params,
) -> Iterable:  # NOQA
    """Try and convert the provided data into usable transaction, tree,
    and era data.  Includes column renaming, and field-level business logic.
    Return dataframe of transactions, tree object of atree, and
    dataframe of eras.

    """
    if not isinstance(raw_trans, pd.DataFrame) or len(raw_trans) == 0:
        raise LoadError("Tried to load transaction data and failed")
    try:
        raw_trans = rename_columns(raw_trans, parameters)
        trans: pd.DataFrame = load_transactions(raw_trans)
    except Exception as E:
        raise LoadError(f"Could not import the transactions because: {type(E)}, {E}")
    atree: Tree = ATree()

    # look for account tree in separate tree file.
    if len(raw_tree) > 0:
        # apply column renaming parameters before loading
        raw_tree = rename_columns(raw_tree, parameters)
        if CONST["fan_col"] in raw_tree.columns:
            atree = ATree.from_names(
                raw_tree[CONST["fan_col"]], parameters.ds_delimiter
            )
        elif set([CONST["parent_col"], CONST["account_col"]]).issubset(
            raw_tree.columns
        ):
            atree = ATree.from_parents(
                raw_tree[[CONST["account_col"], CONST["parent_col"]]]
            )
    # Or, if we don't have a viable atree from an external file,
    # try to get it from the trans file
    if len(atree) == 0:
        if "full account name" in trans.columns:
            atree = ATree.from_names(trans[CONST["fan_col"]], parameters.ds_delimiter)
        elif set([CONST["parent_col"], "account name"]).issubset(trans.columns):
            atree = ATree.from_parents(
                trans[[CONST["account_col"], CONST["parent_col"]]]
            )

    # Because treelib can't be restored from JSON, store it denormalized in
    # trans[CONST['fan_col']] (for simplicity, overwrite if it's already there)
    if len(atree) > 0:
        trans = ATree.stuff_tree_into_trans(trans, atree)

    # Special case for Gnucash and other ledger data.
    # TODO: generalize mangle amounts signs for known account types, to make graphs
    # least surprising Maybe use the account type field from GnuCash to determine
    # what to flip.

    for account in [ra for ra in CONST["root_accounts"] if ra["flip_negative"] is True]:
        if atree.get_node(account["id"]):
            trans["amount"] = np.where(
                trans[CONST["account_col"]].isin(atree.get_descendents(account["id"])),
                trans["amount"] * -1,
                trans["amount"],
            )

    earliest_trans: np.datetime64 = trans["date"].min()
    latest_trans: np.datetime64 = trans["date"].max()

    if len(raw_eras) > 0:
        eras: pd.DataFrame = load_eras(raw_eras, earliest_trans, latest_trans)
    else:
        eras = pd.DataFrame()

    return (trans, atree, eras)
