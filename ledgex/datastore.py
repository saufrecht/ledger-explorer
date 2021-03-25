import json
import pandas as pd
from numpy import datetime64
from dataclasses import dataclass

from app import app
from params import CONST
from atree import ATree


@dataclass
class Datastore:
    """ Class to hold all data to be presented """

    trans: pd.DataFrame = pd.DataFrame  # TODO: would it make any difference to make this an HDFStore?
    eras: pd.DataFrame = pd.DataFrame
    account_tree: ATree = ATree()
    trans_filename: str = ""
    eras_filename: str = ""
    account_filename: str = ""
    earliest_trans: datetime64 = None
    latest_trans: datetime64 = None

    def to_json(self):
        """ Convert data to JSON via dict structure """
        return json.dumps(self, default=lambda x: x.__dict__)

    def __len__(self):
        """Trans is the essential part of datastore, so use its length
        as the length of the whole datastore.  This works with
        preventupdate_if_empty so that a datastore with transactions
        but nothing else still passes the test."""
        return len(self.trans)

    @classmethod
    def from_json(cls, json_data, filter: list = []):
        """Parse data stored in Dash JSON component, in order to move data
        between different callbacks in Dash.  Returns the transaction
        list, account tree, and eras.  A distinct account tree, if
        present in the data, pre-filters the transaction list.  An
        explicit filter, if provided, filters all descendent accounts.
        Also includes earliest and latest trans (post-filter, if any)
        for convenience.

        """
        if (not json_data) or (len(json_data) == 0):
            return None
        data = json.loads(json_data)
        if not data or len(data) == 0:
            return None
        trans = pd.read_json(
            data["trans"],
            dtype={
                "date": "datetime64[ms]",
                "description": "object",
                "amount": "int64",
                CONST["account_col"]: "object",
                CONST["fan_col"]: "object",
            },
        )
        atree = ATree.from_json(data['atree'])
        atree_accounts = [atree.root] + atree.get_descendent_ids()
        trans = trans[trans[CONST["account_col"]].isin(atree_accounts)]
        filter_accounts: list = []
        for account in filter:
            filter_accounts = (
                filter_accounts + [account] + atree.get_descendent_ids(account)
            )
        if len(filter_accounts) > 0:
            trans = trans[trans[CONST["account_col"]].isin(filter_accounts)]
        # rebuild account tree from filtered trans
        # TODO: eras should be much tougher parser
        try:
            eras = pd.read_json(
                data["eras"],
                dtype={
                    "index": "str",
                    "date_start": "datetime64",
                },
            )
            # No idea why era dates suddenly became int64 instead of datetime.  Kludge it back.
        except Exception as E:
            app.logger.warning(f"Error parsing eras: {E}")
            eras = pd.DataFrame()
        if len(eras) > 0:
            eras["date_start"] = eras["date_start"].astype("datetime64[ms]")
            eras = eras.set_index("name")
        trans_filename = data.get("trans_filename")
        eras_filename = "placeholder"
        account_filename = "placeholder"
        earliest_trans: datetime64 = trans["date"].min()
        latest_trans: datetime64 = trans["date"].max()

        return Datastore(
            trans=trans,
            eras=eras,
            account_tree=atree,
            trans_filename=trans_filename,
            eras_filename=eras_filename,
            account_filename=account_filename,
            earliest_trans=earliest_trans,
            latest_trans=latest_trans,
        )
