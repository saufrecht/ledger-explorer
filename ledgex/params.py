import json
from dataclasses import dataclass
import inspect
from typing import Any, Iterable, Optional
from urllib.parse import parse_qs, urlencode

CONST: dict = {
    "parent_col": "parent account",  # TODO: move the column names into Ledger class
    "account_col": "account",
    "fan_col": "full account name",
    "date_col": "date",
    "desc_col": "description",
    "amount_col": "amount",
    "gc_col_labels": [
        ("amount num.", "amount"),
        ("account name", "account"),
    ],  # defaults for gnucash
    "co_label": "Compare",
    "cu_label": "Cumulative",  # Balance Sheet
    "ds_label": "Settings",
    "ex_label": "Explore",
    # "li_label": "Line Items" # or Transactions or Drill
    "pe_label": "Periodic",  # cash flow
    "sa_label": "Sankey",  # flow
    "delim": ":",
    "max_slices": 7,
    "unit": "$",
    "leaf_suffix": " [Leaf]",
    "other_prefix": "Other ",
    "subtotal_suffix": " [Subtotal]",
    "bug_report_md": "[Report an issue](https://github.com/saufrecht/"
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
            "format": "%Y-%m",
            "label": "Month",
            "months": 1,
            "resample_keyword": "M",
        },
        "week": {
            "abbrev": "W",
            "format": "%Y-W%V",
            "label": "Week",
            "months": 0.23,
            "resample_keyword": "W",
        },
        "day": {
            "abbrev": "D",
            "format": "%Y-%m-%d",
            "label": "Day",
            "months": 0.033,
            "resample_keyword": "D",
        },
    },
    "time_res_options": [
        {"value": "decade", "label": "Decade"},
        {"value": "year", "label": "Year"},
        {"value": "quarter", "label": "Quarter"},
        {"value": "month", "label": "Month"},
        {"value": "week", "label": "Week"},
        {"value": "day", "label": "Day"},
    ],
    "time_res_era_option": {"value": "era", "label": "Era"},
    "time_span_lookup": {
        "total": {"label": "Total", "abbrev": ""},
        "annual": {"label": "Average Yearly", "abbrev": " ⁄y", "months": 12},
        "monthly": {"label": "Average Monthly", "abbrev": " ⁄mo", "months": 1},
    },
    "time_span_options": [
        {"value": "total", "label": "Total"},
        {"value": "annual", "label": "Average Yearly"},
        {"value": "monthly", "label": "Average Monthly"},
    ],
}


@dataclass
class Params:
    """ Class to hold everything to do with settings & parameters """

    account_label: Optional[str] = None
    amount_label: Optional[str] = None
    date_label: Optional[str] = None
    desc_label: Optional[str] = None
    fan_label: Optional[str] = None
    init_time_span: Optional[str] = None
    init_time_res: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    ds_data_title: Optional[str] = None
    ds_delimiter: Optional[str] = None
    unit: Optional[str] = None
    co_label: Optional[str] = None
    cu_label: Optional[str] = None
    ds_label: Optional[str] = None
    ex_label: Optional[str] = None
    pe_label: Optional[str] = None
    sa_label: Optional[str] = None
    co_roots: Optional[Iterable[str]] = None
    cu_roots: Optional[Iterable[str]] = None
    ex_roots: Optional[Iterable[str]] = None
    pe_roots: Optional[Iterable[str]] = None
    sa_roots: Optional[Iterable[str]] = None

    @classmethod
    def cleanse_account_list_input(cls, input: Any):
        """Handle input that may come directly from parsed URL and
        ensure that it comes back a tuple of strings, with no leading or
        trailing whitespace"""
        if isinstance(input, str):
            input = input.split(",")
        if isinstance(input, list):
            stripped_list = [x.strip() for x in input]
            string_list = [x for x in stripped_list if isinstance(x, str)]
            return string_list
        return ()

    def to_json(self):
        """ Convert parameters to JSON via dict structure """
        return json.dumps(self, default=lambda x: x.__dict__)

    def to_query_string(self):
        """ Convert parameters to query string"""
        field_dict = vars(self)
        field_string = urlencode(field_dict, doseq=True)
        return f"?{field_string}"

    @classmethod
    def from_dict(cls, env):
        """Return a dict of all environment key:value pairs where the key
        matches the name of a class parameter"""
        return cls(
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )

    @classmethod
    def from_json(cls, json_data: str):
        """ Convert parameters from JSON via dict structure """
        if json_data and isinstance(json_data, str) and len(json_data) > 0:
            dict = json.loads(json_data)
            return Params.from_dict(dict)

    def fill_defaults(self):
        """Since some uses of this class want to know the difference between
        'no input' and default value, and setting defaults in class
        variable definitions would erase that difference, this
        function fills in defaults electively rather than
        automatically.  If called, don't overwrite any user input.  If
        user input is None, treat that as 'use the default' and use
        the default.  For transaction import table, use gnucash
        account labels as defaults.  For root account lists, parse to
        tuples.

        """
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
        if not self.co_label:
            self.co_label = CONST["co_label"]
        if not self.cu_label:
            self.cu_label = CONST["cu_label"]
        if not self.ds_label:
            self.ds_label = CONST["ds_label"]
        if not self.ex_label:
            self.ex_label = CONST["ex_label"]
        if not self.pe_label:
            self.pe_label = CONST["pe_label"]
        if not self.sa_label:
            self.sa_label = CONST["sa_label"]

    def __post_init__(self):
        self.co_roots = self.cleanse_account_list_input(self.co_roots)
        self.cu_roots = self.cleanse_account_list_input(self.cu_roots)
        self.ex_roots = self.cleanse_account_list_input(self.ex_roots)
        self.pe_roots = self.cleanse_account_list_input(self.pe_roots)
        self.sa_roots = self.cleanse_account_list_input(self.sa_roots)

    @classmethod
    def le_parse_qs(cls, search: str):
        """Do some extra cleanup on url string over and above what the
        built-in parser does, on fields that expect to be lists.  Specifically:
        1. Parser returns x=1,2 as {'x': '1, 2'}, but we want {'x': ['1', '2']}"""
        parsed_params: dict = {}
        raw_qs = parse_qs(
            search, max_num_fields=50
        )  # 50 is arbitrary, for DoS prevention
        for key, value_list in raw_qs.items():
            if key[-6:] == "_roots":  # These fields all expect lists.
                key_list = []
                for value in value_list:
                    if (not isinstance(value, str)) or (not len(value) > 0):
                        pass
                    if "," in value:
                        for sub_val in value.split(","):
                            if isinstance(sub_val, str) and len(sub_val) > 0:
                                key_list.append(sub_val)
                    else:
                        key_list.append(value)
                parsed_params[key] = key_list
            else:  # all other fields should have one value, in a list from parse_qs
                parsed_params[key] = value_list[0]

        return parsed_params
