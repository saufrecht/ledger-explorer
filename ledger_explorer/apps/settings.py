import json
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Input, Output
from utils import PARENT_COL, ACCOUNT_COL, FAN_COL, AMOUNT_COL, DATE_COL, DESC_COL, DELIM
from dash.exceptions import PreventUpdate

from app import app


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="flex_down",
            children=[
                html.H2('Data Fields'),
                html.Fieldset(
                    className="field_grid",
                    children=[
                        html.Div(
                            className='three_col',
                            children="If column names in the source data don't match the Fields listed, enter new column names.  Matching and renaming ignores capitalization."),  # NOQA)
                        html.H4('Column Name'),
                        html.H4(' → Field'),
                        html.Div('Read a CSV or XLS file, one row per transaction.'),
                        dcc.Input(
                            id='account_name_col',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Account',
                            debounce=True
                        ),
                        html.Label(
                            htmlFor='account_name_col',
                            children=' → Account'),
                        html.Div('required'),
                        dcc.Input(
                            id='amount_col',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Amount Num.',
                            debounce=True),
                        html.Label(
                            htmlFor='amount_col',
                            children=' → Amount'),
                        html.Div('required'),
                        dcc.Input(
                            id='date_col',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Date',
                            debounce=True),
                        html.Label(
                            htmlFor='date_col',
                            children=' → Date'),
                        html.Div('required.  parsable date, or YYYY.'),
                        dcc.Input(
                            id='desc_col',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Description',
                            debounce=True),
                        html.Label(
                            htmlFor='desc_col',
                            children=' → Description'),
                        html.Div('Label for each individual transaction (if importing Gnucash, Notes and Memo added automatically)'),  # NOQA
                        dcc.Input(
                            id='full_account_name_col',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder=FAN_COL,
                            debounce=True),
                        html.Label(
                            htmlFor='full_account_name_col',
                            children=' → Full Account Name'),
                        html.Div(['Used to determine account tree.  Full path of account, e.g., Assets:Tools:Wheelbarrow.']),  # NOQA
                        dcc.Input(
                            id='parent_col',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder=PARENT_COL,
                            debounce=True),
                        html.Label(
                            htmlFor='parent_col',
                            children=' → Parent Account'),
                        html.Div('Alternative method for account tree'),
                        html.Div(
                            className='three_col',
                            children=(f'Account tree is derived from tree source file if present, or transaction source if not.  Within each source, {FAN_COL} is preferred over "parent".')),  # NOQA
                    ])
            ]),
        html.Div(
            className="flex_down",
            children=[
                html.H2('Configuration'),
                html.Fieldset(
                    className="field_grid",
                    children=[
                        dcc.Input(
                            id='ds_delimiter',
                            persistence=True,
                            persistence_type='memory',
                            size='1',
                            placeholder=DELIM,
                            debounce=True),
                        html.Label(
                            htmlFor='ds_delimiter',
                            children='Account Delimiter'),
                        html.Div('If Full Account Names are used to generate the path, use this delimiter between each account name.'),  # NOQA
                        dcc.Input(
                            id='ds_unit',
                            size='2',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='unit',
                            debounce=True),
                        html.Label(
                            htmlFor='ds_unit',
                            children='Unit'),
                        html.Div('For data not in dollars.  E.g., in $000s, or another unit altogether.'),
                        dcc.Input(
                            id='data_title',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Title',
                            debounce=True),
                        html.Label(
                            htmlFor='data_title',
                            children='Data Title'),
                        html.Div(''),
                        dcc.Input(
                            id='ds_label',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Data Store',
                            debounce=True),
                        html.Label(
                            htmlFor='ds_label',
                            children='DS Tab Label'),
                        html.Div('Data Source Tab Label'),
                        dcc.Input(
                            id='bs_label',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Cumulative View',
                            debounce=True),
                        html.Label(
                            htmlFor='bs_label',
                            children='Balance Sheet Tab Label'),
                        html.Div('Examining cumulative data by account'),
                        dcc.Input(
                            id='ex_label',
                            size='10',
                            persistence=True,
                            persistence_type='memory',
                            placeholder='Explorer',
                            debounce=True),
                        html.Label(
                            htmlFor='ex_label',
                            children='Explorer Tab Label'),
                        html.Div('Examining transactions as flows by account and time'),
                        html.Button(
                            className='three_col',
                            children='Apply settings',
                            id='fields_reload_button'),
                    ])
            ]),
    ])


@app.callback(
    [Output('control_store', 'children')],
    [Input('account_name_col', 'value'),
     Input('amount_col', 'value'),
     Input('date_col', 'value'),
     Input('desc_col', 'value'),
     Input('full_account_name_col', 'value'),
     Input('data_title', 'value'),
     Input('ds_delimiter', 'value'),
     Input('ds_unit', 'value'),
     Input('ds_label', 'value'),
     Input('bs_label', 'value'),
     Input('ex_label', 'value')])
def apply_settings(account_n: str,
                   amount_n: str,
                   date_n: str,
                   desc_n: str,
                   fullname_n: str,
                   ds_data_title: str,
                   ds_delimiter: str,
                   ds_unit: str,
                   ds_label: str,
                   bs_label: str,
                   ex_label: str) -> str:

    """ Store all manually input setting information into the control store for use during load """

    response = {}
    col_labels = []
    # TODO: look up best practices for sanitizing user input
    if account_n and isinstance(account_n, str) and len(account_n) > 0:
        col_labels = col_labels + (account_n, ACCOUNT_COL)

    if amount_n and isinstance(amount_n, str) and len(amount_n) > 0:
        col_labels = col_labels + (amount_n, AMOUNT_COL)

    if date_n and isinstance(date_n, str) and len(date_n) > 0:
        col_labels = col_labels + (date_n, DATE_COL)

    if desc_n and isinstance(desc_n, str) and len(desc_n) > 0:
        col_labels = col_labels + (desc_n, DESC_COL)

    if fullname_n and isinstance(fullname_n, str) and len(fullname_n) > 0:
        col_labels = col_labels + (fullname_n, FAN_COL)

    if len(col_labels) > 0:
        response['col_labels'] = col_labels

    if ds_data_title and isinstance(ds_data_title, str) and len(ds_data_title) > 0:
        response['data_title'] = ds_data_title

    if ds_delimiter and isinstance(ds_delimiter, str) and len(ds_delimiter) > 0:
        response['delimiter'] = ds_delimiter

    if ds_unit and isinstance(ds_unit, str) and len(ds_unit) > 0:
        response['unit'] = ds_unit

    if ds_label and isinstance(ds_label, str) and len(ds_label) > 0:
        response['ds_label'] = ds_label

    if bs_label and isinstance(bs_label, str) and len(bs_label) > 0:
        response['bs_label'] = bs_label

    if ex_label and isinstance(ex_label, str) and len(ex_label) > 0:
        response['ex_label'] = ex_label

    if len(response) > 0:
        return [json.dumps(response)]
    else:
        raise PreventUpdate

# https://ledge.uprightconsulting.com/s/sample_transaction_data.csv',
