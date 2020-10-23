from typing import Iterable
from numpy import datetime64
import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.loading import load_input_file
from ledgex.params import CONST, Params
from ledgex.data_store import Datastore
from ledgex.utils import require_or_raise, pretty_date


layout = (
    html.Div(
        className="layout_box",
        children=[
            html.Div(
                className="ds_column shadow",
                children=[
                    html.H2(
                        "Transactions",
                        className="col_heading",
                        id="trans_heading",
                    ),
                    dcc.Markdown(
                        """Upload a Gnucash transaction CSV export, or any CSV file with
                        matching columns.  See
                        [Instructions](https://github.com/saufrecht/ledger-explorer/blob/master/docs/USAGE.md)
                        for more information."""
                    ),
                    dcc.Upload(
                        id="trans_file",
                        className="upload_target upload_target_big",
                        children=[
                            html.Div(
                                id="trans_filename",
                                className="filename",
                                children="no transaction file",
                            ),
                            html.A(
                                id="trans_select",
                                children="Drop or Select a file",
                            ),
                        ],
                    ),
                    dcc.Input(
                        className="url_input",
                        id="trans_url",
                        persistence=True,
                        persistence_type="memory",
                        type="url",
                        value="",
                        placeholder="URL for transaction csv file",
                    ),
                ],
            ),
            html.Div(
                children=[
                    html.Div(id="trans_loaded_meta"),
                    html.Div(id="trans_status"),
                ]
            ),
            html.Div(
                className="ds_column shadow",
                children=[
                    html.H3("Columns"),
                    html.Fieldset(
                        className="field_grid field_grid4",
                        children=[
                            html.H4("Required Field"),
                            html.H4("Column Name"),
                            html.H4(id="first_row", children="First Row"),
                            html.H4(id="second_row", children="Last Row"),
                            html.Label(htmlFor="account_name_col", children="Account"),
                            dcc.Input(
                                id="account_name_col",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Account",
                                debounce=True,
                            ),
                            html.Div(className="code", id="account_row_1"),
                            html.Div(className="code", id="account_row_2"),
                            html.Label(htmlFor="amount_col", children=" Amount"),
                            dcc.Input(
                                id="amount_col",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Amount Num.",
                                debounce=True,
                            ),
                            html.Div(className="code", id="amount_row_1"),
                            html.Div(className="code", id="amount_row_2"),
                            html.Label(htmlFor="date_col", children=" Date"),
                            dcc.Input(
                                id="date_col",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Date",
                                debounce=True,
                            ),
                            html.Div(className="code", id="date_row_1"),
                            html.Div(className="code", id="date_row_2"),
                            html.Label(htmlFor="desc_col", children=" Description"),
                            dcc.Input(
                                id="desc_col",
                                type="text",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Description",
                                debounce=True,
                            ),
                            html.Div(className="code", id="desc_row_1"),
                            html.Div(className="code", id="desc_row_2"),
                            html.Label(
                                htmlFor="full_account_name_col",
                                children="Full Account Name",
                            ),
                            dcc.Input(
                                id="full_account_name_col",
                                persistence=True,
                                persistence_type="memory",
                                placeholder=CONST["fan_col"],
                                debounce=True,
                            ),
                            html.Div(className="code", id="fan_row_1"),
                            html.Div(className="code", id="fan_row_2"),
                            html.Label(
                                htmlFor="parent_col", children=" Parent Account"
                            ),
                            dcc.Input(
                                id="parent_col",
                                persistence=True,
                                persistence_type="memory",
                                placeholder=CONST["parent_col"],
                                debounce=True,
                            ),
                            html.Div(className="code", id="parent_row_1"),
                            html.Div(className="code", id="parent_row_2"),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="ds_column shadow",
                children=[
                    html.H3("Configuration"),
                    html.Fieldset(
                        className="field_grid",
                        children=[
                            html.Label(
                                htmlFor="ds_delimiter", children="Account Delimiter"
                            ),
                            dcc.Input(
                                id="ds_delimiter",
                                persistence=True,
                                persistence_type="memory",
                                placeholder=CONST["delim"],
                                debounce=True,
                            ),
                            html.Label(htmlFor="unit", children="Unit"),
                            dcc.Input(
                                id="unit",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="unit",
                                debounce=True,
                            ),
                            html.Label(htmlFor="data_title", children="Data Title"),
                            dcc.Input(
                                id="data_title",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Title",
                                debounce=True,
                            ),
                            html.Label(htmlFor="ds_label", children="DS Tab Label"),
                            dcc.Input(
                                id="ds_label",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Data Store",
                                debounce=True,
                            ),
                            html.Label(
                                htmlFor="bs_label", children="Balance Sheet Tab Label"
                            ),
                            dcc.Input(
                                id="bs_label",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Cumulative View",
                                debounce=True,
                            ),
                            html.Label(
                                htmlFor="ex_label", children="Explorer Tab Label"
                            ),
                            dcc.Input(
                                id="ex_label",
                                persistence=True,
                                persistence_type="memory",
                                placeholder="Explorer",
                                debounce=True,
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="ds_column shadow",
                children=[
                    html.H3("Accounts", className="col_heading", id="atree_heading"),
                    dcc.Upload(
                        id="atree_file",
                        className="upload_target",
                        children=[
                            html.Div(
                                id="atree_filename",
                                className="filename",
                                children="No account file",
                            ),
                            html.A(id="atree_select", children="Drop or Select a file"),
                        ],
                    ),
                    dcc.Input(
                        className="url_input",
                        id="atree_url",
                        persistence=True,
                        persistence_type="memory",
                        type="url",
                        placeholder="URL for account csv file",
                    ),
                ],
            ),
            html.Div(
                className="ds_column shadow",
                children=[
                    html.Div(id="atree_loaded_meta"),
                    html.Div(id="atree_status", children=["No accounts"]),
                    html.Pre(id="atree_display", className="code"),
                ],
            ),
            html.Div(
                className="ds_column shadow",
                children=[
                    html.H3(
                        "Custom Reporting Periods",
                        className="col_heading",
                        id="eras_heading",
                    ),
                    dcc.Upload(
                        id="eras_file",
                        className="upload_target",
                        children=[
                            html.Div(
                                id="eras_filename",
                                className="filename",
                                children="No custom reporting period file",
                            ),
                            html.A(id="eras_select", children="Drop or Select a file"),
                        ],
                    ),
                    dcc.Input(
                        className="url_input",
                        id="eras_url",
                        persistence=True,
                        persistence_type="memory",
                        type="url",
                        placeholder="URL for report era csv file",
                    ),
                ],
            ),
            html.Div(
                className="ds_column shadow",
                children=[
                    html.Div(id="eras_loaded_meta"),
                    html.Div(id="eras_status", children=["No reporting periods"]),
                ],
            ),
        ],
    ),
)


@app.callback(
    [
        Output("account_name_col", "value"),
        Output("amount_col", "value"),
        Output("date_col", "value"),
        Output("desc_col", "value"),
        Output("full_account_name_col", "value"),
        Output("data_title", "value"),
        Output("ds_delimiter", "value"),
        Output("unit", "value"),
        Output("ds_label", "value"),
        Output("bs_label", "value"),
        Output("ex_label", "value"),
    ],
    [Input("param_urlnode", "children")],
)
def url_params_to_ui(param_urlnode: str):
    require_or_raise(param_urlnode)
    params = Params.from_json(param_urlnode)
    return [
        params.account_label,
        params.amount_label,
        params.date_label,
        params.desc_label,
        params.fan_label,
        params.ds_data_title,
        params.ds_delimiter,
        params.unit,
        params.ds_label,
        params.bs_label,
        params.ex_label,
    ]


@app.callback(
    [Output("param_node", "children")],
    [
        Input("account_name_col", "value"),
        Input("amount_col", "value"),
        Input("date_col", "value"),
        Input("desc_col", "value"),
        Input("full_account_name_col", "value"),
        Input("data_title", "value"),
        Input("ds_delimiter", "value"),
        Input("unit", "value"),
        Input("ds_label", "value"),
        Input("bs_label", "value"),
        Input("ex_label", "value"),
    ],
)
def apply_settings(
    account_label: str,
    amount_label: str,
    date_label: str,
    desc_label: str,
    fan_label: str,
    ds_data_title: str,
    ds_delimiter: str,
    unit: str,
    ds_label: str,
    bs_label: str,
    ex_label: str,
) -> str:
    """Store all manually input setting information into the param node,
    which in turn will update the param store, for use during
    load
    """

    params: Params = Params(
        account_label=account_label,
        amount_label=amount_label,
        date_label=date_label,
        desc_label=desc_label,
        fan_label=fan_label,
        ds_data_title=ds_data_title,
        ds_delimiter=ds_delimiter,
        unit=unit,
        ds_label=ds_label,
        bs_label=bs_label,
        ex_label=ex_label,
    )
    return [params.to_json()]


@app.callback(
    [
        Output("trans_filename", "children"),
        Output("trans_file_node", "children"),
        Output("trans_loaded_meta", "children"),
        Output("trans_select", "children"),
    ],
    [
        Input("trans_file", "filename"),
        Input("trans_file", "contents"),
        Input("trans_url", "n_submit"),
    ],
    state=[State("trans_url", "value")],
)
def upload_trans(filename: str, content, submit: int, url: str) -> Iterable:
    """Whenever a new transaction source is provided (uploaded file, or new URL),
    upload it and provide visual feedback.
    Can't use time comparison to see which one is more recent (because dcc.Upload
    doesn't have an upload timestamp), so punt that for now; need to reload the page
    to control whether url or file takes precedence. TODO: reuse code between upload_trans,
    upload_atree, and upload_eras"""
    if (not filename or len(filename) == 0) and (not url or len(url) == 0):
        raise PreventUpdate

    new_filename, data, text = load_input_file(content, url, filename)
    if len(data) > 0:
        text = text + f"Columns: {data.columns}"
        return [
            new_filename,
            data.to_json(),
            text,
            " Select a different file",
        ]
    else:
        return [None, None, text, " Select a file"]


@app.callback(
    [
        Output("atree_filename", "children"),
        Output("atree_file_node", "children"),
        Output("atree_loaded_meta", "children"),
        Output("atree_select", "children"),
    ],
    [
        Input("atree_file", "filename"),
        Input("atree_file", "contents"),
        Input("atree_url", "n_submit"),
    ],
    state=[State("atree_url", "value")],
)
def upload_atree(filename: str, content, submit: int, url: str) -> Iterable:
    """Whenever a new atree source is provided (uploaded file, or new URL),
    upload it and provide visual feedback."""
    if (not filename or len(filename) == 0) and (not url or len(url) == 0):
        raise PreventUpdate

    new_filename, data, text = load_input_file(content, url, filename)
    if len(data) == 0:
        return [None, None, text, " Select a file"]
    else:
        return [
            new_filename,
            data.to_json(),
            text,
            " Select a different file",
        ]


@app.callback(
    [
        Output("eras_filename", "children"),
        Output("eras_file_node", "children"),
        Output("eras_loaded_meta", "children"),
        Output("eras_select", "children"),
    ],
    [
        Input("eras_file", "filename"),
        Input("eras_file", "contents"),
        Input("eras_url", "n_submit"),
    ],
    state=[State("eras_url", "value")],
)
def upload_eras(filename: str, content, submit: int, url: str) -> Iterable:
    """Whenever a new transaction source is provided (uploaded file, or new URL),
    upload it and provide visual feedback.
    Can't use time comparison to see which one is more recent (because dcc.Upload
    doesn't have an upload timestamp), so punt that for now; need to reload the page
    to control whether url or file takes precedence."""
    if (not filename or len(filename) == 0) and (not url or len(url) == 0):
        raise PreventUpdate

    new_filename, data, text = load_input_file(content, url, filename)
    if len(data) == 0:
        return [None, None, text, " Select a file"]
    else:
        return [
            new_filename,
            data.to_json(),
            text,
            " Select a different file",
        ]


@app.callback(
    [
        Output("account_row_1", "children"),
        Output("amount_row_1", "children"),
        Output("date_row_1", "children"),
        Output("desc_row_1", "children"),
        Output("fan_row_1", "children"),
        Output("parent_row_1", "children"),
        Output("account_row_2", "children"),
        Output("amount_row_2", "children"),
        Output("date_row_2", "children"),
        Output("desc_row_2", "children"),
        Output("fan_row_2", "children"),
        Output("parent_row_2", "children"),
        Output('trans_status', 'children'),
        Output('atree_status', 'children'),
        Output('atree_display', 'children'),
        Output('eras_status', 'children'),
    ],
    [Input("data_store", "children")],
    state=[State("param_store", "children")])
def update_status_on_tab(data_store: str, param_store: str):
    """ When the loaded files change, and the data source tab is open,
    then presumably the files changed because of user input to the
    tab controls, so show feedback.  If the loaded files change
    through the URL mechanism, and the data source tab isn't open,
    then this callback is ignored. """

    require_or_raise(data_store)
    datastore: Datastore() = Datastore.from_json(data_store)
    params = Params.from_json(param_store)
    trans: pd.DataFrame = datastore.trans
    require_or_raise(trans)
    trans_filename = params.ds_data_title
    c1: pd.DataFrame = trans.iloc[0]
    c2: pd.DataFrame = trans.iloc[-1]
    r1: list = [c1.account, c1.amount, c1.date, c1.get('desc'), c1.get('full account name'), c1.get('parent account')]
    r2: list = [c2.account, c2.amount, c2.date, c2.get('desc'), c2.get('full account name'), c2.get('parent account')]

    # As quick hack to get linebreaks in Dash for pre-formatted text, generate status info as lists,
    # then render lists into Divs

    earliest_trans: datetime64 = trans['date'].min()
    latest_trans: datetime64 = trans['date'].max()

    trans_summary: list = [f'{trans_filename}: {len(trans)} records loaded, between {pretty_date(earliest_trans)} and {pretty_date(latest_trans)}']  # NOQA

    atree = datastore.account_tree
    atree_summary: str = None
    atree_display: str = None
    if atree and len(atree) > 0:
        atree_summary: str = f'{len(atree)} accounts loaded, {atree.depth()} levels deep'
        atree_display: str = atree.show_to_string()

    eras = datastore.eras
    eras_summary: str = None
    if len(eras) > 0:
        eras_summary: str = f'{len(eras)} reporting eras'

    return r1 + r2 + [trans_summary, atree_summary, atree_display, eras_summary]
