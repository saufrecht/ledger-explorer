import dash_core_components as dcc
import dash_html_components as html
import json
import logging
from typing import Iterable, List


from dash.dependencies import Input, Output, State
from utils import load_eras, load_transactions, make_account_tree_from_trans


from app import app


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='data_tab_body',
            className="control_bar dashbox",
            children=[
                html.Fieldset([
                    html.Div([
                        html.Label(
                            htmlFor='transactions_url',
                            children='Transaction Source URL'),
                        dcc.Input(
                            id='transactions_url',
                            type='url',
                            value='http://localhost/transactions.csv',
                            placeholder='URL for transaction csv file'
                        )]),
                    html.Div([
                        html.Label(
                            htmlFor='eras_url',
                            children='Eras source URL (optional)'),
                        dcc.Input(
                            id='eras_url',
                            type='url',
                            value='http://localhost/eras.csv',
                            placeholder='URL for eras csv file'
                        )]),
                    html.Div([
                        html.Button('Load', id='data_load_button')
                    ]),
                ]),
            ]),
        html.Div(id='meta_data',
                 children=[
                 ]),
        html.Div(id='account_tree',
                 className='code',
                 children=[
                 ]),
        html.Div(id='records',
                 className='code',
                 children=[
                 ]),
    ])


@app.callback(
    [Output('data_store', 'children'),
     Output('meta_data', 'children'),
     Output('account_tree', 'children'),
     Output('records', 'children')],
    [Input('data_load_button', 'n_clicks')],
    state=[State('transactions_url', 'value'),
           State('eras_url', 'value')])
def load_data(n_clicks: int, transactions_url: str, eras_url: str) -> Iterable:
    logging.debug(f'Type: n_clicks {type(n_clicks)}')
    logging.debug(f'Type: trans {type(transactions_url)}')
    logging.debug(f'Type: eras_url {type(eras_url)}')
    trans = load_transactions(transactions_url)
    account_tree = make_account_tree_from_trans(trans)
    earliest_trans = trans['date'].min()
    latest_trans = trans['date'].max()
    eras = load_eras(eras_url, earliest_trans, latest_trans)
    data = dict(trans=trans.to_json(orient='split'),
                eras=eras.to_json(orient='split', date_format='iso'))

    meta_info: list = [f'Data loaded: {len(trans)} records',
                       f'Earliest record: {earliest_trans}',
                       f'Latest record: {latest_trans}',
                       f'Eras loaded: {len(eras)}']
    meta_html: list = [html.Div(children=x) for x in meta_info]

    records: list = ['first 5 records'] + trans.head(n=5).values.tolist() + \
        [''] + ['last 5 records'] + trans.tail(n=5).values.tolist()
    records_html: List[str] = [html.Div(children=x, className='code_row') for x in records]

    tree_records: List[str] = [f'Tree nodes: {len(account_tree)}'] + [x.tag for x in account_tree.all_nodes()]

    account_tree_html: List[str] = [html.Div(children=x, className='code_row') for x in tree_records]

    result = [json.dumps(data), meta_html, account_tree_html, records_html]

    for i, item in enumerate(result):
        logging.debug(f'Type: {i} {type(item)}')

    return result
