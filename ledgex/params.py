import json
from dataclasses import dataclass
import inspect
from typing import Iterable
from urllib.parse import urlencode

CONST = {
    "parent_col": "parent account",  # TODO: move the column names into Trans class
    "account_col": "account",
    "fan_col": "full account name",
    "date_col": "date",
    "desc_col": "description",
    "amount_col": "amount",
    "gc_col_labels": [
        ("amount num.", "amount"),
        ("account name", "account"),
    ],  # defaults for gnucash
    "ex_label": "Cash Flow",
    "bs_label": "Balance Sheet",
    "ds_label": "Files",
    "delim": ":",
    "max_slices": 7,
    "unit": "$",
    "leaf_suffix": " [Leaf]",
    "other_prefix": "Other ",
    "subtotal_suffix": " [Subtotal]",
    "bug_report_md": "[Report an issue](https://github.com/saufrecht/"\
    + "ledger-explorer/issues/new?assignees=saufrecht&labels=bug&template=issue.md&title=)",
    "root_accounts": [
        {"id": "Assets", "flip_negative": False},
        {"id": "Equity", "flip_negative": True},
        {"id": "Expenses", "flip_negative": True},
        {"id": "Income", "flip_negative": True},
        {"id": "Liabilities", "flip_negative": True},
    ],
    "time_res_lookup": {
        "era": {"abbrev": "era", "label": "Era"},
        "year": {
            "abbrev": "Y",
            "format": "%Y",
            "label": "Year",
            "months": 12,
            "resample_keyword": "A",
        },
        "decade": {
            "abbrev": "10Y",
            "format": "%Y",
            "label": "Decade",
            "months": 120,
            "resample_keyword": "10A",
        },
        "quarter": {
            "abbrev": "Q",
            "format": "%Y-Q%q",
            "label": "Quarter",
            "months": 3,
            "resample_keyword": "Q",
        },
        "month": {
            "abbrev": "Mo",
            "format": "%Y-%b",
            "label": "Month",
            "months": 1,
            "resample_keyword": "M",
        },
    },
    "time_res_options": [
        {"value": "decade", "label": "Decade"},
        {"value": "year", "label": "Year"},
        {"value": "quarter", "label": "Quarter"},
        {"value": "month", "label": "Month"},
    ],
    "time_res_era_option": {"value": "era", "label": "Era"},
    "time_span_lookup": {
        "annual": {"label": "Annualized", "abbrev": " ⁄y", "months": 12},
        "monthly": {"label": "Monthly", "abbrev": " ⁄mo", "months": 1},
    },
    "time_span_options": [
        {"value": "annual", "label": "Annualized"},
        {"value": "monthly", "label": "Monthly"},
    ],
}


@dataclass
class Params:
    """ Class to hold everything to do with settings & parameters """
    account_label: str = None
    amount_label: str = None
    date_label: str = None
    desc_label: str = None
    fan_label: str = None
    init_time_span: str = None
    init_time_res: str = None
    ds_data_title: str = None
    ds_delimiter: str = None
    unit: str = None
    ds_label: str = None
    bs_label: str = None
    ex_label: str = None
    ex_roots: Iterable[str] = None
    bs_roots: Iterable[str] = None

    @classmethod
    def parse_account_string(cls, input: str):
        """Take a string which is a list of account names, separated by commas,
        and return it as a tuple"""
        if not isinstance(input, str):
            return ()
        input_list = input.split(",")
        stripped_list = [x.strip() for x in input_list]
        return tuple(stripped_list)

    def to_json(self):
        """ Convert parameters to JSON via dict structure """
        return json.dumps(self, default=lambda x: x.__dict__)

    def to_query_string(self):
        """ Convert parameters to query string"""
        field_dict = vars(self)
        field_string = urlencode(field_dict, doseq=True)
        return f'?{field_string}'

    @classmethod
    def from_dict(cls, env):
        return cls(**{
            k: v for k, v in env.items()
            if k in inspect.signature(cls).parameters
        })

    @classmethod
    def from_json(cls, json_data: str):
        """ Convert parameters from JSON via dict structure """
        if json_data and isinstance(json_data, str) and len(json_data) > 0:
            dict = json.loads(json_data)
            return Params.from_dict(dict)

    def fill_defaults(self):
        """If there is any user input, we should use it.  If user input is None,
        treat that as 'use the default' and use the default.  For transaction import table,
        use gnucash account labels as defaults.  For root account lists, parse to tuples."""
        if not self.account_label:
            self.account_label = "Account Name"
        if not self.amount_label:
            self.amount_label = "Amount Num."
        if not self.date_label:
            self.date_label = "Date"
        if not self.desc_label:
            self.desc_label = "Description"
        if not self.fan_label:
            self.fan_label = "Full Account Name"
        if not self.init_time_span:
            self.init_time_span = "monthly"
        if not self.init_time_res:
            self.init_time_res = "year"
        if not self.ds_data_title:
            self.ds_data_title = "Ledger"
        if not self.ds_delimiter:
            self.ds_delimiter = CONST["delim"]
        if not self.unit:
            self.unit = CONST["unit"]
        if not self.ds_label:
            self.ds_label = CONST["ds_label"]
        if not self.bs_label:
            self.bs_label = CONST["bs_label"]
        if not self.ex_label:
            self.ex_label = CONST["ex_label"]

    def __post_init__(self):
        if isinstance(self.ex_roots, str):
            self.ex_roots = self.parse_account_string(self.ex_roots)
        elif not self.ex_roots:
            self.ex_roots = ()
        if isinstance(self.bs_roots, str):
            self.bs_roots = self.parse_account_string(self.bs_roots)
        elif not self.bs_roots:
            self.bs_roots = ()
