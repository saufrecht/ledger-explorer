from typing import Iterable

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.loading import load_input_file

layout = html.Div(
    className="layout_box col3",
    children=[
        html.Div(
            className='ds_column',
            children=[
                html.H3('Transactions', className='col_heading', id='trans_heading'),
                dcc.Markdown('Upload a Gnucash transaction CSV export, or any CSV file with matching columns.  See [Instructions](https://github.com/saufrecht/ledger-explorer/blob/master/docs/USAGE.md) for more information.'),  # NOQA
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
                html.Div(id='trans_status',
                         children=['No transactions']),
                html.Div(id='trans_loaded_meta'),
                html.Div(id='trans_parsed_meta'),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H3('Accounts', className='col_heading', id='atree_heading'),
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
                html.Div(id='atree_status',
                         children=['No accounts']),
                html.Div(id='atree_loaded_meta'),
                html.Div(id='atree_parsed_meta'),
            ]),
        html.Div(
            className='ds_column',
            children=[
                html.H3('Custom Reporting Periods', className='col_heading', id='eras_heading'),
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
                html.Div(id='eras_status',
                         children=['No reporting periods']),
                html.Div(id='eras_loaded_meta'),
                html.Div(id='eras_parsed_meta'),
            ]),
    ])


@app.callback([Output('trans_filename', 'children'),
               Output('trans_file_node', 'children'),
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
    if len(data) > 0:
        text = text + f'Columns: {data.columns}'
        return [new_filename, data.to_json(), text, ' Select a different file', ]
    else:
        return [None, None, text, ' Select a file']


@app.callback([Output('atree_filename', 'children'),
               Output('atree_file_node', 'children'),
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


@app.callback([Output('eras_filename', 'children'),
               Output('eras_file_node', 'children'),
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


# @app.callback([Output('trans_status', 'children'),
#                Output('atree_status', 'children'),
#                Output('eras_status', 'children'),
#                Output('trans_parsed_meta', 'children'),
#                Output('atree_parsed_meta', 'children'),
#                Output('eras_parsed_meta', 'children')],
#               [Input('files_status', 'children')],
#               state=[State('data_store', 'children')])
# def update_load_status(files_status, data_store):
#     """ When the loaded files change, and the data source tab is open,
#     then presumably the files changed because of user input to the
#     tab controls, so show feedback.  If the loaded files change
#     through the URL mechanism, and the data source tab isn't open,
#     then this callback should be ignored. """

#     earliest_trans: np.datetime64 = trans['date'].min()
#     latest_trans: np.datetime64 = trans['date'].max()

#     trans_summary: str = f'File: {trans_filename} loaded, with {len(trans)} transactions'
#     files_status: str = f'{trans_filename}, {len(trans)} transactions'
#     trans_status_list: list = [f'Data loaded: {len(trans)} between {pretty_date(earliest_trans)} and {pretty_date(latest_trans)}']  # NOQA
#     first_rec = pretty_records(trans.head(3))
#     last_rec = pretty_records(trans.tail(3))
#     records: list = ['=================='] + ['first and last 3 records'] + first_rec + ['=================='] + last_rec  # NOQA
#     trans_status_list = trans_status_list + records

#     atree_summary: str = None
#     atree_status_list: list = []
#     if atree and len(atree) > 0:
#         atree_summary: str = f'{len(atree)} accounts'
#         atree_list: list = [f'Account Tree loaded: {atree_summary}, {atree.depth()} levels deep', atree.show_to_string()]  # NOQA
#         files_status = f'{files_status}, {atree_summary}.'

#     eras_summary: str = None
#     eras_status_list: list = []
#     if len(eras) > 0:
#         eras_summary: str = f'{len(eras)} reporting eras'
#         eras_status_list = [eras_summary]
#         files_status = f'{files_status}, {eras_summary}.'

#     trans_detail: list = [html.Div(children=x) for x in trans_status_list]
#     atree_detail: list = [html.Div(children=x) for x in atree_status_list]
#     eras_detail: list = [html.Div(children=x) for x in eras_status_list]

#     data = json.dumps({'trans': trans.to_json(),
#                        'eras': eras.to_json()})
#     return [data, trans_summary, atree_summary, eras_summary, files_status, trans_detail, atree_detail, eras_detail]
