from dataclasses import dataclass
import json
from types import SimpleNamespace
from typing import Iterable


CONST = {'parent_col': 'parent account',  # TODO: move the column names into Trans class
         'account_col': 'account',
         'fan_col': 'full account name',
         'date_col': 'date',
         'desc_col': 'description',
         'amount_col': 'amount',
         'gc_col_labels': [('amount num.',  'amount'), ('account name', 'account')],  # defaults for gnucash
         'ex_label': 'Cash Flow',
         'bs_label': 'Balance Sheet',
         'ds_label': 'Files',
         'delim': ':',
         'max_slices': 7,
         'unit': '$',
         'leaf_suffix': ' [Leaf]',
         'other_prefix': 'Other ',
         'subtotal_suffix': ' [Subtotal]',
         'root_accounts': [{'id': 'Assets', 'flip_negative': False},
                           {'id': 'Equity', 'flip_negative': True},
                           {'id': 'Expenses', 'flip_negative': True},
                           {'id': 'Income', 'flip_negative': True},
                           {'id': 'Liabilities', 'flip_negative': True}],
         'time_res_lookup': {'era': {'abbrev': 'era',
                                     'label': 'Era'},
                             'year': {'abbrev': 'Y',
                                      'format': '%Y',
                                      'label': 'Year',
                                      'months': 12,
                                      'resample_keyword': 'A'},
                             'decade': {'abbrev': '10Y',
                                        'format': '%Y',
                                        'label': 'Decade',
                                        'months': 120,
                                        'resample_keyword': '10A'},
                             'quarter': {'abbrev': 'Q',
                                         'format': '%Y-Q%q',
                                         'label': 'Quarter',
                                         'months': 3,
                                         'resample_keyword': 'Q'},
                             'month': {'abbrev': 'Mo',
                                       'format': '%Y-%b',
                                       'label': 'Month',
                                       'months': 1,
                                       'resample_keyword': 'M'}},
         'time_res_options': [{'value': 'decade', 'label': 'Decade'},
                              {'value': 'year', 'label': 'Year'},
                              {'value': 'quarter', 'label': 'Quarter'},
                              {'value': 'month', 'label': 'Month'}],
         'time_res_era_option': {'value': 'era', 'label': 'Era'},
         'time_span_lookup': {'annual': {'label': 'Annualized', 'abbrev': ' ⁄y', 'months': 12},
                              'monthly': {'label': 'Monthly', 'abbrev': ' ⁄mo', 'months': 1}},
         'time_span_options': [{'value': 'annual', 'label': 'Annualized'},
                               {'value': 'monthly', 'label': 'Monthly'}]}


@dataclass
class Params():
    """ Class to hold everything to do with settings & controls """
    # Default to the column headings of Gnucash exports
    account_label: str = 'Account Name'
    amount_label: str = 'Amount Num.'
    date_label: str = 'Date'
    desc_label: str = 'Description'
    fan_label: str = 'Full Account Name'
    init_time_span: str = 'monthly'
    init_time_res: str = 'annual'
    ds_data_title: str = 'Ledger'
    ds_delimiter: str = CONST['delim']
    ds_unit: str = CONST['unit']
    ds_label: str = CONST['ds_label']
    bs_label: str = CONST['bs_label']
    ex_label: str = CONST['ex_label']
    ex_account_filter: Iterable[str] = ()
    bs_account_filter: Iterable[str] = ()

    @classmethod
    def parse_account_string(cls, input: str):
        """ Take a string which is a list of account names, separated by commas,
        and return it as a tuple """
        # TODO: accept [Total] as an input and return ('[Total]')
        if not isinstance(input, str):
            return ()
        input_list = input.split(',')
        stripped_list = [x.strip() for x in input_list]
        return tuple(stripped_list)

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
            return Params()
