import json
import pandas as pd
from numpy import datetime64
from dataclasses import dataclass
from params import CONST
from atree import ATree

from app import app


@dataclass
class Datastore:
    """ Class to hold all data to be presented """

    trans: pd.DataFrame = pd.DataFrame
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
        """Trans is the essential part of datastore so return that length.
        This is implemented so that require_or_raise works without a special
        case for datastore."""
        return len(self.trans)

    @classmethod
    def from_json(cls, json_data, filter: list = []):
        """Parse data stored in Dash JSON component, in order to move data
        between different callbacks in Dash.  Returns the transaction
        list, account tree, and eras.  If provided with a filter,
        pre-filters everything.  Also includes earliest and latest
        trans (post-filter, if any) for convenience.
        """
        if (not json_data) or (len(json_data) == 0):
            return None
        data = json.loads(json_data)
        data_error = data.get("error", None)
        if data_error:
            # TODO handle these errors better- probably kick them from origin instead of making this
            # pseudo-catching approach?
            return None
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
        orig_account_tree = ATree.from_names(trans[CONST["fan_col"]])
        filter_accounts: list = []
        for account in filter:
            filter_accounts = (
                filter_accounts + [account] + orig_account_tree.get_descendents(account)
            )
        if len(filter_accounts) > 0:
            trans = trans[trans[CONST["account_col"]].isin(filter_accounts)]
        # rebuild account tree from filtered trans
        account_tree = ATree.from_names(trans[CONST["fan_col"]])
        # TODO: should be much tougher parser
        try:
            eras = pd.read_json(
                data["eras"],
                dtype={
                    "index": "str",
                    "date_start": "datetime64",
                    "date_end": "datetime64",
                },
            )
            # No idea why era dates suddenly became int64 instead of datetime.  Kludge it back.
        except Exception as E:
            app.logger.warning(f"Error parsing eras: {E}")
            eras = pd.DataFrame()
        if len(eras) > 0:
            eras["date_start"] = eras["date_start"].astype("datetime64[ms]")
            eras["date_end"] = eras["date_end"].astype("datetime64[ms]")

        trans_filename = data.get("trans_filename")
        eras_filename = "placeholder"
        account_filename = "placeholder"
        earliest_trans: datetime64 = trans["date"].min()
        latest_trans: datetime64 = trans["date"].max()

        return Datastore(
            trans=trans,
            eras=eras,
            account_tree=account_tree,
            trans_filename=trans_filename,
            eras_filename=eras_filename,
            account_filename=account_filename,
            earliest_trans=earliest_trans,
            latest_trans=latest_trans,
        )
